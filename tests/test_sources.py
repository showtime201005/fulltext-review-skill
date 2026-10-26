"""Behavior tests for the source CLI; all mutations use temporary directories."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/fulltext-literature-review/scripts/sources.py"
SPEC = importlib.util.spec_from_file_location("sources", SCRIPT)
SOURCES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCES)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "run/sources.json"
        self.paper = self.root / "資料 paper.md"
        self.paper.write_bytes(b"\xef\xbb\xbf# Title\r\n\r\nValue 0.7\rLast line\n")

    def cli(self, *args, code=0, raw=False):
        process = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *map(str, args)],
                                 cwd=self.root, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        if raw:
            return process
        return json.loads(process.stdout if process.stdout else process.stderr)

    def register(self, *paths, **kwargs):
        return self.cli("index", "--manifest", self.manifest, "--kind", "paper", *(paths or [self.paper]), **kwargs)

    def read(self, start, end, format=None, **kwargs):
        options = [] if format is None else ["--format", format]
        return self.cli("read", "--manifest", self.manifest, "--id", "P001", "--start", start, "--end", end,
                        *options, **kwargs)

    def test_default_json_output_is_unchanged(self):
        self.register()
        result = self.read(1, 4)
        expected = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(self.read(1, 4, raw=True).stdout, expected)
        self.assertEqual(self.read(1, 4, format="json", raw=True).stdout, expected)

    def test_text_output_preserves_source_and_range(self):
        lines = ["標題 é 😀", "", "\tstart\tmiddle\t", "甲\u2028乙", "x" * 20000, "end", ""]
        before = ("\ufeff" + "\r\n".join(lines) + "\r\n").encode("utf-8")
        self.paper.write_bytes(before)
        self.register()
        for start, end in [(1, len(lines)), (2, 5), (7, 7)]:
            with self.subTest(start=start, end=end):
                expected = self.read(start, end)
                output = self.read(start, end, format="text", raw=True)
                header, body = output.stdout.split("\n", 1)
                metadata = {key: value for key, value in expected.items() if key != "lines"}
                self.assertEqual(header, json.dumps(metadata, ensure_ascii=False, separators=(",", ":")))
                self.assertEqual(metadata["sha256"], SOURCES.digest(before))
                self.assertEqual(body, "".join(f"{number}\t{lines[number - 1]}\n"
                                              for number in range(start, end + 1)))
                self.assertEqual(len(body.split("\n")) - 1, end - start + 1)
                self.assertEqual(output.stderr, "")
        self.assertEqual(self.paper.read_bytes(), before)

    def test_text_errors_keep_json_stderr_and_no_stdout(self):
        self.register()
        for start, end in [(0, 1), (2, 1), (1, 5), (-1, 1)]:
            default = self.read(start, end, code=2, raw=True)
            text = self.read(start, end, format="text", code=2, raw=True)
            self.assertEqual(text.stdout, "")
            self.assertEqual(text.stderr, default.stderr)
            self.assertIn("error", json.loads(text.stderr))
        self.paper.write_text("Changed\n", encoding="utf-8")
        for missing in [False, True]:
            if missing:
                self.paper.unlink()
            default = self.read(1, 1, code=2, raw=True)
            text = self.read(1, 1, format="text", code=2, raw=True)
            self.assertEqual(text.stdout, "")
            self.assertEqual(text.stderr, default.stderr)
            self.assertIn("error", json.loads(text.stderr))

    def coverage_fixture(self):
        self.register()
        supplement = self.root / "appendix.md"
        supplement.write_text("First\nSecond\nThird\n", encoding="utf-8")
        self.cli("index", "--manifest", self.manifest, "--kind", "supplement", "--paper", "P001", supplement)
        images = [self.root / "one.png", self.root / "two.png"]
        for image in images:
            image.write_bytes(b"synthetic image")
        self.cli("index", "--manifest", self.manifest, "--kind", "image", "--paper", "P001", *images)
        self.report = self.root / "report.md"
        self.observations = []
        for entry in json.loads(self.manifest.read_text(encoding="utf-8"))["sources"]:
            observation = {"source": entry["id"], "sha256": entry["sha256"],
                           "action": "R1/tool-reference", "confirmed": True}
            if entry["kind"] != "image":
                observation.update(start=1, end=entry["line_count"])
            self.observations.append(observation)

    def check_coverage(self, observations=None, code=0, meta=None, prefix="", suffix=""):
        if observations is None:
            observations = self.observations
        if meta is None:
            meta = {"kind": "paper", "id": "P001"}
        self.report.write_text(prefix + "<!-- review-meta " + json.dumps(meta) + " -->\n\n## Coverage\n" +
                               "".join("<!-- review-observation " + json.dumps(item) + " -->\n"
                                       for item in observations) + suffix, encoding="utf-8")
        return self.cli("coverage", "--manifest", self.manifest, "--paper", "P001", "--report", self.report, code=code)

    def test_coverage_complete_and_repeated_observations(self):
        self.coverage_fixture()
        result = self.check_coverage()
        self.assertTrue(result["ok"])
        self.assertEqual(result["paper"], "P001")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["sources"], [
            {"id": "P001", "kind": "paper", "missing_ranges": []},
            {"id": "P001-T001", "kind": "supplement", "missing_ranges": []},
            {"id": "P001-I001", "kind": "image", "observed": True},
            {"id": "P001-I002", "kind": "image", "observed": True}])
        repeated = self.observations + [dict(self.observations[0], start=2, end=3), self.observations[2]]
        result = self.check_coverage(repeated)
        self.assertTrue(result["ok"])
        self.assertEqual([issue["severity"] for issue in result["issues"]], ["warning", "warning"])

    def test_coverage_holes_and_unconfirmed_ranges_do_not_count(self):
        self.coverage_fixture()
        main = self.observations[0]
        ranges = [dict(main, start=1, end=1), dict(main, start=3, end=3),
                  dict(main, start=2, end=4, confirmed=False)]
        result = self.check_coverage(ranges + self.observations[1:], code=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["sources"][0]["missing_ranges"], [[2, 2], [4, 4]])
        result = self.check_coverage([dict(main, end=2)] + self.observations[1:], code=1)
        self.assertEqual(result["sources"][0]["missing_ranges"], [[3, 4]])
        result = self.check_coverage([dict(main, start=2, end=3)] + self.observations[1:], code=1)
        self.assertEqual(result["sources"][0]["missing_ranges"], [[1, 1], [4, 4]])

    def test_coverage_requires_supplements_and_each_image(self):
        self.coverage_fixture()
        result = self.check_coverage(self.observations[:1] + self.observations[2:3], code=1)
        self.assertEqual(result["sources"][1]["missing_ranges"], [[1, 3]])
        self.assertFalse(result["sources"][3]["observed"])
        result = self.check_coverage(self.observations[:3] + [dict(self.observations[3], confirmed=False)], code=1)
        self.assertFalse(result["sources"][3]["observed"])

    def test_coverage_empty_text_is_vacuously_covered(self):
        self.paper.write_bytes(b"")
        self.register()
        self.report = self.root / "report.md"
        result = self.check_coverage([])
        self.assertTrue(result["ok"])
        self.assertEqual(result["sources"][0]["missing_ranges"], [])

    def test_coverage_stale_missing_and_refreshed_sources(self):
        self.coverage_fixture()
        self.paper.write_bytes(b"new title\n\nValue 0.7\nLast line\n")
        result = self.check_coverage(code=1)
        self.assertIn("source", [issue["code"] for issue in result["issues"]])
        self.cli("index", "--manifest", self.manifest, "--kind", "paper", "--refresh", self.paper)
        result = self.check_coverage(code=1)
        self.assertTrue(any(issue["code"] == "observation" and "SHA-256" in issue["message"]
                            for issue in result["issues"]))
        self.observations[0]["sha256"] = SOURCES.digest(self.paper.read_bytes())
        self.assertTrue(self.check_coverage()["ok"])
        (self.root / "two.png").unlink()
        result = self.check_coverage(code=1)
        self.assertTrue(any(issue["code"] == "source" and issue["source"] == "P001-I002"
                            for issue in result["issues"]))

    def test_coverage_rejects_registered_line_count_mismatch(self):
        self.coverage_fixture()
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["sources"][0]["line_count"] = 2
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        observations = [dict(self.observations[0], end=2)] + self.observations[1:]
        result = self.check_coverage(observations, code=1)
        self.assertTrue(any(issue["code"] == "source" and "line count" in issue["message"]
                            for issue in result["issues"]))

    def test_coverage_rejects_invalid_observations(self):
        self.coverage_fixture()
        main = self.observations[0]
        invalid = [dict(main, source="P999"), dict(main, confirmed="true"), dict(main, action="  "),
                   dict(main, action=1), dict(main, sha256="0" * 64), dict(main, start=0),
                   dict(main, start=True), dict(main, end=5), dict(main, start=3, end=2),
                   dict(main, start=1.0), dict(main, confirmed=False, end=5),
                   dict(self.observations[2], start=1, end=1), [main]]
        second = self.root / "second.md"
        second.write_text("Other paper", encoding="utf-8")
        self.register(second)
        invalid.append(dict(main, source="P002", sha256=SOURCES.digest(second.read_bytes())))
        for observation in invalid:
            with self.subTest(observation=observation):
                result = self.check_coverage(self.observations + [observation], code=1)
                self.assertFalse(result["ok"])
                self.assertIn("observation", [issue["code"] for issue in result["issues"]])

    def test_coverage_metadata_and_malformed_comments(self):
        self.coverage_fixture()
        for meta in [{"kind": "check", "id": "P001"}, {"kind": "paper", "id": "P002"}, [], {}]:
            with self.subTest(meta=meta):
                result = self.check_coverage(meta=meta, code=1)
                self.assertIn("metadata", [issue["code"] for issue in result["issues"]])
        for suffix in ["<!-- review-observation {broken} -->\n", "<!-- review-observation {}\n",
                       "<!-- review-observation\n{} -->\n"]:
            result = self.check_coverage(suffix=suffix, code=1)
            self.assertIn("observation", [issue["code"] for issue in result["issues"]])
        result = self.check_coverage(prefix='<!-- review-meta {broken} -->\n', code=1)
        self.assertIn("metadata", [issue["code"] for issue in result["issues"]])

    def test_coverage_ignores_fenced_examples_with_variable_markers(self):
        self.coverage_fixture()
        for marker in ["````", "~~~~~"]:
            prefix = (marker + "json\n<!-- review-meta {} -->\n" + marker[:-1] + "\n" +
                      "<!-- review-observation {broken} -->\n" + marker + "\n")
            with self.subTest(marker=marker):
                self.assertTrue(self.check_coverage(prefix=prefix)["ok"])
        result = self.check_coverage([], prefix="```\n", code=1)
        self.assertFalse(result["ok"])
        self.assertIn("fence", [issue["code"] for issue in result["issues"]])

    def test_coverage_unreadable_inputs_and_invalid_manifest_exit_two(self):
        self.coverage_fixture()
        self.cli("coverage", "--manifest", self.manifest, "--paper", "P001", "--report", self.report, code=2)
        self.check_coverage()
        self.cli("coverage", "--manifest", self.manifest, "--paper", "P999", "--report", self.report, code=2)
        self.manifest.write_text('{"version": 9}', encoding="utf-8")
        self.cli("coverage", "--manifest", self.manifest, "--paper", "P001", "--report", self.report, code=2)

    def test_round_trip_physical_lines_and_exact_fingerprint(self):
        before = self.paper.read_bytes()
        result = self.register()
        read = self.read(2, 4)
        self.assertEqual(read["lines"], [{"number": 2, "text": ""}, {"number": 3, "text": "Value 0.7"},
                                         {"number": 4, "text": "Last line"}])
        self.assertEqual(read["sha256"], SOURCES.digest(before))
        self.assertEqual(result["registered"][0]["id"], "P001")
        self.assertEqual(self.paper.read_bytes(), before)

    def test_relative_absolute_aliases_keep_id(self):
        self.register(self.paper.name)
        self.assertEqual(self.register(self.paper)["registered"][0]["id"], "P001")
        second = self.root / "second.md"
        second.write_text("Second", encoding="utf-8")
        self.assertEqual(self.register(second)["registered"][0]["id"], "P002")
        self.assertEqual(len(json.loads(self.manifest.read_text())["sources"]), 2)

    def test_image_association_and_binary_not_text(self):
        self.register()
        images = self.root / "figures"
        images.mkdir()
        image = images / "圖 1.png"
        image.write_bytes(b"\x89PNG\xff")
        result = self.cli("index", "--manifest", self.manifest, "--kind", "image", "--paper", "P001",
                          "--base", self.root, "figures/圖 1.png")
        self.assertEqual(result["registered"][0]["id"], "P001-I001")
        self.cli("read", "--manifest", self.manifest, "--id", "P001-I001", "--start", 1, "--end", 1, code=2)
        self.assertTrue(self.cli("check", "--manifest", self.manifest)["ok"])
        image.unlink()
        self.assertEqual(self.cli("check", "--manifest", self.manifest, code=1)["sources"][1]["status"], "unavailable")

    def test_change_requires_explicit_refresh_and_invalidates_read(self):
        original = self.register()["registered"][0]["sha256"]
        self.paper.write_text("Changed\n", encoding="utf-8")
        self.assertEqual(self.cli("check", "--manifest", self.manifest, code=1)["sources"][0]["status"], "changed")
        self.read(1, 1, code=2)
        self.register(code=2)
        updated = self.cli("index", "--manifest", self.manifest, "--kind", "paper", "--refresh", self.paper)
        self.assertEqual(updated["registered"][0]["previous_sha256"], original)
        self.assertEqual(self.read(1, 1)["lines"][0]["text"], "Changed")

    def test_failed_batch_preserves_manifest(self):
        self.register()
        before = self.manifest.read_bytes()
        extra = self.root / "extra.md"
        extra.write_text("Extra", encoding="utf-8")
        self.register(extra, self.root / "missing.md", code=2)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_range_boundaries(self):
        self.register()
        for start, end in [(0, 1), (2, 1), (1, 5), (-1, 1)]:
            self.read(start, end, code=2)
        self.assertEqual(self.read(4, 4)["total_lines"], 4)

    def test_invalid_encoding_does_not_write_manifest(self):
        self.paper.write_bytes(b"\xff\xfe\xff")
        self.register(code=2)
        self.assertFalse(self.manifest.exists())

    def test_explicit_encoding_and_unicode_line_separator(self):
        self.paper.write_bytes("α\u2028β\n終".encode("utf-16"))
        self.cli("index", "--manifest", self.manifest, "--kind", "paper", "--encoding", "utf-16", self.paper)
        self.assertEqual(self.read(1, 2)["lines"], [{"number": 1, "text": "α\u2028β"}, {"number": 2, "text": "終"}])

    def test_empty_source_has_zero_lines(self):
        self.paper.write_bytes(b"")
        self.register()
        self.assertEqual(json.loads(self.manifest.read_text())["sources"][0]["line_count"], 0)
        self.read(1, 1, code=2)

    def test_manifest_cannot_overwrite_input(self):
        original = self.paper.read_bytes()
        self.cli("index", "--manifest", self.paper, "--kind", "paper", self.paper, code=2)
        self.assertEqual(self.paper.read_bytes(), original)

    def test_invalid_manifest_and_unknown_ids(self):
        self.register()
        self.cli("read", "--manifest", self.manifest, "--id", "P999", "--start", 1, "--end", 1, code=2)
        manifest = json.loads(self.manifest.read_text())
        manifest["sources"].append(manifest["sources"][0])
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        self.cli("check", "--manifest", self.manifest, code=2)

    def test_supplement_requires_registered_parent(self):
        self.cli("index", "--manifest", self.manifest, "--kind", "supplement", "--paper", "P001", self.paper, code=2)
        self.register()
        supplement = self.root / "appendix.md"
        supplement.write_text("Appendix", encoding="utf-8")
        item = self.cli("index", "--manifest", self.manifest, "--kind", "supplement", "--paper", "P001", supplement)
        self.assertEqual(item["registered"][0]["id"], "P001-T001")

    def test_report_fingerprint(self):
        value = self.cli("fingerprint", self.paper)["files"][0]
        self.assertEqual(value["sha256"], SOURCES.digest(self.paper.read_bytes()))


if __name__ == "__main__":
    unittest.main()
