#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "bark-notify.env"
DEFAULT_AGENTS_PATH = Path.home() / ".config" / "bark-notify-agents.json"
DEFAULT_SERVER = "https://api.day.app"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_agents_file(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Agent config must be an object: {path}")
    agents: dict[str, dict[str, str]] = {}
    for name, config in data.items():
        if not isinstance(config, dict):
            continue
        normalized = normalize_agent(str(name))
        agents[normalized] = {str(k): str(v) for k, v in config.items() if v is not None}
    return agents


def quote_env_value(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def save_config(path: Path, server: str, key: str, group: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "# Agent Bark Notify config",
            f"BARK_SERVER={quote_env_value(server.rstrip('/'))}",
            f"BARK_KEY={quote_env_value(key)}",
            f"BARK_GROUP={quote_env_value(group)}",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def normalize_agent(agent: str) -> str:
    return agent.strip().lower().replace(" ", "-")


def env_agent_key(agent: str, suffix: str) -> str:
    normalized = normalize_agent(agent).upper().replace("-", "_")
    return f"BARK_AGENT_{normalized}_{suffix}"


def agent_value(agent: str, field: str, cfg: dict[str, str], agents: dict[str, dict[str, str]]) -> str | None:
    if not agent:
        return None
    normalized = normalize_agent(agent)
    env_key = env_agent_key(normalized, field.upper())
    return os.environ.get(env_key, cfg.get(env_key, agents.get(normalized, {}).get(field)))


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 15) -> dict[str, Any]:
    data = None
    headers = {"User-Agent": "agent-bark-notify/0.1"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        method = "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if not body:
                return {"code": resp.status, "message": "empty response"}
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"code": resp.status, "message": body}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Bark HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Bark request failed: {exc.reason}") from exc


def build_parser(config_path: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a Bark notification with optional agent identity metadata")
    parser.add_argument("title", nargs="?", help="notification title")
    parser.add_argument("body", nargs="*", help="notification body")
    parser.add_argument("--server", default=None, help="Bark server URL, defaults to config/env/api.day.app")
    parser.add_argument("--key", default=None, help="Bark device key")
    parser.add_argument("--group", default=None, help="Bark notification group")
    parser.add_argument("--agent", default=None, help="agent name for configured group/icon, e.g. codex")
    parser.add_argument("--agents-file", default=None, help="JSON file mapping agents to group/icon values")
    parser.add_argument("--sound", default=None, help="Bark sound name, e.g. glass, alarm")
    parser.add_argument("--icon", default=None, help="notification icon URL")
    parser.add_argument("--url", default=None, help="URL opened when tapping the notification")
    parser.add_argument("--copy", default=None, help="text copied by Bark")
    parser.add_argument("--level", choices=["passive", "active", "timeSensitive", "critical"], default=None)
    parser.add_argument("--badge", type=int, default=None)
    parser.add_argument("--ping", action="store_true", help="check server health without sending a notification")
    parser.add_argument("--save-config", action="store_true", help=f"save server/key defaults to {config_path}")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    config_path: Path | None = DEFAULT_CONFIG_PATH,
    agents_path: Path | None = DEFAULT_AGENTS_PATH,
) -> int:
    config_path = config_path or DEFAULT_CONFIG_PATH
    agents_path = agents_path or DEFAULT_AGENTS_PATH
    cfg = load_env_file(config_path)
    parser = build_parser(config_path)
    args = parser.parse_args(argv)

    selected_agents_path = Path(args.agents_file).expanduser() if args.agents_file else agents_path
    agents = load_agents_file(selected_agents_path)

    server = (args.server or os.environ.get("BARK_SERVER") or cfg.get("BARK_SERVER") or DEFAULT_SERVER).rstrip("/")
    key = args.key or os.environ.get("BARK_KEY") or cfg.get("BARK_KEY", "")
    agent = args.agent or os.environ.get("BARK_AGENT") or cfg.get("BARK_AGENT", "")
    group = (
        args.group
        or agent_value(agent, "group", cfg, agents)
        or os.environ.get("BARK_GROUP")
        or cfg.get("BARK_GROUP")
        or "Agents"
    )

    if args.save_config:
        if not key:
            raise SystemExit("Missing Bark key. Use --save-config --key <Bark device key>.")
        save_config(config_path, server, key, group)
        print(f"Saved Bark defaults to {config_path}")
        return 0

    if args.ping:
        result = request_json(f"{server}/ping")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if int(result.get("code", 0)) == 200 else 1

    if not key:
        raise SystemExit(f"Missing Bark key. Put BARK_KEY=... in {config_path} or export BARK_KEY.")
    if not args.title:
        parser.error("title is required unless --ping or --save-config is used")

    payload: dict[str, Any] = {
        "device_key": key,
        "title": args.title,
        "body": " ".join(args.body),
        "group": group,
    }
    for name in ("sound", "icon", "url", "copy", "level", "badge"):
        value = getattr(args, name)
        if value is not None:
            payload[name] = value
    if "icon" not in payload:
        icon = agent_value(agent, "icon", cfg, agents)
        if icon:
            payload["icon"] = icon

    result = request_json(f"{server}/push", payload)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if int(result.get("code", 0)) == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
