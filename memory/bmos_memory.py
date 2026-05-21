import json
import os
import sqlite3

from brain.llm import LLMClient


class BMOsMemory:
    def __init__(self, db_path="data/bmo_memory.db"):
        self.db_path = db_path
        # Ensure directory exists before we try to access it
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Instantiate the LLM client for consolidation
        self.llm = LLMClient()

    def seed_database(self, owner_name="Creator"):
        with sqlite3.connect(self.db_path)as conn:
            cursor = conn.cursor()
            #checks if roles exists, if not - hardcode them
            cursor.execute("SELECT COUNT(*) FROM roles")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO roles (name, role_description) VALUES ('Owner', '{\"access\": \"absolute\"}')")
                cursor.execute("INSERT INTO roles (name, role_description) VALUES ('Guest', '{\"access\": \"limited\"}')")

                conn.commit()
                print("[Databse] Default roles injected")
            #check if default user exists, if not - create user ID
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO users (name, facts, role_id, bmo_perception) 
                               VALUES (?, 'Is the creator and owner of BMO.', 1, '{}')
                    """, (owner_name,))
                conn.commit()
                print(f"[Database] Default user '{owner_name} created as User ID 1.")

    # Count memories
    def count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM memories")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error occurred while counting memories: {e}")
            return 0
            
    # ---start session-----
    def start_session(self, mood: str, user_id: int = 1) -> int:
        # Corrected method name and slash direction
        return self.save_conversations(user_id, f"Session started.\n BMO's mood: {mood}")
    
    # -------conversation table functions------
    def save_conversations(self, user_id, message, summary=None):
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO conversations (user_id, message, summary) VALUES (?,?,?)",
                    (user_id, message, summary)
                )
                connection.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error saving conversations: {e}")
            return None
        
    # ------message table functions--------
    def save_chat_message(self, conversation_id, role, content):
        try:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO messages (conversation_id, role_id, content) VALUES (?,?,?)",
                    (conversation_id, role, content),
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
                        (summary, conversation_id,)
                    )
                    connection.commit()
        except sqlite3.Error as e:
            print(f"Could not create or save a summary: {e}")
            return None
        
    
    # Saving 'core' memories
    def save(self, content: str, source: str, importance: int = 0, tags: list = None):
        try:
            if tags:
                source = f"{source} | tags: {','.join(tags)}"
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO memories (content, source, importance) VALUES (?,?,?)",
                    (content, source, importance)
                )
                connection.commit()
        except sqlite3.Error as e:
            print(f"Error saving memory: {e}")

    # -----------user table functions-----------
    def update_user_relation(self, user_id, new_fact, bmo_perception_json):
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
                        (updated_facts, bmo_perception_json, user_id,),
                    )
                    connection.commit()
        except sqlite3.Error as e:
            print(f"Could not update user: {e}")

    # --------bmo state functions------------
    def get_bmo_state(self):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT description, status FROM bmo_state ORDER BY last_updated DESC LIMIT 1"
            )
            return cursor.fetchone()

    def get_conversation_history(self, conversation_id):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT role_id, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            )
            return cursor.fetchall()

    def get_recent(self, limit: int = 5) -> list:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT importance, content FROM memories ORDER BY created_at DESC LIMIT ?", 
                (limit,)
            )
            return [{"importance": row[0], "content": row[1]} for row in cursor.fetchall()]
        
    # Searches memory table for keywords longer than 4 letters
    def search_context(self, query: str) -> list:
        words = [w for w in query.lower().split() if len(w) > 4]
        result = []
        if not words: 
            return result

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            for w in words: 
                cursor.execute(
                    "SELECT content FROM memories WHERE content LIKE ? LIMIT 1", 
                    (f"%{w}%",)
                )
                row = cursor.fetchone()
                if row and row[0] not in result:
                    result.append(row[0])
        return result

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

            # Fetch core memories (2 random high importance entries)
            cursor.execute(
                "SELECT content FROM memories WHERE importance >= 7 ORDER BY RANDOM() LIMIT 2"
            )
            bmo_thoughts["core_memories"] = [row[0] for row in cursor.fetchall()]

            # Fetch recent events (3 most recent entries)
            cursor.execute(
                "SELECT content FROM memories ORDER BY created_at DESC LIMIT 3"
            )
            bmo_thoughts["recent_events"] = [row[0] for row in cursor.fetchall()]

        return bmo_thoughts
    
    def create_user(self, name, facts="", bmo_perception="{}"):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            # Fixed column syntax and commas
            cursor.execute(
                "INSERT INTO users (name, facts, bmo_perception) VALUES (?,?,?)", 
                (name, facts, bmo_perception)
            )
            connection.commit()

    def consolidate_bmo(self, user_id, conversation_id, recent_messages):
        with sqlite3.connect(self.db_path) as c:
            cursor = c.cursor()
            
            cursor.execute("SELECT facts, bmo_perception FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                print(f"User with ID {user_id} not found.Can not consolidate memory.")
                return

            current_facts = row[0] or "No facts recorded yet."
            # Fixed conditional dict/string error inside json.loads
            current_perception = json.loads(row[1]) if row[1] else {}

            analysis_prompt = f"""
            You are the subconscious memory-processing core of BMO. 
            Review the recent conversation messages and update BMO's inner memory and perception of the user.

            Current Memory Facts: {current_facts}
            Current BMO Perception: {json.dumps(current_perception)}

            Recent Conversation:
            {recent_messages}

            Your task is to return a JSON object with two fields:
                1. "updated_facts": Text summary of absolute facts learned about the user.
                2. "updated_perception": JSON object with "connection_to_owner", "bmo_feelings_toward_them", "trust_level" (1-10), and "inside_jokes" (array).
                3. "conversation_summary": A 1 to 2 sentence summary of this entire conversation.
                4. "new_core_memories": An array of strings. Extract 1 or 2 highly important distinct concepts, events, or preferences mentioned. If nothing important happened, return an empty array [].

            Respond ONLY with the raw JSON object. Do not include markdown formatting or backticks.
            """
            
            # Properly using the LLMClient instance and sending formatted messages
            messages = [{"role": "user", "content": analysis_prompt}]
            llm_response = self.llm.chat(messages)

            try: 
                new_data = json.loads(llm_response)
                #
                new_facts = new_data.get("updated_facts")
                new_perception_str = json.dumps(new_data.get("updated_perception"))
                summary = new_data.get("conversation_summary", "No summary provided.")
                core_memories = new_data.get("new_core_memories", [])

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    # Added missing commas in UPDATE query and normalized to CURRENT_TIMESTAMP
                    cursor.execute("""
                        UPDATE users 
                        SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP 
                        WHERE id = ?
                        """, (new_facts, new_perception_str, user_id,))
                    conn.commit()

                    self.end_session(conversation_id, summary)

                    for memory_text in core_memories:
                        #got to give high importance so bmo remebers them
                        self.save(content=memory_text, source="Chat Consolidation", importance=8)
                
                print("BMO safely stored new memories!")
            except json.JSONDecodeError:
                print("Oops! BMO's thoughts were too chaotic to parse this time..")

    def update_bmo_state(self, description, status):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO bmo_state (description, status) VALUES (?,?)",
                               (description, status,))
                
                conn.commit()
        except sqlite3.Error as e:
            print(f"Could not update BMO's status: {e}")