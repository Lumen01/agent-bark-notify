import os
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bark-notify.py"
loader = importlib.machinery.SourceFileLoader("bark_notify_under_test", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
cli = importlib.util.module_from_spec(spec)
loader.exec_module(cli)


def run_main(argv, env=None, config_path=None, agents_path=None):
    calls = []

    def fake_request(url, payload=None, timeout=15):
        calls.append((url, payload))
        return {"code": 200, "message": "ok"}

    with mock.patch.object(cli, "request_json", fake_request), mock.patch.dict(os.environ, env or {}, clear=True):
        rc = cli.main(argv, config_path=config_path, agents_path=agents_path)

    return rc, calls


class BarkNotifyCliTest(unittest.TestCase):
    def test_body_words_after_title_are_joined(self):
        rc, calls = run_main(["Title", "hello", "from", "agent"], env={"BARK_KEY": "test-key"})

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0][1]["title"], "Title")
        self.assertEqual(calls[0][1]["body"], "hello from agent")

    def test_agent_config_adds_group_and_icon(self):
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "agents.json"
            agents.write_text(
                '{"codex": {"group": "Codex", "icon": "https://example.com/codex.png"}}',
                encoding="utf-8",
            )

            rc, calls = run_main(["--agent", "codex", "Done", "Ready"], env={"BARK_KEY": "test-key"}, agents_path=agents)

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0][1]["group"], "Codex")
        self.assertEqual(calls[0][1]["icon"], "https://example.com/codex.png")

    def test_explicit_group_and_icon_override_agent_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "agents.json"
            agents.write_text(
                '{"codex": {"group": "Codex", "icon": "https://example.com/codex.png"}}',
                encoding="utf-8",
            )

            rc, calls = run_main(
                [
                    "--agent",
                    "codex",
                    "--group",
                    "Custom",
                    "--icon",
                    "https://example.com/custom.png",
                    "Done",
                    "Ready",
                ],
                env={"BARK_KEY": "test-key"},
                agents_path=agents,
            )

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0][1]["group"], "Custom")
        self.assertEqual(calls[0][1]["icon"], "https://example.com/custom.png")

    def test_missing_key_exits_without_request(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "missing.env"
            with self.assertRaisesRegex(SystemExit, "Missing Bark key"):
                run_main(["Title", "Body"], config_path=config)

    def test_level_is_included_in_payload(self):
        for level in ("passive", "active", "timeSensitive", "critical"):
            with self.subTest(level=level):
                rc, calls = run_main(["--level", level, "Title", "Body"], env={"BARK_KEY": "test-key"})

                self.assertEqual(rc, 0)
                self.assertEqual(calls[0][1]["level"], level)

    def test_save_config_writes_private_file(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "bark-notify.env"

            rc, calls = run_main(
                ["--save-config", "--server", "https://api.day.app", "--key", "abc123", "--group", "Agents"],
                config_path=config,
            )

            self.assertEqual(rc, 0)
            self.assertEqual(calls, [])
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            text = config.read_text(encoding="utf-8")
            self.assertIn('BARK_SERVER="https://api.day.app"', text)
            self.assertIn('BARK_KEY="abc123"', text)
            self.assertIn('BARK_GROUP="Agents"', text)


if __name__ == "__main__":
    unittest.main()
