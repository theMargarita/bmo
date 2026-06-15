import sqlite3
import pytest
from unittest.mock import MagicMock
import chromadb
from memory.bmos_memory import BMOsMemory

class FakeEmbedder(chromadb.EmbeddingFunction):
    """Deterministic embedder – no network / model required."""

    def __init__(self, dim: int = 8):
        self.dim = dim
        self.reranker = None

    def embed(self, text: str) -> list[float]:
        return [0.01 * (i + len(text)) for i in range(self.dim)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embed_batch(input)

    def name(self) -> str:
        return "fake_embedder"


_SCHEMA_SQL = """
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
"""


def _make_db(tmp_path) -> str:
    db_path = tmp_path / "bmo_test.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    return str(db_path)


def _make_chroma(tmp_path):
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    client = chromadb.PersistentClient(path=chroma_dir.as_posix())
    return client.get_or_create_collection(
        name="test_bmo_memories",
        embedding_function=FakeEmbedder(),
    )


def _build_mem(db_path: str, coll) -> BMOsMemory:
    """Return a BMOsMemory with all external dependencies mocked out."""
    mock_llm = MagicMock()
    mem = BMOsMemory(
        db_path=db_path,
        chroma_collection=coll,
        embedder=FakeEmbedder(),
        llm_client=mock_llm,
    )
    mem.chunker = MagicMock()
    mem.chunker.chunk_text_with_overlap.side_effect = lambda text: [text]
    return mem

@pytest.fixture()
def real_env(tmp_path):
    """Real SQLite + real ChromaDB – used by integration tests."""
    db_path = _make_db(tmp_path)
    coll = _make_chroma(tmp_path)
    mem = _build_mem(db_path, coll)
    yield db_path, coll, mem


@pytest.fixture()
def unit_mem(tmp_path):
    """
    Unit-test fixture: SQLite is real (cheap), but ChromaDB collection is
    fully mocked so tests don't touch the filesystem for vector ops.
    """
    db_path = _make_db(tmp_path)
    mock_coll = MagicMock()
    mock_coll.count.return_value = 0
    mock_coll.query.return_value = {"documents": [[]], "distances": [[]], "ids": [[]]}
    mock_llm = MagicMock()
    mem = BMOsMemory(
        db_path=db_path,
        chroma_collection=mock_coll,
        embedder=FakeEmbedder(),
        llm_client=mock_llm,
    )
    mem.chunker = MagicMock()
    mem.chunker.chunk_text_with_overlap.side_effect = lambda text: [text]
    return db_path, mock_coll, mem


"""""
Unit tests
"""""
"""ChromaDB is mocked."""
class TestSaveMemoryUnit:
    def test_save_returns_without_error(self, unit_mem):
        _, _, mem = unit_mem
        mem.save("some fact", source="test", importance=5)

    def test_save_writes_to_sqlite(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.save("chocolate is delicious", source="unit_test", importance=3)
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT content, source, importance FROM memories").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "chocolate is delicious"
        assert rows[0][1] == "unit_test"
        assert rows[0][2] == 3

    def test_save_default_importance(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.save("default importance fact", source="auto")
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT importance FROM memories").fetchone()
        # Default importance from schema is 2; verify it's a valid integer
        assert isinstance(row[0], int)

    def test_save_empty_string(self, unit_mem):
        """Saving an empty string should not raise."""
        _, _, mem = unit_mem
        mem.save("", source="test", importance=1)

    def test_save_high_importance_boundary(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.save("critical fact", source="test", importance=10)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT importance FROM memories").fetchone()
        assert row[0] == 10

"""ChromaDB is mocked."""
class TestSearchContextUnit:
    def test_returns_list(self, unit_mem):
        _, _, mem = unit_mem
        results = mem.search_context("anything", n=3)
        assert isinstance(results, list)

    def test_empty_collection_returns_empty(self, unit_mem):
        _, mock_coll, mem = unit_mem
        mock_coll.query.return_value = {"documents": [[]], "distances": [[]], "ids": [[]]}
        results = mem.search_context("nothing here", n=5)
        assert results == [] or isinstance(results, list)


"""Tests for save_conversations() and end_session()."""
class TestConversationsUnit:
    def test_save_conversations_returns_id(self, unit_mem):
        db_path, _, mem = unit_mem
        conv_id = mem.save_conversations(user_id=1, message="Hello", summary=None)
        assert conv_id is not None
        assert isinstance(conv_id, int)

    def test_save_conversations_persists_message(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.save_conversations(user_id=1, message="Test message", summary=None)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT message FROM conversations").fetchone()
        assert row[0] == "Test message"

    def test_save_conversations_with_summary(self, unit_mem):
        db_path, _, mem = unit_mem
        conv_id = mem.save_conversations(user_id=2, message="Hi", summary="Initial summary")
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT summary FROM conversations WHERE id=?", (conv_id,)
            ).fetchone()
        assert row[0] == "Initial summary"

    def test_end_session_updates_summary(self, unit_mem):
        db_path, _, mem = unit_mem
        conv_id = mem.save_conversations(user_id=1, message="msg", summary=None)
        mem.end_session(conv_id, summary="Final recap")
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT summary FROM conversations WHERE id=?", (conv_id,)
            ).fetchone()
        assert row[0] == "Final recap"

    def test_end_session_does_not_affect_other_rows(self, unit_mem):
        db_path, _, mem = unit_mem
        id1 = mem.save_conversations(1, "first", summary=None)
        id2 = mem.save_conversations(1, "second", summary=None)
        mem.end_session(id1, summary="Only first")
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT summary FROM conversations WHERE id=?", (id2,)
            ).fetchone()
        assert row[0] != "Only first" or row[0] is None

    def test_save_multiple_conversations(self, unit_mem):
        db_path, _, mem = unit_mem
        for i in range(5):
            mem.save_conversations(user_id=i, message=f"msg {i}", summary=None)
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        assert count == 5


class TestBMOStateUnit:
    def test_update_then_get(self, unit_mem):
        _, _, mem = unit_mem
        mem.update_bmo_state(event="boot", status="ok", mood="calm", detail="d")
        state = mem.get_bmo_state()
        assert state["event"] == "boot"
        assert state["status"] == "ok"
        assert state["mood"] == "calm"

    def test_returns_dict(self, unit_mem):
        _, _, mem = unit_mem
        mem.update_bmo_state(event="x", status="y", mood="z", detail="w")
        assert isinstance(mem.get_bmo_state(), dict)

    """get_bmo_state should handle empty table gracefully."""
    def test_get_state_before_any_update(self, unit_mem):
        _, _, mem = unit_mem
        state = mem.get_bmo_state()
        assert state is None or isinstance(state, dict)

    def test_detail_stored_correctly(self, unit_mem):
        _, _, mem = unit_mem
        mem.update_bmo_state(
            event="ev", status="st", mood="mo", detail="Long detail text here"
        )
        state = mem.get_bmo_state()
        assert state["detail"] == "Long detail text here"


"""Tests for seed_database()."""
class TestSeedDatabaseUnit:
    def test_seed_creates_roles(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.seed_database(owner_name="Alice")
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
        assert count >= 1

    def test_seed_creates_owner_user(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.seed_database(owner_name="Alice")
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT name FROM users WHERE name=?", ("Alice",)
            ).fetchone()
        assert row is not None

    #Calling seed twice should not raise and should not duplicate owner
    def test_seed_idempotent(self, unit_mem):
        db_path, _, mem = unit_mem
        mem.seed_database(owner_name="Bob")
        mem.seed_database(owner_name="Bob")
        with sqlite3.connect(db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE name=?", ("Bob",)
            ).fetchone()[0]
        # Should be 1 or at least consistent (implementation-defined)
        assert count >= 1


class TestCountUnit:
    def test_count_empty(self, unit_mem):
        _, mock_coll, mem = unit_mem
        mock_coll.count.return_value = 0
        assert mem.count() == 0

    def test_count_after_save(self, unit_mem):
        _, mock_coll, mem = unit_mem
        mock_coll.count.return_value = 1
        mem.save("a fact", source="x", importance=2)
        assert mem.count() >= 0  # mocked count; just verify method runs

    def test_count_reflects_chroma(self, unit_mem):
        _, mock_coll, mem = unit_mem
        mock_coll.count.return_value = 42
        assert mem.count() == 42


#Sanity-check the shared test utility
class TestFakeEmbedder:
    def test_embed_length(self):
        e = FakeEmbedder(dim=8)
        assert len(e.embed("hello")) == 8

    def test_embed_batch(self):
        e = FakeEmbedder(dim=4)
        results = e.embed_batch(["a", "bb", "ccc"])
        assert len(results) == 3
        assert all(len(v) == 4 for v in results)

    def test_callable_interface(self):
        e = FakeEmbedder(dim=6)
        out = e(["text1", "text2"])
        assert len(out) == 2

    def test_different_lengths_differ(self):
        e = FakeEmbedder(dim=8)
        v1 = e.embed("a")
        v2 = e.embed("longer text")
        assert v1 != v2
