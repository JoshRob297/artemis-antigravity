# Changelog

All notable changes to the ARTEMIS-Antigravity fork will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0-antigravity] - 2026-09-20

### Fixed
- **Strict Tool Schema Sanitization (Fix HTTP 400 `property is not defined`)**: Added recursive `_sanitize_tool_parameters` in `artemis/antigravity/model.py` to validate Pydantic/LangChain tool schemas against Cloud Code Protobuf requirements, purging orphan required keys and eliminating empty required arrays.

### Added
- **Model Support: `gpt-oss-120b-medium`**: Added backend mapping for Antigravity's open-source 120B model in `_resolve_backend_model`.
- **Client Signature Parity**: Updated User-Agent to `antigravity/cli/1.2.7 (aidev_client; os_type=linux; arch=amd64; cl=962369648; auth_method=consumer)`.

## [1.0.0-antigravity] - 2026-09-17

### Added
- **Native Antigravity OAuth 2.0 Subsystem (`artemis/antigravity/`):**
  - `constants.py`: Cloud Code OAuth client IDs, secrets, scopes, and internal API endpoints (`daily` and `prod`).
  - `accounts.py`: `AntigravityAccountManager` with multi-account loading, automated token refresh via `google.auth.transport.requests`, and hot-rotation index across registered accounts.
  - `model.py`: `AntigravityChatModel` LangChain `BaseChatModel` implementation connecting directly to Cloud Code Assist APIs with SSE stream handling and automatic project resolution.
- **Model Router Integration:**
  - Added `ModelProvider.ANTIGRAVITY` to `artemis/llm/router.py`.
  - Transparent fallback: automatically instantiates `AntigravityChatModel` when no commercial `GEMINI_API_KEY` is present in the environment.
- **Diagnostics Probe Enhancement:**
  - Updated `artemis/core/diagnostics/probes/credentials_probe.py` to recognize Antigravity multi-account OAuth as an active multimodal provider (`ProbeStatus.PASS`).
- **Startup Validation Fix:**
  - Patched `artemis/config/llm.py` (`LLM.validate_provider`) to allow startup without `GOOGLE_API_KEY` when Antigravity accounts are configured.
- **Documentation:**
  - Comprehensive bilingual documentation (`README.md` in English and `README.es.md` in Spanish).
  - Internal operational directives (`AGENTS.md`).
  - Apache-2.0 legal `NOTICE` file.
  - Public environment configuration template (`.env.example`).

### Changed
- **Port Conflict Resolution:** Relocated default Artemis daemon port from `8000` to `8005` to prevent conflicts with local web services (such as `scrcpy-web`).
- **Security Hardening:** Extended `.gitignore` to explicitly prevent accidental commits of account files (`*accounts.json`), environment files, and session traces.
