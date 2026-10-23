"""Tools the model can call, their schemas, and the tool runner."""
import json

from config import BASE, MAX_FILE_CHARS
from ui import Spinner


# ---------- Tool implementations ----------
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


# To add a tool: write the function, then add an entry to each of the
# three tables below (FUNCTIONS, TOOL_LABELS, TOOLS).
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


# ---------- Running tools ----------
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
