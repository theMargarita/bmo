import aiosqlite

from brain.llm import LLMClient
from config import DB_PATH


class DailySummerizer:
    def __init__(self, llm_client: LLMClient | None = None, db_path: str = DB_PATH):
        self.llm = LLMClient() or llm_client
        self.db_path = db_path

    async def summerize_and_save(self, memory_system, user_id: int = 1) -> str | None:
        """
        Fetch today's conversations, summarize them, and save the summary
        as a memory. Call this when a session ends (for now).
        Returns the summary text, or None if there was nothing to summarize.
        """
        conversations = await self._get_todays_conversations(user_id) #function that will be created soon - to get todays convo

        if not conversations: 
            print("[DailySummerizer] No conversations to summerize today")
            return None

        convo_text = "\n\n".join(
            f"User: {conv['message']}" for conv in conversations
        )

        summery = await self._summerize(convo_text) #message prompt for llm 
        if not summery:
            return None

        self._save_summery(memory_system, summery)
        return summery 

    async def _get_today_conversations(self, user_id: int) -> list[dict]:
        try: 
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT id, message, created_at
                    FROM conversations
                    WHERE user_id = ? AND created_at > datetime('now', '-1 day')
                    ORDER BY created_at ASC
                    """,
                    (user_id),
                )
                rows = await cursor.fetchall()
                return [{"id": r[0], "message": r[1], "created_at": r[2]} for r in rows]
        except aiosqlite.Error as e:
            print(f"[DailySummerizer] Error fetching conversations: {e}")
            return []