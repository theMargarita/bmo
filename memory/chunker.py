import re

class Chunker:
    def  __init__(self, chunk_size, int = 80, overlap: int = 15):
        # chunk_size: words per chunk
        # overlap: words shared between consecutive chunks
        # overlap prevents losing meaning at chunk boundaries
        self.chunk_size = chunk_size
        self.overlap = max(0, overlap)

    def chunk(self, text: str) -> list[str]:
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]
        chunks = []
        step = self.chunk_size - self.overlap if 0 < self.overlap < self.chunk_size else self.chunk_size
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + self.chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

        #longer content should be split into chuncks before embedding so retrieval is more precis
    def chunk_text_with_overlap(self, text: str, chunck_size: int = 200, overlap: int = 15) -> list[str]:
        #slit punctuation (roughtly sentence boundaries)
        sentences = re.split(r'(?<=[.!?]) +', text) #re -> regex?
        chunks = []
        current_chunk = []
        current_length = 0

        for sntc in sentences:
            words = sntc.split()
            # If adding this sentence exceeds our chunk size, save the current chunk
            if current_length + len(words) > chunck_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                #keep the last few words (overlap) to maintain contect bridging
                current_chunk = current_chunk[-overlap:]
                current_length = sum(len(w.split()) for w in current_chunk)

            current_chunk.append(sntc)
            current_length += len(words)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
        # words = text.split()
        # return [
        #     " ".join(words[i:i + chunck_size])
        #     for i in range(0, len(words), chunck_size)
        # ]