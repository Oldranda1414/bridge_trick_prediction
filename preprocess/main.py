import csv
import re
import sys

# Pattern to find tags of interest
tag_pattern = re.compile(r'(qx\|[^|]+\||md\|[^|]+\||mb\|[^|]+\||pc\|[^|]+\||mc\|[^|]+\|)')

def parse_bridge_file(input_path, output_path):
    boards = []
    current_board = {}

    def flush_board():
        if current_board and current_board.get("hands") and (
            current_board.get("tricks") is not None or current_board.get("first_card")
        ):
            boards.append(current_board.copy())

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

                elif tag == 'md':
                    hands = data.split(',')
                    if len(hands) == 4:
                        current_board['hands'] = hands

                elif tag == 'pc':
                    if current_board.get('first_card') is None:
                        current_board['first_card'] = data.strip()

                elif tag == 'mc':
                    try:
                        current_board['tricks'] = int(data.strip())
                    except ValueError:
                        pass

    flush_board()

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['north_hand', 'east_hand', 'south_hand', 'west_hand', 'first_card', 'tricks'])
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
