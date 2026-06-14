import aiosqlite
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from memory.bmo_memory_async import BMOMemoryAsync

@pytest.mark.asyncio
async def test_start_session_and_saves():
    mem = BMOMemoryAsync()
    mem.sync = MagicMock()
    mem.save_conversations = AsyncMock(return_value=42)
    
    result = await mem.start_session("Curious", 2)

    mem.sync.update_bmo_state.assert_called_once_with(
        event="start_session",
        status="active",
        mood="Curious",
        detail="User initiated chat.",
    )

    mem.save_conversation.assert_awaited_once_with(2,"Session started.\nBMO's mood: curious")

    assert result == 42

@pytest_asyncio.fixture
async def temp_db(tmp_path):
    db_path = tmp_path / "bmo.db"

    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                facts TEXT,
                role_id INTEGER,
                bmo_perception TEXT,
                last_interaction TIMESTAMP
            );
            CREATE TABLE roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT
            );
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                role_id TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                importance INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await conn.execute("INSERT INTO roles (name) VALUES ('Acquaintance')")
        await conn.commit()

    return str(db_path)

@pytest.mark.asyncio
async def test_save_conversation_round_trip(temp_db):
    with patch("brain.llm.LLMClient"), \
         patch("chromadb.PersistentClient"), \
         patch("memory.embedder.Embedder"):
        memory = await BMOMemoryAsync.create(db_path=temp_db)

    conversation_id = await memory.save_conversation(1, "Hello", "Greeting")

    async with aiosqlite.connect(temp_db) as conn:
        cursor = await conn.execute(
            "SELECT user_id, message, summary FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        row = await cursor.fetchone()

    assert row == (1, "Hello", "Greeting")