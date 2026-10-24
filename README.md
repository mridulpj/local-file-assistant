# Local File Assistant

A command-line chatbot that uses a local LLM via [Ollama](https://ollama.com) or a compatible cloud model API to answer questions about files in a local folder/directory. It uses tool calling, so the model decides when to list or read files and provides info to the user based on their questions.

## Features

- Streaming responses in the terminal
- Tool calling: `list_files` and `read_file`, restricted to a single folder (path traversal such as `../secret.txt` is rejected)
- Spinner that shows what the assistant is doing ("Thinking", "Reading notes.txt", "Summarising")
- Rolling summary of old messages, so long chats stay within the model's context window
- Supports local models for offline operation or cloud model APIs

## Requirements

- Python 3.10 or newer
- Choose one of the following model options:

  **Option 1: Local model using Ollama**

  - [Ollama](https://ollama.com/download) installed and running
  - A model that supports tool calling, such as `qwen3.5:9b`

  Pull your chosen model using Ollama. For example:

  ```bash
  ollama pull qwen3.5:9b
  ```

  You can use another compatible model that supports tool calling.

  **Option 2: Cloud model API**

  - Access to a compatible cloud model API, such as the [OpenAI API](https://platform.openai.com/)
  - A model that supports tool calling
  - An API key for your chosen provider

  Ollama installation and model downloading are not required for this option. Configure the client and model name in `config.py` as described below.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/mridulpj/local-file-assistant.git
cd local-file-assistant
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

On macOS and Linux, use `python3 -m venv venv` if the `python` command is not found.

### 3. Activate the virtual environment

Choose the command for your terminal.

**Windows — Command Prompt (CMD)**

```cmd
venv\Scripts\activate.bat
```

**Windows — PowerShell**

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell shows an error saying that running scripts is disabled on your system, allow locally created scripts for your user account. You only need to do this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run the activation command again. This changes the policy for your user account only and does not need administrator rights.

**macOS — Terminal**

```bash
source venv/bin/activate
```

**Linux — Terminal**

```bash
source venv/bin/activate
```

When the virtual environment is active, your prompt starts with `(venv)`.

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure the model

Open `config.py` and configure the model settings for your chosen provider.

**For Ollama (local):**

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy_key"
)

MODEL = "qwen3.5:9b"
```

Replace `qwen3.5:9b` with the name of any compatible model you have pulled into Ollama.

**For a cloud API, such as OpenAI:**

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_openai_api_key"
)

MODEL = "your_cloud_model_name"
```

When `base_url` is omitted, the OpenAI SDK uses OpenAI's default API endpoint. For another compatible cloud provider, configure its API key, `base_url`, and model name as required.

Keep API keys private. For real projects, prefer loading them from environment variables instead of hardcoding them in `config.py`.

Put any `.txt` or `.md` files you want to ask about inside the `public folder`.

## Usage

Make sure your selected model provider is available and your virtual environment is activated, then run:

```bash
python main.py
```

On macOS and Linux, use `python3 main.py` if the `python` command is not found.

Example session:

```text
You: what files do you have?
Checking available files...

AI: I found leave_policy.txt and onboarding.md.

You: what does the leave policy say about sick days?
```

Type `quit`, `exit` or `bye` to leave (`Ctrl+C` also works).

## Deactivating the virtual environment

When you have finished, leave the virtual environment with the same command in every terminal (Command Prompt, PowerShell, macOS and Linux):

```bash
deactivate
```

The `(venv)` marker disappears from your prompt. To use the project again later, activate the environment again as described in step 3.

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Entry point and chat loop |
| `config.py` | Settings, system prompt, and the shared model client |
| `llm.py` | Streaming a reply and the tool-calling loop |
| `tools.py` | Tool functions, their schemas and spinner labels, and the tool runner |
| `history.py` | Summarising old messages to keep the context small |
| `ui.py` | Terminal spinner |

## Configuration

All settings are in `config.py`:

| Setting | Meaning |
|---|---|
| `MODEL` | Model name supported by your chosen provider |
| `TEMPERATURE` | Sampling temperature |
| `BASE` | Folder the assistant is allowed to read |
| `MAX_FILE_CHARS` | Maximum characters returned from one file |
| `MAX_TOOL_ROUNDS` | Tool calls allowed in a row before stopping |
| `CONTEXT_BUDGET_CHARS` | History size that triggers summarising (roughly 4 characters per token) |
| `KEEP_RECENT_TURNS` | Recent user turns kept word-for-word when summarising |

Set `CONTEXT_BUDGET_CHARS` comfortably below your model's context length. For local models, Ollama's default context window is small, so you may want to raise `num_ctx` for your model.

## Adding a tool

In `tools.py`:

1. Write the function.
2. Add it to `FUNCTIONS`.
3. Add a spinner label to `TOOL_LABELS`.
4. Add its schema to `TOOLS`.
