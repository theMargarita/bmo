import sqlite3
import chromadb
import pytest
from memory.bmos_memory import BMOsMemory
class FakeEmbedder:
    def __init__(self, dim=8):
        self.dim = dim
        self.reranker = None

    def embed(self, text: str):
        return [0.01 * (i + len(text)) for i in range(self.dim)]

    def embed_batch(self, texts: list[str]):
        return [self.embed(t) for t in texts]

    def __call__(self, inputs: list[str]):
        return self.embed_batch(inputs)

    def name(self):
        return "fake_embedder"
    

@pytest.fixture
def tmp_db_and_chroma(tmp_path):
    # SQLite DB
    db_path = tmp_path / "bmo_test.db"
    # Create sqlite schema expected by BMOsMemory
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role_description TEXT,
            relationship_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            facts TEXT,
            role_id INTEGER,
            bmo_perception TEXT,
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role_id TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            source TEXT,
            chroma_id TEXT UNIQUE,
            importance INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bmo_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            status TEXT,
            mood TEXT,
            detail TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
    
    # Chroma persistent store in a temp dir
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    client = chromadb.PersistentClient(chroma_dir.as_posix())
    coll = client.get_or_create_collection(name="test_bmo_memories", embedding_function=FakeEmbedder())

    yield str(db_path), coll

