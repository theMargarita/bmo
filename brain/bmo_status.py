import sqlite3
from enum import Enum


class BMOStatus(Enum):
    IDLE = "idle"
    LISTENING = "listening"  # microphone active
    THINKING = "thinking"  # waiting for LLM response
    SPEAKING = "speaking"  # TTS playing (speaker)
    ERROR = "error"
    STARTING = "starting"
    SHUTTING_DOWN = "shutting_down"


LOGGABLE_EVENTS = {
    "session_start",
    "session_end",
    "error",
    "crash",
    "model_loaded",
    "memory_loaded",
    "low_memory",
}


# moods
class Moods(Enum):
    MOTIVATED = "motivated"
    PRODUCTIVE = "productive"
    CURIOUS = "curious"
    SLEEPY = "sleepy"
    PLAYFUL = "playful"
    EXCITED = "excited"
    THOUGHTFUL = "thoughtful"
    CRANKY = "cranky"
    NEUTRAL = "neutral"

    possible_moods = ["happy", "cranky", "sleepy", "excited", "curious", "thoughtful"]


weekday_moods = {
    0: "motivated",  # Monday
    1: "productive",  # Tuesday
    2: "curious",  # Wednesday
    3: "thoughtful",  # Thursday
    4: "excited",  # Friday
    5: "playful",  # Saturday
    6: "sleepy",  # Sunday
}


class StatusManager:
    def __init__(self, db_path: str = "data/bmo_memory.db", mood: str = Moods.NEUTRAL):
        self._status = BMOStatus.STARTING
        self._db_path = db_path
        self._mood = mood
        # self._ensure_table()

    def get(self) -> BMOStatus:
        return self._status

    def get_label(self) -> str:
        return self._status.value

    def set_mood(self, mood: str):
        self._mood = mood

    def is_busy(self) -> bool:
        return self._status in (
            BMOStatus.LISTENING,
            BMOStatus.THINKING,
            BMOStatus.SPEAKING,
        )

    # for future when connected to a hardware and I want to get recent error
    def get_errors(self, limit: int = 10) -> list[dict]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT event, status, mood, detail, created_at
                    FROM bmo_state
                    WHERE event IN ('error', 'crash')
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []
