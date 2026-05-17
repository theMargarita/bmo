import sqlite3

with sqlite3.connect("data/bmo_memory.db") as connection:
    # Create a cursor object to interact with the database
    # Cursor is used to execute SQL commands and queries on the database
    cursor = connection.cursor()
    print("Database created and connected successfully")

    # SQL commands with table descriptions
    create_table_query = """
        -- Table: memories
        -- Stores individual memory entries with optional source and importance.
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,       
            source TEXT,                  
            importance INTEGER DEFAULT 0, 
            -- vision_data BLOB,           
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        );

        -- Table: conversations
        -- Stores conversations, each linked to a user (users.id).
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, 
            message TEXT NOT NULL,   
            summary TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        );

        -- Table: messages
        -- Stores messages within a conversation, linked to conversations(id).
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL, 
            role TEXT NOT NULL,               
            content TEXT NOT NULL,            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        -- Table: users
        -- Stores user profiles and relationship notes.
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              
            facts TEXT,                      
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            relationship_notes TEXT,        
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        );

        -- Table: bmo_state
        -- Stores the state and status of the BMO system.
        CREATE TABLE IF NOT EXISTS bmo_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,                
            status TEXT,                     
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Table: owner
        -- Stores information about the owner, including preferences and interests.
        CREATE TABLE IF NOT EXISTS owner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,            
            preferred_language TEXT,      
            interests JSON,                  
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        );
    """

    # Execute the SQL commands to create the tables
    cursor.executescript(create_table_query)
    print("Tables created successfully")

    cursor.connection.commit()
    if cursor.connection.commit() is not None:
        cursor.connection.close()  # Close the database connection

    print("Database setup complete.")
