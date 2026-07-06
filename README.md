# Agent Bark Notify

Agent-aware CLI for sending [Bark](https://github.com/Finb/Bark) push notifications.

The tool keeps Bark server/key configuration local, while allowing each agent
such as Codex, Claude, CI, or cron to use its own notification group and icon.

## Install

```bash
python3 -m pip install .
```

For local development:

```bash
python3 -m pip install -e .
```

## Configure

Create `~/.config/bark-notify.env`:

```env
BARK_SERVER="https://api.day.app"
BARK_KEY="your-bark-device-key"
BARK_GROUP="Agents"
```

Or initialize it with:

```bash
bark-notify --save-config --server "https://api.day.app" --key "your-bark-device-key"
```

Do not commit real Bark keys.

## Agent Identity

Agent group and icon metadata can live in `~/.config/bark-notify-agents.json`:

```json
{
  "codex": {
    "group": "Codex",
    "icon": "https://example.com/icons/codex.png"
  }
}
```

The icon must be a URL reachable by the receiving iOS device. Common hosting
choices include GitHub Pages, Cloudflare Pages, S3/R2, nginx, Caddy, or jsDelivr.
If no icon URL is configured, the notification is still sent without a custom icon.

Environment variables override the agent JSON:

```env
BARK_AGENT_CODEX_GROUP="Codex"
BARK_AGENT_CODEX_ICON="https://example.com/icons/codex.png"
```

## Usage

```bash
bark-notify "Title" "Body"
bark-notify Title Body words without quoting the body
bark-notify --agent codex "Build finished" "Codex completed the requested task"
bark-notify --agent codex --group Custom --icon "https://example.com/custom.png" "Title" "Body"
bark-notify --ping
```

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

