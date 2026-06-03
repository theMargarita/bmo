import os

from sentence_transformers import CrossEncoder, SentenceTransformer
from config import EMBEDDING_MODEL, RERANKER_MODEL

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL, cache_folder="./models")
        self.reranker = CrossEncoder(RERANKER_MODEL, cache_folder="./models")


    def emded(self, text: str) -> list[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()
    
    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embed_batch(input)