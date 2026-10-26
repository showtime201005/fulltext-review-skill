"""Preflight for this skill's generated Markdown, not a scientific-content validator."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote


CLAIM = r"(?:P\d{3,}-C\d{2,}|S-C\d{2,})"
ANCHOR = re.compile(r'<a\s+id="(' + CLAIM + r')"\s*></a>')
REFERENCE = re.compile(r"(?<![\w-])" + CLAIM + r"(?![\w-])")
META = re.compile(r"<!-- review-meta (.*?) -->")


def canonical(path):
    return path.with_suffix(".json") if path.parent.name in ("papers", "checks") else path


def current_path(path):
    candidate = canonical(path)
    return candidate if candidate.exists() else path


def json_comment(doc, name):
    matches = re.findall(r"<!-- " + re.escape(name) + r" (.*?) -->", doc["text"])
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} comment")
    value = json.loads(matches[0])
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def utc_time(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO 8601 UTC string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("Timestamp must have UTC timezone")
    return parsed


def check_workflow(run, documents, targets, issue):
    """Validate the declared bounded workflow; this does not observe or run agents."""
    index = run / "run.md"
    new = any((doc["meta"] or {}).get("contract_version") == 2 for doc in documents.values())
    marked = index in documents and "<!-- review-run " in documents[index]["text"]
    if not new and not marked:
        return None
    if not marked:
        issue(index, "workflow-missing", "Contract v2 requires review-run in run.md")
        return None
    try:
        state = json_comment(documents[index], "review-run")
        if state.get("contract_version") != 2:
            raise ValueError("Unsupported run contract_version")
        started = utc_time(state.get("started_at"))
        delivered = utc_time(state["delivered_at"]) if state.get("delivered_at") is not None else None
        budget, reserve = state.get("budget_seconds"), state.get("reserve_seconds")
        if not ((budget is None and type(reserve) is int and reserve == 0) or
                (type(budget) is int and type(reserve) is int and 0 < reserve < budget)):
            raise ValueError("Use null budget_seconds and zero reserve_seconds, or integer budget > reserve > 0")
        if state.get("execution") not in ("active", "waiting-for-focus", "blocked", "finished"):
            raise ValueError("Unknown execution state")
        if delivered and delivered < started:
            raise ValueError("Delivery precedes start")
        if (state["execution"] == "finished") != (delivered is not None):
            raise ValueError("Finished state and delivered_at must agree")
        artifacts, events = state.get("artifacts"), state.get("events")
        if not isinstance(artifacts, dict) or not isinstance(events, list):
            raise ValueError("Require artifact object and event array")
    except (ValueError, TypeError, KeyError) as error:
        issue(index, "workflow-state", str(error))
        return None

    final = state["execution"] == "finished"
    timing = {"elapsed_seconds": (delivered - started).total_seconds() if delivered else None,
              "over_budget": bool(budget is not None and delivered and (delivered - started).total_seconds() > budget),
              "intervals": [], "waits": []}
    dispatched, returned, ready = {}, set(), {}
    previous = started
    for event in events:
        try:
            if not isinstance(event, dict):
                raise ValueError("Event must be an object")
            at = utc_time(event.get("at"))
            ident, name, round_no = event.get("artifact"), event.get("event"), event.get("round")
            if not isinstance(ident, str) or ident not in artifacts or not isinstance(name, str):
                raise ValueError("Event requires registered artifact and event name")
            if not isinstance(event.get("agent"), str) or not event["agent"].strip():
                raise ValueError("Event requires actual agent identity")
            if at < previous:
                raise ValueError("Events must be chronological and not precede run start")
            previous = at
            if delivered and at > delivered and name != "late-return":
                raise ValueError("Only late-return notices may follow delivery")
            if name == "late-return":
                continue
            if name == "verification-ready":
                ready[ident] = at
                continue
            if name not in {f"{stage}-{action}" for stage in ("reading", "draft", "check", "repair")
                            for action in ("dispatched", "returned")}:
                raise ValueError(f"Unknown event: {name}")
            stage, action = name.split("-")
            if stage in ("check", "repair"):
                if type(round_no) is not int or round_no not in (0, 1) or (stage == "repair" and round_no != 1):
                    issue(index, "workflow-round", "Only check rounds 0/1 and repair round 1 are allowed")
                    continue
            elif round_no is not None:
                raise ValueError("Reading/drafting has no verification round")
            key = (ident, stage, round_no)
            if action == "dispatched":
                if key in dispatched:
                    raise ValueError("Repeated dispatch would restart a stage/round")
                elapsed = (at - started).total_seconds()
                if budget is not None and (elapsed >= budget or (stage in ("reading", "repair") and elapsed >= budget - reserve)):
                    issue(index, "workflow-deadline", f"{name} was dispatched outside its budget")
                if stage == "repair" and (ident, "check", 0) not in returned:
                    raise ValueError("Repair must follow initial check return")
                if stage == "check" and round_no == 1 and (ident, "repair", 1) not in returned:
                    raise ValueError("Recheck must follow the single repair return")
                dispatched[key] = at
                if stage == "check" and ident in ready:
                    timing["waits"].append({"artifact": ident, "round": round_no,
                                           "seconds": (at - ready.pop(ident)).total_seconds()})
            else:
                if key not in dispatched or key in returned:
                    raise ValueError("Return requires one matching earlier dispatch")
                returned.add(key)
                timing["intervals"].append({"artifact": ident, "stage": stage, "round": round_no,
                                            "seconds": (at - dispatched[key]).total_seconds()})
        except (ValueError, TypeError, KeyError) as error:
            issue(index, "workflow-state", str(error))

    for ident, item in artifacts.items():
        try:
            if not re.fullmatch(r"P\d{3,}|S", ident) or not isinstance(item, dict):
                raise ValueError("Invalid artifact ID/state")
            round_no, used = item.get("round"), item.get("repair_used")
            if round_no is not None and (type(round_no) is not int or round_no not in (0, 1)):
                issue(index, "workflow-round", f"{ident}: round must be null, 0 or 1")
            if type(used) is not int or used not in (0, 1):
                raise ValueError("repair_used must be 0 or 1")
            rounds = [key[2] for key in dispatched if key[:2] == (ident, "check")]
            if round_no != (max(rounds) if rounds else None) or used != int((ident, "repair", 1) in dispatched):
                raise ValueError(f"{ident}: counters disagree with dispatched work")
            if not isinstance(item.get("revision"), str) or not item["revision"].strip():
                raise ValueError("Artifact requires revision independent of round")
            verdict = item.get("verification")
            if verdict not in ("pending", "passed", "needs-confirmation"):
                raise ValueError("Invalid verification state")
            reason = item.get("stop_reason")
            if reason not in (None, "deadline", "round-limit", "source-gap", "scope", "capability", "preflight"):
                raise ValueError("Unknown stop_reason")
            if reason == "scope" and verdict != "needs-confirmation":
                raise ValueError("Scope-limited verification must remain needs-confirmation")
            if final and verdict != "passed" and reason is None:
                raise ValueError("Final unresolved work needs stop_reason")
            if reason == "round-limit" and used != 1:
                raise ValueError("Cannot claim the repair allowance is exhausted before using it")
            withdrawn = item.get("withdrawn")
            if not isinstance(withdrawn, list) or any(not isinstance(x, str) for x in withdrawn):
                raise ValueError("withdrawn must be a claim ID list")
            if len(withdrawn) != len(set(withdrawn)) or any(not re.fullmatch(re.escape(ident) + r"-C\d{2,}", x) for x in withdrawn):
                raise ValueError("Invalid/duplicate withdrawn claim ID")
            if verdict == "passed" and withdrawn:
                issue(index, "workflow-status", f"{ident}: withdrawn claims cannot pass")
            if verdict == "passed" and used and (ident, "check", 1) not in returned:
                issue(index, "workflow-status", f"{ident}: dispatched repair requires a returned recheck before passing")
            if index not in targets:
                continue  # Workers hand off before the coordinator reconciles returned files.
            report = current_path(run / ("synthesis.md" if ident == "S" else f"papers/{ident}.md"))
            check = current_path(run / ("checks/synthesis.md" if ident == "S" else f"checks/{ident}.md"))
            doc = documents.get(report)
            if doc and (doc["meta"] or {}).get("revision") != item["revision"]:
                issue(index, "workflow-version", f"{ident}: report revision differs from run state")
            if doc and doc["meta"]:
                author = doc["meta"].get("author")
                for event in events:
                    if not isinstance(event, dict) or event.get("artifact") != ident:
                        continue
                    if event.get("event") in ("reading-dispatched", "draft-dispatched", "repair-dispatched") and event.get("agent") != author:
                        issue(index, "workflow-state", f"{ident}: author dispatch identity differs from report")
                    if event.get("event") == "check-dispatched":
                        checker = (documents.get(check, {}).get("meta") or {}).get("author")
                        if event.get("agent") == author or (checker and event.get("agent") != checker):
                            issue(index, "workflow-state", f"{ident}: verifier dispatch identity is not independent/current")
            if verdict == "passed" and (not doc or check not in documents or (ident, "check", round_no) not in returned):
                issue(index, "workflow-status", f"{ident}: pass requires report and returned independent check")
            if check in documents:
                status = json_comment(documents[check], "review-status")
                if any(status.get(k) != item.get(k) for k in ("round", "verification", "withdrawn")):
                    issue(index, "workflow-status", f"{ident}: current check and run state disagree")
        except (ValueError, TypeError, KeyError) as error:
            issue(index, "workflow-state", str(error))
    if index in targets:
        for doc in documents.values():
            meta = doc["meta"] or {}
            if meta and (meta.get("id") not in artifacts or meta.get("contract_version") != 2):
                issue(index, "workflow-state", "All current artifacts must be registered and use contract_version 2")
    return timing


def visible_lines(text):
    """Omit fenced examples, retaining physical line numbers for diagnostics."""
    result, fence = [], None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            marker, suffix = match.groups()
            if fence is None:
                fence = (marker[0], len(marker), number)
            elif marker[0] == fence[0] and len(marker) >= fence[1] and not suffix.strip():
                fence = None
            continue
        if fence is None:
            result.append((number, line))
    return result, fence


def table_cells(line):
    # CommonMark pipes still separate table cells inside inline code.
    cells, cell = [], ""
    for char in line.strip():
        slashes = len(cell) - len(cell.rstrip("\\"))
        if char == "|" and slashes % 2 == 0:
            cells.append(cell.strip())
            cell = ""
        else:
            cell += char
    cells.append(cell.strip())
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    return cells


def link_targets(line):
    """Inline destinations, including angle paths/spaces and balanced parentheses."""
    # Inline examples are not rendered links; table parsing deliberately differs.
    line = re.sub(r"(`+).*?\1", "", line)
    for match in re.finditer(r"(?<!!)\]\(|!\[[^\]]*\]\(", line):
        start = match.end()
        if start >= len(line):
            continue
        if line[start] == "<":
            end = line.find(">", start + 1)
            if end >= 0:
                yield line[start + 1:end]
            continue
        depth, end = 0, start
        while end < len(line):
            char = line[end]
            if char == "\\" and end + 1 < len(line):
                end += 2
                continue
            if char == ")" and depth == 0:
                break
            if char.isspace() and depth == 0:
                break
            depth += (char == "(") - (char == ")")
            end += 1
        if end > start:
            yield re.sub(r"\\([() ])", r"\1", line[start:end])


def lean_run(run):
    try:
        return json_comment({"text": (Path(run) / "run.md").read_text(encoding="utf-8")}, "review-run").get("contract_version") == 3
    except (OSError, ValueError):
        return False


def check_lean_run(run, artifact=None):
    """Three practical gates; event history is optional diagnostic data."""
    import artifacts
    import sources
    from types import SimpleNamespace
    run = Path(run).resolve()
    gates = {"read_complete": True, "reports_present": True, "core_checked": True}
    issues, checked = [], []

    def fail(gate, path, message):
        gates[gate] = False
        issues.append({"file": str(path), "code": gate, "message": message, "severity": "error"})

    if artifact:
        path = (run / artifact).resolve()
        try:
            if run not in path.parents:
                raise ValueError("Artifact must be inside the run")
            if path.suffix == ".json":
                doc = artifacts.load(path)
                if doc["meta"]["kind"] == "check":
                    report = (run / doc["binding"]["report"]).resolve()
                    assessment = artifacts.check_assessment(run, report)
                    if not assessment["completed"] or assessment["issues"]:
                        raise ValueError("; ".join(assessment["issues"]) or "Check incomplete")
            else:
                artifacts.report_binding(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            fail("reports_present", path, str(error))
        return {"ok": not issues, "checked": [str(path)], "issues": issues}

    try:
        manifest = sources.load_manifest(run / "sources.json")
        papers = [e["id"] for e in manifest["sources"] if e["kind"] == "paper"]
        if not papers:
            raise ValueError("No registered papers")
    except (OSError, ValueError) as error:
        for gate in gates:
            fail(gate, run / "sources.json", str(error))
        return {"ok": False, "gates": gates, "issues": issues, "checked": checked}
    for ident in papers:
        path = run / "papers" / (ident + ".json")
        checked.append(str(path))
        try:
            paper = artifacts.load(path)
            if paper["meta"]["id"] != ident or paper["meta"]["kind"] != "paper":
                raise ValueError("Wrong report identity")
        except (OSError, ValueError, KeyError, TypeError) as error:
            for gate in gates:
                fail(gate, path, str(error))
            continue
        try:
            result, _ = sources.coverage(SimpleNamespace(manifest=str(run / "sources.json"), paper=ident, report=str(path)))
            if not result["ok"] or paper["coverage"]["gaps"]:
                fail("read_complete", path, "Unread or changed material: " + json.dumps(result["issues"], ensure_ascii=False))
        except (OSError, ValueError, KeyError, TypeError) as error:
            fail("read_complete", path, str(error))
        try:
            artifacts.check_views([path])
        except (OSError, ValueError) as error:
            fail("reports_present", path, str(error))
        assessment = artifacts.check_assessment(run, path)
        undisclosed = [item for item in assessment["omissions"] if not any(item in limit for limit in paper["limitations"])]
        if not assessment["completed"] or undisclosed:
            fail("core_checked", path, "; ".join(assessment["issues"] + assessment["omissions"]) or "Independent check missing")
        for point in paper["claims"]:
            verdict = assessment["claims"].get(point["id"], "pending")
            if point["id"] not in assessment["reasons"] or verdict == "revise" or (verdict == "pending" and not point["uncertainty"].strip()):
                fail("core_checked", path, point["id"] + ": unresolved correction or undisclosed uncertainty")
    path = run / "synthesis.md"
    checked.append(str(path))
    try:
        text = path.read_text(encoding="utf-8")
        artifacts.report_binding(path)
        body = re.sub(r"<!--.*?-->|<a[^>]*></a>", "", text, flags=re.S)
        body = re.sub(r"^#+.*$", "", body, flags=re.M)
        if len(body.strip()) < 80 or any(ident not in text for ident in papers):
            raise ValueError("Synthesis needs substantive content covering every paper")
        assessment = artifacts.check_assessment(run, path)
        if not assessment["completed"] or any(item not in text for item in assessment["omissions"]):
            fail("core_checked", path, "; ".join(assessment["issues"] + assessment["omissions"]) or "Independent synthesis check missing")
        for key, verdict in assessment["claims"].items():
            if key not in assessment["reasons"] or verdict == "revise" or (verdict == "pending" and not re.search(r"pending|uncertain|待確認|無法判定", text, re.I)):
                fail("core_checked", path, key + ": unresolved synthesis point")
    except (OSError, ValueError, KeyError, TypeError) as error:
        fail("reports_present", path, str(error))
        fail("core_checked", path, "Synthesis unavailable for checking")
    warnings = []
    state = json_comment({"text": (run / "run.md").read_text(encoding="utf-8")}, "review-run")
    if not state.get("started_at"):
        warnings.append("Start time unavailable; timing comparison is unavailable")
    return {"ok": all(gates.values()), "gates": gates, "issues": issues, "warnings": warnings, "checked": checked}


def check_run(run, artifact=None):
    run = Path(run).resolve()
    if lean_run(run):
        return check_lean_run(run, artifact)
    issues, documents = [], {}

    def issue(path, code, message, line=None, severity="error"):
        issues.append({"file": str(path), "line": line, "severity": severity,
                       "code": code, "message": message})

    def inside(path):
        return path == run or run in path.parents

    all_paths = sorted(set([*(current_path(p) for pattern in ("papers/*.md", "checks/*.md", "papers/*.json", "checks/*.json") for p in run.glob(pattern)),
                            *(run / name for name in ("synthesis.md", "run.md") if (run / name).exists())]))
    selected = None
    if artifact:
        selected = (run / artifact).resolve()
        if not inside(selected):
            issue(selected, "artifact-path", "Artifact must be inside the run directory")
            return {"ok": False, "checked": [], "issues": issues}
        selected = current_path(selected)
        if selected not in all_paths:
            all_paths.append(selected)
    targets = {selected} if selected else set(all_paths)
    if not targets:
        issue(run, "no-artifacts", "No paper, synthesis or check artifacts found")

    # Load reports too when checking one artifact, so references and versions resolve.
    for path in all_paths:
        try:
            data = path.read_bytes()
            text = data.decode("utf-8-sig")
            if path.suffix == ".json":
                import artifacts
                import sources
                value = artifacts.load(path)
                artifacts.validate_sources(value, sources.load_manifest(run / "sources.json"))
                text = artifacts.render(value)
        except (OSError, ValueError) as error:
            if path in targets:
                issue(path, "unreadable", str(error))
            continue
        lines, fence = visible_lines(text)
        rendered = "\n".join(line for _, line in lines)
        matches = META.findall(rendered)
        meta = None
        if len(matches) == 1:
            try:
                meta = json.loads(matches[0])
                if not isinstance(meta, dict):
                    raise ValueError("Metadata must be a JSON object")
            except (ValueError, TypeError) as error:
                meta = None
                if path in targets:
                    issue(path, "metadata", str(error))
        elif path in targets and path.name != "run.md":
            issue(path, "metadata", "Expected exactly one current review-meta comment")
        documents[path] = {"data": data, "lines": lines, "text": rendered,
                           "meta": meta, "anchors": ANCHOR.findall(rendered)}
        if path not in targets:
            continue
        if fence:
            issue(path, "fence", "Unclosed code fence", fence[2])
        for number, line in enumerate(text.splitlines(), 1):
            if "\ufffd" in line or re.search(r"[\u0080-\u009f]|\?(?=\d)", line):
                issue(path, "encoding-suspect", "Inspect possible corrupted characters against source",
                      number, "warning")
        for number, line in lines:
            for target in link_targets(line):
                if target.startswith("#") or (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target)
                                               and not re.match(r"^[A-Za-z]:[\\/]", target)):
                    continue
                local = unquote(target.split("#", 1)[0].split("?", 1)[0])
                if local and not (path.parent / local).exists():
                    issue(path, "link", f"Missing local target: {target}", number)
        # A table begins only when a header is followed by a separator row.
        for index in range(1, len(lines)):
            number, line = lines[index]
            if not line.lstrip().startswith("|"):
                continue
            separator = table_cells(line)
            if not separator or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
                continue
            header_number, header = lines[index - 1]
            if number != header_number + 1 or not header.lstrip().startswith("|"):
                continue
            width = len(separator)
            if len(table_cells(header)) != width:
                issue(path, "table", "Header/separator column counts differ", header_number)
            previous = number
            for row_number, row in lines[index + 1:]:
                if row_number != previous + 1 or not row.lstrip().startswith("|"):
                    break
                if len(table_cells(row)) != width:
                    issue(path, "table", f"Expected {width} columns; escape literal pipes", row_number)
                previous = row_number

    declarations = {}
    for path, doc in documents.items():
        for claim in doc["anchors"]:
            declarations.setdefault(claim, []).append(path)
    for path in targets:
        doc = documents.get(path)
        if doc is None:
            continue
        meta = doc["meta"]
        if meta is not None:
            required = ("kind", "id", "author", "revision")
            if any(not isinstance(meta.get(key), str) or not meta[key].strip() for key in required):
                issue(path, "metadata-fields", "kind, id, author and revision must be nonempty strings")
            if meta.get("kind") not in ("paper", "synthesis", "check"):
                issue(path, "metadata-kind", "Unknown artifact kind")
            if "contract_version" in meta and meta["contract_version"] != 2:
                issue(path, "metadata-fields", "Unsupported contract_version")
            if meta.get("contract_version") == 2 and meta.get("kind") != "check":
                for number, line in doc["lines"]:
                    label = re.fullmatch(r"\s*Revision:\s*(\S+)\s*", line)
                    cells = table_cells(line) if line.lstrip().startswith("|") else []
                    revision = label[1] if label else (cells[1] if len(cells) == 2 and cells[0] == "Revision" else None)
                    if revision is not None and revision.strip("`*") != meta.get("revision"):
                        issue(path, "revision-label", "Visible revision differs from metadata", number)
            expected = "S" if path.stem == "synthesis" else path.stem
            if meta.get("id") != expected:
                issue(path, "metadata-id", f"Expected artifact id {expected}")
            expected_kind = "check" if path.parent.name == "checks" else ("synthesis" if expected == "S" else "paper")
            if meta.get("kind") != expected_kind:
                issue(path, "metadata-kind", f"Expected {expected_kind} at this path")
            if meta.get("kind") == "check":
                report_name = meta.get("report")
                report = (run / report_name).resolve() if isinstance(report_name, str) else None
                source = documents.get(report)
                correct = current_path(run / ("synthesis.md" if expected == "S" else f"papers/{expected}.md"))
                if report != correct or not source or not source["meta"]:
                    issue(path, "check-report", "Check must bind its matching report with readable metadata")
                else:
                    author = source["meta"].get("author")
                    if meta.get("report_author") != author or meta.get("author") == author:
                        issue(path, "check-author", "Author binding differs or checker is the report author")
                    if meta.get("revision") != source["meta"].get("revision"):
                        issue(path, "check-revision", "Current check revision differs from report")
                    if meta.get("sha256") != hashlib.sha256(source["data"]).hexdigest():
                        issue(path, "check-hash", "Current check SHA-256 differs from report bytes")
                    if meta.get("contract_version") == 2:
                        try:
                            status = json_comment(doc, "review-status")
                            round_no, claims = status.get("round"), status.get("claims")
                            if type(round_no) is not int or round_no not in (0, 1):
                                raise ValueError("Current check round must be 0 or 1")
                            if not isinstance(claims, dict) or set(claims) != set(source["anchors"]):
                                raise ValueError("Current verdicts must cover every declared report claim")
                            allowed = ("supported", "revise", "unresolved", "pending", "withdrawn")
                            if any(value not in allowed for value in claims.values()):
                                raise ValueError("Invalid current claim verdict")
                            withdrawn = status.get("withdrawn")
                            if not isinstance(withdrawn, list) or any(not isinstance(x, str) for x in withdrawn):
                                raise ValueError("withdrawn must be a list of claim IDs")
                            if len(withdrawn) != len(set(withdrawn)) or set(withdrawn) != {k for k, v in claims.items() if v == "withdrawn"}:
                                raise ValueError("Withdrawn list and verdicts disagree")
                            verdict = status.get("verification")
                            if verdict not in ("pending", "passed", "needs-confirmation"):
                                raise ValueError("Invalid current verification state")
                            if verdict == "passed" and any(v != "supported" for v in claims.values()):
                                raise ValueError("A pass cannot contain unchecked/unresolved/withdrawn claims")
                        except (ValueError, TypeError) as error:
                            issue(path, "current-status", str(error))
        for claim in doc["anchors"]:
            if len(declarations[claim]) > 1:
                issue(path, "claim-duplicate", f"Repeated claim declaration: {claim}")
            if meta and (meta.get("kind") == "check" or not claim.startswith(str(meta.get("id")) + "-C")):
                issue(path, "claim-owner", f"Claim declaration does not belong to this report: {claim}")
            if path.name == "run.md":
                issue(path, "claim-owner", "Declare claims in reports, not the coordinator index")
        without_anchors = ANCHOR.sub("", doc["text"])
        for claim in sorted(set(REFERENCE.findall(without_anchors))):
            if claim not in declarations:
                issue(path, "claim-reference", f"Undeclared claim: {claim}")
    timing = check_workflow(run, documents, targets, issue)
    result = {"ok": not any(item["severity"] == "error" for item in issues),
              "checked": sorted(str(path) for path in targets), "issues": issues}
    if timing is not None:
        result["timing"] = timing
    return result


def record_event(run, name, artifact=None, agent=None, round_no=None):
    """Coordinator-only clock writes; existing observations are never backdated."""
    path = Path(run) / "run.md"
    text = path.read_text(encoding="utf-8")
    state = json_comment({"text": text}, "review-run")
    now = datetime.now(timezone.utc).isoformat()
    if state.get("contract_version") == 3:
        result = {"ok": True}
        if name == "start":
            if state.get("started_at"):
                raise ValueError("Start already recorded")
            state.update(started_at=now, delivered_at=None, execution="active")
        elif name == "first-report":
            state.setdefault("first_report_at", now)
        elif name == "delivery":
            result = check_lean_run(Path(run))
            state.update(delivered_at=now, execution="finished", delivery="complete" if result["ok"] else "partial", gates=result["gates"])
        else:
            raise ValueError("Lean runs record start, first-report and delivery only")
        replacement = "<!-- review-run " + json.dumps(state, ensure_ascii=True) + " -->"
        temporary = path.with_suffix(".md.tmp")
        temporary.write_text(re.sub(r"<!-- review-run .*? -->", lambda _: replacement, text), encoding="utf-8")
        temporary.replace(path)
        return {**result, "event": name, "at": now}
    if name == "start":
        if state.get("started_at") is not None or state.get("events"):
            raise ValueError("Start already recorded; preserve the original clock")
        state.update(started_at=now, delivered_at=None, execution="active")
    elif name == "delivery":
        if state.get("execution") != "active":
            raise ValueError("Delivery requires an active run")
        result = checkpoint_check(run, None, "final", views=True, complete=True)
        if not result["ok"]:
            return result
        now = datetime.now(timezone.utc).isoformat()
        state.update(delivered_at=now, execution="finished")
    else:
        if state.get("execution") != "active":
            raise ValueError("Record events only in an active run")
        previous = state["events"][-1]["at"] if state["events"] else state["started_at"]
        if utc_time(now) < utc_time(previous):
            raise ValueError("Clock precedes the last observation")
        allowed = {f"{stage}-{action}" for stage in ("reading", "draft", "check", "repair")
                   for action in ("dispatched", "returned")} | {"verification-ready"}
        if name not in allowed or artifact not in state["artifacts"] or not agent or not agent.strip():
            raise ValueError("Require a known event, registered artifact and actual agent")
        stage = name.split("-")[0]
        if ((stage == "check" and round_no not in (0, 1)) or
                (stage == "repair" and round_no != 1) or
                (stage not in ("check", "repair") and round_no is not None)):
            raise ValueError("Invalid event round")
        if any(e["artifact"] == artifact and e["event"] == name and e["round"] == round_no
               for e in state["events"]) and name != "verification-ready":
            raise ValueError("Event already recorded")
        state["events"].append(dict(at=now, artifact=artifact, event=name, agent=agent, round=round_no))
        if name == "check-dispatched":
            state["artifacts"][artifact]["round"] = round_no
        if name == "repair-dispatched":
            state["artifacts"][artifact]["repair_used"] = 1
    replacement = "<!-- review-run " + json.dumps(state, ensure_ascii=True) + " -->"
    updated = re.sub(r"<!-- review-run .*? -->", lambda _: replacement, text)
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(path)
    return {"ok": True, "event": name, "at": now}


def require_complete(run, result):
    """Completeness is stricter than a valid, honestly partial delivery."""
    if lean_run(Path(run)):
        return check_lean_run(Path(run))
    try:
        state = json_comment({"text": (Path(run) / "run.md").read_text(encoding="utf-8")}, "review-run")
        if "S" not in state["artifacts"] or not any(k.startswith("P") for k in state["artifacts"]):
            raise ValueError("Register all papers and synthesis before complete delivery")
        import sources
        manifest = sources.load_manifest(Path(run) / "sources.json")
        expected = {entry["id"] for entry in manifest["sources"] if entry["kind"] == "paper"} | {"S"}
        if set(state["artifacts"]) != expected:
            raise ValueError("Run artifact inventory differs from registered corpus")
        for ident, item in state["artifacts"].items():
            report = Path(run) / ("synthesis.md" if ident == "S" else f"papers/{ident}.json")
            check = Path(run) / ("checks/synthesis.json" if ident == "S" else f"checks/{ident}.json")
            if not report.is_file() or not check.is_file() or item["verification"] == "pending":
                raise ValueError(f"{ident}: missing report or completed independent check")
            if not any(e["artifact"] == ident and e["event"] == "check-returned"
                       and e["round"] == item["round"] for e in state["events"]):
                raise ValueError(f"{ident}: current independent check has not returned")
            if ident != "S" and json.loads(report.read_text(encoding="utf-8"))["coverage"]["status"] != "complete":
                raise ValueError(f"{ident}: reading coverage incomplete")
    except (OSError, ValueError, KeyError, TypeError) as error:
        result["ok"] = False
        result["issues"].append({"code": "incomplete-delivery", "message": str(error)})
    return result


def checkpoint_check(run, artifact, checkpoint, views=False, complete=False):
    if lean_run(Path(run)):
        return check_lean_run(Path(run), artifact)
    # The coordinator serializes checkpoint calls; failed attempts remain on disk.
    journal = Path(run) / "preflight-attempts.jsonl"
    history = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()] if journal.exists() else []
    previous = [item for item in history if item["checkpoint"] == checkpoint]
    if any(not item["ok"] for item in previous) and len(previous) >= 2:
        return {"ok": False, "issues": [{"code": "mechanical-limit", "message": "Checkpoint exhausted; disclose preflight limitation."}]}
    result = check_run(run, artifact)
    if complete:
        require_complete(run, result)
    if views:
        import artifacts
        try:
            artifacts.check_views(artifacts.artifact_paths([run]))
        except (OSError, ValueError) as error:
            result["ok"] = False
            result["issues"].append({"code": "generated-view", "message": str(error)})
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"checkpoint": checkpoint, "at": datetime.now(timezone.utc).isoformat(),
                                 "ok": result["ok"], "issues": result["issues"]}, ensure_ascii=True) + "\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--artifact", help="One path relative to run; otherwise check all current artifacts")
    parser.add_argument("--checkpoint", help="Persist attempts; use the same name for the initial check and its one retry")
    parser.add_argument("--views", action="store_true", help="Also require current generated Markdown (with --checkpoint)")
    parser.add_argument("--complete", action="store_true", help="Require all registered reports and independent checks")
    parser.add_argument("--record-event", help="Stamp start or a workflow event with current UTC; coordinator only")
    parser.add_argument("--agent")
    parser.add_argument("--round", type=int, choices=(0, 1))
    args = parser.parse_args(argv)
    if args.record_event:
        if args.checkpoint or args.views or args.complete:
            parser.error("Recording and validation are separate operations")
        try:
            result = record_event(args.run, args.record_event, args.artifact, args.agent, args.round)
        except (OSError, ValueError, KeyError, TypeError) as error:
            result = {"ok": False, "error": str(error)}
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    if args.complete and (args.artifact or not args.checkpoint or not args.views):
        parser.error("--complete requires whole-run --checkpoint and --views")
    if args.views and not args.checkpoint:
        parser.error("--views requires --checkpoint")
    result = checkpoint_check(args.run, args.artifact, args.checkpoint, args.views, args.complete) if args.checkpoint else check_run(args.run, args.artifact)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
