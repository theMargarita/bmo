from brain.llm import LLMClient
from brain.prompt_builder import PromptBuilder
from memory.short_term import ShortTermMemory
from memory.identity import Identity
import sys
import random
from brain.personality import get_system_prompt
from memory.bmos_memory import BMOsMemory

def print_bmo(text: str):
    print(f"[BMO] {text}")


def print_separator():
    print("-" * 50)  # 50 is the number of dashes in the separator line


def run_bmo():
    print_separator()
    print("BMO is starting up.")
    print_separator()
    # Auto-set mood based on time of day (only on fresh startup)
    identity = Identity()
    identity.auto_shift_mood()
    # initialize the core components
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


    # opening line from BMO
    opening_promt = [
        {"role": "system", "content": get_system_prompt()},
    ]
    opening = llm_client.chat(opening_promt)
    print_bmo(opening)
    
    bmo_memory = BMOsMemory()
    conversation_id = bmo_memory.save_conversations(user_id=1, message="Session started.")

    while True:
        # contunue to propmt even if I press enter without typing anything
        try:
            user_input = input("\nYou: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\n\nBMO: See you.\n")
            break

        if not user_input:
            continue

        # built in commands
        if user_input.lower() == "quit":
            randomize = [
                "Goodbye!",
                "See you later!",
                "Take care!",
                "Catch you later aligator!",
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
        # Add user message to short-term memory
        # The empty list [] is the memory slot — long-term memories plug in here later
        memo = BMOsMemory()
        content = user_input
        memo.save_chat_message(conversation_id, "user", content)
        relevant_memories = memo.seach_context(user_input)

        bmo_thought = memo.fetch_bmos_thoughts(user_id=1)
        memo.save("Some memory content", "source", importance=5)


        short_term_memory.add("user", user_input)
        messages = prompt_builder.build(
            history=short_term_memory.get_history(), 
            memories=relevant_memories,
            bmo_thought=bmo_thought
        )
        
        response = llm_client.chat(messages)
        short_term_memory.add("assistant", response)
        print_bmo(response)


# generate the opening instruction for BMO to use when starting a conversation
# unused for now
def get_opening_instruction() -> str:
    return """You are BMO, an AI companion. Generate a single short opening line to start a conversation. 
    Do not introduce your capabilities. Do not say 'How can I help you today?'. 
    Just say something natural — curious, direct, warm. One or two sentences maximum.
    You can reference something genuinely interesting you have been thinking about, or simply acknowledge you are here and ready."""

if __name__ == "__main__":
    # Import here to avoid circular issues
    from brain.personality import get_system_prompt

    run_bmo()