import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory.commands import run_bmo
from brain.personality import get_system_prompt


def print_bmo(text: str):
    print(f"[BMO] {text}")


def print_separator():
    print("-" * 50)  # 50 is the number of dashes in the separator line


def main():
    run_bmo.commands()


# Run the main function if this script is executed directly
# This allows the script to be imported as a module without executing the main function
if __name__ == "__main__":
    # Import here to avoid circular issues
    from brain.personality import get_system_prompt

    main()
