import json
import os
import sqlite3
import uuid
from brain.llm import LLMClient
import chromadb
from chromadb.utils import embedding_functions

# small offline emmbedding model
# EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class BMOsMemory:
    def __init__(self, db_path="data/bmo_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.llm = LLMClient()

        ##chroma setup
        self.chroma = chromadb.PersistentClient(path="data/chroma")

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

    def seed_database(self, owner_name="Creator"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # checks if roles exists, if not - hardcode them
            cursor.execute("SELECT COUNT(*) FROM roles")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO roles (name, role_description, relationship_notes) VALUES (?, ?, ?)",
                    (
                        'Creator', 
                        'The creator of BMO', 
                        "Sees BMO as her baby, because it is her (Margo's) first ever made machine."
                    )
                )
                
                cursor.execute(
                    "INSERT INTO roles (name, role_description, relationship_notes) VALUES (?, ?, ?)",
                    (
                        'Acquaintance', 
                        'A familiar face, or a casual contact', 
                        'Highlighting someone you know casually, but not on an intimate level'
                    )
                )
                
                cursor.execute(
                    "INSERT INTO roles (name, role_description, relationship_notes) VALUES (?, ?, ?)",
                    (
                        'Friend', 
                        'Be there for each other', 
                        'Capturing personality and shared history'
                    )
                )
                
                cursor.execute(
                    "INSERT INTO roles (name, role_description, relationship_notes) VALUES (?, ?, ?)",
                    (
                        'Partner-in-crime', 
                        'Serves as the twin', 
                        'Chaos and fun'
                    )
                )

                conn.commit()
                print("[Database] Default roles injected")
            # check if default user exists, if not - create user ID
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    INSERT INTO users (name, facts, role_id, bmo_perception) 
                               VALUES (?, 'Is the creator and owner of BMO.', 1, '{}')
                    """,
                    (owner_name,),
                )
                conn.commit()
                print(f"[Database] Default user '{owner_name} created as User ID 1.")

    # Count memories
    # def count(self) -> int:
    #     try:
    #         return self.collection.count()
    #     except sqlite3.Error as e:
    #         print(f"Error occurred while counting memories: {e}")
    #         return 0

    # ---start session-----
    #removed equal to one in user_id - lets tests what will happend 
    def start_session(self, mood: str, user_id: int = 1) -> int:
        self.update_bmo_state(event="start_session", status="active", mood=mood, detail="User initiated chat.")
        return self.save_conversations(
            user_id, f"Session started.\n BMO's mood: {mood}"
        )

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

    # ------message table functions--------
    def save_chat_message(self, conversation_id, role_id, content):
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO messages (conversation_id, role_id, content) VALUES (?,?,?)",
                    (conversation_id, role_id, content),
                )
                connection.commit()
        except sqlite3.Error as e:
            print(f"Could not save save latest chat message: {e}")
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

    # Saving 'core' memories
    def save(self, content: str, source: str, importance: int = 0, tags: list = None):
        try:
            chroma_id = str(uuid.uuid4())
            if tags:
                source = f"{source} | tags: {','.join(tags)}"

            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO memories (content, source, importance, chroma_id) VALUES (?,?,?,?)",
                    (content, source, importance, chroma_id),
                )
                connection.commit()

                # save vectors to chromadb
                self.collection.add(
                    documents=[content],
                    ids=[chroma_id],
                    metadatas=[{"source": source, "importance": importance}],
                )
        except sqlite3.Error as e:
            print(f"Error saving memory: {e}")

    # -----------user table functions-----------
    def update_user_relation(self, user_id: int, new_fact: str, bmo_perception_json):
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT facts FROM users WHERE id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_facts = f"{row[0]} | {new_fact}" if row[0] else new_fact
                    cursor.execute(
                        """
                        UPDATE users 
                        SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP 
                        WHERE id = ?
                        """,
                        (
                            updated_facts,
                            bmo_perception_json,
                            user_id,
                        ),
                    )
                    connection.commit()
        except sqlite3.Error as e:
            print(f"Could not update user: {e}")

    # --------bmo state functions------------
    def get_bmo_state(self):
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT event,status, mood, detail FROM bmo_state ORDER BY last_updated DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "event": row[0],
                        "status": row[1],
                        "mood": row[2],
                        "detail": row[3],
                    }
        except sqlite3.Error as e:
            print(f"Could not fetch BMOs status: {e}")
            return None

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
        except sqlite3.Error as e:
            print(f"Could not update BMO's status: {e}")

    def get_conversation_history(self, conversation_id):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT role_id, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            )
            return cursor.fetchall()

    # now this will be used for chromadb
    def search_context(self, query: str, n: int = 3) -> list[str]:
        if self.collection.count() == 0:
            return []

        try:
            results = self.collection.query(
                query_texts=[query], n_results=min(n, self.collection.count())
            )

            if (
                results
                and results.get("documents")
                and len(results["documents"][0]) > 0
            ):
                return results["documents"][0]
        except Exception as e:
            print(f"[BMO memory] Search error: {e}")
            return []

    # -----------fetching BMO's thoughts for response generation------
    def fetch_bmos_thoughts(self, user_id):
        bmo_thoughts = {
            "user_context": "",
            "core_memories": [],
            "recent_events": [],
        }

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            # Swapped relationship_notes for bmo_perception to align with your schema update
            cursor.execute(
                "SELECT name, facts, bmo_perception FROM users WHERE id = ?",
                (user_id,),
            )
            user_data = cursor.fetchone()

            if user_data:
                bmo_thoughts["user_context"] = (
                    f"You are talking to {user_data[0]}. "
                    f"Facts you know about them: {user_data[1]}. "
                    f"Your private thoughts/perception about them: {user_data[2]}."
                )

            cursor.execute(
                "SELECT content FROM memories WHERE importance >= 7 ORDER BY RANDOM() LIMIT 2"
            )
            bmo_thoughts["core_memories"] = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT content FROM memories ORDER BY created_at DESC LIMIT 3"
            )
            bmo_thoughts["recent_events"] = [row[0] for row in cursor.fetchall()]
        return bmo_thoughts

    def consolidate_bmo(self, user_id, conversation_id, recent_messages):
        with sqlite3.connect(self.db_path) as c:
            cursor = c.cursor()

            cursor.execute(
                "SELECT facts, bmo_perception FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()

            if not row:
                print(f"User with ID {user_id} not found.Can not consolidate memory.")
                return

            current_facts = row[0] or "No facts recorded yet."
            current_perception = json.loads(row[1]) if row[1] else {}

            analysis_prompt = f"""
            You are the subconscious memory-processing core of BMO. 
            Review the conversation and update your records.

            Current Memory Facts: {current_facts}
            Current BMO Perception: {json.dumps(current_perception)}

            Recent Conversation:
            {recent_messages}

            Your task is to return a raw JSON object with these fields:
                1. "updated_facts": Summary of concrete facts learned.
                2. "updated_perception": JSON with "connection_to_owner", "bmo_feelings_toward_them", "trust_level" (1-10), and "inside_jokes" (array).
                3. "conversation_summary": A 1-2 sentence summary.
                4. "emotional_valence": Overarching emotional tone of this chat: Choose exactly one ("Positive", "Negative", "Neutral", "Anxious", "Curious").
                5. "new_core_memories": Array of strings extracting highly distinct concepts or preferences.

            Respond ONLY with the raw JSON object. Do not wrap in markdown fences.
            """

            # Properly using the LLMClient instance and sending formatted messages
            messages = [{"role": "user", "content": analysis_prompt}]
            llm_response = self.llm.chat(messages)

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
                new_perception_str = json.dumps(new_data.get("updated_perception"))
                summary = new_data.get("conversation_summary", "No summary provided.")
                valence = new_data.get("emotional_valence", "Neutral")
                core_memories = new_data.get("new_core_memories", [])

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE users 
                        SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP 
                        WHERE id = ?
                        """,
                        (
                            new_facts,
                            new_perception_str,
                            user_id,
                        ),
                    )
                    conn.commit()
                    #ending session - start processing new memory
                    self.end_session(conversation_id, summary)

                    self.update_bmo_state(
                        event="end_session_consolidation",
                        status="resting",
                        mood=valence,
                        detail=f"Proccessed session summary: {summary}"
                    )

                    for memory_text in core_memories:
                        # got to give high importance so bmo remebers them
                        self.save(
                            content=memory_text,
                            source="Chat Consolidation",
                            importance=8,
                        )
                print("BMO safely stored new memories!")
            except json.JSONDecodeError:
                print("Oops! BMO's thoughts were too chaotic to parse this time..")

    def get_role_id(self, role_name: str) -> int | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            row = cursor.fetchone()
            return row[0] if row else None

#to avoid duplicates
    def get_or_create_user(self, name: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return row[0]

            guest_role_id = self.get_role_id("Guest")
            initial_perception = json.dumps(
                {
                    "connection_to_owner": "unknown",
                    "bmo_feelings_toward_them": "neutral, just met",
                    "trust_level": 3,
                    "inside_jokes": [],
                }
            )
            cursor.execute(
                """INSERT INTO users (name, facts, role_id, bmo_perception) 
                VALUES (?, ?, ?, ?)""",
                (
                    name,
                    "A new person BMO has just met.",
                    guest_role_id,
                    initial_perception,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    # def create_user(self, name, facts="", bmo_perception="{}"):
    #     with sqlite3.connect(self.db_path) as connection:
    #         cursor = connection.cursor()
    #         cursor.execute(
    #             "INSERT INTO users (name, facts, bmo_perception) VALUES (?,?,?)",
    #             (name, facts, bmo_perception),
    #         )
    #         connection.commit()
