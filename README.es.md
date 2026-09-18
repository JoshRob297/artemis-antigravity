# ARTEMIS-Antigravity

> Automatización autónoma de interfaz de usuario en Android impulsada de forma nativa por Google Cloud Code / Antigravity OAuth 2.0.  
> Cero requerimiento de API keys comerciales.

[English](README.md) • [Español](README.es.md) • [Arquitectura](docs/architecture.md) • [Registro de Cambios](CHANGELOG.md)

---

## ¿Qué es ARTEMIS-Antigravity?

**ARTEMIS-Antigravity** es un fork independiente y de código abierto de [Google ARTEMIS](https://github.com/google/artemis). Hereda el motor de automatización para Android de última generación (con una tasa de éxito superior al 99% en el benchmark AndroidWorld de Google Research) eliminando por completo la exigencia de contar con claves de pago de Google AI Studio (`GEMINI_API_KEY`) o proveedores comerciales externos.

Al integrarse directamente con las APIs de Google Cloud Code / Antigravity OAuth 2.0, este fork permite a los asistentes de desarrollo con IA y a las suites de prueba inspeccionar pantallas, interpretar jerarquías visuales y operar teléfonos Android físicos a costo cero, utilizando cuentas de Google existentes con rotación automática multi-cuenta.

---

## Características Principales

- **OAuth 2.0 Multi-Cuenta Nativo:** Utiliza tokens estándar de Google (`refresh_token`) en lugar de claves de API estáticas.
- **Rotación en Caliente Automatizada:** Cuando una cuenta alcanza su ventana de cuota de 5 horas o devuelve HTTP 429 (`RESOURCE_EXHAUSTED`), el motor conmuta de inmediato a la siguiente cuenta disponible sin interrumpir la tarea en curso.
- **Percepción Multimodal:** Soporte completo para Gemini 3.8 Flash, Gemini 3.7 Flash y Gemini 2.5 Flash a través de las APIs de Google Cloud Code Assist.
- **Detección Híbrida de Credenciales:**
  - Modo Independiente: Lee `~/.config/antigravity/accounts.json`.
  - Integración OpenCode: Detecta y reutiliza automáticamente cuentas en `~/.config/opencode/antigravity-accounts.json`.
- **Servidor MCP Integrado:** Conexión transparente mediante Model Context Protocol con OpenCode, Claude Code, Cursor, Codex y Windsurf a través de stdio en el puerto `8005`.
- **Helper de Accesibilidad en Dispositivo:** Incluye el APK Artemis Accessibility Helper v1.2.0 para la extracción no intrusiva de la jerarquía de vistas sin requerir bloqueos exclusivos de UiAutomation.

---

## Arquitectura del Sistema

```text
┌──────────────────────────────────────────────────────────────────┐
│                   CAPA CLIENTE / IDE DE IA                       │
│   • OpenCode CLI / Claude Code / Cursor / Windsurf               │
│   • Model Context Protocol (MCP) vía stdio (Puerto Daemon: 8005) │
└─────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│               FORK: artemis-antigravity (Python)                 │
│                                                                  │
│  ┌─────────────────────────┐     ┌────────────────────────────┐  │
│  │   Servidor MCP & Tools  │     │      Consola Web & UI      │  │
│  │  (mobile_run_task, etc) │     │      (Puerto: 8005)        │  │
│  └────────────┬────────────┘     └─────────────┬──────────────┘  │
│               │                                │                 │
│               ▼                                ▼                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │             MOTOR DE AGENTES ARTEMIS (LangGraph)           │  │
│  │     (Percepción, OCR, Árbol de Accesibilidad, Toques)      │  │
│  └────────────────────────────┬───────────────────────────────┘  │
│                               │                                  │
│                               ▼                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │      SUBSISTEMA NATIVO: artemis.antigravity                │  │
│  │   • Gestor Multi-Cuenta (OAuth 2.0)                        │  │
│  │   • Resolvedor Dinámico de Proyecto (loadCodeAssist)       │  │
│  │   • Rotación ante Agotamiento de Cuota (429/503)          │  │
│  │   • Cliente SSE Stream para Cloud Code API                 │  │
│  └────────────────────────────┬───────────────────────────────┘  │
└───────────────────────────────┼──────────────────────────────────┘
                                │
                                ▼  ADB por TCP / Wi-Fi o USB
┌──────────────────────────────────────────────────────────────────┐
│             DISPOSITIVO ANDROID DESTINO / EMULADOR               │
│            • Artemis Accessibility Helper APK v1.2.0             │
│            • Eventos táctiles reales, capturas, simulación       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Inicio Rápido

### 1. Requisitos

- Linux o macOS (Windows soportado vía WSL2)
- Python >= 3.12 (gestionado mediante `uv`)
- Android Debug Bridge (`adb`) instalado en el sistema
- Dispositivo Android físico o emulador con Depuración USB / Inalámbrica activa

### 2. Instalación

Clonar el repositorio y sincronizar el entorno virtual:

```bash
git clone https://github.com/JoshRob297/artemis-antigravity.git
cd artemis-antigravity
uv sync
```

### 3. Configuración del Entorno

Copiar la plantilla de variables de entorno:

```bash
cp .env.example .env
```

Editar `.env` según la configuración de tu dispositivo:
```env
ARTEMIS_DAEMON_PORT=8005
ANDROID_SERIAL=127.0.0.1:5555
ARTEMIS_LLM_PROVIDER=antigravity
ARTEMIS_DEFAULT_MODEL=gemini-3.8-flash
```

### 4. Diagnóstico del Sistema

Comprobar que todos los componentes estén en orden:

```bash
uv run artemis doctor
```

Salida esperada:
```text
Component                    Status      Details & Recommendations
Python Runtime Environment   OK          Python 3.14.7 Ready
Artemis System Configuration OK          Config Valid (gemini-3.8-flash)
MCP / IDE Integration Host   OK          Host Ready (Puerto 8005)
Multimodal LLM API Key       OK          Active (Antigravity: 3 cuentas)
Device / Emulator Connected  OK          ADB connected to device
```

---

## Modos de Uso

### Ejecución por Línea de Comandos (CLI)

Lanzar un flujo de trabajo móvil autónomo:

```bash
uv run artemis run "Abre Ajustes, navega a Batería y reporta el nivel actual" --profile flash
```

Para flujos exploratorios complejos con verificación por puntos de control:

```bash
uv run artemis run "Probar flujo completo de registro de usuario" --profile pro
```

### Servidor MCP (Para IDEs y Asistentes con IA)

Agregar a la configuración MCP (ej. `opencode.json`, Claude Code o Cursor):

```json
{
  "mcpServers": {
    "artemis": {
      "command": "/ruta/a/artemis-antigravity/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/ruta/a/artemis-antigravity",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": "/ruta/a/artemis-antigravity",
        "ARTEMIS_DAEMON_PORT": "8005",
        "ANDROID_SERIAL": "127.0.0.1:5555"
      }
    }
  }
}
```

---

## Comparativa con el Repositorio Original de Google

| Capacidad | Upstream `google/artemis` | Fork `artemis-antigravity` |
|---|---|---|
| **Autenticación LLM** | Requiere clave de pago `GEMINI_API_KEY` (AI Studio) | Google OAuth 2.0 nativo (Cloud Code / Antigravity) |
| **Costo por Token** | Cobro comercial por cada captura/paso de UI | Costo cero mediante cuentas Google Pro |
| **Conmutación Multi-Cuenta** | Inexistente (la tarea se detiene con error 429) | Rotación automática en caliente entre N cuentas |
| **Puerto por Defecto** | 8000 (frecuente colisión con scrcpy-web) | 8005 (configurable en `.env`) |
| **Integración OpenCode** | Requiere configuración manual extensa | Detección automática de cuentas y configuración MCP lista |

---

## Seguridad y OPSEC

- Credenciales (`accounts.json`, `.env`, tokens) estrictamente excluidas del control de versiones mediante `.gitignore`.
- Los tokens de acceso se renuevan en memoria de forma dinámica; nunca se imprimen refresh tokens en logs de ejecución ni salidas estándar.
- Cumplimiento estricto de la directiva de Cero Emojis en código, commits y documentación técnica.

---

## Licencia y Atribución

Este proyecto está bajo la licencia [Apache License 2.0](LICENSE).  
Consultar el archivo [NOTICE](NOTICE) para las atribuciones legales y de autoría original a Google LLC y Minitap, Inc.
