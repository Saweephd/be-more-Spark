"""Route selection and bmo-ctl.sh argument handling.  No network needed.

Run: python -m unittest tests.test_edge_route
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.edge.bmo_skills import BMOSkillRouter

REPO = Path(__file__).resolve().parent.parent
CTL = str(REPO / "ops" / "bmo-ctl.sh")


class RouteTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="bmo-test-"))
        # Throwaway config and memory, so the real household memory is never read.
        self.router = BMOSkillRouter(config_path=tmp / "config.json", memory_path=tmp / "memory.json")

    def test_time_is_answered_locally(self):
        reply = self.router.try_handle("what time is it")
        self.assertIsInstance(reply, str)
        self.assertTrue(reply)

    def test_general_knowledge_goes_to_the_model(self):
        self.assertIsNone(self.router.try_handle("what is the capital of Peru"))

    def test_math_is_local_and_safe(self):
        self.assertIn("4", self.router.try_handle("calculate 2 + 2"))
        # Not evaluated as Python.
        reply = self.router.try_handle("calculate __import__('os').system('true')")
        self.assertNotIn("0", reply[:1])


class CtlArgumentTests(unittest.TestCase):
    def run_ctl(self, *args):
        env = dict(os.environ, XDG_RUNTIME_DIR=tempfile.mkdtemp())
        return subprocess.run(["bash", CTL, *args], capture_output=True, text=True, env=env, timeout=30)

    def test_help(self):
        r = self.run_ctl("help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("deploy <branch>", r.stdout)

    def test_no_arguments_shows_help(self):
        self.assertEqual(self.run_ctl().returncode, 0)

    def test_unknown_command(self):
        r = self.run_ctl("frobnicate")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown command", r.stdout)

    def test_deploy_needs_a_branch(self):
        self.assertEqual(self.run_ctl("deploy").returncode, 2)

    def test_ask_and_say_need_text(self):
        self.assertEqual(self.run_ctl("ask").returncode, 2)
        self.assertEqual(self.run_ctl("say").returncode, 2)

    def test_listen_rejects_bad_seconds(self):
        self.assertEqual(self.run_ctl("listen", "abc").returncode, 2)
        self.assertEqual(self.run_ctl("listen", "99").returncode, 2)

    def test_logs_rejects_non_number(self):
        self.assertEqual(self.run_ctl("logs", "x; rm -rf /").returncode, 2)


if __name__ == "__main__":
    unittest.main()
