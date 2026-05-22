import sys
import os
from memory.short_term import ShortTermMemory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_add_message():
    mem = ShortTermMemory()
    mem.add("Hello", "Goodbye")
    assert len(mem.get_history()) == 1


def test_get_history():
    mem = ShortTermMemory()
    for i in range(20):  # over the MAX_HISTORY limit
        mem.add("user", f"message {i}")
    assert len(mem.get_history()) <= 20


def test_clear_wipes_messages():
    mem = ShortTermMemory()
    mem.add("USER", "Something text")
    mem.clear()
    assert mem.is_empty()


def test_roles_are_correct():
    mem = ShortTermMemory()
    mem.add("user", "hello")
    mem.add("assistant", "hi")
    assert mem.get_history()[0]["role"] == "user"
    assert mem.get_history()[1]["role"] == "assistant"
