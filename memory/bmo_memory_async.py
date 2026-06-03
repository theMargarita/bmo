import asyncio
import json
import os
import aiosqlite
import chromadb
from brain.llm import LLMClient
from config import CHROMA_PATH
from memory.chunker import Chunker
from chromadb.utils import embedding_functions


class BMOMemoryAsync:
    def __init__(self):
        self.db_path = None
        self.llm = None
        self.chroma = None
        self.collection = None

    @classmethod
    async def create(cls, db_path="data/bmo_memory.db"):
        self = cls()
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.llm = await asyncio.to_thread(LLMClient)   # construct off-loop if blocking
        self.chroma = await asyncio.to_thread(chromadb.PersistentClient, CHROMA_PATH)
        self.embedding_fu = embedding_functions.OllamaEmbeddingFunction(model_name="nomic-embed-text")
        self.collection = await asyncio.to_thread(self.chroma.get_or_create_collection, name="bmo_memories", embedding_function=self.embedding_fu)
        self.chunker = Chunker(chunk_size=200, opverlap=15)
        return self

    async def start_session(self, mood: str, user_id: int = 1) -> int:
        self.update_bmo_state(
            event="start_session",
            status="active",
            mood=mood,
            detail="User initiated chat.",
        )
        return await self.save_conversation(
            user_id, f"Session started.\nBMO's mood: {mood}"
        )

    async def save_conversation(
        self, user_id: int, message: str, summary=None
    ) -> int | None:
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

    async def update_user_relation(
        self, user_id: int, new_fact: str, bmo_perception_json: str
    ):
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
                    return cursor.fetchall()
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

            # high-importance memories (random sample so BMO feels varied)
            cursor = await connection.execute(
                "SELECT content FROM memories WHERE importance >= 7 ORDER BY RANDOM() LIMIT 2"
            )
            bmo_thoughts["core_memories"] = [row[0] for row in await cursor.fetchall()]

            # most recent memories
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
        try:
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
                    print(
                        "[Warning] 'Acquaintance' role not found — did seed_database() run?"
                    )

                initial_perception = json.dumps(
                    {
                        "connection_to_owner": "unknown",
                        "bmo_feelings_toward_them": "neutral, just met",
                        "trust_level": 3,
                        "inside_jokes": [],
                    }
                )

                cursor = await connection.execute(
                    "INSERT INTO users (name, facts, role_id, bmo_perception) VALUES (?,?,?,?)",
                    (
                        name,
                        "A new person BMO has just met.",
                        default_role_id,
                        initial_perception,
                    ),
                )
                await connection.commit()
                return cursor.lastrowid
        except json.JSONDecodeError:
            print("Something went wrong with function get_or_creat_user")

    async def consolidate_bmo(
        self, user_id: int, conversation_id: int, recent_messages: str
    ):
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
                # Strip markdown fences if the LLM includes them
                clean_response = (
                    llm_response.strip()
                    .removeprefix("```json")
                    .removeprefix("```")
                    .removesuffix("```")
                    .strip()
                )
                new_data = json.loads(clean_response)
                new_facts = new_data.get("updated_facts")
                if isinstance(new_facts, (dict, list)):
                    new_facts = json.dumps(new_facts)
                else:
                    new_facts = str(new_facts) if new_facts else "No new facts recorded"

                new_perception = json.dumps(new_data.get("updated_perception"))
                if isinstance(new_perception, (dict, list)):
                    new_perception = json.dumps(new_perception) 
                else:
                    new_perception = str(new_perception) if new_perception else {}
                summary = new_data.get("conversation_summary", "No summary provided.")
                valence = new_data.get("emotional_valence", "Neutral")
                core_memories = new_data.get("new_core_memories", [])

                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute(
                        """UPDATE users
                        SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP
                        WHERE id = ?""",
                        (new_facts, new_perception, user_id),
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
