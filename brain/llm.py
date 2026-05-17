import ollama  # type: ignore
from config import MODEL, OLLAMA_URL


class LLMClient:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_URL)
        self.model = MODEL

    def chat(self, messages: list[dict]) -> str:
        """
        Send a list of messages to the model and return the response text.

        messages format:
        [
            {"role": "system", "content": "..."},
            {"role": "user",   "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
        """
        try:
            response = self.client.chat(model=self.model, messages=messages)
            return response["message"]["content"]

        except Exception as e:
            print(f"Error during chat: {e}")
            return "Sorry, I'm having trouble responding right now."

    def is_available(self) -> bool:
        try:
            self.client.list()
            # self.client.get_model(self.model)
            return True
        except Exception as e:
            print(f"LLM model not available: {e}")
            return False
