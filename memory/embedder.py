from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL) #loads from cache

    def emdeb(self, text: str) -> list[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()
    