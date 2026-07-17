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
DEFAULT_ICON = "https://cdn.jsdelivr.net/gh/Lumen01/agent-bark-notify@main/assets/agent-bark.png"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Unable to read Bark config {path}: {exc.strerror or exc}") from exc
    for raw_line in content.splitlines():
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
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid agent JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    except OSError as exc:
        raise SystemExit(f"Unable to read agent config {path}: {exc.strerror or exc}") from exc
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


def agent_value(agent: str, field: str, cfg: dict[str, str], agents: dict[str, dict[str, str]]) -> tuple[str | None, str]:
    if not agent:
        return None, "not configured"
    normalized = normalize_agent(agent)
    env_key = env_agent_key(normalized, field.upper())
    if value := os.environ.get(env_key):
        return value, "environment"
    if value := cfg.get(env_key):
        return value, "config"
    if value := agents.get(normalized, {}).get(field):
        return value, "agent config"
    return None, "not configured"


def config_permission(path: Path) -> str:
    if not path.exists():
        return "not found"
    try:
        return oct(path.stat().st_mode & 0o777)
    except OSError as exc:
        return f"unreadable: {exc.strerror or exc}"


def build_payload(key: str, title: str, body: list[str], group: str, args: argparse.Namespace, icon: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "device_key": key,
        "title": title,
        "body": " ".join(body),
        "group": group,
    }
    for name in ("sound", "icon", "url", "copy", "level", "badge"):
        value = getattr(args, name)
        if value is not None:
            payload[name] = value
    if "icon" not in payload and icon:
        payload["icon"] = icon
    return payload


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
    parser.add_argument("--dry-run", action="store_true", help="print the final payload with the device key masked; do not send")
    parser.add_argument("--doctor", action="store_true", help="report resolved configuration and server ping without exposing the device key")
    parser.add_argument("--key-stdin", action="store_true", help="read the Bark device key from standard input instead of command-line arguments")
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

    stdin_key = sys.stdin.readline().rstrip("\r\n") if args.key_stdin else ""
    server = (args.server or os.environ.get("BARK_SERVER") or cfg.get("BARK_SERVER") or DEFAULT_SERVER).rstrip("/")
    key = args.key or stdin_key or os.environ.get("BARK_KEY") or cfg.get("BARK_KEY", "")
    agent = args.agent or os.environ.get("BARK_AGENT") or cfg.get("BARK_AGENT", "")
    agent_group, agent_group_source = agent_value(agent, "group", cfg, agents)
    agent_icon, agent_icon_source = agent_value(agent, "icon", cfg, agents)
    icon = args.icon or agent_icon or DEFAULT_ICON
    icon_source = "command line" if args.icon else agent_icon_source if agent_icon else "default"
    group = (
        args.group
        or agent_group
        or os.environ.get("BARK_GROUP")
        or cfg.get("BARK_GROUP")
        or "Agents"
    )
    group_source = (
        "command line"
        if args.group
        else agent_group_source
        if agent_group
        else "environment"
        if os.environ.get("BARK_GROUP")
        else "config"
        if cfg.get("BARK_GROUP")
        else "default"
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

    if args.doctor:
        ping = request_json(f"{server}/ping")
        report = {
            "server": server,
            "key_configured": bool(key),
            "config_file": {"path": str(config_path), "permissions": config_permission(config_path)},
            "agents_file": {"path": str(selected_agents_path), "configured": selected_agents_path.exists()},
            "agent": {"name": agent or None, "configured": normalize_agent(agent) in agents if agent else False},
            "group": {"value": group, "source": group_source},
            "icon": {"value": icon, "source": icon_source},
            "ping": ping,
        }
        print(json.dumps(report, ensure_ascii=False))
        return 0 if int(ping.get("code", 0)) == 200 else 1

    if not key:
        raise SystemExit(f"Missing Bark key. Put BARK_KEY=... in {config_path} or export BARK_KEY.")
    if not args.title:
        parser.error("title is required unless --ping, --doctor, or --save-config is used")

    payload = build_payload(key, args.title, args.body, group, args, icon)
    if args.dry_run:
        preview = {**payload, "device_key": "***"}
        print(json.dumps(preview, ensure_ascii=False))
        return 0

    result = request_json(f"{server}/push", payload)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if int(result.get("code", 0)) == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
