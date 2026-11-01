#!/usr/bin/env python3
"""Redacted heuristic scan of Git blobs in specified history; no repository writes.

Does not inspect working-tree files, index-only changes, GitHub-hosted artifacts,
or contents of files classified as sensitive by filename.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SIGNATURES = {
    "private_key_header": re.compile(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "google_api_key": re.compile(rb"\bAIza[A-Za-z0-9_-]{30,}\b"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_style_key": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "credential_assignment": re.compile(
        rb"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*"
        rb"[\"']?[A-Za-z0-9+/_.:-]{16,}"
    ),
}
OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def git(repo: Path, *args: str, input_data: bytes | None = None) -> bytes:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], input=input_data,
        capture_output=True, env=env, check=False,
    )
    if proc.returncode:
        # Git errors, not examined blob data; do not echo arbitrary contents.
        raise RuntimeError(f"git {args[0]} failed (exit {proc.returncode})")
    return proc.stdout


def sensitive_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return (
        name == ".env" or name.startswith(".env.")
        or name in {"id_rsa", "id_ed25519", "id_ecdsa", "kaggle.json",
                    "credentials.json", "service-account.json"}
        or name.endswith((".pem", ".p12", ".pfx", ".key"))
    )


def collect_refs(repo: Path, all_refs: bool, refs: list[str]) -> dict[str, set[str]]:
    if all_refs:
        raw = git(repo, "rev-list", "--objects", "--all")
    else:
        roots = []
        for ref in refs:
            resolved = git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
            sha = resolved.decode("ascii").strip()
            if not OID.fullmatch(sha):
                raise RuntimeError(f"unable to resolve commit ref: {ref!r}")
            roots.append(sha)
        raw = git(repo, "rev-list", "--objects", *roots)
    objs: dict[str, set[str]] = {}
    for line in raw.decode("utf-8", "replace").splitlines():
        sha, _, path = line.partition(" ")
        if not OID.fullmatch(sha):
            raise RuntimeError("cannot parse git rev-list output")
        objs.setdefault(sha, set())
        if path:
            objs[sha].add(path)
    # rev-list --objects emits at most one name for each object. Recover all
    # historical blob paths from commit diffs, including roots and merges.
    # This must complete before examining any blob content: a blob may also
    # have been committed as .env even when rev-list names it as a.txt.
    history = git(repo, "log", "--raw", "-m", "--no-renames", "--no-abbrev",
                  "--root", "--format=", "-z", *( ["--all"] if all_refs else roots))
    fields = history.split(b"\0")
    index = 0
    while index < len(fields):
        metadata = fields[index].lstrip(b"\n")
        index += 1
        if not metadata:
            continue
        parts = metadata.split()
        if len(parts) != 5 or not parts[0].startswith(b":"):
            raise RuntimeError("cannot parse git log raw-diff metadata")
        if index >= len(fields):
            raise RuntimeError("missing path in git log raw-diff output")
        path = fields[index].decode("utf-8", "replace")
        index += 1
        if parts[1] == b"160000":
            # Git submodule: not a blob stored in this repository.
            continue
        sha = parts[3].decode("ascii")
        if sha in objs and parts[1] != b"000000":
            objs[sha].add(path)
    return objs


def collect_unreachable(repo: Path) -> set[str]:
    # Reflogs are excluded, so reflog-only commits become candidates here.
    # The Git index is still treated as a reachability root by fsck.
    raw = git(repo, "fsck", "--full", "--unreachable", "--no-reflogs", "--no-progress")
    result = set()
    for line in raw.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[:2] == ["unreachable", "blob"] and OID.fullmatch(parts[2]):
            result.add(parts[2])
    return result


def blob_metadata(repo: Path, ids: list[str]) -> list[tuple[str, int]]:
    if not ids:
        return []
    raw = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
              input_data=("\n".join(ids) + "\n").encode("ascii"))
    result = []
    for line in raw.decode("ascii", "replace").splitlines():
        parts = line.split()
        if len(parts) != 3 or not OID.fullmatch(parts[0]) or not parts[2].isdigit():
            raise RuntimeError("cannot parse git cat-file metadata")
        if parts[1] == "blob":
            result.append((parts[0], int(parts[2])))
    return result


def scan(repo: Path, objs: dict[str, set[str]], unreachable: set[str],
         max_bytes: int, max_findings: int, max_unscanned: int) -> dict:
    # Scan each identical blob only once. Multiple historical paths are retained.
    ids = sorted(set(objs) | unreachable)
    blobs = blob_metadata(repo, ids)
    findings = []
    unscanned = []
    stats = {"blobs": len(blobs), "sensitive_files_not_read": 0,
             "oversized_not_read": 0, "content_scanned": 0,
             "total_findings": 0, "total_unscanned": 0}
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env)
    assert proc.stdin is not None and proc.stdout is not None
    try:
        for sha, size in blobs:
            paths = sorted(objs.get(sha, set()))
            scope = "reachable" if sha in objs else "local_unreachable"
            path_names = paths or ["<path unavailable>"]
            if any(sensitive_path(p) for p in paths):
                stats["sensitive_files_not_read"] += 1
                reason = "sensitive_filename_content_not_read"
            elif size > max_bytes:
                stats["oversized_not_read"] += 1
                reason = "oversized_blob_not_read"
            else:
                reason = None
            if reason is not None:
                stats["total_unscanned"] += 1
                if len(unscanned) < max_unscanned:
                    unscanned.append({"object": sha, "paths": path_names,
                                      "scope": scope, "reason": reason})
                continue
            else:
                proc.stdin.write((sha + "\n").encode("ascii"))
                proc.stdin.flush()
                header = proc.stdout.readline().split()
                if len(header) != 3 or header[0].decode() != sha or header[1] != b"blob" or int(header[2]) != size:
                    raise RuntimeError("unexpected git cat-file response")
                data = proc.stdout.read(size)
                newline = proc.stdout.read(1)
                if len(data) != size or newline != b"\n":
                    raise RuntimeError("truncated git cat-file response")
                stats["content_scanned"] += 1
                # Scan raw bytes, including binary data. For NUL-containing
                # text, also scan UTF-16LE and UTF-16BE representations, with
                # or without BOM. Matches are leads requiring manual review.
                candidates = [data]
                if b"\x00" in data:
                    for encoding in ("utf-16-le", "utf-16-be"):
                        candidates.append(data.decode(encoding, errors="ignore").encode("utf-8"))
                kinds = [name for name, regex in SIGNATURES.items()
                         if any(regex.search(candidate) for candidate in candidates)]
            if kinds:
                stats["total_findings"] += 1
                if len(findings) < max_findings:
                    findings.append({"object": sha, "paths": path_names,
                                     "scope": scope, "categories": kinds})
    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError("git cat-file batch processing failed")
    findings_truncated = stats["total_findings"] > len(findings)
    unscanned_truncated = stats["total_unscanned"] > len(unscanned)
    return {"status": "completed_with_limits" if (stats["total_unscanned"]
                or findings_truncated or unscanned_truncated) else "completed",
            "statistics": stats,
            "findings_truncated": findings_truncated,
            "findings": findings,
            "unscanned_truncated": unscanned_truncated,
            "unscanned": unscanned,
            "caveats": ["Signature matches are leads, not proof of leaked credentials.",
                        "Sensitive-named files are identified but their contents are not read.",
                        "Working tree, index-only changes, remote GitHub data, and LFS objects are not scanned.",
                        "Reflog-only and unreachable blobs are local unless separately published.",
                        "Reachable blob paths are collected from historical raw diffs.",
                        "Unreachable blobs have no known path association."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--ref", action="append", help="Commit/ref root; repeatable")
    choice.add_argument("--all", action="store_true", help="All local Git refs")
    parser.add_argument("--unreachable", action="store_true", help="Also scan locally unreachable blobs")
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-findings", type=int, default=200)
    parser.add_argument("--max-unscanned", type=int, default=200)
    args = parser.parse_args()
    if args.max_bytes < 1 or args.max_findings < 1 or args.max_unscanned < 1:
        parser.error("--max-bytes, --max-findings and --max-unscanned must be positive")
    try:
        git(args.repo, "rev-parse", "--git-dir")
        objects = collect_refs(args.repo, args.all, args.ref or [])
        unreachable = collect_unreachable(args.repo) if args.unreachable else set()
        result = scan(args.repo, objects, unreachable, args.max_bytes,
                      args.max_findings, args.max_unscanned)
        result["scope"] = {"refs": "all_local_refs" if args.all else args.ref,
                           "include_local_unreachable": args.unreachable}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, OSError, UnicodeError, ValueError) as exc:
        # Never include content of scanned files in error output.
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
