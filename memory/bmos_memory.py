import asyncio
import json
import os
import uuid
import aiosqlite
import sqlite3
from brain.llm import LLMClient
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_PATH

# small offline emmbedding model
# EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class BMOsMemory:
    def __init__(self, db_path="data/bmo_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.llm = LLMClient()

        #chroma setup
        self.chroma = chromadb.PersistentClient(CHROMA_PATH)

        # embeddings function converts text -> verctors
        # self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        #     model_name=EMBEDDING_MODEL
        # )'
        self.embedding_fu = embedding_functions.OllamaEmbeddingFunction(
            model_name="nomic-embed-text"
        )

        self.collection = self.chroma.get_or_create_collection(
            name="bmo_memories",
            embedding_function=self.embedding_fu,
            metadata={"hnsw:space": "cosine"},
        )

    #-----SYNC function-----
    def seed_database(self, owner_name="Creator"):
        # checks if roles exists, if not - hardcode the
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # checks if roles exists, if not - hardcode them
            cursor.execute("SELECT COUNT(*) FROM roles")
            if cursor.fetchone()[0] == 0:
                #streamline code instead of repeat code
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

    #chromadb har no async API so it stays sync
    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error counting memories: {e}")
            return 0

    def search_context(self, query: str, n: int = 3) -> list[str]:
        if self.collection.count() == 0:
            return []
        try:
            results = self.collection.query(
                query_texts=[query], n_results=min(n, self.collection.count())
            )
            if results and results.get("documents") and results["documents"][0]:
                return results["documents"][0]
        except Exception as e:
            print(f"[BMO memory] Search error: {e}")
        return []
    #saving both DBs so must stay sync for chromadb
    def save(self, content: str, source: str, importance: int = 0, tags: list = None):
        try:
            chroma_id = str(uuid.uuid4())
            if tags:
                source = f"{source} | tags: {','.join(tags)}"

            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO memories (content, source, chroma_id, importance) VALUES (?,?,?,?)",
                    (content, source, chroma_id, importance),
                )
                connection.commit()
                # save vectors to chromadb
            self.collection.add(
                documents=[content],
                ids=[chroma_id],
                metadatas=[{"source": source, "importance": importance}],
            )
        except Exception as e:
            print(f"Error saving memory: {e}")
    #same here
    def update_bmo_state(self, event: str, status: str, mood: str = None, detail: str = None):
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

    def end_session(self, conversation_id, summary=None):
        if not summary:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE conversations SET summary = ? WHERE id = ?",
                    (summary, conversation_id),
                )
                conn.commit()
        except Exception as e:
            print(f"Could not save summary: {e}")

    #--------ASYNC functions--------

    async def start_session(self, mood: str, user_id: int = 1) -> int:
        self.update_bmo_state(
            event="start_session",
            status="active",
            mood=mood,
            detail="User initiated chat.",
        )
        return await self.save_conversation(user_id, f"Session started.\nBMO's mood: {mood}")

    async def save_conversation(self, user_id: int, message: str, summary=None) -> int | None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "INSERT INTO conversations (user_id, message, summary) VALUES (?,?,?)",
                    (user_id, message, summary),
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return None

    async def save_chat_message(self, conversation_id: int, role_id: str, content: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "INSERT INTO messages (conversation_id, role_id, content) VALUES (?,?,?)",
                    (conversation_id, role_id, content),
                )
                await conn.commit()
        except Exception as e:
            print(f"Could not save chat message: {e}")

    async def get_conversation_history(self, conversation_id: int) -> list:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT role_id, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            )
            return await cursor.fetchall()

    async def update_user_relation(self, user_id: int, new_fact: str, bmo_perception_json: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT facts FROM users WHERE id = ?", (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    updated_facts = f"{row[0]} | {new_fact}" if row[0] else new_fact
                    await conn.execute(
                        """UPDATE users
                           SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP
                           WHERE id = ?""",
                        (updated_facts, bmo_perception_json, user_id),
                    )
                    await conn.commit()
        except Exception as e:
            print(f"Could not update user: {e}")

    async def fetch_bmos_thoughts(self, user_id: int) -> dict:
        bmo_thoughts = {
            "user_context": "",
            "core_memories": [],
            "recent_events": [],
        }

        async with aiosqlite.connect(self.db_path) as connection:
            # User context
            cursor = await connection.execute(
                "SELECT name, facts, bmo_perception FROM users WHERE id = ?",
                (user_id,),
            )
            user_data = await cursor.fetchone()
            if user_data:
                bmo_thoughts["user_context"] = (
                    f"You are talking to {user_data[0]}. "
                    f"Facts you know about them: {user_data[1]}. "
                    f"Your private thoughts/perception about them: {user_data[2]}."
                )

            #high-importance memories (random sample so BMO feels varied)
            cursor = await connection.execute(
                "SELECT content FROM memories WHERE importance >= 7 ORDER BY RANDOM() LIMIT 2"
            )
            bmo_thoughts["core_memories"] = [row[0] for row in await cursor.fetchall()]

            #most recent memories
            cursor = await connection.execute(
                "SELECT content FROM memories ORDER BY created_at DESC LIMIT 3"
            )
            bmo_thoughts["recent_events"] = [row[0] for row in await cursor.fetchall()]

        return bmo_thoughts

    async def get_role_id(self, role_name: str) -> int | None:
        async with aiosqlite.connect(self.db_path) as connection:
            cursor = await connection.execute(
                "SELECT id FROM roles WHERE name = ?", (role_name,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_or_create_user(self, name: str) -> int:
        async with aiosqlite.connect(self.db_path) as connection:
            cursor = await connection.execute(
                "SELECT id FROM users WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if row:
                return row[0]

            # Look up role_id on the SAME connection instead of opening a new one
            cursor = await connection.execute(
                "SELECT id FROM roles WHERE name = ?", ("Acquaintance",)
            )
            role_row = await cursor.fetchone()
            default_role_id = role_row[0] if role_row else None

            if default_role_id is None:
                print("[Warning] 'Acquaintance' role not found — did seed_database() run?")

            initial_perception = json.dumps({
                "connection_to_owner": "unknown",
                "bmo_feelings_toward_them": "neutral, just met",
                "trust_level": 3,
                "inside_jokes": [],
            })

            cursor = await connection.execute(
                "INSERT INTO users (name, facts, role_id, bmo_perception) VALUES (?,?,?,?)",
                (name, "A new person BMO has just met.", default_role_id, initial_perception),
            )
            await connection.commit()
            return cursor.lastrowid

    async def consolidate_bmo(self, user_id: int, conversation_id: int, recent_messages: str):
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT facts, bmo_perception FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()

        if not row:
            print(f"User {user_id} not found. Cannot consolidate memory.")
            return

        current_facts = row[0] or "No facts recorded yet."
        current_perception = json.loads(row[1]) if row[1] else {}

        analysis_prompt = f"""
            You are the subconscious memory-processing core of a companion AI named BMO.
            You are reflective, curious, emotionally intelligent, playful, and slightly strange in a comforting way.

            Review the conversation and update your records.

            Current Memory Facts: {current_facts}
            Current BMO Perception: {json.dumps(current_perception)}

            Recent Conversation:
            {recent_messages}

            Return a raw JSON object with these fields:
            1. "updated_facts": Summary of concrete facts learned (string).
            2. "updated_perception": JSON with "connection_to_owner", "bmo_feelings_toward_them",
                "trust_level" (1-10), and "inside_jokes" (array).
            3. "conversation_summary": 1-2 sentence summary (string).
            4. "emotional_valence": One of: "Positive", "Negative", "Neutral", "Anxious", "Curious", "Skeptical".
            5. "new_core_memories": Array of strings with highly distinct concepts or preferences.

            Respond ONLY with the raw JSON object. Do not wrap in markdown fences.
            """
        messages = [{"role": "user", "content": analysis_prompt}]
        llm_response = await asyncio.to_thread(self.llm.chat, messages)

        try:
            clean_response = (
                llm_response.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            new_data = json.loads(clean_response)

            # Normalise updated_facts to a plain string regardless of what the LLM returns
            new_facts = new_data.get("updated_facts")
            if isinstance(new_facts, list):
                new_facts = "\n".join(f"- {fact}" for fact in new_facts)
            elif isinstance(new_facts, dict):
                new_facts = json.dumps(new_facts)
            elif not new_facts:
                new_facts = "No facts recorded yet."
            else:
                new_facts = str(new_facts)

            new_perception_str = json.dumps(new_data.get("updated_perception", {}))
            summary = new_data.get("conversation_summary", "No summary provided.")
            valence = new_data.get("emotional_valence", "Neutral")
            core_memories = new_data.get("new_core_memories", [])

            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """UPDATE users
                       SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (new_facts, new_perception_str, user_id),
                )
                await conn.commit()
            # ending session - start processing new memory
            await asyncio.to_thread(self.end_session, conversation_id, summary)

            self.update_bmo_state(
                event="end_session_consolidation",
                status="resting",
                mood=valence,
                detail=f"Processed session summary: {summary}",
            )

            for memory_text in core_memories:
                await asyncio.to_thread(self.save, memory_text, "Chat Consolidation", 8)

            print("BMO safely stored new memories!")

        except json.JSONDecodeError:
            print("Oops! BMO's thoughts were too chaotic to parse this time.")