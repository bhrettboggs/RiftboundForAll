#!/usr/bin/env python3
"""
Game State Parser
Parses a game state document with sections marked by numbers 1-4
"""

import argparse
import sys


def parse_game_state(file_path):
    """
    Parse game state file with format: "1 words 2 words 3 words 4 words"
    
    Returns:
        Dictionary with keys: 'total_mana', 'homebase', 'enemy_battlefield', 'ally_battlefield'
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Split by section markers
    sections = {
        'total_mana': [],
        'homebase': [],
        'enemy_battlefield': [],
        'ally_battlefield': []
    }
    
    # Find positions of markers 1, 2, 3, 4
    words = content.split()
    
    try:
        idx_1 = words.index('1')
        idx_2 = words.index('2')
        idx_3 = words.index('3')
        idx_4 = words.index('4')
        
        # Extract words between markers
        sections['total_mana'] = words[idx_1 + 1:idx_2]
        sections['homebase'] = words[idx_2 + 1:idx_3]
        sections['enemy_battlefield'] = words[idx_3 + 1:idx_4]
        sections['ally_battlefield'] = words[idx_4 + 1:]
        
    except ValueError as e:
        print(f"Error: File must contain markers 1, 2, 3, and 4 in order", file=sys.stderr)
        sys.exit(1)
    
    return sections


def display_section(section_name, words):
    """Display a section's contents."""
    print(f"\n{section_name}:")
    print("-" * 50)
    if words:
        for word in words:
            print(f"  - {word}")
    else:
        print("  (empty)")
    print()


def interactive_mode(sections):
    """Run interactive menu for selecting sections."""
    while True:
        print("\n" + "=" * 50)
        print("GAME STATE VIEWER")
        print("=" * 50)
        print("1. Total Mana")
        print("2. Homebase")
        print("3. Enemy Battlefield")
        print("4. Ally Battlefield")
        print("5. Show All")
        print("6. Exit")
        print()
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '1':
            display_section("Total Mana", sections['total_mana'])
        elif choice == '2':
            display_section("Homebase", sections['homebase'])
        elif choice == '3':
            display_section("Enemy Battlefield", sections['enemy_battlefield'])
        elif choice == '4':
            display_section("Ally Battlefield", sections['ally_battlefield'])
        elif choice == '5':
            display_section("Total Mana", sections['total_mana'])
            display_section("Homebase", sections['homebase'])
            display_section("Enemy Battlefield", sections['enemy_battlefield'])
            display_section("Ally Battlefield", sections['ally_battlefield'])
        elif choice == '6':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter 1-6.")


def main():
    parser = argparse.ArgumentParser(
        description='Parse and display game state sections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s gamestate.txt
  %(prog)s gamestate.txt --section total_mana
  %(prog)s gamestate.txt --section homebase
        """
    )
    
    parser.add_argument('file', help='Input game state file')
    parser.add_argument('--section', 
                       choices=['total_mana', 'homebase', 'enemy_battlefield', 'ally_battlefield', 'all'],
                       help='Display specific section (skips interactive mode)')
    
    args = parser.parse_args()
    
    # Parse the game state file
    sections = parse_game_state(args.file)
    
    # If section specified, display it and exit
    if args.section:
        if args.section == 'all':
            display_section("Total Mana", sections['total_mana'])
            display_section("Homebase", sections['homebase'])
            display_section("Enemy Battlefield", sections['enemy_battlefield'])
            display_section("Ally Battlefield", sections['ally_battlefield'])
        else:
            section_names = {
                'total_mana': 'Total Mana',
                'homebase': 'Homebase',
                'enemy_battlefield': 'Enemy Battlefield',
                'ally_battlefield': 'Ally Battlefield'
            }
            display_section(section_names[args.section], sections[args.section])
    else:
        # Run interactive mode
        interactive_mode(sections)


if __name__ == "__main__":
    main()