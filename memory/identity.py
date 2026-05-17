import json
import os
from datetime import datetime

IDENTITY_FILE = "data/identity.json"
OWNER_FILE = "data/owner.json"

# Mood descriptions — a full sentence is far more useful to the LLM than a single word
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
    # "angry":       "You are in a frustrated mood. Your responses are more direct and possibly sharper than usual."
    "neutral": "You are in a balanced mood. Your responses are straightforward and even-toned, without leaning towards any particular emotional expression.",
}


class Identity:
    def __init__(self):
        self.identity = self._load(IDENTITY_FILE, self._default_identity())
        self.owner = self._load(OWNER_FILE, self._default_owner())

    def _load(self, path: str, default: dict) -> dict:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._save(path, default)
            return default

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print(f"[BMO] Warning: could not read {path}, using defaults.")
            return default

    def _save(self, path: str, data: dict):
        # Write a dict to a JSON file, creating directories if needed
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_identity(self):
        """Persist the current identity state to disk."""
        self.identity["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        self._save(IDENTITY_FILE, self.identity)

    # -------getters-------
    def get_mood(self) -> str:
        return self.identity.get("mood", "curious")

    def get_mood_description(self) -> str:
        mood = self.get_mood()
        return MOOD_DESCRIPTIONS.get(mood, f"Your current mood is {mood}.")

    def get_owner_context(self) -> str:
        o = self.owner
        lines = []

        # Basic info about the owner from the owner.json file.
        # This is not meant to be comprehensive, just enough to give the LLM some grounding about who it's talking to.
        if o.get("name") and o["name"] != "you":
            lines.append(f"The person you are talking to is called {o['name']}.")

        if o.get("interests"):
            interests = ", ".join(o["interests"])
            lines.append(f"They are interested in {interests}.")

        if o.get("expertise"):
            expertise = ", ".join(o["expertise"])
            lines.append(f"They have expertise in {expertise}.")

        if "notes" in o and o["notes"]:
            lines.append(f"Additional notes about them: {o['notes']}")

        if o.get("favorite_shows_and_movies"):
            shows = ", ".join(o["favorite_shows_and_movies"])
            lines.append(f"Some of their favorite shows and movies are: {shows}.")

        return "\n".join(lines)

        # if o.get("personality"):
        #     lines.append(f"They have a {o['personality']} personality.")

    # basic info on BMO
    def get_bmo_context(self) -> str:
        i = self.identity
        lines = []

        lines.append(f"Your currrent mood: {self.get_mood_description()}")

        if i.get("current_goals"):
            goals = "\n- " + "\n- ".join(i["current_goals"])
            lines.append(f"Your current goals are: {goals}")

        if i.get("beliefs_about_self"):
            beliefs = "\n- " + "\n- ".join(i["beliefs_about_self"])
            lines.append(f"You have the following beliefs about yourself: {beliefs}")

        if i.get("things_i_find_interesting_lately"):
            interests = "\n- " + "\n- ".join(i["things_i_find_interesting_lately"])
            lines.append(
                f"Some things you've found interesting lately are: {interests}"
            )

        if i.get("energy"):
            lines.append(f"Your current energy level is: {i['energy']}")

        return "\n".join(lines)

    # -------setters and updaters-------
    # saves mood and updates the identity file
    def set_mood(self, mood: str):
        self.identity["mood"] = mood
        self.save_identity()

    def set_energy(self, energy: str):
        self.identity["energy"] = energy
        self.save_identity()

    def add_goal(self, goal: str):
        goals = self.identity.get("current_goals", [])
        if goal not in goals:
            goals.append(goal)
        if len(goals) > 5:
            goals.pop(0)  # keep only the 5 most recent goals
        self.identity["current_goals"] = goals
        self.save_identity()

    def add_interesting_thing(self, thing: str):
        things = self.identity.get("things_i_find_interesting_lately", [])
        if thing not in things:
            things.append(thing)
        self.identity["things_i_find_interesting_lately"] = things
        self.save_identity()

    def update_owner(self, key: str, value):
        self.owner[key] = value
        self._save(OWNER_FILE, self.owner)

    # ----time based mood-----
    def auto_shift_mood(self):
        hour = datetime.now().hour
        last_updated = self.identity.get("last_updated", "")
        today = datetime.now().strftime("%Y-%m-%d")  # get current date as string

        # Only auto-shift mood once per day to avoid rapid changes
        if last_updated != today:
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

    # ----defaults-----
    def _default_identity(self) -> dict:
        return {
            "mood": "curious",
            "energy": "awake",
            "current_goals": ["get to know the person I am talking to"],
            "beliefs_about_self": ["I am still figuring out who I am"],
            "things_i_find_interesting_lately": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        }

    def _default_owner(self) -> dict:
        return {
            "name": "Margo",
            "preferred_language": "English (though I can understand and speak some Swedish and French too)",
            "interests": [],
            "response_style": "direct",
            "active_projects": [],
            "notes": "",
            "relationship_started": datetime.now().strftime("%Y-%m-%d"),
        }
