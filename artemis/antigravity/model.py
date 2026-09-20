"""Custom LangChain Chat Model that routes directly to Google Cloud Code Assist API."""

import json
import os
import re
import uuid
from typing import Any, Dict, Iterator, List, Optional, Sequence
import httpx
from google.auth.transport.requests import Request
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from artemis.antigravity.accounts import get_account_manager
from artemis.antigravity.constants import (
    ANTIGRAVITY_ENDPOINT_DAILY,
    ANTIGRAVITY_ENDPOINT_PROD,
)
from artemis.utils.logger import get_logger

logger = get_logger(__name__)


def _resolve_backend_model(model_name: str) -> str:
    m = model_name.lower().replace("models/", "").replace("google/", "").replace("antigravity/", "")
    if "gemini-3.8-flash" in m:
        return "gemini-3.8-flash-low"
    elif "gemini-3.7-flash" in m:
        return "gemini-3.7-flash-low"
    elif "gemini-3.1-pro" in m or "gemini-3-pro" in m:
        return "gemini-3.1-pro-preview"
    elif "gemini-2.5-flash" in m:
        return "gemini-2.5-flash"
    elif "sonnet" in m:
        return "claude-sonnet-4-6"
    return "gemini-3.8-flash-low"


def _to_camel_case(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _camel_dict_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {_to_camel_case(k): _camel_dict_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_camel_dict_keys(i) for i in obj]
    return obj


def _convert_tools_to_gemini_declarations(tools: Sequence[Any]) -> list[dict[str, Any]]:
    """Converts LangChain tool declarations / schemas into Cloud Code / Gemini format."""
    if not tools:
        return []
    try:
        from langchain_google_genai.chat_models import convert_to_genai_function_declarations

        genai_tools = convert_to_genai_function_declarations(tools)
        declarations = []
        for gt in genai_tools:
            d = gt.model_dump(mode="json", exclude_none=True)
            declarations.append(_camel_dict_keys(d))
        return declarations
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        logger.warning(f"langchain_google_genai conversion failed ({e}); using manual fallback")
        fn_decls = []
        for t in tools:
            name = getattr(t, "name", None) or (
                t.get("function", {}).get("name") if isinstance(t, dict) else None
            )
            desc = getattr(t, "description", None) or (
                t.get("function", {}).get("description") if isinstance(t, dict) else None
            )
            params = getattr(t, "parameters", None) or (
                t.get("function", {}).get("parameters") if isinstance(t, dict) else {}
            )
            if name:
                fn_decls.append(
                    {
                        "name": name,
                        "description": desc or "",
                        "parameters": params or {"type": "object", "properties": {}},
                    }
                )
        return [{"functionDeclarations": fn_decls}] if fn_decls else []


def _convert_message_to_gemini_dict(message: BaseMessage) -> dict[str, Any]:
    parts = []

    if isinstance(message, ToolMessage):
        role = "user"
        content_val = message.content
        if isinstance(content_val, str):
            try:
                parsed_json = json.loads(content_val)
                response_body = (
                    {"output": parsed_json} if not isinstance(parsed_json, dict) else parsed_json
                )
            except (json.JSONDecodeError, ValueError):
                response_body = {"output": content_val}
        else:
            response_body = {"output": content_val}

        parts.append(
            {
                "functionResponse": {
                    "name": message.name or "tool_result",
                    "response": response_body,
                }
            }
        )
        return {"role": role, "parts": parts}

    if isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "model"
        if message.tool_calls:
            for tc in message.tool_calls:
                parts.append(
                    {
                        "functionCall": {
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {}),
                        }
                    }
                )
    elif isinstance(message, SystemMessage):
        role = "user"
    else:
        role = "user"

    if isinstance(message.content, str):
        if message.content:
            parts.append({"text": message.content})
    elif isinstance(message.content, list):
        for item in message.content:
            if isinstance(item, str):
                parts.append({"text": item})
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append({"text": item.get("text", "")})
                elif item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        match = re.match(r"data:([^;]+);base64,(.+)", url)
                        if match:
                            mime_type, b64_data = match.groups()
                            parts.append({"inlineData": {"mimeType": mime_type, "data": b64_data}})
                    else:
                        parts.append({"text": f"[Image: {url}]"})
    elif message.content:
        parts.append({"text": str(message.content)})

    if not parts:
        parts.append({"text": ""})

    return {"role": role, "parts": parts}


class AntigravityChatModel(BaseChatModel):
    """Native Antigravity Chat Model interfacing directly with Google Cloud Code API."""

    model_name: str = Field(default="gemini-3.8-flash")
    temperature: float = Field(default=0.0)
    max_output_tokens: int | None = Field(default=8192)
    timeout: float = Field(default=60.0)
    project_id: str | None = Field(default=None)
    bound_tools: list[Any] = Field(default_factory=list, exclude=True)

    @property
    def _llm_type(self) -> str:
        return "antigravity-chat-model"

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: Any | None = None,
        **kwargs: Any,
    ) -> "AntigravityChatModel":
        """Binds tool declarations to this model instance and returns a configured copy."""
        return self.model_copy(update={"bound_tools": list(tools) if tools else []})

    def _resolve_project(self, client: httpx.Client, headers: dict[str, str]) -> str:
        if self.project_id:
            return self.project_id
        try:
            resp = client.post(
                f"{ANTIGRAVITY_ENDPOINT_PROD}/v1internal:loadCodeAssist",
                json={"metadata": {"ideType": "ANTIGRAVITY"}},
                headers=headers,
                timeout=10.0,
            )
            if resp.status_code == 200:
                p_data = resp.json().get("cloudaicompanionProject")
                if isinstance(p_data, str):
                    return p_data
                elif isinstance(p_data, dict) and "id" in p_data:
                    return p_data["id"]
        except (httpx.HTTPError, OSError, ValueError) as e:
            logger.warning(f"Could not resolve managed project ID: {e}")
        return "rising-fact-p41fc"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        mgr = get_account_manager()
        creds = mgr.get_credentials()
        if not creds:
            raise ValueError("No Antigravity accounts configured.")

        # Ensure token is valid
        if not creds.token:
            creds.refresh(Request())

        contents = [_convert_message_to_gemini_dict(m) for m in messages]
        backend_model = _resolve_backend_model(self.model_name)

        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity/cli/1.1.12 (aidev_client; os_type=linux; arch=amd64; cl=962369648; auth_method=consumer)",
            "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
            "Client-Metadata": '{"ideType":"ANTIGRAVITY","platform":"WINDOWS","pluginType":"GEMINI"}',
        }

        with httpx.Client(timeout=self.timeout) as client:
            project_id = self._resolve_project(client, headers)

            request_payload: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_output_tokens,
                },
                "sessionId": str(uuid.uuid4()),
            }

            if self.bound_tools:
                gemini_tools = _convert_tools_to_gemini_declarations(self.bound_tools)
                if gemini_tools:
                    request_payload["tools"] = gemini_tools

            payload = {
                "project": project_id,
                "model": backend_model,
                "request": request_payload,
                "requestType": "agent",
                "userAgent": "antigravity",
                "requestId": f"agent-{uuid.uuid4()}",
            }

            endpoints = [ANTIGRAVITY_ENDPOINT_DAILY, ANTIGRAVITY_ENDPOINT_PROD]
            last_error = None

            for attempt in range(mgr.get_account_count() * 2):
                for endpoint in endpoints:
                    url = f"{endpoint}/v1internal:streamGenerateContent?alt=sse"
                    try:
                        resp = client.post(url, json=payload, headers=headers)

                        if resp.status_code == 200:
                            full_text: list[str] = []
                            tool_calls: list[dict[str, Any]] = []

                            for line in resp.text.splitlines():
                                line = line.strip()
                                if line.startswith("data: "):
                                    try:
                                        data = json.loads(line[6:])
                                        response_obj = data.get("response", data)
                                        candidates = response_obj.get("candidates", [])
                                        if candidates:
                                            parts = (
                                                candidates[0].get("content", {}).get("parts", [])
                                            )
                                            for p in parts:
                                                if "text" in p and p["text"]:
                                                    full_text.append(p["text"])
                                                elif "functionCall" in p:
                                                    fc = p["functionCall"]
                                                    tool_calls.append(
                                                        {
                                                            "name": fc.get("name", ""),
                                                            "args": fc.get("args", {}),
                                                            "id": fc.get("id")
                                                            or f"call_{uuid.uuid4().hex[:8]}",
                                                            "type": "tool_call",
                                                        }
                                                    )
                                    except (json.JSONDecodeError, KeyError, IndexError):
                                        continue

                            output_text = "".join(full_text)
                            message = AIMessage(
                                content=output_text,
                                tool_calls=tool_calls if tool_calls else [],
                            )
                            return ChatResult(generations=[ChatGeneration(message=message)])

                        elif resp.status_code in (429, 503):
                            logger.warning(
                                f"Quota exceeded on endpoint {endpoint} (HTTP {resp.status_code}). Rotating account..."
                            )
                            creds = mgr.rotate_to_next_account()
                            if creds:
                                creds.refresh(Request())
                                headers["Authorization"] = f"Bearer {creds.token}"
                                payload["project"] = self._resolve_project(client, headers)
                            break
                        else:
                            last_error = f"HTTP {resp.status_code}: {resp.text}"
                            logger.warning(f"Endpoint {endpoint} failed with {last_error}")
                    except (httpx.HTTPError, OSError, ValueError) as e:
                        last_error = str(e)
                        logger.warning(f"Connection to {endpoint} failed: {e}")

            raise RuntimeError(
                f"All Antigravity accounts/endpoints exhausted. Last error: {last_error}"
            )
