# BMO: Conversational AI Agent

## Overview

BMO is a conversational AI agent designed to interact with users, maintain a memory of past interactions, and exhibit a customizable personality and mood. The project is modular, making it easy to extend or adapt for different use cases.

## Features

- **Personality & Mood:** Customizable system prompt and mood for dynamic responses.
- **Memory Management:** Long-term (SQLite/ChromaDB) and short-term memory modules for context-aware conversations.
- **Prompt Building:** Assembles messages for the LLM, including system prompts, memories, and conversation history.
- **Configurable Identity:** Loads identity and owner information from JSON files.
- **LLM & Embeddings:** Integrates with local LLMs and supports text embeddings for memory search.
- **Testing:** Includes a test suite for memory modules.

## Project Structure

```
config.py                # Configuration settings
main.py                  # Entry point for running the agent
requirements.txt         # Python dependencies

brain/
    __init__.py
    bmo_status.py        # BMO state and status logic
    llm.py               # LLM interface and logic
    personality.py       # Personality and mood management
    prompt_builder.py    # Builds prompts for the LLM

data/
    db.py                # Database helpers
    identity.json        # Agent's identity configuration
    owner.json           # Owner/user configuration
    chroma/              # ChromaDB persistent storage
        chroma.sqlite3
        ...

memory/
    __init__.py
    bmos_memory.py       # Long-term memory (SQLite/ChromaDB)
    commands.py          # CLI and memory commands
    identity.py          # Identity management logic
    short_term.py        # Short-term memory implementation

tests/
    __init__.py
    test_async_memory.py  # Tests for async memory/session behavior
    test_db.py            # Tests for SQLite + ChromaDB memory operations
    test_short_term.py    # Tests for short-term memory logic
```

## How It Works

1. **Initialization:** Loads configuration, identity, and owner data.
2. **Prompt Building:** Uses `PromptBuilder` to assemble the system prompt, relevant memories, and recent conversation history.
3. **LLM Interaction:** Sends the built prompt to the LLM and receives a response.
4. **Memory Update:** Updates short-term and long-term memory (SQLite/ChromaDB) as needed.
5. **Testing:** Run tests in the `tests/` folder to validate memory logic.

## Getting Started

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the agent:
   ```bash
   python main.py
   ```

## Customization

- Edit `data/identity.json` and `data/owner.json` to change the agent's identity and owner information.
- Modify `brain/personality.py` to adjust the system prompt and mood.
- Update `brain/llm.py` to change LLM backend or embedding model.

## Requirements

- Python 3.9+
- See `requirements.txt` for dependencies

## Troubleshooting

- **SQLite ProgrammingError: type 'list' is not supported**
  - This error occurs if you try to store a Python list directly in a SQLite column. Convert lists to strings (e.g., with `json.dumps(your_list)`) before saving, and use `json.loads()` to restore them.

## License

MIT License

---

BMO is inspired by the idea of a friendly, context-aware AI companion. Contributions and suggestions are welcome!
