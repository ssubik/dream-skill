#!/usr/bin/env python3
"""Local versioned memory. No network, dependencies, or model calls."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3] / "memory"
NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}\Z")
STAMP = re.compile(r"(\d{8}T\d{6}Z)-[0-9a-f]{8}\Z")
INDEX_LINES = 120
INDEX_BYTES = 12288
# Unattended cadence: roughly daily, with a floor so a single episode does not
# create a version. Reconciliation is a separate, attended lane; a long
# unattended streak means duplicates have not been merged for that many cycles.
CADENCE_HOURS = 20
UNATTENDED_MIN_EPISODES = 3
COMPACT_AFTER_STREAK = 7


def identifier(value):
    if not NAME.fullmatch(value):
        raise ValueError("Invalid version or dream identifier")
    return value


def consolidated_at(version):
    # Promoted versions carry their dream's UTC stamp; `initial` has none.
    match = STAMP.fullmatch(version)
    return None if not match else datetime.strptime(
        match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path):
    if path.is_symlink():
        raise ValueError(f"Symlink not allowed: {path}")
    result = {}
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"Symlink not allowed: {item}")
        if item.is_file():
            result[item.relative_to(path).as_posix()] = digest(item)
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def active():
    # A fresh checkout may omit the local CURRENT pointer.
    pointer = ROOT / "CURRENT"
    version = identifier(pointer.read_text().strip()) if pointer.exists() else "initial"
    path = ROOT / "stores" / version
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"Missing or unsafe active store: {version}")
    return version, path


def pending(store):
    processed = read_json(store / "processed.json")
    paths = sorted((ROOT / "episodes").glob("*.md"))
    result = []
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"Symlink episode: {path}")
        old = processed.get(path.name)
        if old is not None and old != digest(path):
            raise ValueError(f"Processed episode changed: {path.name}; restore it and capture a correction separately")
        if old is None:
            result.append(path)
    return result


@contextmanager
def lock():
    path = ROOT / ".write-lock"
    try:
        path.mkdir()
    except FileExistsError:
        raise ValueError("Memory writer lock exists; retry after the other writer completes")
    try:
        (path / "owner").write_text(str(os.getpid()), encoding="utf-8")
        yield
    finally:
        (path / "owner").unlink(missing_ok=True)
        path.rmdir()


def switch(version):
    temp = ROOT / (".CURRENT-" + uuid.uuid4().hex)
    try:
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(version + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, ROOT / "CURRENT")
    finally:
        temp.unlink(missing_ok=True)


def validate(store):
    files = inventory(store)
    if "MEMORY.md" not in files or "processed.json" not in files:
        raise ValueError("Store requires MEMORY.md and processed.json")
    for name in files:
        if name not in {"MEMORY.md", "processed.json"} and not re.fullmatch(r"topics/[a-z0-9][a-z0-9-]*\.md", name):
            raise ValueError(f"Unexpected store file: {name}")
    processed = read_json(store / "processed.json")
    if not isinstance(processed, dict) or any(
        not isinstance(k, str) or Path(k).name != k or not k.endswith(".md")
        or not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
        for k, v in processed.items()
    ):
        raise ValueError("Invalid processed episode ledger")
    index = (store / "MEMORY.md").read_text(encoding="utf-8")
    if len(index.splitlines()) > INDEX_LINES or len(index.encode()) > INDEX_BYTES:
        raise ValueError(f"Index exceeds {INDEX_LINES} lines / {INDEX_BYTES // 1024} KiB")
    links = []
    for line in index.splitlines():
        if not line.strip() or re.fullmatch(r"#{1,3} .+", line):
            continue
        match = re.fullmatch(r"- \[[^\]]+\]\((topics/[a-z0-9][a-z0-9-]*\.md)\)(?: [—-] .+)?", line)
        if not match:
            raise ValueError(f"Index must contain headings and one-line topic links: {line}")
        links.append(match.group(1))
    topics = {name for name in files if name.startswith("topics/")}
    if len(links) != len(set(links)) or set(links) != topics:
        raise ValueError("Index has duplicate, broken, or missing topic links")
    for name in topics:
        body = (store / name).read_text(encoding="utf-8")
        parts = body.split("---", 2)
        if len(parts) != 3 or parts[0] != "":
            raise ValueError(f"Missing frontmatter: {name}")
        fields = dict(re.findall(r"^([a-z]+):\s*(.+)$", parts[1], re.M))
        if not all(fields.get(k) for k in ("name", "description", "type", "updated")):
            raise ValueError(f"Missing topic metadata: {name}")
        if fields["type"] not in {"project", "user", "feedback", "reference", "insight"}:
            raise ValueError(f"Invalid type: {name}")
        datetime.strptime(fields["updated"], "%Y-%m-%d")
        for field in ("Kind:", "Scope:", "Evidence:"):
            if field not in parts[2]:
                raise ValueError(f"Missing {field} in {name}")
    return {"topics": len(topics), "index_lines": len(index.splitlines())}


def topic_blocks(text):
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0] != "":
        raise ValueError("Missing frontmatter")
    fields = dict(re.findall(r"^([a-z]+):\s*(.+)$", parts[1], re.M))
    fields.pop("updated", None)
    blocks, current = [], []
    for line in parts[2].splitlines(True):
        if line.startswith("## ") and current:
            blocks.append("".join(current))
            current = []
        current.append(line)
    if current:
        blocks.append("".join(current))
    return fields, blocks


def additive_only(source, candidate):
    """Restrict a candidate to additions, so promotion needs no human reading.

    Existing claims must survive byte-identical. New topics and new sections are
    allowed; merging duplicates, rewording, and resolving conflicts are not,
    because those are the judgements that require review.
    """
    before, after = inventory(source), inventory(candidate)
    missing = sorted(set(before) - set(after))
    if missing:
        raise ValueError(f"Unattended consolidation cannot remove: {', '.join(missing)}")
    for name in sorted(before):
        if name == "processed.json":
            continue  # Helper-owned; check_dream already requires it unchanged.
        old = (source / name).read_text(encoding="utf-8")
        new = (candidate / name).read_text(encoding="utf-8")
        if old == new:
            continue
        if name == "MEMORY.md":
            kept = Counter(line.strip() for line in old.splitlines() if line.strip())
            kept.subtract(Counter(line.strip() for line in new.splitlines() if line.strip()))
            dropped = sorted(line for line, count in kept.items() if count > 0)
            if dropped:
                raise ValueError(f"Unattended consolidation cannot rewrite index lines: {dropped[0]}")
            continue
        old_fields, old_blocks = topic_blocks(old)
        new_fields, new_blocks = topic_blocks(new)
        if old_fields != new_fields:
            raise ValueError(f"Unattended consolidation cannot change topic metadata: {name}")
        # Trailing whitespace only: appending a section necessarily reflows the
        # blank line after the one before it. Claim text still must match exactly.
        remaining = Counter(block.rstrip() for block in old_blocks)
        remaining.subtract(Counter(block.rstrip() for block in new_blocks))
        lost = sorted(block for block, count in remaining.items() if count > 0)
        if lost:
            heading = lost[0].splitlines()
            raise ValueError(f"Unattended consolidation cannot rewrite existing claims: "
                             f"{name} / {heading[0].strip() if heading else 'preamble'}")
    return {"added_topics": len(set(after) - set(before))}


def dream_path(value):
    path = ROOT / "dreams" / identifier(value)
    if not path.is_dir() or path.is_symlink():
        raise ValueError("Dream does not exist or is unsafe")
    return path


def check_dream(path):
    manifest = read_json(path / "manifest.json")
    if inventory(path / "input") != manifest["input_hashes"]:
        raise ValueError("Dream input snapshot changed")
    if inventory(path / "episodes") != manifest["episodes"]:
        raise ValueError("Dream episode snapshot changed")
    if (path / "output" / "processed.json").read_bytes() != (path / "input" / "processed.json").read_bytes():
        raise ValueError("Do not edit the helper-owned processed ledger")
    result = validate(path / "output")
    report = path / "report.md"
    if not report.is_file() or report.is_symlink():
        raise ValueError("Write report.md before validation or promotion")
    report_text = report.read_text(encoding="utf-8")
    if "## Verification" not in report_text or len(report_text.strip()) < 100:
        raise ValueError("Report must describe changes and include ## Verification")
    for name in manifest["episodes"]:
        if name not in report_text:
            raise ValueError(f"Report must account for episode: {name}")
    return manifest, result


def unattended_streak(version):
    """Consecutive additive-only versions ending at the active one."""
    stores = ROOT / "stores"
    names = sorted(n for n in (p.name for p in stores.iterdir() if p.is_dir()) if consolidated_at(n))
    names = names[:names.index(version) + 1] if version in names else []
    count = 0
    for name in reversed(names):
        if not (ROOT / "dreams" / name / "unattended").is_file():
            break
        count += 1
    return count


def status():
    version, store = active()
    items = pending(store)
    candidates = []
    for path in sorted((ROOT / "dreams").glob("*")):
        if path.is_dir() and not (ROOT / "stores" / path.name).exists():
            candidates.append(path.name)
    index = (store / "MEMORY.md").read_text(encoding="utf-8")
    lines, size = len(index.splitlines()), len(index.encode())
    topics = len(list((store / "topics").glob("*.md"))) if (store / "topics").is_dir() else 0
    since = consolidated_at(version)
    hours = None if since is None else round(
        (datetime.now(timezone.utc) - since).total_seconds() / 3600, 1)
    streak = unattended_streak(version)
    print(json.dumps({"version": version, "pending_count": len(items),
                      "recent_pending": [str(p.relative_to(ROOT.parent.parent)) for p in items[-5:]],
                      "dream_recommended": len(items) >= 10,
                      "unattended_recommended": len(items) >= UNATTENDED_MIN_EPISODES
                      and (hours is None or hours >= CADENCE_HOURS),
                      "hours_since_consolidation": hours,
                      "unattended_streak": streak,
                      "compaction_recommended": streak >= COMPACT_AFTER_STREAK
                      or lines >= 0.75 * INDEX_LINES or size >= 0.75 * INDEX_BYTES,
                      "topics": topics, "index_lines": lines, "index_bytes": size,
                      "candidates": candidates}, indent=2))


def begin(limit):
    if not 1 <= limit <= 100:
        raise ValueError("Batch limit must be between 1 and 100")
    with lock():
        version, store = active()
        validate(store)
        selected = pending(store)[:limit]
        before = inventory(store)
        episode_hashes = {p.name: digest(p) for p in selected}
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        path = ROOT / "dreams" / name
        path.mkdir(parents=True)
        shutil.copytree(store, path / "input")
        shutil.copytree(store, path / "output")
        (path / "episodes").mkdir()
        for episode in selected:
            shutil.copy2(episode, path / "episodes" / episode.name)
        if inventory(path / "input") != before or inventory(store) != before or inventory(path / "episodes") != episode_hashes:
            raise ValueError("Sources changed while snapshotting; leave this candidate unused and retry")
        write_json(path / "manifest.json", {"base": version, "input_hashes": before,
                                           "episodes": episode_hashes})
    print(json.dumps({"dream": name, "base": version, "selected_episodes": len(selected),
                      "candidate": str(path / "output")}, indent=2))


def promote(name, unattended=False):
    path = dream_path(name)
    with lock():
        manifest, result = check_dream(path)
        if unattended:
            result = {**result, **additive_only(path / "input", path / "output")}
        version, store = active()
        if version != manifest["base"] or inventory(store) != manifest["input_hashes"]:
            raise ValueError("Active memory changed; start a fresh dream")
        for episode, sha in manifest["episodes"].items():
            original = ROOT / "episodes" / episode
            if original.is_symlink() or not original.is_file() or digest(original) != sha:
                raise ValueError(f"Source episode changed or disappeared: {episode}")
        target = ROOT / "stores" / identifier(name)
        if target.exists():
            raise ValueError("Version already exists; inspect status instead of overwriting it")
        expected = inventory(path / "output")
        shutil.copytree(path / "output", target)
        if inventory(target) != expected or inventory(path / "output") != expected:
            raise ValueError("Candidate changed while copying; active memory remains unchanged")
        processed = read_json(target / "processed.json")
        processed.update(manifest["episodes"])
        write_json(target / "processed.json", processed)
        validate(target)
        if unattended:
            (path / "unattended").write_text("additive-only promotion\n", encoding="utf-8")
        switch(name)
    print(json.dumps({"promoted": name, "previous": version, "unattended": unattended,
                      "validation": result,
                      "rollback": f"python3 .kiro/skills/dream/scripts/memory.py rollback {version}"}, indent=2))


def rollback(name):
    name = identifier(name)
    with lock():
        previous, _ = active()
        validate(ROOT / "stores" / name)
        switch(name)
    print(json.dumps({"active": name, "previous": previous}))


def diff(name):
    path = dream_path(name)
    files = set(inventory(path / "input")) | set(inventory(path / "output"))
    for name in sorted(files):
        before, after = path / "input" / name, path / "output" / name
        a = before.read_text(encoding="utf-8").splitlines(True) if before.exists() else []
        b = after.read_text(encoding="utf-8").splitlines(True) if after.exists() else []
        sys.stdout.writelines(difflib.unified_diff(a, b, fromfile="input/" + name, tofile="output/" + name))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("begin").add_argument("--limit", type=int, default=20)
    check = sub.add_parser("validate")
    check.add_argument("--dream")
    check.add_argument("--unattended", action="store_true")
    push = sub.add_parser("promote")
    push.add_argument("id")
    push.add_argument("--unattended", action="store_true")
    for command in ("rollback", "diff"):
        sub.add_parser(command).add_argument("id")
    args = parser.parse_args()
    try:
        if args.command == "status":
            status()
        elif args.command == "begin":
            begin(args.limit)
        elif args.command == "validate":
            if args.unattended and not args.dream:
                raise ValueError("--unattended applies to a dream candidate; pass --dream <id>")
            if args.dream:
                path = dream_path(args.dream)
                result = check_dream(path)[1]
                if args.unattended:
                    result = {**result, **additive_only(path / "input", path / "output")}
            else:
                result = validate(active()[1])
            print(json.dumps({"valid": True, **result}))
        elif args.command == "promote":
            promote(args.id, args.unattended)
        elif args.command == "rollback":
            rollback(args.id)
        elif args.command == "diff":
            diff(args.id)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Memory error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
