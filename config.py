"""Settings, prompts and the shared model client."""
from pathlib import Path

from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="dummy_key")

MODEL = "qwen3.5:9b"
TEMPERATURE = 0.4
BASE = (Path(__file__).parent / "public folder").resolve() # folder path where files are read from

MAX_FILE_CHARS = 3000          # maximum characters read from a file
MAX_TOOL_ROUNDS = 5            # tool calls in a row before we stop
CONTEXT_BUDGET_CHARS = 12000   # history size that triggers summarising
KEEP_RECENT_TURNS = 2          # recent user turns kept word-for-word
TOOL_SNIPPET_CHARS = 600       # tool-result chars shown to the summariser
EXIT_WORDS = ("bye", "good bye", "goodbye", "quit", "exit", "end") # Words that will exit the chat loop when typed by the user.
EXIT_MESSAGE = "bye!"          # Message printed when the user exits the chat loop.

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