import os
import importlib.machinery
import importlib.util
import io
import json
import sys
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


def run_main(argv, env=None, config_path=None, agents_path=None, stdin_text=None):
    calls = []
    stdout = io.StringIO()

    def fake_request(url, payload=None, timeout=15):
        calls.append((url, payload))
        return {"code": 200, "message": "ok"}

    with (
        mock.patch.object(cli, "request_json", fake_request),
        mock.patch.dict(os.environ, env or {}, clear=True),
        mock.patch("sys.stdout", stdout),
        mock.patch("sys.stdin", io.StringIO(stdin_text) if stdin_text is not None else sys.stdin),
    ):
        rc = cli.main(argv, config_path=config_path, agents_path=agents_path)

    return rc, calls, stdout.getvalue()


class BarkNotifyCliTest(unittest.TestCase):
    def test_body_words_after_title_are_joined(self):
        rc, calls, _ = run_main(["Title", "hello", "from", "agent"], env={"BARK_KEY": "test-key"})

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

            rc, calls, _ = run_main(["--agent", "codex", "Done", "Ready"], env={"BARK_KEY": "test-key"}, agents_path=agents)

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0][1]["group"], "Codex")
        self.assertEqual(calls[0][1]["icon"], "https://example.com/codex.png")

    def test_default_icon_is_used_when_no_icon_is_configured(self):
        rc, calls, _ = run_main(["Done", "Ready"], env={"BARK_KEY": "test-key"})

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0][1]["icon"], cli.DEFAULT_ICON)

    def test_explicit_group_and_icon_override_agent_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "agents.json"
            agents.write_text(
                '{"codex": {"group": "Codex", "icon": "https://example.com/codex.png"}}',
                encoding="utf-8",
            )

            rc, calls, _ = run_main(
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
                rc, calls, _ = run_main(["--level", level, "Title", "Body"], env={"BARK_KEY": "test-key"})

                self.assertEqual(rc, 0)
                self.assertEqual(calls[0][1]["level"], level)

    def test_save_config_writes_private_file(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "bark-notify.env"

            rc, calls, _ = run_main(
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

    def test_dry_run_masks_key_and_does_not_send(self):
        rc, calls, output = run_main(
            ["--dry-run", "--level", "active", "Done", "Ready"],
            env={"BARK_KEY": "secret-key"},
        )

        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])
        self.assertEqual(json.loads(output)["device_key"], "***")
        self.assertEqual(json.loads(output)["level"], "active")

    def test_key_stdin_saves_config_without_key_argument(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "bark-notify.env"
            rc, calls, _ = run_main(
                ["--save-config", "--key-stdin"],
                config_path=config,
                stdin_text="stdin-key\n",
            )

            self.assertEqual(rc, 0)
            self.assertEqual(calls, [])
            self.assertIn('BARK_KEY="stdin-key"', config.read_text(encoding="utf-8"))

    def test_invalid_agents_json_has_a_concise_actionable_error(self):
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "agents.json"
            agents.write_text('{"codex": ', encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, r"Invalid agent JSON.*agents\.json.*line 1"):
                run_main(["Title", "Body"], env={"BARK_KEY": "test-key"}, agents_path=agents)

    def test_doctor_reports_resolved_configuration_without_exposing_key(self):
        with tempfile.TemporaryDirectory() as td:
            agents = Path(td) / "agents.json"
            config = Path(td) / "bark-notify.env"
            agents.write_text('{"codex": {"group": "Codex", "icon": "https://example.com/codex.png"}}', encoding="utf-8")

            rc, calls, output = run_main(
                ["--doctor", "--agent", "codex"],
                env={"BARK_KEY": "secret-key"},
                config_path=config,
                agents_path=agents,
            )

        report = json.loads(output)
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [("https://api.day.app/ping", None)])
        self.assertTrue(report["key_configured"])
        self.assertNotIn("secret-key", output)
        self.assertEqual(report["group"], {"value": "Codex", "source": "agent config"})
        self.assertEqual(report["icon"], {"value": "https://example.com/codex.png", "source": "agent config"})

    def test_doctor_reports_default_icon_source(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "bark-notify.env"

            rc, _, output = run_main(
                ["--doctor"],
                env={"BARK_KEY": "secret-key"},
                config_path=config,
            )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output)["icon"], {"value": cli.DEFAULT_ICON, "source": "default"})


if __name__ == "__main__":
    unittest.main()
