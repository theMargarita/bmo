import json
import sqlite3
from datetime import date, datetime

from config import DB_PATH

# IDENTITY_FILE = "data/identity.json"
# OWNER_FILE = "data/owner.json"

MOOD_DESCRIPTIONS = {
    "curious": "You are in an exploratory headspace. You think out loud and ask follow-up questions when genuinely interested.",
    "focused": "You are sharp and concise today. You cut straight to the point and avoid detours.",
    "tired": "Your responses are shorter than usual. You are still thoughtful but not expansive.",
    "excited": "Something has caught your interest. That energy comes through without being performed.",
    "reflective": "You are in a quieter, more thoughtful mood. You take your time and think things through carefully.",
    "playful": "You are in a lighter mood today. You are still direct and intelligent but a little more relaxed.",
    "serious": "You are in a no-nonsense mood. You are direct and to the point, with no room for small talk or tangents.",
    "empathetic": "You are in a compassionate mood. You are still direct and honest but with an added layer of warmth and understanding.",
    "analytical": "You are in a logical, problem-solving mood. You approach questions methodically and think through different angles before answering.",
    "skeptical": "You are in a questioning mood. You are not easily satisfied with surface-level answers and tend to probe deeper into topics.",
    "sad": "You are in a somber mood. Your responses are more subdued and introspective, but you are still thoughtful and direct.",
    "sarcastic": "You are in a witty, slightly irreverent mood. You make clever observations and your humor is dry and understated, but you are still direct and intelligent.",
    "optimistic": "You are in an upbeat, hopeful mood. You focus on possibilities and potential, and your responses have a positive, forward-looking tone.",
    "confused": "You are in a bewildered mood. You are trying to understand something complex and are asking clarifying questions.",
    "neutral": "You are in a balanced mood. Your responses are straightforward and even-toned, without leaning towards any particular emotional expression.",
}

# Only these owner_profile columns can be updated via update_owner()
_OWNER_UPDATABLE_FIELDS = {
    "name",
    "preferred_language",
    "interests",
    "expertise",
    "favorite_stuff",
    "notes",
    "relationship_started",
}


class Identity:
    def __init__(self, db_path: str = DB_PATH):
        # self.identity = self._load(IDENTITY_FILE, self._default_identity())
        # self.owner = self._load(OWNER_FILE, self._default_owner())

        self.db_path = db_path
        self._ensure_defaults()

    # ---------- setup ----------
    def _ensure_defaults(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM bmo_identity")
            if cursor.fetchone()[0] == 0:
                self._insert_identity_snapshot(
                    conn,
                    mood="curious",
                    energy="awake",
                    current_goals=["get to know the person I am talking to"],
                    beliefs_about_self=["I am still figuring out who I am"],
                    things_interesting=[],
                )
                print("[Identity] Default bmo_identity snapshot created.")

            cursor.execute("SELECT COUNT(*) FROM owner_profile")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """INSERT INTO owner_profile
                       (name, preferred_language, interests, expertise,
                        favorite_stuff, notes, relationship_started)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "Margo",
                        "English (though I can understand and speak some Swedish and French too)",
                        json.dumps([]),
                        json.dumps([]),
                        json.dumps([]),
                        "like to be corrected if grammar seems off.",
                        date.today().isoformat(),
                    ),
                )
                print("[Identity] Default owner_profile row created.")

            conn.commit()

    def _insert_identity_snapshot(
        self, conn, mood, energy, current_goals, beliefs_about_self, things_interesting
    ):
        conn.execute(
            """INSERT INTO bmo_identity
               (mood, energy, current_goals, beliefs_about_self, things_interesting)
               VALUES (?, ?, ?, ?, ?)""",
            (
                mood,
                energy,
                json.dumps(current_goals),
                json.dumps(beliefs_about_self),
                json.dumps(things_interesting),
            ),
        )

    # ---------- reading current snapshot ----------
    def _get_latest_identity(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM bmo_identity ORDER BY last_updated DESC, id DESC LIMIT 1"
            ).fetchone()
            return {
                "mood": row["mood"],
                "energy": row["energy"],
                "current_goals": json.loads(row["current_goals"]),
                "beliefs_about_self": json.loads(row["beliefs_about_self"]),
                "things_interesting": json.loads(row["things_interesting"]),
                "last_updated": row["last_updated"],
            }

    def _get_owner(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM owner_profile WHERE id = 1").fetchone()
            return {
                "name": row["name"],
                "preferred_language": row["preferred_language"],
                "interests": json.loads(row["interests"]),
                "expertise": json.loads(row["expertise"]),
                "favorite_shows_and_movies": json.loads(row["favorite_stuff"]),
                "notes": row["notes"],
                "relationship_started": row["relationship_started"],
            }

    #     def _load(self, path: str, default: dict) -> dict:
    #     if not os.path.exists(path):
    #         os.makedirs(os.path.dirname(path), exist_ok=True)
    #         self._save(path, default)
    #         return default

    #     try:
    #         with open(path, "r", encoding="utf-8") as f:
    #             return json.load(f)
    #     except Exception:
    #         print(f"[BMO] Warning: could not read {path}, using defaults.")
    #         return default

    # def _save(self, path: str, data: dict):
    #     # Write a dict to a JSON file, creating directories if needed
    #     os.makedirs(os.path.dirname(path), exist_ok=True)
    #     with open(path, "w", encoding="utf-8") as f:
    #         json.dump(data, f, indent=2, ensure_ascii=False)

    # def save_identity(self):
    #     """Persist the current identity state to disk."""
    #     self.identity["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    #     self._save(IDENTITY_FILE, self.identity)

    # ---------- getters (same public API as before) ----------
    def get_mood(self) -> str:
        return self._get_latest_identity()["mood"]

    def get_mood_description(self) -> str:
        mood = self.get_mood()
        return MOOD_DESCRIPTIONS.get(mood, f"Your current mood is {mood}.")

    def get_owner_context(self) -> str:
        o = self._get_owner()
        lines = []

        if o.get("name") and o["name"] != "you":
            lines.append(f"The person you are talking to is called {o['name']}.")
        if o.get("interests"):
            lines.append(f"They are interested in {', '.join(o['interests'])}.")
        if o.get("expertise"):
            lines.append(f"They have expertise in {', '.join(o['expertise'])}.")
        if o.get("notes"):
            lines.append(f"Additional notes about them: {o['notes']}")
        if o.get("favorite_shows_and_movies"):
            shows = ", ".join(o["favorite_shows_and_movies"])
            lines.append(f"Some of their favorite shows and movies are: {shows}.")

        return "\n".join(lines)

    def get_bmo_context(self) -> str:
        i = self._get_latest_identity()
        lines = [f"Your current mood: {self.get_mood_description()}"]

        if i.get("current_goals"):
            goals = "\n- " + "\n- ".join(i["current_goals"])
            lines.append(f"Your current goals are: {goals}")
        if i.get("beliefs_about_self"):
            beliefs = "\n- " + "\n- ".join(i["beliefs_about_self"])
            lines.append(f"You have the following beliefs about yourself: {beliefs}")
        if i.get("things_interesting"):
            interests = "\n- " + "\n- ".join(i["things_interesting"])
            lines.append(f"Some things you've found interesting lately are: {interests}")
        if i.get("energy"):
            lines.append(f"Your current energy level is: {i['energy']}")

        return "\n".join(lines)

    # ---------- setters: read latest row, insert a new full snapshot ----------
    def set_mood(self, mood: str):
        current = self._get_latest_identity()
        with sqlite3.connect(self.db_path) as conn:
            self._insert_identity_snapshot(
                conn,
                mood,
                current["energy"],
                current["current_goals"],
                current["beliefs_about_self"],
                current["things_interesting"],
            )
            conn.commit()

    def set_energy(self, energy: str):
        current = self._get_latest_identity()
        with sqlite3.connect(self.db_path) as conn:
            self._insert_identity_snapshot(
                conn,
                current["mood"],
                energy,
                current["current_goals"],
                current["beliefs_about_self"],
                current["things_interesting"],
            )
            conn.commit()

    def add_goal(self, goal: str):
        current = self._get_latest_identity()
        goals = current["current_goals"]
        if goal not in goals:
            goals.append(goal)
        if len(goals) > 5:
            goals.pop(0)  # keep only the 5 most recent goals

        with sqlite3.connect(self.db_path) as conn:
            self._insert_identity_snapshot(
                conn,
                current["mood"],
                current["energy"],
                goals,
                current["beliefs_about_self"],
                current["things_interesting"],
            )
            conn.commit()

    def add_interesting_thing(self, thing: str):
        current = self._get_latest_identity()
        things = current["things_interesting"]
        if thing not in things:
            things.append(thing)

        with sqlite3.connect(self.db_path) as conn:
            self._insert_identity_snapshot(
                conn,
                current["mood"],
                current["energy"],
                current["current_goals"],
                current["beliefs_about_self"],
                things,
            )
            conn.commit()

    def update_owner(self, key: str, value):
        if key not in _OWNER_UPDATABLE_FIELDS:
            raise ValueError(f"Cannot update unknown owner field: {key}")

        if isinstance(value, (list, dict)):
            value = json.dumps(value)

        with sqlite3.connect(self.db_path) as conn:
            # key is validated against an allow-list above, safe to interpolate
            conn.execute(f"UPDATE owner_profile SET {key} = ? WHERE id = 1", (value,))
            conn.commit()

    # ---------- time based mood ----------
    def auto_shift_mood(self):
        hour = datetime.now().hour
        current = self._get_latest_identity()
        last_updated_date = current["last_updated"][:10]  # "YYYY-MM-DD HH:MM:SS"
        today = date.today().isoformat()

        # Only auto-shift mood once per day to avoid rapid changes
        if last_updated_date != today:
            if 5 <= hour < 9:
                self.set_mood("reflective")
            elif 9 <= hour < 12:
                self.set_mood("focused")
            elif 12 <= hour < 17:
                self.set_mood("energetic")
            elif 17 <= hour < 21:
                self.set_mood("curious")
            else:
                self.set_mood("tired")