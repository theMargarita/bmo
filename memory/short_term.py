from config import MAX_HISTORY

#noticed that this one does not work as well as I want to. 
class ShortTermMemory:
    def __init__(self):
        self._messages: list[dict] = []
        self.game_active: bool = False
        self.game_system_prompt: str = "" #Special instructions for the LLM during the game


    def add(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        while (
            len(self._messages) > MAX_HISTORY
        ):  
            self._messages.pop(0)  

    def get_history(self) -> list[dict]:
        return self._messages.copy()  # return a copy of the short term memory messages

    def clear(self):
        self._messages = []
        self.end_game()

    def is_empty(self) -> bool:
        return len(self._messages) == 0  # return True if the short term memory is empty

#game management methods
    def start_game(self, special_instructions: str):
        self.game_active = True
        self.game_system_prompt = special_instructions

    def end_game(self):
        self.game_active = False
        self.game_system_prompt = ""