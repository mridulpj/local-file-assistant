import itertools
import json
import threading
import time
import re
from pathlib import Path

from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="dummy_key")
MODEL = "qwen3.5:9b"
TEMPERATURE = 0.4
BASE = (Path(__file__).parent / "public folder").resolve()
MAX_FILE_CHARS = 3000          # maximum characters read from a file
MAX_TOOL_ROUNDS = 5            # how many times the assistant can call tools in a row before we stop and return the reply
CONTEXT_BUDGET_CHARS = 12000   # how much of the conversation history we keep before summarizing
KEEP_RECENT_TURNS = 2          # how many recent user turns we keep in full when summarizing
TOOL_SNIPPET_CHARS = 600       # how many characters of a tool result we show in the conversation transcript when summarizing

SYSTEM = (
    "You are a helpful and accurate assistant. Answer general questions directly "
    "using your existing knowledge, but always use the provided tools to retrieve "
    "information when answering questions about the company, its employees, "
    "policies, projects, or internal records. Base company-specific answers "
    "strictly on the information returned by the tools; never guess, assume, or "
    "fabricate missing information. If the tools cannot find the requested "
    "information or fail, clearly state that the information is unavailable."
)

SUMMARY_PREFIX = (
    "Summary of earlier conversation "
    "(re-read files with the tools if exact details are needed):\n"
)

# ---------- Tools ----------
def read_file(filename: str) -> str:
    path = (BASE / filename).resolve()
    if not path.is_relative_to(BASE):
        return "Error: only files in the public folder are allowed."
    if not path.is_file():
        return "Error: file not found."
    with path.open(encoding="utf-8", errors="replace") as f:
        text = f.read(MAX_FILE_CHARS + 1)
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n[... file truncated ...]"
    return text


def list_files() -> str:
    if not BASE.is_dir():
        return "Error: the public folder does not exist."
    files = sorted(p.name for p in BASE.iterdir() if p.is_file())
    return "\n".join(files) if files else "No files found."


FUNCTIONS = {"read_file": read_file, "list_files": list_files}

TOOL_LABELS = {
    "read_file": "Reading {filename}",
    "list_files": "Checking available files",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the company's public folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "File name, for example notes.txt",
                    }
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the file names in the company's public folder. "
                           "Use this to find the name of a file to read.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ---------- UI helper ----------
class Spinner:
    def __init__(self, label="Thinking"):
        self.label = label
        self._width = 0
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        for dots in itertools.cycle(["   ", ".  ", ".. ", "..."]):
            if self._done.is_set():
                break
            text = f"{self.label}{dots}"
            self._width = max(self._width, len(text))
            print("\r" + text.ljust(self._width), end="", flush=True)
            time.sleep(0.2)

    def start(self):
        self._thread.start()

    def stop(self):
        if not self._done.is_set():
            self._done.set()
            self._thread.join()
            print("\r" + " " * self._width + "\r", end="", flush=True)


def describe_call(call) -> str:
    """Human-readable label for a tool call; safe on partial or bad arguments."""
    name = call["function"]["name"]
    template = TOOL_LABELS.get(name, f"Running {name}")
    try:
        args = json.loads(call["function"]["arguments"] or "{}")
        label = template.format(**args)
    except (ValueError, KeyError, IndexError, TypeError):
        # Arguments are still streaming in, or malformed: drop the placeholder
        label = template.split("{")[0].strip()
    return label


# ---------- Model interaction ----------
def stream_once(messages):
    """One streamed model call. Returns (reply_text, tool_calls_list)."""
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
    finally:
        spinner.stop()
    if reply:
        print()
    return reply, [calls[i] for i in sorted(calls)]


def run_tool(call) -> str:
    label = describe_call(call)
    name = call["function"]["name"]
    func = FUNCTIONS.get(name)

    spinner = Spinner(label)
    spinner.start()
    try:
        if func is None:
            result = f"Error: unknown tool '{name}'."
        else:
            args = json.loads(call["function"]["arguments"] or "{}")
            result = str(func(**args))
    except Exception as e:
        result = f"Error: {e}"
    finally:
        spinner.stop()

    print(f"  [tool] {label}")
    return result


def _msg_chars(m) -> int:
    n = len(m.get("content") or "")
    for c in m.get("tool_calls") or []:
        n += len(c["function"]["name"]) + len(c["function"]["arguments"])
    return n


def _has_summary(messages) -> bool:
    return (
        len(messages) > 1
        and messages[1]["role"] == "system"
        and messages[1]["content"].startswith(SUMMARY_PREFIX)
    )


def _transcript(msgs) -> str:
    lines = []
    for m in msgs:
        content = m.get("content") or ""
        if m["role"] == "tool":
            if len(content) > TOOL_SNIPPET_CHARS:
                content = content[:TOOL_SNIPPET_CHARS] + " [...]"
            lines.append(f"TOOL RESULT: {content}")
            continue
        for c in m.get("tool_calls") or []:
            fn = c["function"]
            lines.append(f"ASSISTANT CALLED: {fn['name']}({fn['arguments']})")
        if content:
            lines.append(f"{m['role'].upper()}: {content}")
    return "\n".join(lines)


def summarize(previous: str, old_msgs) -> str | None:
    prompt = (
        "Condense the conversation below into a compact summary of at most "
        "200 words. Keep: the user's goals and open questions, names, numbers, "
        "dates, file names that were read, and any facts found in company files. "
        "Drop greetings and filler. Output only the summary.\n\n"
    )
    if previous:
        prompt += f"EARLIER SUMMARY:\n{previous}\n\n"
    prompt += f"NEW MESSAGES:\n{_transcript(old_msgs)}"

    spinner = Spinner("Summarizing")
    spinner.start()
    try:
        with client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        ) as resp:
            text = resp.choices[0].message.content or ""
            # Some reasoning models leak <think> blocks into the content
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            return text or None
    except Exception:
        return None   # on failure, keep the full history untouched
    finally:
        spinner.stop()


def compact_history(messages) -> None:
    """Replace old messages with a rolling summary once history is too big."""
    if sum(_msg_chars(m) for m in messages) <= CONTEXT_BUDGET_CHARS:
        return

    has_summary = _has_summary(messages)
    start = 2 if has_summary else 1   # skip system prompt (+ existing summary)

    # Cut only at a user message so assistant tool_calls are never separated
    # from their tool results.
    user_idx = [i for i in range(start, len(messages)) if messages[i]["role"] == "user"]
    if len(user_idx) <= KEEP_RECENT_TURNS:
        return
    cut = user_idx[-KEEP_RECENT_TURNS]

    previous = messages[1]["content"][len(SUMMARY_PREFIX):] if has_summary else ""
    summary = summarize(previous, messages[start:cut])
    if summary:
        messages[1:cut] = [{"role": "system", "content": SUMMARY_PREFIX + summary}]

def ask(messages):
    for _ in range(MAX_TOOL_ROUNDS):
        reply, calls = stream_once(messages)

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


# ---------- Main loop ----------
def main():
    try:
        messages = [{"role": "system", "content": SYSTEM}]
        print("Type 'quit' to exit.")
        while True:
            try:
                user = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye!")
                break
            if user.lower() in ("bye", "good bye", "goodbye", "quit", "exit", "end"):
                print("\nbye!")
                break
            if not user:
                continue
            messages.append({"role": "user", "content": user})
            compact_history(messages)
            ask(messages)
    finally:
        client.close()

if __name__ == "__main__":
    main()