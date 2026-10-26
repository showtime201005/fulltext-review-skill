"""JSON behavior tests use temporary sources; no historical runs are rewritten."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / ".agents/skills/fulltext-literature-review/scripts"
sys.path.insert(0, str(SCRIPTS))
import artifacts
import check_artifacts
import sources


class JsonArtifactTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name)
        self.source = self.run / "input.md"
        self.source.write_text("# Test\nA improves 5 points on task X.\nOnly two trials.\nNo gain on task Y.\n", encoding="utf-8")
        self.manifest = self.run / "sources.json"
        sources.index_sources(SimpleNamespace(manifest=str(self.manifest), kind="paper", paper=None,
                              base=str(self.run), encoding="utf-8", refresh=False, paths=["input.md"]))
        self.sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.evidence = {"source": "P001", "sha256": self.sha, "start": 2, "end": 3,
                         "locator": "Test, results", "excerpt": "A improves 5 points on task X. Only two trials.",
                         "reasoning": "The stated gain is limited to task X and two trials."}
        self.paper = {
            "schema_version": 1,
            "meta": {"contract_version": 2, "kind": "paper", "id": "P001", "author": "reader", "revision": "r1"},
            "title": "Small experiment", "paper_type": "empirical",
            "bibliography": dict(authors=None, year=None, venue=None, identifier=None),
            "question": "Does A improve results?", "methods": [], "comparison_claim_ids": ["P001-C01"],
            "claims": [{"id": "P001-C01", "kind": "author claim", "role": "finding",
                        "statement": "A improves 5 points on task X.", "conditions": "Task X; two trials.",
                        "uncertainty": "No dispersion reported.", "evidence": [copy.deepcopy(self.evidence)],
                        "results": [dict(metric="score", value="5", unit="points", dataset="task X",
                                         comparison="baseline", setting="two trials; dispersion not reported")]}],
            "coverage": {"status": "complete", "understanding": "resolved", "observations": [
                dict(source="P001", sha256=self.sha, start=1, end=4, action="test fixture read", confirmed=True,
                     note="Small positive result on X; negative result on Y.")]},
            "issues": []}
        self.paper_path = self.run / "papers/P001.json"
        self.check_path = self.run / "checks/P001.json"
        self.save(self.paper_path, self.paper)
        self.finding = {"claim_id": "P001-C01", "excerpt": "A improves 5 points on task X.",
                        "claimed_locator": "P001 lines 2-3", "inspected": [copy.deepcopy(self.evidence)],
                        "verdict": "supported", "severity": "none", "reason": "Matches the supplied text with its restriction."}
        self.check = {
            "schema_version": 1,
            "meta": {"contract_version": 2, "kind": "check", "id": "P001", "author": "checker",
                     "report_author": "reader", "report": "papers/P001.json", "revision": "r1", "sha256": self.paper_hash()},
            "verification": "passed", "withdrawals": [], "rounds": [
                {"round": 0, "revision": "r1", "sha256": self.paper_hash(), "findings": [copy.deepcopy(self.finding)],
                 "carry_forward": [], "coverage_findings": [dict(location="P001 lines 1-4", verdict="supported",
                     severity="none", reason="Synthetic schema fixture; coverage accounted for.")]}]}
        self.save(self.check_path, self.check)
        self.state = {
            "contract_version": 2, "budget_seconds": 600, "reserve_seconds": 120,
            "started_at": "2026-10-26T00:00:00Z", "delivered_at": None, "execution": "active",
            "artifacts": {"P001": dict(revision="r1", round=0, repair_used=0, verification="passed", stop_reason=None, withdrawn=[])},
            "events": [dict(at=f"2026-10-26T00:00:{i * 10:02d}Z", artifact="P001", event=event,
                            agent="reader" if i < 3 else "checker", round=None if i < 3 else 0)
                       for i, event in enumerate(["reading-dispatched", "reading-returned", "check-dispatched", "check-returned"], 1)]}
        self.save_state()

    def save(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def save_state(self):
        (self.run / "run.md").write_text(artifacts.comment("review-run", self.state) + "\n", encoding="utf-8")

    def paper_hash(self):
        return hashlib.sha256(self.paper_path.read_bytes()).hexdigest()

    def coverage(self):
        return sources.coverage(SimpleNamespace(manifest=str(self.manifest), paper="P001", report=str(self.paper_path)))[0]

    def preflight(self, artifact=None):
        return check_artifacts.check_run(self.run, artifact)

    def test_focused_check_keeps_secondary_claim_pending_without_claiming_full_pass(self):
        secondary = copy.deepcopy(self.paper["claims"][0])
        secondary["id"] = "P001-C02"
        self.paper["claims"].append(secondary)
        self.save(self.paper_path, self.paper)
        finding = copy.deepcopy(self.finding)
        finding.update(claim_id="P001-C02", verdict="pending", inspected=[],
                       reason="Secondary detail outside focused verification scope.")
        self.check["rounds"][0]["findings"].append(finding)
        self.check["verification"] = "needs-confirmation"
        self.check["meta"]["sha256"] = self.paper_hash()
        self.check["rounds"][0]["sha256"] = self.paper_hash()
        self.save(self.check_path, self.check)
        self.state["artifacts"]["P001"].update(verification="needs-confirmation", stop_reason="scope")
        self.save_state()
        self.assertTrue(self.preflight()["ok"])
        self.assertEqual(artifacts.current_status(self.check)["claims"]["P001-C02"], "pending")
        self.check["verification"] = "passed"
        with self.assertRaises(ValueError):
            artifacts.validate(self.check)

    def test_scope_stop_reason_cannot_describe_a_full_pass(self):
        self.state["artifacts"]["P001"]["stop_reason"] = "scope"
        self.save_state()
        self.assertFalse(self.preflight()["ok"])

    def test_completeness_gate_accepts_disclosed_limits_but_requires_inventory(self):
        # Other preflight gates validate content; this exercises the completeness gate.
        self.state["artifacts"]["S"] = dict(self.state["artifacts"]["P001"], verification="needs-confirmation", stop_reason="source-gap")
        self.state["events"].append(dict(at="2026-10-26T00:01:00Z", artifact="S",
                                         event="check-returned", agent="checker", round=0))
        (self.run / "synthesis.md").write_text("Qualified synthesis", encoding="utf-8")
        self.save(self.run / "checks/synthesis.json", {})
        self.save_state()
        self.assertTrue(check_artifacts.require_complete(self.run, {"ok": True, "issues": []})["ok"])
        self.state["artifacts"]["P002"] = dict(self.state["artifacts"]["P001"])
        self.save_state()
        self.assertFalse(check_artifacts.require_complete(self.run, {"ok": True, "issues": []})["ok"])

    def test_source_replacement_character_is_allowed_only_in_excerpt(self):
        data = copy.deepcopy(self.paper)
        data["claims"][0]["evidence"][0]["excerpt"] = "source damage: \ufffd"
        artifacts.validate(data)
        data["claims"][0]["statement"] = "new damage: \ufffd"
        with self.assertRaises(ValueError):
            artifacts.validate(data)

    def test_check_can_quote_corrupted_locator_without_authoring_one(self):
        data = copy.deepcopy(self.check)
        data["rounds"][0]["findings"][0]["excerpt"] = "Damaged input locator: 629?642"
        artifacts.validate(data)
        for field in ("reason", "claimed_locator"):
            broken = copy.deepcopy(data)
            broken["rounds"][0]["findings"][0][field] = "New damaged locator: 629?642"
            with self.assertRaises(ValueError):
                artifacts.validate(broken)

    def test_full_run_and_generated_views_do_not_duplicate_claims(self):
        result = self.preflight()
        self.assertTrue(result["ok"], result)
        for path in (self.paper_path, self.check_path):
            artifacts.write_markdown(path, artifacts.render(artifacts.load(path)))
        result = self.preflight()
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["checked"]), 3)
        self.assertTrue(self.coverage()["ok"])

    def test_render_is_deterministic_and_does_not_change_check_binding(self):
        before = self.paper_hash()
        text = artifacts.render(self.paper)
        target = artifacts.write_markdown(self.paper_path, text)
        first = target.read_bytes()
        artifacts.write_markdown(self.paper_path, text)
        self.assertEqual(first, target.read_bytes())
        self.assertEqual(before, self.paper_hash())
        target.write_text(target.read_text(encoding="utf-8") + "\nPresentation edit.\n", encoding="utf-8")
        self.assertTrue(self.preflight()["ok"])
        artifacts.write_markdown(self.paper_path, text)
        self.assertEqual(first, target.read_bytes())

    def test_renderer_refuses_handwritten_markdown(self):
        target = self.paper_path.with_suffix(".md")
        target.write_text("User authored report", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "non-generated"):
            artifacts.write_markdown(self.paper_path, artifacts.render(self.paper))
        self.assertEqual(target.read_text(), "User authored report")

    def test_json_change_invalidates_check_even_without_revision_change(self):
        self.paper["claims"][0]["conditions"] += " Additional qualification."
        self.save(self.paper_path, self.paper)
        result = self.preflight()
        self.assertFalse(result["ok"])
        self.assertIn("check-hash", {i["code"] for i in result["issues"]})

    def test_author_and_report_binding_are_enforced(self):
        for key, value in (("author", "reader"), ("report_author", "wrong"), ("report", "../outside.json")):
            with self.subTest(key=key):
                check = copy.deepcopy(self.check)
                check["meta"][key] = value
                self.save(self.check_path, check)
                self.assertFalse(self.preflight("checks/P001.json")["ok"])

    def test_json_schema_rejects_wrong_types_unknown_fields_and_duplicate_ids(self):
        mutations = [lambda d: d.update(schema_version=True), lambda d: d.update(extra="silently lost"),
                     lambda d: d["coverage"].update(observations=None),
                     lambda d: d["claims"].append(copy.deepcopy(d["claims"][0])),
                     lambda d: d["comparison_claim_ids"].append("P001-C99"),
                     lambda d: d["claims"][0].update(id="P002-C01"),
                     lambda d: d["claims"][0]["evidence"][0].update(start=True)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                doc = copy.deepcopy(self.paper)
                mutation(doc)
                with self.assertRaises(ValueError):
                    artifacts.validate(doc)

    def test_duplicate_json_keys_and_nonfinite_constants_are_rejected(self):
        for text in ('{"meta": {}, "meta": {}}', '{"schema_version": NaN}'):
            self.paper_path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                artifacts.load(self.paper_path)
            self.assertFalse(self.preflight("papers/P001.json")["ok"])

    def test_source_hash_and_locator_boundaries(self):
        for change in (dict(sha256="0" * 64), dict(end=90), dict(source="P001-T999")):
            paper = copy.deepcopy(self.paper)
            paper["claims"][0]["evidence"][0].update(change)
            self.save(self.paper_path, paper)
            self.assertFalse(self.preflight("papers/P001.json")["ok"])

    def test_coverage_missing_ranges_and_changed_bytes_fail(self):
        self.paper["coverage"]["observations"][0]["end"] = 3
        self.save(self.paper_path, self.paper)
        self.assertFalse(self.coverage()["ok"])
        self.paper["coverage"]["observations"][0]["end"] = 4
        self.save(self.paper_path, self.paper)
        self.source.write_text("Changed", encoding="utf-8")
        self.assertFalse(self.coverage()["ok"])

    def test_image_observation_requires_actual_registered_view_attestation(self):
        image = self.run / "figure.png"
        image.write_bytes(b"test image bytes, not an actual viewing test")
        sources.index_sources(SimpleNamespace(manifest=str(self.manifest), kind="image", paper="P001",
                              base=str(self.run), encoding="utf-8", refresh=False, paths=["figure.png"]))
        self.assertFalse(self.coverage()["ok"])
        self.paper["coverage"]["observations"].append(dict(source="P001-I001", sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                         action="synthetic test attestation", confirmed=True, note="Fixture; no real image inspection claimed."))
        self.save(self.paper_path, self.paper)
        self.assertTrue(self.coverage()["ok"])
        self.paper["coverage"]["observations"][-1]["start"] = 1
        with self.assertRaises(ValueError):
            artifacts.validate(self.paper)

    def test_incomplete_empty_report_is_allowed_but_cannot_pass_check(self):
        self.paper.update(claims=[], comparison_claim_ids=[])
        self.paper["coverage"].update(status="incomplete", observations=[])
        artifacts.validate(self.paper)
        self.check["rounds"][0]["findings"] = []
        with self.assertRaises(ValueError):
            artifacts.validate(self.check)

    def test_open_gap_cannot_be_declared_complete(self):
        self.paper["issues"] = [dict(id="gap1", category="coverage", location="missing figure", description="Unavailable",
                                    severity="major", claim_ids=[], impact="Unseen result", status="open")]
        with self.assertRaises(ValueError):
            artifacts.validate(self.paper)
        self.paper["coverage"]["status"] = "incomplete"
        artifacts.validate(self.paper)

    def test_supported_requires_original_evidence_and_coverage_assessment(self):
        for mutation in (lambda d: d["rounds"][0]["findings"][0].update(inspected=[]),
                         lambda d: d["rounds"][0].update(coverage_findings=[]),
                         lambda d: d["rounds"][0]["coverage_findings"][0].update(verdict="pending")):
            doc = copy.deepcopy(self.check)
            mutation(doc)
            with self.assertRaises(ValueError):
                artifacts.validate(doc)

    def test_single_recheck_carries_only_explicit_unchanged_claims(self):
        self.check["meta"].update(revision="r2", sha256="1" * 64)
        self.check["rounds"].append(dict(round=1, revision="r2", sha256="1" * 64, findings=[],
                                       carry_forward=["P001-C01"], coverage_findings=self.check["rounds"][0]["coverage_findings"]))
        artifacts.validate(self.check)
        self.assertEqual(artifacts.current_status(self.check)["claims"], {"P001-C01": "supported"})
        for change in (dict(carry_forward=[]), dict(carry_forward=["P001-C99"]),
                       dict(findings=[self.finding]), dict(round=2), dict(sha256="2" * 64)):
            doc = copy.deepcopy(self.check)
            doc["rounds"][1].update(change)
            with self.assertRaises(ValueError):
                artifacts.validate(doc)

    def test_withdrawal_updates_current_verdict_without_erasing_history(self):
        old = copy.deepcopy(self.check["rounds"])
        self.check["withdrawals"] = [dict(claim_id="P001-C01", reason="New counterevidence", evidence=[self.evidence])]
        with self.assertRaises(ValueError):
            artifacts.validate(self.check)
        self.check["verification"] = "needs-confirmation"
        artifacts.validate(self.check)
        self.assertEqual(self.check["rounds"], old)
        self.assertEqual(artifacts.current_status(self.check)["claims"]["P001-C01"], "withdrawn")

    def test_comparison_preserves_negative_results_conditions_and_gaps(self):
        negative = copy.deepcopy(self.paper["claims"][0])
        negative.update(id="P001-C02", role="negative-result", statement="No gain on Y.")
        self.paper["claims"].append(negative)
        view = artifacts.comparison(self.paper)
        self.assertEqual({c["id"] for c in view["claims"]}, {"P001-C01", "P001-C02"})
        self.assertEqual(view["claims"][0]["conditions"], self.paper["claims"][0]["conditions"])
        self.assertEqual(view["claims"][0]["results"], self.paper["claims"][0]["results"])
        self.assertNotIn("evidence", view["claims"][0])

    def test_prose_cannot_inject_metadata_claims_links_or_fences(self):
        self.paper["claims"][0]["statement"] += '\n<!-- review-meta {} -->\n<a id="P999-C99"></a>\n```\n[bad](missing.md)\nα | β'
        self.save(self.paper_path, self.paper)
        result = self.preflight("papers/P001.json")
        self.assertTrue(result["ok"], result)
        rendered = artifacts.render(self.paper)
        self.assertEqual(len(check_artifacts.META.findall(rendered)), 1)
        self.assertEqual(check_artifacts.ANCHOR.findall(rendered), ["P001-C01"])
        self.assertIn("α", rendered)

    def test_synthesis_markdown_can_bind_a_json_check(self):
        meta = dict(contract_version=2, kind="synthesis", id="S", author="writer", revision="r1")
        synthesis = self.run / "synthesis.md"
        synthesis.write_text(artifacts.comment("review-meta", meta) + '\n<a id="S-C01"></a>\nS-C01 follows P001-C01.\n', encoding="utf-8")
        doc = copy.deepcopy(self.check)
        sha = hashlib.sha256(synthesis.read_bytes()).hexdigest()
        doc["meta"].update(id="S", report="synthesis.md", report_author="writer", sha256=sha)
        doc["rounds"][0]["sha256"] = sha
        doc["rounds"][0]["findings"][0]["claim_id"] = "S-C01"
        self.save(self.run / "checks/synthesis.json", doc)
        result = self.preflight("checks/synthesis.json")
        self.assertTrue(result["ok"], result)

    def test_cli_validate_render_compare_and_invalid_input(self):
        for command in ("validate", "render", "compare"):
            result = subprocess.run([sys.executable, str(SCRIPTS / "artifacts.py"), command, str(self.paper_path)],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), list)
        self.paper_path.write_text("[]", encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "artifacts.py"), "validate", str(self.paper_path)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_encoding_damage_is_rejected_and_unicode_survives_rendering(self):
        for damaged in ("difference ?0.06", "0.61?0.67", "bad \ufffd"):
            self.paper["claims"][0]["statement"] = damaged
            with self.assertRaisesRegex(ValueError, "encoding damage"):
                artifacts.validate(self.paper)
        text = "Does it improve? Difference \u22120.06; lines 13\u201315."
        self.paper["claims"][0]["statement"] = text
        self.save(self.paper_path, self.paper)
        loaded = artifacts.load(self.paper_path)
        self.assertEqual(loaded["claims"][0]["statement"], text)
        target = artifacts.write_markdown(self.paper_path, artifacts.render(loaded))
        self.assertIn("\u22120", target.read_text(encoding="utf-8"))
        self.assertIn("13\u201315", target.read_text(encoding="utf-8"))

    def test_directory_render_includes_late_synthesis_check_and_detects_stale_views(self):
        self.test_synthesis_markdown_can_bind_a_json_check()
        result = subprocess.run([sys.executable, str(SCRIPTS / "artifacts.py"), "render", str(self.run)],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.run / "checks/synthesis.md"
        self.assertTrue(target.exists())
        paths = artifacts.artifact_paths([self.run])
        artifacts.check_views(paths)
        target.unlink()
        with self.assertRaisesRegex(ValueError, "Missing or stale"):
            artifacts.check_views(paths)
        artifacts.write_markdown(self.run / "checks/synthesis.json",
                                 artifacts.render(artifacts.load(self.run / "checks/synthesis.json")))
        target.write_text(target.read_text(encoding="utf-8") + "stale", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Missing or stale"):
            artifacts.check_views(paths)

    def test_checkpoint_second_failure_stays_exhausted_after_file_is_fixed(self):
        self.paper_path.write_text("[]", encoding="utf-8")
        for _ in range(2):
            self.assertFalse(check_artifacts.checkpoint_check(self.run, "papers/P001.json", "P001-reader-r1")["ok"])
        self.save(self.paper_path, self.paper)
        result = check_artifacts.checkpoint_check(self.run, "papers/P001.json", "P001-reader-r1")
        self.assertFalse(result["ok"])
        self.assertEqual(result["issues"][0]["code"], "mechanical-limit")
        self.assertEqual(len((self.run / "preflight-attempts.jsonl").read_text().splitlines()), 2)

    def test_checkpoint_allows_one_successful_correction_for_missing_views(self):
        self.assertFalse(check_artifacts.checkpoint_check(self.run, None, "final", views=True)["ok"])
        for path in artifacts.artifact_paths([self.run]):
            artifacts.write_markdown(path, artifacts.render(artifacts.load(path)))
        self.assertTrue(check_artifacts.checkpoint_check(self.run, None, "final", views=True)["ok"])


class LeanArtifactTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name)
        self.source = self.run / "input.md"
        self.source.write_text("# Test\nA improves 5 points.\nOnly two trials.\n", encoding="utf-8")
        (self.run / "figure.png").write_bytes(b"fixture-image")
        manifest = str(self.run / "sources.json")
        for kind, paths, paper in (("paper", ["input.md"], None), ("image", ["figure.png"], "P001")):
            sources.index_sources(SimpleNamespace(manifest=manifest, kind=kind, paper=paper,
                                  base=str(self.run), encoding="utf-8", refresh=False, paths=paths))
        (self.run / "run.md").write_text(artifacts.comment("review-run", {"contract_version": 3}) + "\n", encoding="utf-8")
        self.evidence = {"source": "P001", "locator": "Results", "start": 2, "end": 3}
        self.paper = {"schema_version": 2,
            "meta": {"contract_version": 3, "kind": "paper", "id": "P001", "author": "reader", "revision": "r1"},
            "title": "Small experiment", "question": "Does A improve?", "methods": "Two trial comparison.",
            "claims": [{"id": "P001-C01", "statement": "A improves 5 points.", "conditions": "Two trials.",
                        "uncertainty": "", "evidence": [copy.deepcopy(self.evidence)]}], "limitations": ["Small sample."],
            "coverage": {"observations": [
                {"source": "P001", "start": 1, "end": 3, "action": "read fixture", "confirmed": True, "note": "Results and limits read."},
                {"source": "P001-I001", "start": None, "end": None, "action": "view fixture", "confirmed": True, "note": "Figure observed."}], "gaps": []}}
        self.path = self.run / "papers/P001.json"
        artifacts.atomic_json(self.path, self.paper)
        artifacts.prepare(self.path)
        self.synthesis = self.run / "synthesis.md"
        self.synthesis.write_text(artifacts.comment("review-meta", {"contract_version": 3, "kind": "synthesis", "id": "S", "author": "coordinator", "revision": "r1"}) +
            '\n# Synthesis\n\n<a id="S-C01"></a>\nThe P001 experiment reports a five-point increase in the measured outcome. This small two-trial result supports only the reported setting; the corpus cannot establish broader effectiveness. See [paper](papers/P001.md#P001-C01).\n', encoding="utf-8")
        self.finish_check(self.path, "P001-C01")
        self.finish_check(self.synthesis, "S-C01")
        artifacts.prepare(self.path)

    def finish_check(self, path, ident):
        target = artifacts.start_check(path, "checker")
        check = artifacts.load(target)
        check["findings"] = [{"claim_id": ident, "verdict": "supported", "inspected": [copy.deepcopy(self.evidence)], "reason": "Matches the original results and trial limit."}]
        check["completed"] = True
        artifacts.atomic_json(target, check)
        artifacts.prepare(target)
        return target

    def test_basic_completion_without_event_journal_and_image_null_lines(self):
        paper = artifacts.load(self.path)
        self.assertNotIn("start", paper["coverage"]["observations"][1])
        result = check_artifacts.check_run(self.run)
        self.assertTrue(result["ok"], result)
        self.assertEqual(set(result["gates"]), {"read_complete", "reports_present", "core_checked"})
        delivered = check_artifacts.record_event(self.run, "delivery")
        self.assertTrue(delivered["ok"], delivered)
        self.assertIn('"delivery": "complete"', (self.run / "run.md").read_text())

    def test_broken_check_does_not_prevent_rendering_reports(self):
        (self.run / "checks/P001.json").write_text("{broken", encoding="utf-8")
        self.path.with_suffix(".md").unlink()
        result = subprocess.run([sys.executable, str(SCRIPTS / "artifacts.py"), "render", str(self.run)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(self.path.with_suffix(".md").exists())
        self.assertTrue(self.synthesis.exists())
        self.assertIn("pending", self.path.with_suffix(".md").read_text())
        self.assertNotIn("Expecting property name", self.path.with_suffix(".md").read_text())
        self.assertIn("Independent check is unavailable", self.path.with_suffix(".md").read_text())
        self.assertFalse(check_artifacts.check_run(self.run)["gates"]["core_checked"])

    def test_changed_content_and_source_cannot_keep_old_support(self):
        paper = artifacts.load(self.path)
        paper["claims"][0]["statement"] = "A improves 500 points."
        artifacts.atomic_json(self.path, paper)
        self.assertFalse(artifacts.check_assessment(self.run, self.path)["completed"])
        target = artifacts.start_check(self.path, "checker")
        self.assertEqual(artifacts.load(target)["findings"][0]["verdict"], "pending")
        self.source.write_text("# Test\nChanged source result.\nOnly two trials.\n", encoding="utf-8")
        result = artifacts.prepare(self.path)
        self.assertTrue(result["warnings"])
        self.assertFalse(check_artifacts.check_run(self.run)["gates"]["read_complete"])

    def test_invalid_paper_locator_is_pending_and_requires_disclosure(self):
        paper = artifacts.load(self.path)
        paper["claims"][0]["evidence"][0]["end"] = 99
        artifacts.atomic_json(self.path, paper)
        self.finish_check(self.path, "P001-C01")
        artifacts.prepare(self.path)
        self.assertFalse(check_artifacts.check_run(self.run)["gates"]["core_checked"])
        self.assertIn("pending", self.path.with_suffix(".md").read_text())
        paper["claims"][0]["uncertainty"] = "The original locator is invalid; this reported result remains unconfirmed."
        artifacts.atomic_json(self.path, paper)
        self.finish_check(self.path, "P001-C01")
        artifacts.prepare(self.path)
        self.finish_check(self.synthesis, "S-C01")
        self.assertTrue(check_artifacts.check_run(self.run)["gates"]["core_checked"])

    def test_synthesis_check_expires_when_upstream_check_changes(self):
        check_path = self.run / "checks/P001.json"
        check = artifacts.load(check_path)
        check["findings"][0]["reason"] = "Updated source interpretation."
        artifacts.atomic_json(check_path, check)
        result = artifacts.check_assessment(self.run, self.synthesis)
        self.assertFalse(result["completed"])
        self.assertIn("Upstream", result["issues"][0])
        restarted = artifacts.start_check(self.synthesis, "checker")
        self.assertEqual(artifacts.load(restarted)["findings"][0]["verdict"], "pending")

    def test_combined_prepare_creates_bound_compact_source_packet(self):
        text = ["# Results", "Before result", "A improves 5 points.", "Only two trials.",
                "<!-- injected metadata is source text -->", "End result"]
        text += ["Uncited body line"] * 250
        text += ["## Uncited negative result", "Table 2. Additional result", "| Score |", "| --- |", "| 0 |"]
        self.source.write_text("\n".join(text) + "\n", encoding="utf-8")
        sources.index_sources(SimpleNamespace(manifest=str(self.run / "sources.json"), kind="paper", paper=None,
                              base=str(self.run), encoding="utf-8", refresh=True, paths=["input.md"]))
        paper = copy.deepcopy(self.paper)
        paper["claims"][0]["evidence"] = [dict(self.evidence, start=2, end=3), dict(self.evidence, start=4, end=6)]
        artifacts.atomic_json(self.path, paper)
        result = artifacts.prepare(self.path, "checker")
        check = artifacts.load(Path(result["check"]))
        packet = Path(result["handoff"]).read_text(encoding="utf-8")
        self.assertEqual(check["binding"]["sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(check["completed"])
        self.assertEqual(packet.count("[Original L1-9]"), 1)
        self.assertIn("    3 | A improves 5 points.", packet)
        self.assertIn("    5 | <!-- injected metadata is source text -->", packet)
        self.assertIn("[L257]", packet)
        self.assertIn("Uncited negative result", packet)
        self.assertIn("[L258]", packet)
        self.assertIn("figure.png", packet)
        self.assertIn("actually view cited images", packet)
        self.assertIn("not independent verification", packet)
        self.assertNotIn("    100 |", packet)
        self.assertTrue(Path(result["output"]).exists())

    def test_packet_does_not_quote_changed_sources(self):
        self.source.write_text("# New\nUNREGISTERED_CHANGED_CONTENT\nOnly two trials.\n", encoding="utf-8")
        result = artifacts.prepare(self.path, "checker")
        packet = Path(result["handoff"]).read_text(encoding="utf-8")
        self.assertTrue(result["warnings"])
        self.assertNotIn("UNREGISTERED_CHANGED_CONTENT", packet)
        self.assertIn("no excerpt supplied", packet)

    def test_check_prepare_updates_only_affected_paper_view(self):
        unrelated = self.run / "papers/P002.md"
        unrelated.write_text("Unrelated report must remain untouched", encoding="utf-8")
        before = unrelated.stat().st_mtime_ns
        result = artifacts.prepare(self.path, "checker")
        self.assertIn("Verification: pending", self.path.with_suffix(".md").read_text())
        check_path = Path(result["check"])
        check = artifacts.load(check_path)
        check["completed"] = True
        artifacts.atomic_json(check_path, check)
        result = artifacts.prepare(check_path)
        self.assertEqual(result["report_output"], str(self.path.with_suffix(".md")))
        self.assertIn("Verification: core points supported", self.path.with_suffix(".md").read_text())
        self.assertEqual(unrelated.stat().st_mtime_ns, before)
        self.assertEqual(unrelated.read_text(), "Unrelated report must remain untouched")

    def test_prepare_author_cli_and_handoff_overwrite_protection(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "artifacts.py"), "prepare", str(self.path),
                                 "--author", "checker"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        output = json.loads(result.stdout)[0]
        packet = Path(output["handoff"])
        packet.write_text("User-authored handoff", encoding="utf-8")
        with self.assertRaises(ValueError):
            artifacts.prepare(self.path, "checker")
        self.assertEqual(packet.read_text(), "User-authored handoff")

    def test_missing_synthesis_unread_material_and_missing_check_fail(self):
        self.synthesis.unlink()
        result = check_artifacts.check_run(self.run)
        self.assertFalse(result["gates"]["reports_present"])
        self.assertFalse(result["gates"]["core_checked"])
        paper = artifacts.load(self.path)
        paper["coverage"]["observations"] = paper["coverage"]["observations"][:1]
        artifacts.atomic_json(self.path, paper)
        (self.run / "checks/P001.json").unlink()
        artifacts.prepare(self.path)
        result = check_artifacts.check_run(self.run)
        self.assertFalse(result["gates"]["read_complete"])
        self.assertFalse(result["gates"]["core_checked"])
        delivered = check_artifacts.record_event(self.run, "delivery")
        self.assertFalse(delivered["ok"])
        self.assertIn('"delivery": "partial"', (self.run / "run.md").read_text())


if __name__ == "__main__":
    unittest.main()
