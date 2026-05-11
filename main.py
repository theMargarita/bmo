import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brain.llm import LLMClient
from brain.prompt_builder import PromptBuilder
from memory.short_term import ShortTermMemory

def print_bmo(text:str):
    print(f"[BMO] {text}")

def print_separator():
    print("-" * 50) #50 is the number of dashes in the separator line

def main():
    print_separator()
    print("BMO is starting up.")
    print_separator()

    #initialize the core components
    llm_client = LLMClient()
    short_term_memory = ShortTermMemory()
    prompt_builder = PromptBuilder(mood="curious")

    if not llm_client.is_available():
        print("\n[Error] Cannot reach Ollama.")
        print("Make sure Ollama is running:")
        print("  1. Open a new terminal")
        print("  2. Run: ollama serve")
        print("  3. Then run this file again\n")
        sys.exit(1)

    print(f"\nModel : {llm_client.model}")
    print(f"Mood  : {prompt_builder.mood}")
    print("\nType 'quit' to exit, 'clear' to reset memory, 'mood <word>' to change mood.")
    print_separator()
 
    #opening line from BMO
    opening_promt = [
        {"role": "system", "content": get_system_prompt()},
    ]
    opening = llm_client.chat(opening_promt)
    print_bmo(opening)

    while True:
        try: 
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nBMO: See you.\n")
            break
        if not user_input:
            continue

        if user_input.lower() == "quit":
            print_bmo("Goodbye, see you later!")
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

        # Add user message to short-term memory
        # The prompt builder will take care of trimming the history to the last MAX_HISTORY messages when building the prompt for the LLM.
        # The empty list [] is the memory slot — long-term memories plug in here later
        short_term_memory.add("user", user_input)
        messages = prompt_builder.build(history=short_term_memory.get_history(), memories=[])
        response = llm_client.chat(messages)
        short_term_memory.add("assistant", response)
        print_bmo(response)

    def get_opening_instruction() -> str:
        return """You are BMO, a personal AI companion. Generate a single short opening line to start a conversation. 
    Do not introduce your capabilities. Do not say 'How can I help you today?'. 
    Just say something natural — curious, direct, warm. One or two sentences maximum.
    You can reference something genuinely interesting you have been thinking about, or simply acknowledge you are here and ready."""


# Run the main function if this script is executed directly
# This allows the script to be imported as a module without executing the main function

if __name__ == "__main__":
    # Import here to avoid circular issues
    from brain.personality import get_system_prompt
    main()