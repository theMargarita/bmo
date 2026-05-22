import sys
import random
from brain.llm import LLMClient
from brain.prompt_builder import PromptBuilder
from memory.short_term import ShortTermMemory
from memory.identity import Identity
from brain.personality import get_system_prompt
from memory.bmos_memory import BMOsMemory


def print_bmo(text: str):
    print(f"\n[BMO]: {text}")


def print_separator():
    print("-" * 50)


def run_bmo():
    print_separator()
    print("BMO is starting up.")
    print_separator()

    # Auto-set mood based on time of day (only on fresh startup)
    identity = Identity()
    identity.auto_shift_mood()

    # Initialize the core components
    llm_client = LLMClient()
    short_term_memory = ShortTermMemory()
    prompt_builder = PromptBuilder(identity_manager=identity)

    if not llm_client.is_available():
        print("\n[Error] Cannot reach Ollama.")
        print("Make sure Ollama is running and try again")
        sys.exit(1)

    print(f"\nModel : {llm_client.model}")
    print(f"Mood  : {prompt_builder.identity_manager.get_bmo_context()}")
    print(
        "\nType 'quit' to exit, 'clear' to reset memory, 'mood <word>' to change mood."
    )
    print_separator()

    # Opening line from BMO
    opening_prompt = [
        {"role": "system", "content": get_system_prompt()},
    ]
    opening = llm_client.chat(opening_prompt)
    print_bmo(opening)

    # Instantiate database once and use it everywhere
    bmo_memory = BMOsMemory()
    bmo_memory.seed_database()
    conversation_id = bmo_memory.save_conversations(
        user_id=1, message="Session started."
    )

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "quit"  # Treat terminal interruptions as an orderly quit

        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() == "quit":
            # --- THE CONSOLIDATION TRIGGER ---
            print("\n[System] BMO is processing today's experiences...")

            # Fetch the recent history from short term memory to hand over to BMO's subconscious
            recent_history = short_term_memory.get_history()
            # Convert python list to a readable text block for the LLM
            history_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in recent_history]
            )

            # Run the automated database update!
            bmo_memory.consolidate_bmo(
                user_id=1, conversation_id=conversation_id, recent_messages=history_text
            )

            randomize = [
                "Goodbye!",
                "See you later!",
                "Take care!",
                "Catch you later alligator!",
            ]
            print_bmo(random.choice(randomize))
            break

        if user_input.lower() == "clear":
            short_term_memory.clear()
            print_bmo("Memory cleared. Fresh start!")
            continue

        if user_input.lower().startswith("mood "):
            new_mood = user_input[5:].strip()
            prompt_builder.set_mood(new_mood)
            print_bmo(f"Mood changed to {new_mood}.")
            continue

        if user_input.lower().startswith("energy "):
            new_energy = user_input[7:].strip()
            identity.set_energy(new_energy)
            print_bmo(f"Energy level updated to {new_energy}.")
            continue

        # 1. Save your text message to SQLite
        bmo_memory.save_chat_message(conversation_id, "user", user_input)

        # 2. Grab long-term database search results (fixed spelling here!)
        relevant_memories = bmo_memory.search_context(user_input)

        # 3. Pull BMO's current feelings/perception from database
        bmo_thought = bmo_memory.fetch_bmos_thoughts(user_id=1)

        # 4. Update short-term chat tracking
        short_term_memory.add("user", user_input)

        # 5. Compile everything into a unified prompt
        messages = prompt_builder.build(
            history=short_term_memory.get_history(),
            memories=relevant_memories,
            bmo_thought=bmo_thought,
        )

        # 6. Generate answer from Ollama
        response = llm_client.chat(messages)

        # 7. Save BMO's answer to short-term memory AND the database!
        short_term_memory.add("assistant", response)
        bmo_memory.save_chat_message(conversation_id, "assistant", response)

        # 8. Output to screen
        print_bmo(response)


if __name__ == "__main__":
    run_bmo()
