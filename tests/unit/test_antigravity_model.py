# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for AntigravityChatModel and its tool binding capabilities."""

import json
from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from artemis.antigravity.model import (
    AntigravityChatModel,
    _convert_message_to_gemini_dict,
    _convert_tools_to_gemini_declarations,
    _resolve_backend_model,
)
from artemis.core.tool_declaration import ToolDeclaration
from artemis.services.llm import RobustChatModelWrapper


@pytest.fixture
def sample_click_tool():
    return ToolDeclaration(
        name="click",
        description="Clicks on an element or coordinate",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "integer", "description": "Element index"},
                "delay_ms": {"type": "integer", "description": "Delay in milliseconds"},
            },
            "required": ["target"],
        },
    )


@pytest.fixture
def sample_input_tool():
    return ToolDeclaration(
        name="input_text",
        description="Types text into an active input field",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["text"],
        },
    )


def test_model_resolution():
    assert _resolve_backend_model("gemini-3.8-flash") == "gemini-3.8-flash-low"
    assert _resolve_backend_model("google/gemini-3.7-flash") == "gemini-3.7-flash-low"
    assert _resolve_backend_model("gemini-3.1-pro") == "gemini-3.1-pro-preview"
    assert _resolve_backend_model("gemini-2.5-flash") == "gemini-2.5-flash"
    assert _resolve_backend_model("sonnet") == "claude-sonnet-4-6"
    assert _resolve_backend_model("unknown-model") == "gemini-3.8-flash-low"


def test_bind_tools_stateless_copy(sample_click_tool, sample_input_tool):
    model = AntigravityChatModel(model_name="gemini-3.8-flash")
    assert len(model.bound_tools) == 0

    bound = model.bind_tools([sample_click_tool, sample_input_tool])

    assert isinstance(bound, AntigravityChatModel)
    assert len(model.bound_tools) == 0
    assert len(bound.bound_tools) == 2
    assert bound.bound_tools[0].name == "click"
    assert bound.bound_tools[1].name == "input_text"


def test_bind_tools_empty_list():
    model = AntigravityChatModel()
    bound = model.bind_tools([])
    assert isinstance(bound, AntigravityChatModel)
    assert len(bound.bound_tools) == 0


def test_bind_tools_integration_with_robust_wrapper(sample_click_tool):
    model = AntigravityChatModel()
    wrapper = RobustChatModelWrapper(model)

    bound_wrapper = wrapper.bind_tools([sample_click_tool])

    assert isinstance(bound_wrapper, RobustChatModelWrapper)
    assert isinstance(bound_wrapper.base_model, AntigravityChatModel)
    assert len(bound_wrapper.base_model.bound_tools) == 1
    assert bound_wrapper.base_model.bound_tools[0].name == "click"


def test_tool_declaration_conversion(sample_click_tool):
    declarations = _convert_tools_to_gemini_declarations([sample_click_tool])
    assert len(declarations) == 1
    assert "functionDeclarations" in declarations[0]
    fns = declarations[0]["functionDeclarations"]
    assert len(fns) == 1
    assert fns[0]["name"] == "click"
    assert "clicks on an element" in fns[0]["description"].lower()
    assert fns[0]["parameters"]["type"] == "OBJECT"
    assert "target" in fns[0]["parameters"]["properties"]


def test_message_conversion_human_and_ai():
    human = HumanMessage(content="Hello")
    converted_human = _convert_message_to_gemini_dict(human)
    assert converted_human["role"] == "user"
    assert converted_human["parts"] == [{"text": "Hello"}]

    ai = AIMessage(
        content="I will click",
        tool_calls=[{"name": "click", "args": {"target": 1}, "id": "call_1"}],
    )
    converted_ai = _convert_message_to_gemini_dict(ai)
    assert converted_ai["role"] == "model"
    part_types = [list(p.keys())[0] for p in converted_ai["parts"]]
    assert "text" in part_types
    assert "functionCall" in part_types


def test_message_conversion_tool_message():
    tool_msg = ToolMessage(
        content='{"status": "success"}',
        name="click",
        tool_call_id="call_1",
    )
    converted = _convert_message_to_gemini_dict(tool_msg)
    assert converted["role"] == "user"
    assert len(converted["parts"]) == 1
    fn_resp = converted["parts"][0]["functionResponse"]
    assert fn_resp["name"] == "click"
    assert fn_resp["response"] == {"status": "success"}


def test_generate_parses_sse_tool_calls():
    model = AntigravityChatModel()

    mock_sse_body = (
        'data: {"response": {"candidates": [{"content": {"role": "model", "parts": ['
        '{"thoughtSignature": "abc", "functionCall": {"name": "click", "args": {"target": 42}, "id": "call_99"}}]}}]}}\n'
        'data: {"response": {"candidates": [{"content": {"role": "model", "parts": [{"text": ""}]}, "finishReason": "STOP"}]}}\n'
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_sse_body

    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    mock_creds = MagicMock()
    mock_creds.token = "mock-token"

    mock_mgr = MagicMock()
    mock_mgr.get_credentials.return_value = mock_creds
    mock_mgr.get_account_count.return_value = 1

    with (
        patch("artemis.antigravity.model.httpx.Client", return_value=mock_client),
        patch("artemis.antigravity.model.get_account_manager", return_value=mock_mgr),
    ):
        result = model._generate([HumanMessage(content="Click 42")])

    assert len(result.generations) == 1
    msg = result.generations[0].message
    assert isinstance(msg, AIMessage)
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0]["name"] == "click"
    assert msg.tool_calls[0]["args"] == {"target": 42}
    assert msg.tool_calls[0]["id"] == "call_99"
