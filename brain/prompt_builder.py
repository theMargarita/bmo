from brain.personality import get_system_prompt

class PromptBuilder:
    def __init__(self, mood: str = "curious"):
        self.mood = mood

    def build(self, history: list[dict], memories: list[str] = []) -> list[str]:
        """
        Build the full messages list to send to the LLM.
 
        Structure:
        1. System prompt (personality + mood)
        2. Injected long-term memories if any (added as a system message)
        3. Current session conversation history
        """
        messages = [] #empty list to hold the final messages
        messages.append({
            "role": "system", 
            "content": get_system_prompt(self.mood)
            }) #add the system prompt to the messages list
        if memories:
            memory_block = "Relevant things you remember: n" + "\n".join(f"- {m}" for m in memories)
            messages.append({
                "role": "system",
                "content": memory_block
            })

        #else
        messages.extend(history[-20:]) #add the last 20 messages from the history to the messages list
        return messages
    
    def set_mood(self, mood:str):
        self.mood = mood