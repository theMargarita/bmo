from config import MAX_HISTORY

class ShortTermMemory:
    def __init__(self):
        #list of messges in the short term memory, each message is a dict with keys "role" and "content"
        self.messages: list[dict]=[] 

    def add(self, role: str, content: str):
       #add a message to session history, keeping only the last MAX_HISTORY messages
       self._messages.append({"role": role, "content": content}) 

       while len(self._messages) > MAX_HISTORY: #if the number of messages in the short term memory exceeds MAX_HISTORY
            self._messages.pop(0) #remove the oldest message 

    def get_history(self) -> list[dict]:
        #return the current session history as a list of messages
        return self._messages.copy() #return a copy of the short term memory messages
    
    def clear(self):
        #clear the short term memory
        self._messages = []
        
    def is_empty(self) -> bool:
        #check if the short term memory is empty
        return len(self._messages) == 0 #return True if the short term memory is empty