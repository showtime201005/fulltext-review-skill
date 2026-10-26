"""Versioned local-source inventory and inclusive line reads. Python 3.10+, stdlib only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


KINDS = ("paper", "supplement", "image")
ID_PATTERN = re.compile(r"P\d{3,}(?:-[TI]\d{3,})?")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text_lines(data, encoding):
    # Split only physical LF/CRLF/CR lines; Unicode paragraph separators are source text.
    text = data.decode(encoding)
    if not text:
        return []
    lines = re.split(r"\r\n|\r|\n", text)
    return lines[:-1] if lines[-1] == "" else lines


def load_manifest(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError("Expected manifest version 1")
    entries = manifest.get("sources")
    if not isinstance(entries, list):
        raise ValueError("Manifest sources must be a list")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid source entry")
        source_id = entry.get("id")
        if not isinstance(source_id, str) or not ID_PATTERN.fullmatch(source_id):
            raise ValueError("Invalid source ID")
        if source_id in seen:
            raise ValueError("Duplicate source ID")
        seen.add(source_id)
        kind = entry.get("kind")
        paper_id = entry.get("paper_id")
        if kind not in KINDS or not isinstance(paper_id, str) or not re.fullmatch(r"P\d{3,}", paper_id):
            raise ValueError("Invalid source kind or paper ID")
        expected_id = paper_id if kind == "paper" else paper_id + ("-T" if kind == "supplement" else "-I")
        if (kind == "paper" and source_id != expected_id) or (
            kind != "paper" and not re.fullmatch(re.escape(expected_id) + r"\d{3,}", source_id)
        ):
            raise ValueError("Source ID does not match kind/paper")
        if not isinstance(entry.get("path"), str) or not Path(entry["path"]).is_absolute():
            raise ValueError("Source path must be absolute")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
            raise ValueError("Invalid SHA-256")
        if kind != "image" and (
            not isinstance(entry.get("encoding"), str)
            or type(entry.get("line_count")) is not int
            or entry["line_count"] < 0
        ):
            raise ValueError("Text source needs encoding and line count")
    papers = {entry["id"] for entry in entries if entry["kind"] == "paper"}
    if any(entry["paper_id"] not in papers for entry in entries):
        raise ValueError("Source refers to an unregistered paper")
    return manifest


def save_manifest(path, manifest):
    for entry in manifest["sources"]:
        if Path(entry["path"]).resolve() == path:
            raise ValueError("Manifest must not overwrite a source")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def next_id(entries, prefix):
    numbers = [int(entry["id"][len(prefix):]) for entry in entries
               if re.fullmatch(re.escape(prefix) + r"\d{3,}", entry["id"])]
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


def index_sources(args):
    path = Path(args.manifest).resolve()
    manifest = load_manifest(path) if path.exists() else {"version": 1, "sources": []}
    entries = manifest["sources"]
    if args.kind == "paper" and args.paper:
        raise ValueError("--paper is only for supplements/images")
    if args.kind != "paper" and not any(e["kind"] == "paper" and e["id"] == args.paper for e in entries):
        raise ValueError("Provide --paper with a registered main paper ID")
    base = Path(args.base).resolve()
    updates = []
    for original in args.paths:
        source_path = (base / original).resolve(strict=True)
        if not source_path.is_file():
            raise ValueError(f"Not a file: {source_path}")
        if source_path == path:
            raise ValueError("Manifest cannot be registered as its own source")
        data = source_path.read_bytes()
        sha = digest(data)
        existing = next((e for e in entries if Path(e["path"]) == source_path
                         and e["kind"] == args.kind
                         and (args.kind == "paper" or e["paper_id"] == args.paper)), None)
        if existing and existing["sha256"] != sha and not args.refresh:
            raise ValueError(f"Source changed: {existing['id']}; invalidate affected evidence before --refresh")
        encoding = existing.get("encoding", args.encoding) if existing else args.encoding
        count = len(text_lines(data, encoding)) if args.kind != "image" else None
        if existing:
            entry = existing
            previous = entry["sha256"]
        else:
            prefix = "P" if args.kind == "paper" else args.paper + ("-T" if args.kind == "supplement" else "-I")
            source_id = next_id(entries, prefix)
            entry = {"id": source_id, "paper_id": source_id if args.kind == "paper" else args.paper,
                     "kind": args.kind, "input_path": original, "base": str(base), "path": str(source_path)}
            entries.append(entry)
            previous = None
        entry["sha256"] = sha
        if args.kind != "image":
            entry.update(encoding=encoding, line_count=count)
        updates.append({"id": entry["id"], "path": str(source_path), "previous_sha256": previous, "sha256": sha})
    save_manifest(path, manifest)
    return {"manifest": str(path), "registered": updates}, 0


def read_source(args):
    manifest = load_manifest(Path(args.manifest))
    entry = next((e for e in manifest["sources"] if e["id"] == args.id), None)
    if entry is None:
        raise ValueError(f"Unknown source ID: {args.id}")
    if entry["kind"] == "image":
        raise ValueError("Use the actual image-viewing tool for images")
    data = Path(entry["path"]).read_bytes()
    sha = digest(data)
    if sha != entry["sha256"]:
        raise ValueError("Source changed; invalidate affected evidence and register the new version")
    lines = text_lines(data, entry["encoding"])
    if args.start < 1 or args.end < args.start or args.end > len(lines):
        raise ValueError(f"Invalid inclusive range; source has {len(lines)} lines")
    return {"id": entry["id"], "path": entry["path"], "sha256": sha,
            "total_lines": len(lines), "start": args.start, "end": args.end,
            "lines": [{"number": number, "text": lines[number - 1]}
                      for number in range(args.start, args.end + 1)]}, 0


def check_sources(args):
    manifest = load_manifest(Path(args.manifest))
    results = []
    for entry in manifest["sources"]:
        try:
            actual = digest(Path(entry["path"]).read_bytes())
            status = "unchanged" if actual == entry["sha256"] else "changed"
            result = {"id": entry["id"], "status": status, "expected_sha256": entry["sha256"], "actual_sha256": actual}
        except OSError as error:
            result = {"id": entry["id"], "status": "unavailable", "error": str(error)}
        results.append(result)
    ok = all(item["status"] == "unchanged" for item in results)
    return {"ok": ok, "sources": results}, 0 if ok else 1


def fingerprint(args):
    return {"files": [{"path": str(Path(p).resolve()), "sha256": digest(Path(p).read_bytes())}
                      for p in args.paths]}, 0


def coverage(args):
    """Check registered-source attestations, not unregistered references, tool use or understanding."""
    manifest = load_manifest(Path(args.manifest))
    entries = {entry["id"]: entry for entry in manifest["sources"] if entry["paper_id"] == args.paper}
    if args.paper not in entries or entries[args.paper]["kind"] != "paper":
        raise ValueError("Provide --paper with a registered main paper ID")
    report_path = Path(args.report)
    report = report_path.read_text(encoding="utf-8-sig")
    if report_path.suffix == ".json":
        import artifacts
        document = artifacts.load(report_path)
        if document.get("schema_version") == 2:
            report = artifacts.comment("review-meta", document["meta"]) + "\n"
            report += "\n".join(artifacts.comment("review-observation", item)
                                for item in document["coverage"]["observations"])
        else:
            artifacts.validate_sources(document, manifest)
            report = artifacts.render(document)
    issues, metadata, observations = [], [], []

    def issue(code, message, source=None, line=None, severity="error"):
        issues.append({"code": code, "message": message, "source": source,
                       "line": line, "severity": severity})

    fence = None
    for number, line in enumerate(report.split("\n"), 1):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            marker, suffix = match.groups()
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1] and not suffix.strip():
                fence = None
            continue
        if fence is not None:
            continue
        metadata.extend(re.findall(r"<!-- review-meta (.*?) -->", line))
        if "<!-- review-observation" in line:
            match = re.fullmatch(r"\s*<!-- review-observation (.*?) -->\s*", line)
            if match:
                observations.append((number, match[1]))
            else:
                issue("observation", "Expected a single-line review-observation JSON comment", line=number)
    if fence:
        issue("fence", "Unclosed code fence")
    try:
        if len(metadata) != 1:
            raise ValueError("Expected exactly one current review-meta comment")
        meta = json.loads(metadata[0])
        if not isinstance(meta, dict) or meta.get("kind") != "paper" or meta.get("id") != args.paper:
            raise ValueError("Report review-meta must have kind paper and the assigned paper ID")
    except ValueError as error:
        issue("metadata", str(error))

    intervals = {source_id: [] for source_id in entries}
    views = {source_id: 0 for source_id in entries}
    for number, raw in observations:
        source_id = None
        try:
            observation = json.loads(raw)
            if not isinstance(observation, dict):
                raise ValueError("Observation must be a JSON object")
            source_id = observation.get("source")
            if not isinstance(source_id, str) or source_id not in entries:
                raise ValueError("Unknown source or source belongs to another paper")
            entry = entries[source_id]
            if type(observation.get("confirmed")) is not bool:
                raise ValueError("Observation confirmed must be a boolean")
            if not isinstance(observation.get("action"), str) or not observation["action"].strip():
                raise ValueError("Observation needs a nonempty action reference")
            if observation.get("sha256") != entry["sha256"]:
                raise ValueError("Observation SHA-256 does not match the registered source")
            if entry["kind"] == "image":
                if "start" in observation or "end" in observation:
                    raise ValueError("Image observations must not have line ranges")
                if observation["confirmed"]:
                    views[source_id] += 1
            else:
                start, end = observation.get("start"), observation.get("end")
                if type(start) is not int or type(end) is not int or not 1 <= start <= end <= entry["line_count"]:
                    raise ValueError("Invalid inclusive observation range")
                if observation["confirmed"]:
                    intervals[source_id].append((start, end))
        except ValueError as error:
            issue("observation", str(error), source=source_id, line=number)

    results = []
    for source_id, entry in entries.items():
        try:
            data = Path(entry["path"]).read_bytes()
            if digest(data) != entry["sha256"]:
                raise ValueError("Source changed since registration")
            if entry["kind"] != "image" and len(text_lines(data, entry["encoding"])) != entry["line_count"]:
                raise ValueError("Registered line count does not match the current source")
        except (OSError, ValueError, LookupError) as error:
            issue("source", str(error), source=source_id)
        result = {"id": source_id, "kind": entry["kind"]}
        if entry["kind"] == "image":
            result["observed"] = views[source_id] > 0
            if not result["observed"]:
                issue("missing-image", "No confirmed image observation", source=source_id)
            if views[source_id] > 1:
                issue("overlap", "Repeated image observation", source=source_id, severity="warning")
        else:
            missing, covered = [], 0
            for start, end in sorted(intervals[source_id]):
                if start <= covered:
                    issue("overlap", f"Repeated or overlapping range {start}-{end}",
                          source=source_id, severity="warning")
                if start > covered + 1:
                    missing.append([covered + 1, start - 1])
                covered = max(covered, end)
            if covered < entry["line_count"]:
                missing.append([covered + 1, entry["line_count"]])
            result["missing_ranges"] = missing
            if missing:
                issue("missing-lines", "Text has unconfirmed line ranges", source=source_id)
        results.append(result)
    ok = not any(item["severity"] == "error" for item in issues)
    return {"ok": ok, "paper": args.paper, "sources": results, "issues": issues}, 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Register explicit local sources; updates are serial")
    index.add_argument("--manifest", required=True)
    index.add_argument("--kind", choices=KINDS, required=True)
    index.add_argument("--paper")
    index.add_argument("--base", default=".", help="Resolve references against containing Markdown's directory")
    index.add_argument("--encoding", default="utf-8-sig", help="Explicit text encoding on first registration")
    index.add_argument("--refresh", action="store_true", help="Accept changed source after invalidating dependent checks")
    index.add_argument("paths", nargs="+")
    index.set_defaults(action=index_sources)
    read = commands.add_parser("read", help="Read a fingerprint-checked inclusive line range")
    read.add_argument("--manifest", required=True)
    read.add_argument("--id", required=True)
    read.add_argument("--start", required=True, type=int)
    read.add_argument("--end", required=True, type=int)
    read.add_argument("--format", choices=("json", "text"), default="json")
    read.set_defaults(action=read_source)
    check = commands.add_parser("check", help="Check missing/changed sources; exit 1 on differences")
    check.add_argument("--manifest", required=True)
    check.set_defaults(action=check_sources)
    hashed = commands.add_parser("fingerprint", help="Hash reports or sources without registering them")
    hashed.add_argument("paths", nargs="+")
    hashed.set_defaults(action=fingerprint)
    covered = commands.add_parser("coverage", description=coverage.__doc__,
                                  help="Check registered-source attestations, not tool use or understanding")
    covered.add_argument("--manifest", required=True)
    covered.add_argument("--paper", required=True)
    covered.add_argument("--report", required=True)
    covered.set_defaults(action=coverage)
    args = parser.parse_args(argv)
    try:
        result, code = args.action(args)
    except (OSError, ValueError, LookupError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.command == "read" and args.format == "text":
        print(json.dumps({key: value for key, value in result.items() if key != "lines"},
                         ensure_ascii=False, separators=(",", ":")))
        for line in result["lines"]:
            print(f"{line['number']}\t{line['text']}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
