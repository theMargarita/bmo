# BMO: Conversational AI Agent

## Overview

BMO is a conversational AI agent designed to interact with users, maintain a memory of past interactions, and exhibit a customizable personality and mood. The project is modular, making it easy to extend or adapt for different use cases.

## Features

- **Personality & Mood:** Customizable system prompt and mood for dynamic responses.
- **Memory Management:** Supports both long-term and short-term memory to provide context-aware conversations.
- **Prompt Building:** Assembles messages for the LLM, including system prompts, memories, and conversation history.
- **Configurable Identity:** Loads identity and owner information from JSON files.

## Project Structure

```
config.py                # Configuration settings
main.py                  # Entry point for running the agent
requirements.txt         # Python dependencies

brain/
    __init__.py
    llm.py               # LLM interface and logic
    personality.py       # Personality and mood management
    prompt_builder.py    # Builds prompts for the LLM

data/
    identity.json        # Agent's identity configuration
    owner.json           # Owner/user configuration

memory/
    __init_.py
    identity.py          # Identity management logic
    short_term.py        # Short-term memory implementation
```

## How It Works

1. **Initialization:** Loads configuration, identity, and owner data.
2. **Prompt Building:** Uses `PromptBuilder` to assemble the system prompt, relevant memories, and recent conversation history.
3. **LLM Interaction:** Sends the built prompt to the LLM and receives a response.
4. **Memory Update:** Updates short-term and long-term memory as needed.

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

## Requirements

- Python 3.9+
- See `requirements.txt` for dependencies

## License

MIT License

---

BMO is inspired by the idea of a friendly, context-aware AI companion. Contributions and suggestions are welcome!
