import csv
import re
import sys
from typing import Any

# Pattern to find tags of interest
tag_pattern = re.compile(r'(qx\|[^|]+\||md\|[^|]+\||mb\|[^|]+\||pc\|[^|]+\||mc\|[^|]+\|)')

def parse_bridge_file(input_path, output_path) -> None:
    boards = []
    current_board: dict[str,Any] = {}
    current_play_sequence: list[str] = []
    in_board = False

    def calculate_tricks_from_play(play_sequence, trump):
        """Calculate number of tricks from play sequence (4 cards per trick)"""
        if not play_sequence:
            return None
        # Each trick consists of 4 cards
        print(play_sequence)
        total_cards_played = len(play_sequence)
        tricks_completed = total_cards_played // 4
        return tricks_completed

    def flush_board():
        nonlocal in_board, current_play_sequence
        if current_board and current_board.get("hands"):
            # Calculate tricks if not provided
            if current_board.get("tricks") is None and current_play_sequence:
                calculated_tricks = calculate_tricks_from_play(current_play_sequence)
                if calculated_tricks is not None:
                    current_board['tricks'] = calculated_tricks
            
            # Only add board if we have at least hands and either tricks or first_card
            if current_board.get("tricks") is not None or current_board.get("first_card"):
                boards.append(current_board.copy())
        
        current_board.clear()
        current_play_sequence = []
        in_board = False

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
                        "tricks": None
                    }
                    in_board = True
                    current_play_sequence = []

                elif tag == 'md' and in_board:
                    hands = data.split(',')
                    if len(hands) == 4:
                        current_board['hands'] = hands

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

    flush_board()  # Don't forget the last board

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['south_hand', 'west_hand', 'north_hand', 'east_hand', 'first_card', 'tricks'])
        for b in boards:
            h = b.get('hands', ['','','',''])
            writer.writerow([
                h[0] if len(h) > 0 else '',
                h[1] if len(h) > 1 else '',
                h[2] if len(h) > 2 else '',
                h[3] if len(h) > 3 else '',
                b.get('first_card', ''),
                b.get('tricks', '')
            ])

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python bridge_parser_to_csv.py input.txt output.csv")
    else:
        parse_bridge_file(sys.argv[1], sys.argv[2])
