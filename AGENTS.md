# AGENTS.md — Artemis-Antigravity Fork Operational Directives

Operational guide for autonomous coding agents modifying or testing this repository.

---

## Global Mandates

1. **Zero Emojis:** Strictly prohibited in all code, comments, docstrings, commits, and logs.
2. **Upstream Cleanliness:** Do not alter core Artemis logic (`artemis/core/`, `artemis/engine/`, `artemis/planner/`) unless directly required to support the Antigravity provider.
3. **OPSEC & Secrets:**
   - Never commit `.env`, `accounts.json`, `traces/`, or credentials.
   - Respect `.gitignore` rules at all times.
   - Mask all tokens before writing to any log stream.

---

## Subsystem Architecture

The Antigravity integration lives under `artemis/antigravity/`:
- `constants.py`: OAuth client identifiers and API endpoints.
- `accounts.py`: Multi-account manager with automatic token refresh and failover rotation.
- `model.py`: `AntigravityChatModel` LangChain wrapper interfacing directly with Google Cloud Code API.

### Core Hook Points:
- `artemis/llm/router.py`: `ModelFactory.create_model()` instantiates `AntigravityChatModel` when `provider == ModelProvider.ANTIGRAVITY` or when no `GEMINI_API_KEY` is present.
- `artemis/core/diagnostics/probes/credentials_probe.py`: Checks for configured Antigravity accounts to pass environment validation.

---

## Development & Verification Commands

```bash
# Sincronizar dependencias con uv
uv sync

# Ejecutar diagnostico del entorno
uv run artemis doctor

# Probar inferencia directa del modelo Antigravity
uv run python -c '
from artemis.antigravity.model import AntigravityChatModel
model = AntigravityChatModel(model_name="gemini-3.8-flash")
resp = model.invoke("ping")
print("Response:", resp.content)
'

# Ejecutar suite de pruebas
uv run pytest
```

---

## Configuration & Ports

- **Daemon Port:** `8005` (set in `.env` as `ARTEMIS_DAEMON_PORT=8005`). Port 8000 is reserved for `scrcpy-web`.
- **Target Device:** Configure via `ANDROID_SERIAL` in `.env` or pass `--serial <ip:port>` to CLI commands.
