import asyncio

import aiosqlite

from brain.llm import LLMClient
from config import DB_PATH

# from memory.bmos_memory import BMOsMemory
from memory.importance_score import calculate_importance


class DailySummarizer:
    def __init__(self, llm_client: LLMClient | None = None, db_path: str = DB_PATH):
        self.llm = llm_client or LLMClient()
        self.db_path = db_path

    async def summerize_and_save(self, memory_system, user_id: int = 1) -> str | None:
        """
        Fetch today's conversations, summarize them, and save the summary
        as a memory. Call this when a session ends (for now).
        Returns the summary text, or None if there was nothing to summarize.
        """
        conversations = await self._get_todays_conversations(
            user_id
        )  # function that will be created soon - to get todays convo

        if not conversations:
            print("[DailySummarizer] No conversations to summerize today")
            return None

        conversation_text = "\n\n".join(
            f"User: {conv['message']}" for conv in conversations
        )

        summary = await self._summerize(conversation_text)  # message prompt for llm
        if not summary:
            return None

        self._save_summary(memory_system, summary)
        return summary

    # private function
    async def _get_todays_conversations(self, user_id: int) -> list[dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, message, created_at
                    FROM conversations
                    WHERE user_id = ? AND created_at > datetime('now', '-1 day')
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                )
                rows = await cursor.fetchall()
                return [{"id": r[0], "message": r[1], "created_at": r[2]} for r in rows]
        except aiosqlite.Error as e:
            print(f"[DailySummarizer] Error fetching conversations: {e}")
            return []

    # private function
    async def _summerize(self, conversation_text: str) -> str | None:
        messages = [
            {
                "role": "system",
                "content": (
                    "You summarize a day's conversations between BMO and its "
                    "companion in 2-3 sentences. Focus on what the user cared "
                    "about, decisions made, emotional state, or recurring topics."
                ),
            },
            {"role": "user", "content": conversation_text},
        ]
        try:
            summary = await asyncio.to_thread(self.llm.chat, messages)
            return summary.strip() if summary else None
        except Exception as e:  # noqa: BLE001
            print(f"[DailySummarizer] Error during summarization: {e}")
            return None

    # private function
    def _save_summary(self, memory_system, summary: str):
        importance = max(calculate_importance(summary), 6)  # 6 as mediocer importance
        # memory_system = BMOsMemory() #added this for refenrence to bmomemory save
        memory_system.save(
            content=f"[Daily Summary] {summary}",
            source="daily_summary",
            importance=importance,
        )

        print(f"[DailySummarizer] Saved (importance={importance}): {summary[:100]}...")
