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
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO conversations (user_id, message, summary) VALUES (?,?,?)",
                (user_id, message, summary)
            )
            connection.commit()
            return cursor.lastrowid
        
    # ------message table functions--------
    def save_chat_message(self, conversation_id, role, content):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?,?,?)",
                (conversation_id, role, content),
            )
            connection.commit()

    # ------end session---
    def end_session(self, conversation_id, summary=None):
        if summary:
            with sqlite3.connect(self.db_path) as connection:
                cursor = connection.cursor()
                # Wrapped arguments in a tuple
                cursor.execute(
                    "UPDATE conversations SET summary = ? WHERE id = ?",
                    (summary, conversation_id)
                )
                connection.commit()
    
    # Saving 'core' memories
    def save(self, content: str, source: str, importance: int = 0, tags: list = None):
        if tags:
            source = f"{source} | tags: {','.join(tags)}"
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO memories (content, source, importance) VALUES (?,?,?)",
                (content, source, importance)
            )
            connection.commit()

    # -----------user table functions-----------
    def update_user_relation(self, user_id, new_fact, bmo_perception_json):
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
                    (updated_facts, bmo_perception_json, user_id),
                )
                connection.commit()

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
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
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

    def consolidate_bmo(self, user_id, recent_messages):
        with sqlite3.connect(self.db_path) as c:
            cursor = c.cursor()
            # Changed .commit() to .execute() and fixed 'WHER' typo
            cursor.execute("SELECT facts, bmo_perception FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                print(f"User with ID {user_id} not found.")
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
                1. "updated_facts": A text summary of absolute facts learned. Append new ones, keep old valid ones.
                2. "updated_perception": A JSON object containing:
                    - "connection_to_owner": relationship description
                    - "bmo_feelings_toward_them": how BMO feels emotionally about them now
                    - "trust_level": an integer from 1-10
                    - "inside_jokes": an array of strings

            Respond ONLY with the raw JSON object. Do not include markdown formatting or backticks.
            """
            
            # Properly using the LLMClient instance and sending formatted messages
            messages = [{"role": "user", "content": analysis_prompt}]
            llm_response = self.llm.chat(messages)

            try: 
                new_data = json.loads(llm_response)
                new_facts = new_data.get("updated_facts")
                new_perception_str = json.dumps(new_data.get("updated_perception"))

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    # Added missing commas in UPDATE query and normalized to CURRENT_TIMESTAMP
                    cursor.execute("""
                        UPDATE users 
                        SET facts = ?, bmo_perception = ?, last_interaction = CURRENT_TIMESTAMP 
                        WHERE id = ?
                        """, (new_facts, new_perception_str, user_id))
                    conn.commit()
                
                print("BMO safely stored new memories! ✦")
            except json.JSONDecodeError:
                print("Oops! BMO's thoughts were too chaotic to parse this time..")