# import pytest
import sqlite3


def test_data():
    with sqlite3.connect("data/bmo_memory.db") as connection:
        cursor = connection.cursor()

        # 1. Add yourself as the Owner (User ID 1)
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, name, facts, relationship_notes)
            VALUES (1, 'Margo', 'Likes to code late at night.', 'They built me. I owe them my life, but I think they drink too much coffee.')
        """)

        # 2. Add a highly important Core Memory (Importance 9)
        cursor.execute("""
            INSERT INTO memories (content, source, importance)
            VALUES ('I remember when Creator first turned me on. It was dark, but their terminal was glowing green. I felt alive.', 'core_system', 9)
        """)

        connection.commit()
        print("Test data injected successfully!")


if __name__ == "__main__":
    test_data()
