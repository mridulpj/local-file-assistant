"""Entry point: the chat loop. Run with: python main.py"""
from config import SYSTEM, EXIT_WORDS, EXIT_MESSAGE, client
from history import compact_history
from llm import ask


def main():
    try:
        messages = [{"role": "system", "content": SYSTEM}]
        print("Type 'quit' to exit.")
        while True:
            try:
                user = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n" + EXIT_MESSAGE + "\n")
                break
            if user.lower() in EXIT_WORDS:
                print("\n" + EXIT_MESSAGE + "\n")
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
