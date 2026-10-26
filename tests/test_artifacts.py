"""Behavioral preflight tests; every artifact and mutation lives in a temporary run."""

import hashlib
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/fulltext-literature-review/scripts/check_artifacts.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("check_artifacts", SCRIPT)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name)
        self.paper = self.run / "papers/P001.md"
        self.check = self.run / "checks/P001.md"
        self.write_report()

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_report(self, body="", paper="P001", **changes):
        meta = {"kind": "paper", "id": paper, "author": "reader-a", "revision": "r1"}
        meta.update(changes)
        self.write(self.run / f"papers/{paper}.md", self.header(meta)
                   + f'<a id="{paper}-C01"></a>\n{paper}-C01: A qualified result.\n' + body)

    @staticmethod
    def header(meta):
        return "<!-- review-meta " + json.dumps(meta) + " -->\n"

    def write_check(self, body="", **changes):
        meta = {"kind": "check", "id": "P001", "author": "verifier-b", "revision": "r1",
                "report": "papers/P001.md", "report_author": "reader-a",
                "sha256": hashlib.sha256(self.paper.read_bytes()).hexdigest()}
        meta.update(changes)
        self.write(self.check, self.header(meta) + "P001-C01: supported with stated qualification.\n" + body)

    def codes(self, result):
        return {item["code"] for item in result["issues"]}

    def test_valid_report_and_version_bound_check_with_history(self):
        self.write_check("Historical round 0 SHA-256: " + "0" * 64 + "; old revision r0.\n")
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["checked"]), 2)

    def test_damaged_markdown_locator_warns_without_rejecting_literal_quotes(self):
        self.write_report("Source P001:629?642; Figures 9?10.\n")
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertIn("encoding-suspect", self.codes(result))
        self.assertTrue(all(i["severity"] == "warning" for i in result["issues"]))
        self.write_report("Source P001:629-642; Figures 9-10.\n")
        self.assertNotIn("encoding-suspect", self.codes(CHECKER.check_run(self.run)))

    def test_literal_pipe_inside_code_breaks_table_but_escaped_pipe_passes(self):
        for value, valid in [("`P(A|B)`", False), (r"`P(A\|B)`", True)]:
            with self.subTest(value=value):
                self.write_report(f"\n| Term | Meaning |\n| --- | --- |\n| {value} | probability |\n")
                result = CHECKER.check_run(self.run)
                self.assertEqual(result["ok"], valid, result)
                self.assertEqual("table" in self.codes(result), not valid)

    def test_fenced_examples_do_not_declare_claims_or_links_or_metadata(self):
        self.write_report('```markdown\n[example](missing.md)\n<a id="P001-C01"></a>\n'
                          + self.header({"kind": "example"}) + "P999-C99\n```\n"
                          + "`[inline example](missing.md)`\n")
        self.assertTrue(CHECKER.check_run(self.run)["ok"])

    def test_unclosed_fence_is_reported(self):
        self.write_report("~~~markdown\nAn unfinished example\n")
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertIn("fence", self.codes(result))

    def test_local_links_resolve_relative_spaces_parentheses_and_url_encoding(self):
        self.write(self.run / "資料 file.md", "target")
        self.write(self.run / "figure(1).png", "image")
        self.write_report("[space](<../資料 file.md>)\n[encoded](../資料%20file.md#section)\n"
                          "![image](../figure(1).png)\n[external](https://invalid.example/path)\n")
        self.assertTrue(CHECKER.check_run(self.run)["ok"])

    def test_missing_local_link_is_an_error(self):
        self.write_report("[missing](../not-there.md)\n")
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertIn("link", self.codes(result))

    def test_run_index_links_are_checked_without_report_metadata(self):
        self.write(self.run / "run.md", "# Index\n[paper](papers/P001.md)\n")
        self.assertTrue(CHECKER.check_run(self.run)["ok"])
        self.write(self.run / "run.md", "# Index\n[check](checks/P001.md)\n")
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertEqual(self.codes(result), {"link"})

    def test_invalid_utf8_is_error_and_replacement_character_only_warning(self):
        self.paper.write_bytes(b"\xff\xfe")
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertIn("unreadable", self.codes(result))
        self.write_report("Uncertain symbol: \ufffd\n")
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertEqual([item["severity"] for item in result["issues"]], ["warning"])

    def test_duplicate_declarations_and_undeclared_references_fail(self):
        self.write_report('<a id="P001-C01"></a>\nCompare P001-C02.\n')
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertTrue({"claim-duplicate", "claim-reference"}.issubset(self.codes(result)))

    def test_current_hash_revision_and_author_binding_are_checked(self):
        for changes, code in [({"sha256": "0" * 64}, "check-hash"),
                              ({"revision": "r2"}, "check-revision"),
                              ({"report_author": "other"}, "check-author"),
                              ({"author": "reader-a"}, "check-author")]:
            with self.subTest(changes=changes):
                self.write_check(**changes)
                result = CHECKER.check_run(self.run)
                self.assertFalse(result["ok"])
                self.assertIn(code, self.codes(result))

    def test_post_check_report_mutation_invalidates_check(self):
        self.write_check()
        self.write_report("Additional qualification.\n")
        self.assertIn("check-hash", self.codes(CHECKER.check_run(self.run)))

    def test_selected_artifact_resolves_cross_paper_ids_without_future_checks(self):
        self.write_report("See P002-C01.\n")
        self.write_report(paper="P002", author="reader-b")
        result = CHECKER.check_run(self.run, "papers/P001.md")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["checked"], [str(self.paper)])
        self.assertFalse((self.run / "checks").exists())

    def test_missing_metadata_fields_and_wrong_artifact_kind_fail(self):
        self.write_report(author="", kind="synthesis")
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertTrue({"metadata-fields", "metadata-kind"}.issubset(self.codes(result)))

    def test_non_object_metadata_is_reported_without_crashing(self):
        self.write(self.paper, '<!-- review-meta [] -->\n<a id="P001-C01"></a>\n')
        result = CHECKER.check_run(self.run)
        self.assertFalse(result["ok"])
        self.assertIn("metadata", self.codes(result))

    def test_synthesis_and_its_check_bind_to_synthesis_report(self):
        meta = {"kind": "synthesis", "id": "S", "author": "synth", "revision": "r1"}
        synthesis = self.run / "synthesis.md"
        self.write(synthesis, self.header(meta) + '<a id="S-C01"></a>\nS-C01 follows P001-C01.\n')
        check_meta = {"kind": "check", "id": "S", "author": "independent", "report_author": "synth",
                      "revision": "r1", "report": "synthesis.md",
                      "sha256": hashlib.sha256(synthesis.read_bytes()).hexdigest()}
        self.write(self.run / "checks/synthesis.md", self.header(check_meta) + "S-C01: supported.\n")
        self.assertTrue(CHECKER.check_run(self.run)["ok"])

    def test_cli_exit_status_and_selected_path_boundary(self):
        process = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "--run", str(self.run)],
                                 text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)["ok"])
        result = CHECKER.check_run(self.run, "../outside.md")
        self.assertFalse(result["ok"])
        self.assertIn("artifact-path", self.codes(result))


class BoundedWorkflowTests(unittest.TestCase):
    write = ArtifactTests.write
    write_report = ArtifactTests.write_report
    write_check = ArtifactTests.write_check
    header = staticmethod(ArtifactTests.header)
    codes = ArtifactTests.codes

    def setUp(self):
        ArtifactTests.setUp(self)
        self.state = {
            "contract_version": 2, "budget_seconds": 600, "reserve_seconds": 120,
            "started_at": self.at(0), "delivered_at": None, "execution": "active",
            "artifacts": {
                "P001": {"revision": "r1", "round": 0, "repair_used": 0,
                         "verification": "passed", "stop_reason": None, "withdrawn": []},
                "S": {"revision": "r1", "round": None, "repair_used": 0,
                      "verification": "pending", "stop_reason": None, "withdrawn": []}},
            "events": [self.event(10, "reading-dispatched"), self.event(100, "reading-returned"),
                       self.event(105, "verification-ready"), self.event(110, "check-dispatched", 0),
                       self.event(150, "check-returned", 0)]}
        self.status = {"round": 0, "verification": "passed",
                       "claims": {"P001-C01": "supported"}, "withdrawn": []}
        self.write_report(contract_version=2)
        self.save_check()
        self.save_state()

    @staticmethod
    def at(seconds):
        return (datetime(2026, 10, 26, 9, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat()

    def event(self, seconds, name, round=None, artifact="P001"):
        return {"at": self.at(seconds), "artifact": artifact, "event": name,
                "agent": "verifier-b" if name.startswith("check-") else "reader-a", "round": round}

    def save_state(self):
        self.write(self.run / "run.md", "<!-- review-run " + json.dumps(self.state) + " -->\n")

    def save_check(self):
        self.write_check("<!-- review-status " + json.dumps(self.status) + " -->\n",
                         contract_version=2, revision=self.state["artifacts"]["P001"]["revision"])

    def repaired(self):
        self.state["events"] += [self.event(160, "repair-dispatched", 1),
                                 self.event(180, "repair-returned", 1),
                                 self.event(190, "check-dispatched", 1),
                                 self.event(220, "check-returned", 1)]
        self.state["artifacts"]["P001"].update(revision="r2", round=1, repair_used=1)
        self.status["round"] = 1
        self.write_report(revision="r2", contract_version=2)
        self.save_check()
        self.save_state()

    def assert_issue(self, code, artifact=None):
        result = CHECKER.check_run(self.run, artifact)
        self.assertFalse(result["ok"], result)
        self.assertIn(code, self.codes(result), result)

    def test_initial_check_and_single_repair_are_valid(self):
        initial = CHECKER.check_run(self.run)
        self.assertTrue(initial["ok"], initial)
        self.assertEqual(initial["timing"]["intervals"], [
            {"artifact": "P001", "stage": "reading", "round": None, "seconds": 90},
            {"artifact": "P001", "stage": "check", "round": 0, "seconds": 40}])
        self.assertEqual(initial["timing"]["waits"], [
            {"artifact": "P001", "round": 0, "seconds": 5}])
        self.repaired()
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertIsNone(result["timing"]["elapsed_seconds"])
        self.assertIsInstance(result["timing"]["intervals"], list)
        self.assertIsInstance(result["timing"]["waits"], list)

    def test_unbudgeted_work_can_continue_past_ten_minutes(self):
        self.state.update(budget_seconds=None, reserve_seconds=0)
        self.state["events"] += [self.event(800, "draft-dispatched", artifact="S")]
        self.save_state()
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["timing"]["over_budget"])

    def test_clock_start_is_once_only_and_preserves_prose(self):
        self.state.update(started_at=None, events=[])
        self.save_state()
        with (self.run / "run.md").open("a", encoding="utf-8") as stream:
            stream.write("Keep this scope.\n")
        result = CHECKER.record_event(self.run, "start")
        self.assertIsNotNone(CHECKER.utc_time(result["at"]))
        saved = (self.run / "run.md").read_bytes()
        with self.assertRaises(ValueError):
            CHECKER.record_event(self.run, "start")
        self.assertEqual(saved, (self.run / "run.md").read_bytes())
        self.assertIn(b"Keep this scope.", saved)

    def test_clock_records_round_and_rejects_duplicate(self):
        CHECKER.record_event(self.run, "repair-dispatched", "P001", "reader-a", 1)
        state = CHECKER.json_comment({"text": (self.run / "run.md").read_text(encoding="utf-8")}, "review-run")
        self.assertEqual(state["artifacts"]["P001"]["repair_used"], 1)
        self.assertEqual(state["events"][-1]["event"], "repair-dispatched")
        saved = (self.run / "run.md").read_bytes()
        with self.assertRaises(ValueError):
            CHECKER.record_event(self.run, "repair-dispatched", "P001", "reader-a", 1)
        self.assertEqual(saved, (self.run / "run.md").read_bytes())

    def test_failed_delivery_does_not_stamp_or_reset_retry_limit(self):
        saved = (self.run / "run.md").read_bytes()
        result = CHECKER.record_event(self.run, "delivery")
        self.assertFalse(result["ok"])
        self.assertIn("incomplete-delivery", self.codes(result))
        self.assertEqual(saved, (self.run / "run.md").read_bytes())
        CHECKER.record_event(self.run, "delivery")
        self.assertIn("mechanical-limit", self.codes(CHECKER.record_event(self.run, "delivery")))

    def test_delivery_clock_follows_successful_final_validation(self):
        with patch.object(CHECKER, "checkpoint_check", return_value={"ok": True}) as check:
            result = CHECKER.record_event(self.run, "delivery")
        check.assert_called_once_with(self.run, None, "final", views=True, complete=True)
        state = CHECKER.json_comment({"text": (self.run / "run.md").read_text(encoding="utf-8")}, "review-run")
        self.assertEqual(state["delivered_at"], result["at"])
        self.assertEqual(state["execution"], "finished")

    def test_revision_number_does_not_consume_repair_round(self):
        self.state["artifacts"]["P001"]["revision"] = "r2"
        self.write_report(revision="r2", contract_version=2)
        self.save_check()
        self.save_state()
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)

    def test_second_repair_and_third_check_are_rejected(self):
        self.repaired()
        self.state["artifacts"]["P001"].update(round=2, repair_used=2)
        self.status["round"] = 2
        self.state["events"] += [self.event(230, "repair-dispatched", 2),
                                 self.event(250, "repair-returned", 2),
                                 self.event(260, "check-dispatched", 2),
                                 self.event(280, "check-returned", 2)]
        self.save_state()
        self.save_check()
        self.assert_issue("workflow-round")

    def test_duplicate_dispatch_cannot_reset_round_by_reusing_number(self):
        self.state["events"].append(self.event(170, "check-dispatched", 0))
        self.save_state()
        self.assert_issue("workflow-state")

    def test_round_limit_cannot_be_claimed_without_a_repair(self):
        self.state["artifacts"]["P001"].update(verification="needs-confirmation", stop_reason="round-limit")
        self.save_state()
        self.assert_issue("workflow-state")

    def test_repair_in_progress_cannot_keep_a_pass(self):
        self.state["events"].append(self.event(160, "repair-dispatched", 1))
        self.state["artifacts"]["P001"]["repair_used"] = 1
        self.save_state()
        self.assert_issue("workflow-status")

    def test_dispatch_identity_must_match_independent_verifier(self):
        for agent in ("reader-a", "unrelated-verifier"):
            with self.subTest(agent=agent):
                self.state["events"][3]["agent"] = agent
                self.save_state()
                self.assert_issue("workflow-state")

    def test_missing_or_inconsistent_repair_events_are_rejected(self):
        self.repaired()
        for remove in ("repair-dispatched", "repair-returned"):
            with self.subTest(remove=remove):
                original = self.state["events"]
                self.state["events"] = [event for event in original if event["event"] != remove]
                self.save_state()
                self.assert_issue("workflow-state")
                self.state["events"] = original

    def test_bad_schema_reports_errors_instead_of_crashing(self):
        original = copy.deepcopy(self.state)
        for field, value in (("artifacts", []), ("events", {}), ("events", [None]),
                             ("budget_seconds", "600"), ("reserve_seconds", -1),
                             ("started_at", "not-a-date")):
            with self.subTest(field=field, value=value):
                self.state = copy.deepcopy(original)
                self.state[field] = value
                self.save_state()
                self.assert_issue("workflow-state")

    def test_v2_requires_coordinator_state_but_legacy_does_not(self):
        (self.run / "run.md").unlink()
        self.assert_issue("workflow-missing")
        self.write_report()
        self.write_check()
        self.assertTrue(CHECKER.check_run(self.run)["ok"])

    def test_withdrawal_requires_current_claim_and_run_to_agree(self):
        self.status.update(verification="needs-confirmation", withdrawn=["P001-C01"])
        self.save_check()
        self.assert_issue("current-status")
        self.status["claims"]["P001-C01"] = "withdrawn"
        self.save_check()
        self.assert_issue("workflow-status")
        self.state["artifacts"]["P001"].update(verification="needs-confirmation",
                                               withdrawn=["P001-C01"], stop_reason="source-gap")
        self.save_state()
        self.assertTrue(CHECKER.check_run(self.run)["ok"])

    def test_current_status_must_account_for_all_declared_claims(self):
        self.status["claims"] = {}
        self.save_check()
        self.assert_issue("current-status")

    def test_final_deadline_delivery_may_include_unwritten_pending_artifacts(self):
        self.state.update(delivered_at=self.at(600), execution="finished")
        self.state["artifacts"]["S"]["stop_reason"] = "deadline"
        self.state["artifacts"]["P002"] = {
            "revision": "r1", "round": None, "repair_used": 0, "verification": "pending",
            "stop_reason": "deadline", "withdrawn": []}
        self.save_state()
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["timing"]["elapsed_seconds"], 600)
        self.assertFalse(result["timing"]["over_budget"])

    def test_missing_report_or_check_cannot_be_declared_passed(self):
        self.check.unlink()
        self.assert_issue("workflow-status")
        self.paper.unlink()
        self.assert_issue("workflow-status")

    def test_visible_revision_label_is_checked_before_handoff(self):
        for label in ("Revision: r0\n", "| Revision | r0 |\n"):
            with self.subTest(label=label):
                self.write_report(label, contract_version=2)
                self.assert_issue("revision-label", "papers/P001.md")
        self.write_report("Revision: r1\n", contract_version=2)
        self.assertTrue(CHECKER.check_run(self.run, "papers/P001.md")["ok"])

    def test_worker_handoff_can_precede_coordinator_version_reconciliation(self):
        self.write_report(revision="r2", contract_version=2)
        self.write_check("<!-- review-status " + json.dumps(self.status) + " -->\n",
                         contract_version=2, revision="r2")
        result = CHECKER.check_run(self.run, "checks/P001.md")
        self.assertTrue(result["ok"], result)
        self.assert_issue("workflow-version")

    def test_no_new_reading_or_repairs_during_delivery_reserve(self):
        self.state["artifacts"]["P002"] = {
            "revision": "r1", "round": None, "repair_used": 0, "verification": "pending",
            "stop_reason": None, "withdrawn": []}
        for name, round in (("reading-dispatched", None), ("repair-dispatched", 1)):
            with self.subTest(name=name):
                original = self.state["events"]
                artifact = "P002" if name == "reading-dispatched" else "P001"
                self.state["events"] = original + [self.event(480, name, round, artifact)]
                self.save_state()
                self.assert_issue("workflow-deadline")
                self.state["events"] = original

    def test_no_check_dispatch_at_deadline(self):
        self.state["events"].append(self.event(600, "check-dispatched", 1))
        self.save_state()
        self.assert_issue("workflow-deadline")

    def test_late_return_records_delay_without_reopening_work(self):
        self.state.update(delivered_at=self.at(610), execution="finished")
        self.state["artifacts"]["S"]["stop_reason"] = "deadline"
        self.state["events"].append(self.event(620, "late-return"))
        self.save_state()
        result = CHECKER.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["timing"]["elapsed_seconds"], 610)
        self.assertTrue(result["timing"]["over_budget"])

    def test_invalid_event_order_and_naive_timestamps_fail(self):
        original = copy.deepcopy(self.state["events"])
        cases = [list(reversed(original)),
                 [self.event(5, "check-returned", 0)] + original,
                 [{**original[0], "at": "2026-10-26T09:00:10"}] + original[1:]]
        for events in cases:
            with self.subTest(events=events):
                self.state["events"] = events
                self.save_state()
                self.assert_issue("workflow-state")


if __name__ == "__main__":
    unittest.main()
