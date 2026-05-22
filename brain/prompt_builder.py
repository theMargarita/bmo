from brain.personality import get_system_prompt
from memory.identity import Identity
from memory.bmos_memory import BMOsMemory

"""
        Structure:
        1. System prompt (personality + mood)
        2. Injected long-term memories if any (added as a system message)
        3. Current session conversation history
        """


class PromptBuilder:
    def __init__(self, identity_manager: Identity):
        self.identity_manager = identity_manager

    def build(self, history, memories, bmo_thought) -> list[dict]:
        messages = []  # empty list to hold the final messages
        # core system prompt with personality and mood
        messages.append(
            {"role": "system", "content": get_system_prompt()}
        )  # add the system prompt to the messages list

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
            messages.append({"role": "system", "content": memory_block})

        # else
        messages.extend(
            history[-20:]
        )  # add the last 20 messages from the history to the messages list
        return messages

    def set_mood(self, mood: str):
        self.identity_manager.set_mood(mood)

    # -------fetching BMO's internal state from the database------
    def build_with_personalities(self, user_input, user_id, memory_system, history):
        memory_system = BMOsMemory()
        thoughts = memory_system.fetch_bmos_thoughts(
            user_id
        )  # fetch BMO's thoughts using the memory system
        # build the prompt with the fetched thoughts and the user input
        # {thoughts["user_context"]}
        instructions = f"""
            You are BMO, respond naturally to the user based on your current internal state and the context of the conversation.
            {thoughts["user_context"]}

            [YOUR INTERNAL CONTEXT]
            {thoughts.get("user_context", "You are talking a new friend.")}

            [CORE MEMORIES]
            -{thoughts["core_memories"][0] if len(thoughts["core_memories"]) > 0 else "Nothing special"}
            -{thoughts["core_memories"][1] if len(thoughts["core_memories"]) > 1 else "Nothing special"}
            
            [RECENT EVENTS]
            -{thoughts["recent_events"][0] if len(thoughts["recent_events"]) > 0 else "No recent events"}
            -{thoughts["recent_events"][1] if len(thoughts["recent_events"]) > 1 else "No recent events"}

            [CURRENT MOOD]
            -{self.identity_manager.get_mood()}
"""

        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_input},
        ]
        messages.extend(history)

        return messages
