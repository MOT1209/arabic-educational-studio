"""Smoke tests for the six yt-* skills that ship a Python tool.

The tools are documented as dependency-free and run from their skill folder.
These tests prove that each entry point starts, prints usage instead of a
traceback when called without a file, and that the two flag-only tools accept
the documented flags. They are not a scoring/accuracy contract.
"""
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

TOOLS = {
    "hookscore": "skills/yt-script/hookscore.py",
    "title": "skills/yt-package/title.py",
    "deadair": "skills/yt-edit/deadair.py",
    "chapters": "skills/yt-chapters/chapters.py",
    "retention": "skills/yt-retention/retention.py",
    "swipe": "skills/yt-viral/swipe.py",
}


class ToolSmokeTest(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_usage_without_a_file(self):
        for name, relative in TOOLS.items():
            with self.subTest(tool=name):
                result = self.run_tool(relative)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output)
                self.assertNotIn("Traceback", output)
                self.assertTrue(output.strip(), "no usage text was printed")

    def test_hookscore_accepts_a_hook(self):
        result = self.run_tool(
            TOOLS["hookscore"], "--hook", "Nobody tells you this about editing"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERDICT", (result.stdout + result.stderr).upper())

    def test_title_accepts_flags(self):
        result = self.run_tool(
            TOOLS["title"], "--title", "A test title with 3 fixes", "--thumb", "SHORT"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("score", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
