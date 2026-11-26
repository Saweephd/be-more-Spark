"""The flight recorder: lines reach the file at once and the file stays small."""
import os
import tempfile
import unittest

from core import blackbox


class TestBlackbox(unittest.TestCase):
    def test_lines_are_written_and_read_back(self):
        path = os.path.join(tempfile.mkdtemp(), "box.log")
        blackbox.write("first", path)
        blackbox.write(blackbox.line("idle", "yes", "80%/4.0V", "on"), path)
        rows = blackbox.last(5, path)
        self.assertEqual(rows[0], "first")
        self.assertIn("state=idle game=yes battery=80%/4.0V tv=on supply=", rows[1])
        self.assertIn("flags=", rows[1])

    def test_the_file_is_trimmed(self):
        path = os.path.join(tempfile.mkdtemp(), "box.log")
        with open(path, "w") as fh:
            fh.write(("x" * 159 + "\n") * (blackbox.KEEP + 10))
        blackbox.write("newest", path)
        rows = open(path).read().splitlines()
        self.assertLessEqual(len(rows), blackbox.KEEP // 2 + 1)
        self.assertEqual(rows[-1], "newest")
        self.assertEqual(blackbox.last(3, "/no/such/file"), [])


if __name__ == "__main__":
    unittest.main()
