"""Smoke/regression tests for the read-only redacted history scanner."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_history.py"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


class HistoryScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "tester@example.invalid")
        git(self.repo, "config", "user.name", "Test")

    def tearDown(self):
        self.tmp.cleanup()

    def run_scan(self, *args):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo),
                               *args], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout), proc.stdout

    def test_deleted_history_secret_is_redacted(self):
        marker = "ghp_" + "A" * 36
        (self.repo / "settings.txt").write_text("token=" + marker)
        git(self.repo, "add", "settings.txt")
        git(self.repo, "commit", "-qm", "initial")
        git(self.repo, "rm", "-q", "settings.txt")
        git(self.repo, "commit", "-qm", "remove")
        report, output = self.run_scan("--ref", "HEAD")
        self.assertNotIn(marker, output)
        self.assertTrue(any("github_token" in x["categories"] for x in report["findings"]))
        self.assertIn("settings.txt", str(report["findings"]))

    def test_secret_filename_is_not_read(self):
        marker = "sk-" + "B" * 36
        (self.repo / ".env").write_text("token=" + marker)
        git(self.repo, "add", ".env")
        git(self.repo, "commit", "-qm", "initial")
        report, output = self.run_scan("--all")
        self.assertNotIn(marker, output)
        self.assertEqual(report["statistics"]["sensitive_files_not_read"], 1)
        self.assertEqual(report["statistics"]["total_findings"], 0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["unscanned"][0]["reason"], "sensitive_filename_content_not_read")

    def test_identical_blob_under_sensitive_and_ordinary_paths_is_not_read(self):
        marker = "ghp_" + "Z" * 36
        (self.repo / "a.txt").write_text(marker)
        (self.repo / "z").mkdir()
        (self.repo / "z" / ".env").write_text(marker)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "initial")
        report, output = self.run_scan("--ref", "HEAD")
        self.assertNotIn(marker, output)
        self.assertEqual(report["statistics"]["content_scanned"], 0)
        self.assertEqual(report["statistics"]["sensitive_files_not_read"], 1)
        self.assertEqual(report["statistics"]["total_findings"], 0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["unscanned"][0]["paths"], ["a.txt", "z/.env"])

    def test_utf16_bomless_and_bom_secrets_are_scanned(self):
        values = [
            ("little.txt", "utf-16-le", b""),
            ("big.txt", "utf-16-be", b""),
            ("bom.txt", "utf-16-le", b"\xff\xfe"),
        ]
        tokens = []
        for i, (name, encoding, prefix) in enumerate(values):
            token = "ghp_" + chr(65 + i) * 36
            tokens.append(token)
            (self.repo / name).write_bytes(prefix + ("key=" + token).encode(encoding))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "initial")
        report, output = self.run_scan("--all")
        self.assertEqual(report["statistics"]["content_scanned"], 3)
        self.assertEqual(report["statistics"]["total_findings"], 3)
        self.assertEqual(len(report["findings"]), 3)
        for token in tokens:
            self.assertNotIn(token, output)
        self.assertTrue(all("github_token" in item["categories"] for item in report["findings"]))

    def test_unscanned_entries_do_not_exhaust_findings_cap(self):
        (self.repo / ".env").write_text("not examined")
        (self.repo / "long.txt").write_text("x" * 200)
        token = "ghp_" + "F" * 36
        (self.repo / "ordinary.txt").write_text(token)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "initial")
        report, output = self.run_scan("--ref", "HEAD", "--max-bytes", "100",
                                       "--max-findings", "1", "--max-unscanned", "1")
        self.assertNotIn(token, output)
        self.assertEqual(report["statistics"]["total_findings"], 1)
        self.assertEqual(report["statistics"]["total_unscanned"], 2)
        self.assertEqual(report["statistics"]["sensitive_files_not_read"], 1)
        self.assertEqual(report["statistics"]["oversized_not_read"], 1)
        self.assertEqual(len(report["findings"]), 1)
        self.assertIn("github_token", report["findings"][0]["categories"])
        self.assertFalse(report["findings_truncated"])
        self.assertEqual(len(report["unscanned"]), 1)
        self.assertTrue(report["unscanned_truncated"])

    def test_scan_does_not_change_repository_state(self):
        (self.repo / "a.txt").write_text("normal")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-qm", "initial")
        before_head = git(self.repo, "rev-parse", "HEAD")
        before_index = (self.repo / ".git" / "index").read_bytes()
        self.run_scan("--ref", "HEAD", "--unreachable")
        self.assertEqual(before_head, git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(before_index, (self.repo / ".git" / "index").read_bytes())

    def test_oversized_blob_is_reported_as_unscanned(self):
        (self.repo / "data.txt").write_text("normal " * 100)
        git(self.repo, "add", "data.txt")
        git(self.repo, "commit", "-qm", "initial")
        report, _ = self.run_scan("--ref", "HEAD", "--max-bytes", "10")
        self.assertEqual(report["status"], "completed_with_limits")
        self.assertEqual(report["statistics"]["oversized_not_read"], 1)

    def test_unreachable_blob_is_separate_scope(self):
        (self.repo / "a.txt").write_text("clean")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-qm", "initial")
        # hash-object -w creates a loose blob not reachable from refs.
        blob = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
                              input=b"ghp_" + b"C" * 36, capture_output=True, check=True).stdout.decode().strip()
        report, _ = self.run_scan("--all", "--unreachable")
        self.assertTrue(any(x["object"] == blob and x["scope"] == "local_unreachable"
                            for x in report["findings"]))


if __name__ == "__main__":
    unittest.main()
