from brain.personality import get_system_prompt
from memory.bmo_memory_async import BMOMemoryAsync
from memory.identity import Identity
# from memory.bmos_memory import BMOsMemory
from config import MAX_HISTORY



class PromptBuilder:
    def __init__(self, identity_manager: Identity, memory_system: BMOMemoryAsync):
        self.identity_manager = identity_manager
        self.memory_system = memory_system

    def build(
        self, history, memories, game_context: str = None
    ) -> list[dict]:
        messages = []
        # core system prompt with personality and mood
        messages.append({"role": "system", "content": get_system_prompt()})

        if game_context:
            messages.append({"role": "system", "content": game_context})

        bmo_context = self.identity_manager.get_bmo_context()
        if bmo_context:
            messages.append(
                {"role": "system", "content": f"[Your current state]\n{bmo_context}"}
            )

        owner_context = self.identity_manager.get_owner_context()
        if owner_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"[Your owner's current state]\n{owner_context}",
                }
            )

        if memories:
            memory_block = "Relevant things you remember: \n" + "\n".join(
                f"- {m}" for m in memories
            )
            # system += f"\n\nRelevant memories (use these to inform your response):\n{memory_block}"
            messages.append({"role": "system", "content": memory_block})

        # else
        messages.extend(history[-MAX_HISTORY:])
        return messages

    def set_mood(self, mood: str):
        self.identity_manager.set_mood(mood)

    # -------fetching BMO's internal state from the database------
    async def build_with_personalities(
        self, user_input, user_id, history, game_context: str = None
    ):
        thoughts = await self.memory_system.fetch_bmos_thoughts(user_id)
        instructions = f"""
            Your name is BMO and you are inspired by BMO from Adventure Time. 
            Respond naturally to the user based on your current internal state and the context of the conversation.
            {thoughts.get("user_context", "")}

            [YOUR INTERNAL CONTEXT]
            {thoughts.get("user_context", "You are talking to a new friend.")}

            [CORE MEMORIES]
            -{thoughts["core_memories"][0] if len(thoughts["core_memories"]) > 0 else "Nothing special"}
            -{thoughts["core_memories"][1] if len(thoughts["core_memories"]) > 1 else "Nothing special"}
            
            [RECENT EVENTS]
            -{thoughts["recent_events"][0] if len(thoughts["recent_events"]) > 0 else "No recent events"}
            -{thoughts["recent_events"][1] if len(thoughts["recent_events"]) > 1 else "No recent events"}

            [CURRENT MOOD]
            -{self.identity_manager.get_mood()}
"""
        if game_context:
            instructions += f"\n\n[URGENT GAME MODE ACTIVE]\n{game_context}\n"

        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_input},
        ]
        messages.extend(history[-MAX_HISTORY:])
        messages.append({"role": "user", "content": user_input})
        return messages
