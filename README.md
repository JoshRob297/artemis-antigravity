# ARTEMIS-Antigravity

> Autonomous Android UI Automation powered by native Google Cloud Code / Antigravity OAuth 2.0.  
> Zero commercial API keys required.

[English](README.md) • [Español](README.es.md) • [Architecture](docs/architecture.md) • [Changelog](CHANGELOG.md)

---

## What is ARTEMIS-Antigravity?

**ARTEMIS-Antigravity** is a standalone, open-source fork of [Google ARTEMIS](https://github.com/google/artemis). It inherits the state-of-the-art Android automation engine (achieving 99%+ on Google Research's AndroidWorld benchmark) while completely eliminating the requirement for paid Google AI Studio (`GEMINI_API_KEY`) or third-party commercial API keys.

By integrating directly with Google Cloud Code / Antigravity OAuth 2.0 endpoints, this fork allows AI coding assistants and automation suites to inspect screens, analyze visual hierarchies, and drive real Android phones at zero API cost using your existing Google accounts with automated multi-account rotation.

---

## Key Features

- **Native Multi-Account OAuth:** Uses standard Google OAuth 2.0 tokens (`refresh_token`) instead of static API keys.
- **Automated Hot-Rotation:** When an account hits its 5-hour quota window or returns HTTP 429 (`RESOURCE_EXHAUSTED`), the engine rotates to the next available account on the fly without interrupting running automation tasks.
- **Multimodal Perception:** Full support for Gemini 3.8 Flash, Gemini 3.7 Flash, and Gemini 2.5 Flash through Google Cloud Code Assist APIs.
- **Hybrid Credential Discovery:**
  - Standalone: reads `~/.config/antigravity/accounts.json`.
  - OpenCode Integration: automatically detects and uses existing accounts in `~/.config/opencode/antigravity-accounts.json`.
- **Model Context Protocol (MCP) Ready:** Connects seamlessly with OpenCode, Claude Code, Cursor, Codex, and Windsurf via stdio transport on dedicated port `8005`.
- **Lightweight On-Device Helper:** Bundles the Artemis Accessibility Helper APK v1.2.0 for non-intrusive UI hierarchy extraction without taking exclusive UiAutomation locks.

---

## System Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                   AI CLIENT / IDE LAYER                          │
│   • OpenCode CLI / Claude Code / Cursor / Windsurf               │
│   • Model Context Protocol (MCP) via stdio (Daemon Port: 8005)   │
└─────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│               FORK: artemis-antigravity (Python)                 │
│                                                                  │
│  ┌─────────────────────────┐     ┌────────────────────────────┐  │
│  │   MCP Server & Tools    │     │      Web UI & Console      │  │
│  │  (mobile_run_task, etc) │     │      (Port: 8005)          │  │
│  └────────────┬────────────┘     └─────────────┬──────────────┘  │
│               │                                │                 │
│               ▼                                ▼                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │             ARTEMIS AGENT GRAPH ENGINE (LangGraph)         │  │
│  │     (Perception, OCR, Accessibility Tree, Touch/Swipe)     │  │
│  └────────────────────────────┬───────────────────────────────┘  │
│                               │                                  │
│                               ▼                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │      NATIVE SUBSYSTEM: artemis.antigravity                 │  │
│  │   • Multi-Account Manager (OAuth 2.0)                      │  │
│  │   • Automatic Project Resolver (loadCodeAssist)            │  │
│  │   • Hot-Rotation on Quota Exhaustion (429/503)             │  │
│  │   • Direct SSE Stream Client for Cloud Code API            │  │
│  └────────────────────────────┬───────────────────────────────┘  │
└───────────────────────────────┼──────────────────────────────────┘
                                │
                                ▼  ADB over TCP / USB
┌──────────────────────────────────────────────────────────────────┐
│             TARGET ANDROID DEVICE / EMULATOR                     │
│            • Artemis Accessibility Helper APK v1.2.0             │
│            • Real touch events, screencap, input simulation      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Requirements

- Linux or macOS (Windows supported via WSL2)
- Python >= 3.12 (managed via `uv`)
- Android Debug Bridge (`adb`) installed
- Android device or emulator with USB / Wireless debugging enabled

### 2. Installation

Clone the repository and sync dependencies:

```bash
git clone https://github.com/JoshRob297/artemis-antigravity.git
cd artemis-antigravity
uv sync
```

### 3. Environment Configuration

Copy the example environment template:

```bash
cp .env.example .env
```

Edit `.env` to match your target device serial:
```env
ARTEMIS_DAEMON_PORT=8005
ANDROID_SERIAL=127.0.0.1:5555
ARTEMIS_LLM_PROVIDER=antigravity
ARTEMIS_DEFAULT_MODEL=gemini-3.8-flash
```

### 4. System Diagnosis

Verify your setup:

```bash
uv run artemis doctor
```

Output:
```text
Component                    Status      Details & Recommendations
Python Runtime Environment   OK          Python 3.14.7 Ready
Artemis System Configuration OK          Config Valid (gemini-3.8-flash)
MCP / IDE Integration Host   OK          Host Ready (Port 8005)
Multimodal LLM API Key       OK          Active (Antigravity: 3 accounts)
Device / Emulator Connected  OK          ADB connected to device
```

---

## Usage

### Run via Command Line

Execute an autonomous mobile workflow:

```bash
uv run artemis run "Open Settings, find Battery and report current level" --profile flash
```

For complex, multi-branch exploratory testing with verification checkpoints:

```bash
uv run artemis run "Verify user registration flow" --profile pro
```

### Run as an MCP Server (for AI IDEs)

Add to your MCP configuration (e.g. `opencode.json`, Claude Code, or Cursor):

```json
{
  "mcpServers": {
    "artemis": {
      "command": "/path/to/artemis-antigravity/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/artemis-antigravity",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": "/path/to/artemis-antigravity",
        "ARTEMIS_DAEMON_PORT": "8005",
        "ANDROID_SERIAL": "127.0.0.1:5555"
      }
    }
  }
}
```

---

## Differences from Upstream Google ARTEMIS

| Capability | Upstream `google/artemis` | Fork `artemis-antigravity` |
|---|---|---|
| **LLM Authentication** | Requires paid `GEMINI_API_KEY` (AI Studio) | Native Google OAuth 2.0 (Cloud Code / Antigravity) |
| **API Cost** | Paid per multimodal token/step | Zero API cost via Google Pro accounts |
| **Multi-Account Failover** | None (task halts on HTTP 429) | Automatic hot-rotation across N registered accounts |
| **Default Daemon Port** | 8000 (frequent conflict with scrcpy-web) | 8005 (configurable in `.env`) |
| **OpenCode Integration** | Manual setup required | Automatic account detection & MCP integration |

---

## Security and OPSEC

- Credentials (`accounts.json`, `.env`, tokens) are explicitly excluded from version control via `.gitignore`.
- Tokens are refreshed dynamically in memory; refresh tokens are never written to execution logs or stdout.
- Zero emojis directive strictly adhered to across code, documentation, and commit messages.

---

## License & Attribution

This project is licensed under the [Apache License 2.0](LICENSE).  
See [NOTICE](NOTICE) for original authorship and copyright attributions to Google LLC and Minitap, Inc.
