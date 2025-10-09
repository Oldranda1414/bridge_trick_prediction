import csv
import re
import sys
from typing import Any

# Pattern to find tags of interest
tag_pattern = re.compile(r'(qx\|[^|]+\||md\|[^|]+\||mb\|[^|]+\||pc\|[^|]+\||mc\|[^|]+\|)')

# Card value mapping
CARD_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 
    'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}

def get_trump_from_bidding(bidding_sequence) -> str | None:
    """Extract trump suit from the final contract bid (last non-pass bid)."""
    if not bidding_sequence:
        return None

    # Go through the bidding sequence backwards
    for bid in reversed(bidding_sequence):
        bid = bid.strip().upper()
        if len(bid) >= 2 and bid[0].isdigit() and bid[1] in 'CDHSN':
            suit_char = bid[1]
            suit_map = {'C': 'C', 'D': 'D', 'H': 'H', 'S': 'S', 'N': 'NT'}
            return suit_map.get(suit_char)
    return None

def calculate_tricks_won_by_declarer(play_sequence, trump_suit, first_player_index) -> int | None:
    """
    Calculate how many tricks were won by declarer's side.
    first_player_index: 0=N, 1=E, 2=S, 3=W (the player who led the first card)
    Returns: tricks won by declarer's side
    """
    if not play_sequence:
        return None
    
    declarer_side = 'EW' if first_player_index in [0, 2] else 'NS'
    
    tricks_won_by_declarer = 0
    current_trick = []
    current_leader = first_player_index
    
    for card in play_sequence:
        current_trick.append((card, current_leader))
        current_leader = (current_leader + 1) % 4  # Move to next player
        
        if len(current_trick) == 4:
            winning_card, winning_player = determine_trick_winner(current_trick, trump_suit)
            if (declarer_side == 'NS' and winning_player in [0, 2]) or \
               (declarer_side == 'EW' and winning_player in [1, 3]):
                tricks_won_by_declarer += 1
            current_leader = winning_player
            current_trick = []
    
    return tricks_won_by_declarer

def determine_trick_winner(trick_cards, trump_suit) -> tuple[str, int]:
    """Determine who wins a trick given the cards played and trump suit."""
    led_suit = trick_cards[0][0][0].upper()
    
    winning_card, winning_player = trick_cards[0]
    winning_value = get_card_value(winning_card, led_suit, trump_suit)
    
    for card, player in trick_cards[1:]:
        card_value = get_card_value(card, led_suit, trump_suit)
        if card_value > winning_value:
            winning_card, winning_player, winning_value = card, player, card_value
    
    return winning_card, winning_player

def get_card_value(card, led_suit, trump_suit):
    """Get numeric value of card considering trump and led suit."""
    suit = card[0].upper()
    rank = card[1]
    base_value = CARD_VALUES.get(rank, 0)
    
    if trump_suit and suit == trump_suit:
        return 100 + base_value  # Trump cards are valued higher
    elif suit == led_suit:
        return base_value
    else:
        return 0

def parse_bridge_file(input_path, output_path) -> None:
    boards = []
    current_board: dict[str, Any] = {}
    current_play_sequence: list[str] = []
    current_bidding: list[str] = []
    in_board = False

    def flush_board() -> None:
        nonlocal in_board, current_play_sequence, current_bidding
        if current_board and current_board.get("hands"):
            # Determine trump from bidding
            trump_suit = get_trump_from_bidding(current_bidding)
            current_board['trump'] = trump_suit

            # Calculate tricks if not provided
            if current_board.get("tricks") is None and current_play_sequence:
                first_card = current_play_sequence[0] if current_play_sequence else None
                first_player_index = determine_first_player(first_card, current_board["hands"])
                
                if first_player_index is not None:
                    calculated_tricks = calculate_tricks_won_by_declarer(
                        current_play_sequence, trump_suit, first_player_index
                    )
                    if calculated_tricks is not None:
                        current_board['tricks'] = calculated_tricks
            
            if current_board.get("tricks") is not None or current_board.get("first_card"):
                boards.append(current_board.copy())
        
        current_board.clear()
        current_play_sequence = []
        current_bidding = []
        in_board = False

    def determine_first_player(first_card, hands) -> int | None:
        if not first_card or not hands:
            return None
        for i, hand in enumerate(hands):
            if hand_contains_card(hand, first_card):
                return i
        return None

    def hand_contains_card(hand, card) -> bool:
        suit = card[0].upper()
        rank = card[1]
        suit_pattern = re.compile(r'([SHDC])([2-9AKQJT]+)')
        matches = suit_pattern.findall(hand)
        for hand_suit, ranks in matches:
            if hand_suit == suit and rank in ranks:
                return True
        return False

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            for match in tag_pattern.finditer(line):
                token = match.group(1)
                parts = token.split('|')
                if not parts:
                    continue
                tag = parts[0]
                data = parts[1] if len(parts) > 1 else ''

                if tag == 'qx':
                    flush_board()
                    current_board = {
                        "hands": None,
                        "first_card": None,
                        "tricks": None,
                        "trump": None
                    }
                    in_board = True
                    current_play_sequence = []
                    current_bidding = []

                elif tag == 'md' and in_board:
                    hands = data.split(',')
                    if len(hands) == 4:
                        current_board['hands'] = hands

                elif tag == 'mb' and in_board:
                    current_bidding.append(data.strip())

                elif tag == 'pc' and in_board:
                    card = data.strip()
                    current_play_sequence.append(card)
                    if current_board.get('first_card') is None:
                        current_board['first_card'] = card

                elif tag == 'mc' and in_board:
                    try:
                        current_board['tricks'] = int(data.strip())
                    except ValueError:
                        pass

    flush_board()

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['south_hand', 'west_hand', 'north_hand', 'east_hand', 'first_card', 'trump', 'tricks'])
        for b in boards:
            h = b.get('hands', ['','','',''])
            writer.writerow([
                h[0] if len(h) > 0 else '',
                h[1] if len(h) > 1 else '',
                h[2] if len(h) > 2 else '',
                h[3] if len(h) > 3 else '',
                b.get('first_card', ''),
                b.get('trump', ''),
                b.get('tricks', '')
            ])

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python bridge_parser_to_csv.py input.txt output.csv")
    else:
        parse_bridge_file(sys.argv[1], sys.argv[2])

