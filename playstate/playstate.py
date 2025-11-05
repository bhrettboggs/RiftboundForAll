import os
import time

def speak_to_player(message, output_file="speech_output.txt"):
    """Print message and save it to output file for text-to-speech."""
    print(message)
    with open(output_file, 'a') as f:
        f.write(message + "\n")

def card_value(card):
    """Convert card notation to its blackjack value."""
    rank = card[0]
    if rank == 'A':
        return 11  # Ace starts as 11, adjusted later if needed
    elif rank == '0':
        return 10  # Ten
    elif rank in 'JQK':
        return 10
    else:
        return int(rank)

def card_name(card):
    """Convert card notation to readable name."""
    rank = card[0]
    suit = card[1].lower()
    
    rank_names = {
        'A': 'Ace', '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five',
        '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine', '0': 'Ten',
        'J': 'Jack', 'Q': 'Queen', 'K': 'King'
    }
    
    suit_names = {
        's': 'Spades', 'd': 'Diamonds', 'h': 'Hearts', 'c': 'Clubs'
    }
    
    return f"{rank_names.get(rank, rank)} of {suit_names.get(suit, suit)}"

def calculate_hand_value(hand):
    """Calculate the total value of a hand, adjusting for Aces."""
    total = sum(card_value(card) for card in hand)
    aces = sum(1 for card in hand if card[0] == 'A')
    
    # Adjust Aces from 11 to 1 if needed to avoid busting
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    
    return total

def speak_hand(owner, hand):
    """Create a readable description of a hand."""
    cards_description = ", ".join(card_name(card) for card in hand)
    total = calculate_hand_value(hand)
    return f"{owner} has: {cards_description}. Total: {total}"

def parse_line(line):
    """Parse a line from the text file into dealer and player cards."""
    dealer_cards = []
    player_cards = []
    
    # Split by spaces
    tokens = line.strip().split()
    
    current_target = None
    
    for token in tokens:
        if token == 'D:':
            current_target = 'dealer'
        elif token == 'P:':
            current_target = 'player'
        else:
            # This is a card
            if len(token) >= 2:  # Valid card format
                if current_target == 'dealer':
                    dealer_cards.append(token)
                elif current_target == 'player':
                    player_cards.append(token)
    
    return dealer_cards, player_cards

def read_latest_response(response_file="responses.txt"):
    """Read the last line from the response file."""
    try:
        with open(response_file, 'r') as f:
            lines = [line.strip().lower() for line in f.readlines() if line.strip()]
            if lines:
                return lines[-1]  # Return last line
    except FileNotFoundError:
        pass
    return None

def wait_for_response(response_file="responses.txt", last_response=None):
    """Wait for a new response in the response file."""
    speak_to_player("\nWaiting for your decision (hit/stand)...", "speech_output.txt")
    
    while True:
        current_response = read_latest_response(response_file)
        
        # Check if we have a new response
        if current_response and current_response != last_response:
            if current_response in ['hit', 'stand']:
                speak_to_player(f"\nYou chose: {current_response}", "speech_output.txt")
                return current_response
        
        time.sleep(0.5)  # Wait before checking again

def read_file_lines(filename):
    """Read all lines from the file."""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []
    """Read all lines from the file."""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []

def play_blackjack(filename):
    """Main game function."""
    output_file = "speech_output.txt"
    
    # Clear previous speech output
    if os.path.exists(output_file):
        os.remove(output_file)
    
    if not os.path.exists(filename):
        speak_to_player(f"Error: File '{filename}' not found.", output_file)
        return
    
    # Read initial deal (first line)
    lines = read_file_lines(filename)
    
    if not lines:
        speak_to_player("Error: File is empty.", output_file)
        return
    
    # Parse initial deal
    dealer_cards, player_cards = parse_line(lines[0])
    
    if len(dealer_cards) < 1:
        speak_to_player("Error: Need at least 1 dealer card (format: D: 4c)", output_file)
        return
    
    if len(player_cards) < 2:
        speak_to_player("Error: Need at least 2 player cards (format: P: 5h 9s)", output_file)
        return
    
    speak_to_player("\n=== NEW HAND ===", output_file)
    speak_to_player(f"Dealer shows: {card_name(dealer_cards[0])}", output_file)
    speak_to_player(speak_hand("You", player_cards), output_file)
    
    current_line = 1  # Track which line we're on (0 was initial deal)
    last_response = None  # Track last response to detect new ones
    
    # Player's turn
    while True:
        player_total = calculate_hand_value(player_cards)
        
        if player_total == 21:
            speak_to_player("\nYou have 21!", output_file)
            break
        elif player_total > 21:
            speak_to_player(f"\nBUST! You have {player_total}. You lose.", output_file)
            return
        
        # Wait for response from file instead of terminal input
        action = wait_for_response("responses.txt", last_response)
        last_response = action  # Update last response
        
        if action == 'hit':
            speak_to_player("\nWaiting for next card...", output_file)
            
            # Keep checking file for new line
            new_card = None
            while new_card is None:
                lines = read_file_lines(filename)
                
                if len(lines) > current_line:
                    # New line available
                    new_line = lines[current_line]
                    dealer_new, player_new = parse_line(new_line)
                    
                    # Get the new player card(s) from this line
                    if player_new:
                        new_card = player_new[0]  # Take first card from new line
                        current_line += 1
                        break
                
                time.sleep(0.5)  # Wait half second before checking again
            
            player_cards.append(new_card)
            
            speak_to_player(f"\nYou drew: {card_name(new_card)}", output_file)
            speak_to_player(speak_hand("You", player_cards), output_file)
            
        elif action == 'stand':
            speak_to_player("\nYou stand.", output_file)
            speak_to_player("\nWaiting for dealer cards...", output_file)
            
            # Keep checking for new lines with dealer cards
            dealer_done = False
            while not dealer_done:
                lines = read_file_lines(filename)
                
                # Check all remaining lines for dealer cards
                for i in range(current_line, len(lines)):
                    new_line = lines[i]
                    dealer_new, _ = parse_line(new_line)
                    
                    # Add any new dealer cards
                    for card in dealer_new:
                        if card not in dealer_cards:
                            dealer_cards.append(card)
                
                # Check if dealer has finished (has 17+ or busted)
                if calculate_hand_value(dealer_cards) >= 17:
                    dealer_done = True
                    break
                
                # If we have new cards but dealer still under 17, keep waiting
                if len(lines) > current_line:
                    time.sleep(0.5)
                else:
                    time.sleep(0.5)
            
            break
        # Removed else clause for invalid actions since we only accept hit/stand from file
    
    # Dealer's turn results
    player_total = calculate_hand_value(player_cards)
    
    if player_total > 21:
        return  # Player already busted
    
    speak_to_player("\n=== DEALER'S TURN ===", output_file)
    speak_to_player(speak_hand("Dealer", dealer_cards), output_file)
    
    dealer_total = calculate_hand_value(dealer_cards)
    
    # Determine winner
    speak_to_player("\n=== RESULT ===", output_file)
    if dealer_total > 21:
        speak_to_player(f"Dealer busts with {dealer_total}. YOU WIN!", output_file)
    elif dealer_total > player_total:
        speak_to_player(f"Dealer has {dealer_total}, you have {player_total}. You lose.", output_file)
    elif player_total > dealer_total:
        speak_to_player(f"You have {player_total}, dealer has {dealer_total}. YOU WIN!", output_file)
    else:
        speak_to_player(f"Both have {player_total}. PUSH (tie).", output_file)

if __name__ == "__main__":
    print("Blackjack Assistant for Blind Players")
    print("======================================")
    
    filename = input("Enter the card data filename (or press Enter for 'cards.txt'): ").strip()
    if not filename:
        filename = "cards.txt"
    
    play_blackjack(filename)