import sqlite3

with sqlite3.connect('bmo_memory.db') as connection:
#create a cursor object to interact with the database
#crusor is used to execute SQL commands and queries on the database
    cursor = connection.cursor()
    print("Database created and connected successfully")

    #SQL commands
    create_table_query = '''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT,
            importance INTEGER DEFAULT 0,
            # vision_data BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        create TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            facts TEXT,
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relationship_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bmo_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            status TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS owner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            preferred_language TEXT,
            interests JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
'''

    #execute the SQL commands to create the tables
    cursor.executescript(create_table_query)
    print("Tables created successfully")

    cursor.commit()
    print ("Database setup complete.")

    
#need to close the finished database connection
# def close_connection():
#     connection.close()