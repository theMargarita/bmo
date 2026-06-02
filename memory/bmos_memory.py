import os
import uuid
import sqlite3
from brain.llm import LLMClient
import chromadb
from chromadb.utils import embedding_functions
from memory.chunker import Chunker

from config import CHROMA_PATH

class BMOsMemory:
    def __init__(self, db_path="data/bmo_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.llm = LLMClient()
        # self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.chunker = Chunker(chunk_size=200, overlap=15)

        # chroma setup
        self.chroma = chromadb.PersistentClient(CHROMA_PATH)

        self.embedding_fu = embedding_functions.OllamaEmbeddingFunction(
            model_name="nomic-embed-text"
        )

        self.collection = self.chroma.get_or_create_collection(
            name="bmo_memories",
            embedding_function=self.embedding_fu,
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
                    (owner_name,),
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


    #not sure about thins one yet 
    def calculate_importance(self, text:str) -> int:
        text_lower = text.lower()
        score = 3 #mundane facts

        #high-value emotional or relational keywords
        core_concepts = [] #emotions, feeling, other keywords
        if any(w in text_lower for w in core_concepts):
            score += 3

        #identity marks (more focus on me and bmo)
        identity_marks = [] #like 'you are' 'my' etc
        if any(m in text_lower for m in identity_marks):
            score += 2

        if '!' in text or text.isupper():
            score += 1

        return min(score, 10)

    # Saving 'core' memories
    def save(self, content: str, source: str, importance: int = 0, tags: list = None):
        try:
            chunks = self.chunker.chunk_text_with_overlap(content)
            for c in chunks:
                chroma_id = str(uuid.uuid4())
                entry_source = source
                if tags:
                    entry_source = f"{source} | tags: {','.join(tags)}"

                # save chunk to sqlite
                try:
                    with sqlite3.connect(self.db_path) as connection:
                        cursor = connection.cursor()
                        cursor.execute(
                            "INSERT INTO memories (content, source, importance, chroma_id) VALUES (?,?,?,?)",
                            (c, entry_source, importance, chroma_id),
                        )
                        connection.commit()
                except sqlite3.Error as db_err:
                    print(f"SQLite error saving memory chunk: {db_err}")
                    # continue to attempt adding to chroma, but do not crash

                # save vectors to chromadb (one add per chunk)
                try:
                    self.collection.add(
                        documents=[c],
                        ids=[chroma_id],
                        metadatas=[{"source": entry_source, "importance": importance}],
                    )
                except Exception as ch_err:
                    print(f"Chroma add failed for chunk (id={chroma_id}): {ch_err}")
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
                include=["documents", "metadatas", "distances"]
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]

           #combine sematics similarity with importance score 
            scored = []
            for doc, meta, dist in zip(docs, metas, distances):
                similarity = 1 - dist #consine distance importance score
                importance_boost = meta.get("importance", 0) / 10
                score = similarity + (importance_boost * 0.3)
                scored.append((score, doc))

            scored.sort(reverse=True)
            return [doc for _, doc in scored[:3]]

            # if (
            #     results
            #     and results.get("documents")
            #     and len(results["documents"][0]) > 0
            # ):
            #     return results["documents"][0]
        except Exception as e:
            print(f"Could not update user: {e}")

