import sqlite3

class BMOsMemory:
    def __inint__(self, db_path='data/bmo_memory.db'):
        self.db_path = db_path


    #------conversation table functions--------
    def save_chat_message(self, conversation_id, role, content):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('''
        INSERT INTO messages (conversation_id, role, content) VALUES (?,?,?)
        ''', (conversation_id, role, content))
            connection.commit()


    #-----------user table functions-----------
    def update_user_relation(self, user_id, new_fact, relationship_notes):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('''
        SELECT facts, relationship_notes FROM users WHERE id = ?
        ''', (user_id,))
            row = cursor.fetchone()

            if row:
                updated_facts = f"{row[0] | [new_fact]}" if row[0] else new_fact
                cursor.execute('''
            UPDATE users SET facts = ?, relationship_notes = ?, last_interaction = CURRENT_TIMESTAMP 
            WHERE id = ?
            ''', (updated_facts, relationship_notes, user_id))
                connection.commit()
            

    #--------bmo state functions------------
    def get_bmo_state(self):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('''
        SELECT description, status FROM bmo_state ORDER BY last_updated DESC LIMIT 1
            ''',)
            return cursor.fetchone() #returns the most recent BMO state as a tuple (description, status)


    #-------conversation table functions------
    def save_conversation(self, user_id, message, summary=None):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('''
        INSERT INTO conversations (user_id, message, summary) VALUES (?,?,?)
        ''', (user_id, message, summary))
            connection.commit()
            return cursor.lastrowid 
        
    def get_conversation_history(self, conversation_id, summary=None):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute('''
        SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
        ''', (conversation_id,))
            return cursor.fetchall() 
        
    