"""Talking to the model: streaming a reply and the tool-calling loop."""
from config import MAX_TOOL_ROUNDS, MODEL, TEMPERATURE, client
from tools import TOOLS, describe_call, run_tool
from ui import Spinner
from openai import APIConnectionError, APIStatusError

def stream_call(messages):
    """Streamed model call. Returns (reply_text, tool_calls_list)."""
    spinner = Spinner()
    spinner.start()
    reply, calls, first = "", {}, True
    try:
        with client.chat.completions.create(
            model=MODEL, messages=messages, temperature=TEMPERATURE,
            tools=TOOLS, stream=True,
        ) as stream:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    if first:
                        spinner.stop()
                        print("\nAI: ", end="", flush=True)
                        first = False
                    print(delta.content, end="", flush=True)
                    reply += delta.content
                for tc in delta.tool_calls or []:
                    call = calls.setdefault(tc.index, {
                        "id": "", "type": "function",
                        "function": {"name": "", "arguments": ""},
                    })
                    if tc.id:
                        call["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            call["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            call["function"]["arguments"] += tc.function.arguments
                    spinner.label = describe_call(call)
    except APIConnectionError:
        spinner.stop()
        print(
            "\nError: Unable to connect to the LLM server. "
            "Check whether the server is running and the URL/port is correct."
        )
        return None, None
    except APIStatusError as e:
        spinner.stop()
        print(f"\nAPI Error: HTTP {e.status_code} - {e.message}")
        return None, None
    finally:
        spinner.stop()
    if reply:
        print()
    return reply, [calls[i] for i in sorted(calls)]


def ask(messages):
    for _ in range(MAX_TOOL_ROUNDS):
        reply, calls = stream_call(messages)
        if reply is None and calls is None:
            return
        assistant_msg = {"role": "assistant", "content": reply or None}
        if calls:
            assistant_msg["tool_calls"] = calls
        messages.append(assistant_msg)

        if not calls:
            return
        for call in calls:
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": run_tool(call),
            })
    print("\n[Stopped: too many tool calls in a row.]")
