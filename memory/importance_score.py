import re

HIGH_IMPORTANCE = [
        "always", "never", "hate", "love", "fear", "dream", "goal",
    "important", "remember", "secret", "family", "friend", "trauma",
    "birthday", "favourite", "favorite", "promise", "believe", "regret",
]

MEDIUM_IMPORTANCE = [
    "sometimes", "usually", "prefer", "like", "dislike", "often",
    "work", "study", "hobby", "pet", "live", "job",
]


def calculate_importance(text: str) -> int:
    text_lower = text.lower()
    score = 3  

    for word in HIGH_IMPORTANCE:
        if re.search(rf"\b{word}\b", text_lower):
            score += 2

    if '!' in text or text.isupper():
        score += 1

    for word in MEDIUM_IMPORTANCE:
        if re.search(rf"\b{word}\b", text_lower):
            score += 1
        

    # Length bonus — longer memories tend to be more detailed
    word_count = len(text.split())
    if word_count > 50:
        score += 1

    return min(score, 10)

