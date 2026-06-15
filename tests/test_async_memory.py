import json

import aiosqlite
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from memory.bmo_memory_async import BMOMemoryAsync

@pytest.mark.asyncio
async def test_start_session_and_saves():
    mem = BMOMemoryAsync()
    mem.sync = MagicMock()
    mem.save_conversation = AsyncMock(return_value=42)   # <- corrected name

    result = await mem.start_session("Curious", 2)

    mem.sync.update_bmo_state.assert_called_once_with(
        event="start_session",
        status="active",
        mood="Curious",
        detail="User initiated chat.",
    )

    mem.save_conversation.assert_awaited_once_with(
        2, "Session started.\nBMO's mood: Curious"
    )
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


@pytest.mark.asyncio
async def test_consolidate_bmo_updates_db_and_calls_side_effects(tmp_path):
    db_path = tmp_path / "bmo.db"

    # Create schema and seed a user (id will be 1)
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
            CREATE TABLE roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
            CREATE TABLE conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, summary TEXT);
            CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER, role_id TEXT, content TEXT);
            CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, importance INTEGER);
        """)
        await conn.execute("INSERT INTO roles (name) VALUES ('Acquaintance')")
        # insert a user with some initial facts and perception
        initial_perception = json.dumps({"connection_to_owner": "unknown"})
        await conn.execute(
            "INSERT INTO users (name, facts, role_id, bmo_perception) VALUES (?, ?, ?, ?)",
            ("TestUser", "Existing facts", 1, initial_perception),
        )
        await conn.commit()

    # Prepare BMOMemoryAsync instance and mock heavy collaborators / side-effects
    memory = BMOMemoryAsync()
    memory.db_path = str(db_path)
    # Mock LLM to return a JSON string the method expects
    llm_response = {
        "updated_facts": "Learned that they like tea.",
        "updated_perception": {"connection_to_owner": "friend", "bmo_feelings_toward_them": "warm", "trust_level": 7, "inside_jokes": []},
        "conversation_summary": "Talked about tea and coding.",
        "emotional_valence": "Positive",
        "new_core_memories": ["They prefer green tea."]
    }
    memory.llm = MagicMock()
    memory.llm.chat = MagicMock(return_value=json.dumps(llm_response))

    # Mock sync-side effects that are called (end_session, update_bmo_state, save)
    memory.end_session = MagicMock()
    memory.update_bmo_state = MagicMock()
    memory.save = MagicMock()

    # Run consolidation
    await memory.consolidate_bmo(user_id=1, conversation_id=42, recent_messages="User: I love tea. BMO: Nice!")

    # Assert DB was updated with the new facts and perception
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT facts, bmo_perception FROM users WHERE id = ?", (1,))
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "Learned that they like tea."
    # bmo_perception is stored as JSON string
    assert row[1] == json.dumps(llm_response["updated_perception"])

    # Assert side-effect calls
    memory.end_session.assert_called_once_with(42, "Talked about tea and coding.")
    memory.update_bmo_state.assert_called_once_with(
        event="end_session_consolidation",
        status="resting",
        mood="Positive",
        detail="Processed session summary: Talked about tea and coding."
    )
    memory.save.assert_called_with("They prefer green tea.", "Chat Consolidation", 8)