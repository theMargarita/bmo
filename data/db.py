import sqlite3

# The 'with' statement automatically handles closing the connection when done!
with sqlite3.connect("data/bmo_memory.db") as connection:
    cursor = connection.cursor()
    print("Database created and connected successfully")

    # SQL commands with table descriptions
    create_table_query = """
        -- Table: memories
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,       
            source TEXT,  
            chroma_id TEXT UNIQUE,             
            importance INTEGER DEFAULT 2, 
            -- vision_data BLOB,           
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        );

        -- Table: conversations
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, 
            message TEXT NOT NULL,   
            summary TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        --for bmo and me
        -- Table: messages
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL, 
            role_id INTEGER NOT NULL,                
            content TEXT NOT NULL,            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        );

        --for bmo
        -- Table: roles
        -- Stores information about roles (e.g., owner, users, guests, acquaintances etc), including permissions or descriptions.
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name JSON NOT NULL,            
            role_description JSON,     
            relationship_notes JSON,             
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        );

        -- for bmo
        -- Table: users
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              
            facts TEXT,                      
            role_id INTEGER,
            bmo_perception JSON,  -- BMO's internal thoughts and relationship mapping
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id)  
        );
        
        -- this is mostly for me
        -- Table: bmo_state
        CREATE TABLE IF NOT EXISTS bmo_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT NOT NULL, --what happend: start_session, error, crach etc
            status TEXT NOT NULL, --how bo should 'feel' in the terms it can 'feel' 
            mood TEXT, --good to know mood
            detail TEXT, --extra info if crash etc
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    # Execute the SQL commands to create the tables
    cursor.executescript(create_table_query)

    # Commit the transaction
    connection.commit()
    print("Tables created successfully")
    print("Database setup complete.")
