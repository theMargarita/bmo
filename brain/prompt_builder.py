from brain.personality import get_system_prompt
from memory.identity import Identity

class PromptBuilder:
    def __init__(self, identity_manager: Identity):
        self.identity_manager = identity_manager

    def build(self, history: list[dict], memories: list[str] = []) -> list[dict]:
        """
        Build the full messages list to send to the LLM.
 
        Structure:
        1. System prompt (personality + mood)
        2. Injected long-term memories if any (added as a system message)
        3. Current session conversation history
        """
        messages = [] #empty list to hold the final messages
        #core system prompt with personality and mood
        messages.append({
            "role": "system", 
            "content": get_system_prompt()
            }) #add the system prompt to the messages list
        
        bmo_context = self.identity_manager.get_bmo_context()
        if bmo_context:
            messages.append({
                "role": "system",
                "content": f"[Your current state]\n{bmo_context}"
            })

        owner_context = self.identity_manager.get_owner_context()
        if owner_context:
            messages.append({
                "role": "system",
                "content": f"[Your owner's current state]\n{owner_context}"
            })

        if memories:
            memory_block = "Relevant things you remember: \n" + "\n".join(f"- {m}" for m in memories)
            messages.append({
                "role": "system",
                "content": memory_block
            })

        #else
        messages.extend(history[-20:]) #add the last 20 messages from the history to the messages list
        return messages
    
    def set_mood(self, mood:str):
        self.identity_manager.set_mood(mood)