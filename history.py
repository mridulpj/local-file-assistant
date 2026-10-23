"""Conversation history compaction (rolling summary)."""
import re

from config import (
    CONTEXT_BUDGET_CHARS,
    KEEP_RECENT_TURNS,
    MODEL,
    SUMMARY_PREFIX,
    TEMPERATURE,
    TOOL_SNIPPET_CHARS,
    client,
)
from ui import Spinner


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


def summarise(previous: str, old_msgs) -> str | None:
    prompt = (
        "Condense the conversation below into a compact summary of at most "
        "200 words. Keep: the user's goals and open questions, names, numbers, "
        "dates, file names that were read, and any facts found in company files. "
        "Drop greetings and filler. Output only the summary.\n\n"
    )
    if previous:
        prompt += f"EARLIER SUMMARY:\n{previous}\n\n"
    prompt += f"NEW MESSAGES:\n{_transcript(old_msgs)}"

    spinner = Spinner("summarising")
    spinner.start()
    try:
        # Non-streaming call: the response is a plain object, not a context manager.
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
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
    summary = summarise(previous, messages[start:cut])
    if summary:
        messages[1:cut] = [{"role": "system", "content": SUMMARY_PREFIX + summary}]
