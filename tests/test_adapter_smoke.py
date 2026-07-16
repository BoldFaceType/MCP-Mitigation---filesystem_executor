import json

from scripts.adapter_smoke import mcp_input, parse_adapter_output


def test_adapter_smoke_invokes_run_agent_through_tools_call() -> None:
    messages = [json.loads(line) for line in mcp_input().splitlines()]

    call = next(message for message in messages if message.get("method") == "tools/call")

    assert call["params"]["name"] == "run_agent"
    assert call["params"]["arguments"]["agent"] == "homecmd-agent"
    content = call["params"]["arguments"]["input"][0]["parts"][0]["content"]
    assert json.loads(content)["command_id"] == "system.python_version"


def test_parse_adapter_output_requires_tools_and_call_results() -> None:
    stdout = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "run_agent"}]}}),
        json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"content": [{"type": "text", "text": "system.python_version"}], "isError": False},
        }),
    ])

    tools, call_result = parse_adapter_output(stdout)

    assert [tool["name"] for tool in tools] == ["run_agent"]
    assert call_result["isError"] is False
