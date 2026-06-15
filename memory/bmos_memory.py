import os
import uuid
import sqlite3

# from sentence_transformers import CrossEncoder
from brain.llm import LLMClient
import chromadb  # type: ignore
from memory.chunker import Chunker

from config import CHROMA_PATH
from memory.embedder import Embedder
from memory.importance_score import calculate_importance


class BMOsMemory:
    def __init__(
        self,
        db_path="data/bmo_memory.db",
        chroma_collection=None,
        embedder: Embedder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.llm = llm_client or LLMClient()
        self.chunker = Chunker(chunk_size=200, overlap=15)
        self.embedder = embedder or Embedder()
        self.reranker = self.embedder.reranker

        if chroma_collection is not None:
            self.collection = chroma_collection
            self.chroma = None
        else:
            self.chroma = chromadb.PersistentClient(CHROMA_PATH)
            self.collection = self.chroma.get_or_create_collection(
                name="bmo_memories",
                embedding_function=self.embedder,
                metadata={"hnsw:space": "cosine"},
            )

    # -----SYNC function-----
    def seed_database(self, owner_name="Creator"):
        # checks if roles exists, if not - hardcode
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # checks if roles exists, if not - hardcode them
            cursor.execute("SELECT COUNT(*) FROM roles")
            if cursor.fetchone()[0] == 0:
                # streamline code instead of repeat code
                roles = [
                    ("Creator", "The creator of AI inspired BMO", "It's her child."),
                    ("Acquaintance", "A familiar face", "Casual contact."),
                    ("Friend", "Be there for each other", "Shared history."),
                    ("Partner-in-crime", "Serves as the twin", "Chaos and fun."),
                ]
                cursor.executemany(
                    "INSERT INTO roles (name, role_description, relationship_notes) VALUES (?,?,?)",
                    roles,
                )
                conn.commit()
                print("[Database] Default roles injected")
            # check if default user exists, if not - create user ID
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (name, facts, role_id, bmo_perception) VALUES (?, ?, 1, '{}')",
                    (owner_name, ""),
                )
                conn.commit()
                print(f"[Database] Default user '{owner_name}' created as User ID 1.")

    # chromadb har no async API so it stays sync
    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error counting memories: {e}")
            return 0

    # -------conversation table functions------
    def save_conversations(self, user_id, message, summary=None):
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO conversations (user_id, message, summary) VALUES (?,?,?)",
                    (user_id, message, summary),
                )
                connection.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error saving conversations: {e}")
            return None

    # ------end session---
    def end_session(self, conversation_id, summary=None):
        try:
            if summary:
                with sqlite3.connect(self.db_path) as connection:
                    cursor = connection.cursor()
                    # Wrapped arguments in a tuple
                    cursor.execute(
                        "UPDATE conversations SET summary = ? WHERE id = ?",
                        (
                            summary,
                            conversation_id,
                        ),
                    )
                    connection.commit()
        except sqlite3.Error as e:
            print(f"Could not create or save a summary: {e}")
            return None

    #'core' memory saving
    def save(
        self, content: str, source: str, importance: int = None, tags: list = None
    ):
        try:
            if importance is None:
                importance = calculate_importance(content)

            chunks = self.chunker.chunk_text_with_overlap(content)
            if not chunks:
                return

            # Format source with tags if provided
            entry_source = source
            if tags:
                entry_source = f"{source} | tags: {','.join(tags)}"

            # Generate distinct unique IDs for each chunk
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [
                {"source": entry_source, "importance": importance} for _ in chunks
            ]
            embeddings = self.embedder.embed_batch(chunks)

            self.collection.add(
                documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas
            )

            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                for id, single_chunk in zip(ids, chunks):
                    cursor.execute(
                        "INSERT INTO memories (content, source, chroma_id, importance) VALUES (?,?,?,?)",
                        (single_chunk, entry_source, id, importance),
                    )
                connection.commit()
                #
                print(
                    f"[Memory] Librarian successfully archived {len(chunks)} new memory chunks."
                )

        except Exception as e:
            print(f"Error saving memory: {e}")

    # same here
    def update_bmo_state(
        self, event: str, status: str, mood: str = None, detail: str = None
    ):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bmo_state (event, status, mood, detail) VALUES (?,?,?,?)",
                    (event, status, mood, detail),
                )
                conn.commit()
        except Exception as e:
            print(f"Could not update BMO's status: {e}")

    def get_bmo_state(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT event, status, mood, detail FROM bmo_state ORDER BY last_updated DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "event": row[0],
                        "status": row[1],
                        "mood": row[2],
                        "detail": row[3],
                    }
        except Exception as e:
            print(f"Could not fetch BMOs status: {e}")
            return None

    # now this will be used for chromadb
    def search_context(self, query: str, n: int = 5) -> list[str]:
        if self.collection.count() == 0:
            return []
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n, self.collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]

            # combine sematics similarity with importance score
            scored = []
            for doc, meta, dist in zip(docs, metas, distances):
                similarity = 1 - dist  # consine distance importance score
                importance_boost = meta.get("importance", 0) / 10
                score = similarity + (importance_boost * 0.3)
                scored.append((score, doc))

            scored.sort(reverse=True)
            return [doc for _, doc in scored[:3]]

        except Exception as e:
            print(f"Could not update user: {e}")
            return []
