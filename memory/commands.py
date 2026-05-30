import asyncio
import random
import sys
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


async def run_bmo():
    print_separator()
    print("BMO is starting up.")
    print_separator()

    identity = Identity()
    identity.auto_shift_mood()

    llm_client = LLMClient()
    short_term_memory = ShortTermMemory()
    prompt_builder = PromptBuilder(identity_manager=identity)

    if not llm_client.is_available():
        print("\n[Error] Cannot reach Ollama.")
        sys.exit(1)

    bmo_memory = BMOsMemory()
    bmo_memory.seed_database(owner_name="Margo")  # sync — fine at startup

    name = input("Who am I speaking to? ").strip()
    if not name:
        name = "Stranger"

    user_id = await bmo_memory.get_or_create_user(name)

    last_state = bmo_memory.get_bmo_state()  # sync — called once at startup
    baseline_mood = last_state["mood"] if last_state else "Normal"

    conversation_id = await bmo_memory.start_session(
        mood=baseline_mood, user_id=user_id
    )

    print(f"\nModel: {llm_client.model}")
    print(f"Mood : {baseline_mood}")
    print("\nType 'quit' to exit, 'clear' to reset.")
    print_separator()

    opening_prompt = [
        {"role": "system", "content": get_system_prompt()},
        {
            "role": "user",
            "content": f"You are talking to {name}. Greet them appropriately based on your relationship.",
        },
    ]
    # LLMClient.chat is blocking — run in thread so the event loop stays free
    opening = await asyncio.to_thread(llm_client.chat, opening_prompt)
    print_bmo(opening)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "quit"

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\n[System] BMO is processing today's experiences...")
            recent_history = short_term_memory.get_history()
            history_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in recent_history]
            )

            await bmo_memory.consolidate_bmo(
                user_id=user_id,
                conversation_id=conversation_id,
                recent_messages=history_text,
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
            bmo_memory.update_bmo_state(
                event="manual_mood_shift",
                status="altered",
                mood=new_mood,
                detail="User manual intervention.",
            )
            print_bmo(f"Mood changed to {new_mood}.")
            continue

        if user_input.lower().startswith("energy "):
            new_energy = user_input[7:].strip()
            identity.set_energy(new_energy)
            print_bmo(f"Energy level updated to {new_energy}.")
            continue

        # Log conversation data
        await bmo_memory.save_chat_message(conversation_id, "user", user_input)

        # search_context is sync (ChromaDB) — no await needed
        relevant_memories = bmo_memory.search_context(user_input)

        bmo_thought = await bmo_memory.fetch_bmos_thoughts(user_id=user_id)
        short_term_memory.add("user", user_input)

        messages = prompt_builder.build(
            history=short_term_memory.get_history(),
            memories=relevant_memories,
            bmo_thought=bmo_thought,
        )

        # LLMClient.chat is blocking — run in thread
        response = await asyncio.to_thread(llm_client.chat, messages)

        short_term_memory.add("BMO", response)
        await bmo_memory.save_chat_message(conversation_id, "BMO", response)
        print_bmo(response)


if __name__ == "__main__":
    asyncio.run(run_bmo())
