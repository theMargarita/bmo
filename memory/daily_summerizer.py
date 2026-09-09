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

        summery = await self._summerize(convo_text)
        if not summery:
            return None

        self._save_summery(memory_system, summery)
        return summery 