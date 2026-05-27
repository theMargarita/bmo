# Central settings for BMO behaviour

# Ollama model to use
# Options: "llama3.2", "llama3.2:1b", "mistral", "gemma3:1b"
# Start with llama3.2 on your laptop, switch to llama3.2:1b if too slow on Pi
MODEL = "llama3.2"
# MODEL = "llama3.2:3b"

# Ollama runs locally — no API key needed
OLLAMA_URL = "http://localhost:11434"

# How many past messages to keep in short-term memory per session
# Higher = better context but slower responses on Pi
MAX_HISTORY = 20

# How many long-term memories to inject per response (once DB is added)
MAX_MEMORIES = 5

# Identity file path (created automatically if missing)
IDENTITY_FILE = "data/identity.json"

# Database path (used later when we add long-term memory)
DB_PATH = "data/bmo_memory.db"
CHROMA_PATH = "data/chroma"
