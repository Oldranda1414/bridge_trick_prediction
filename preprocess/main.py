def main():
    import csv
    import re

    input_file = "example.lin"
    output_file = "bridge_summary.csv"

    boards = []
    current_board = {}
    current_bids = []

    # The fixed player rotation order
    base_order = ["N", "E", "S", "W"]

    def rotated_players(start_index):
        """Rotate player order according to dealer index (1=N, 2=E, 3=S, 4=W)"""
        return base_order[start_index:] + base_order[:start_index]

    def flush_board():
        """Add the current board to list if it’s complete enough"""
        if "north_hand" in current_board and "tricks" in current_board:
            # Determine declarer
            if current_bids:
                for bid, player in reversed(current_bids):
                    if bid.lower() not in ("p", "d", "r"):
                        current_board["declarer"] = player
                        break
            print("current_board inside flush_board:", current_board)
            boards.append(current_board.copy())

    with open(input_file, "r", encoding="utf-8") as f:
        player_index = 0
        player_order = base_order.copy()

        for line in f:
            line = line.strip()

            # Start of a new board
            if line.startswith("qx|"):
                flush_board()
                current_board = {}
                current_bids = []
                player_index = 0
                player_order = base_order.copy()

                # Extract board id (e.g. o13, c13)
                m = re.search(r"qx\|([^|]+)\|", line)
                if m:
                    current_board["board"] = m.group(1)
                    print("current board inside if m", current_board)

            # Hands
            elif line.startswith("md|"):
                m = re.search(r"md\|([^|]+)\|", line)
                if m:
                    full_md = m.group(1)
                    # Check for dealer code (1–4)
                    dealer_match = re.match(r"(\d)(.*)", full_md)
                    if dealer_match:
                        dealer_code = int(dealer_match.group(1))
                        hands_str = dealer_match.group(2)
                        player_order = rotated_players(dealer_code - 1)
                    else:
                        hands_str = full_md

                    hands = hands_str.split(",")
                    if len(hands) == 4:
                        current_board["north_hand"] = hands[0]
                        current_board["east_hand"] = hands[1]
                        current_board["south_hand"] = hands[2]
                        current_board["west_hand"] = hands[3]
                        print("current board inside len(hands)", current_board)
                    else:
                        print("hands len not good:", len(hands))

            # Bids
            elif line.startswith("mb|"):
                bids = re.findall(r"mb\|([^|]+)\|", line)
                for bid in bids:
                    player = player_order[player_index % 4]
                    current_bids.append((bid, player))
                    player_index += 1

            # First card played
            elif line.startswith("pc|") and "first_card" not in current_board:
                m = re.search(r"pc\|([^|]+)\|", line)
                if m:
                    current_board["first_card"] = m.group(1)
                    print("current board inside first card", current_board)

            # Tricks
            elif line.startswith("mc|"):
                m = re.search(r"mc\|(\d+)\|", line)
                if m:
                    current_board["tricks"] = int(m.group(1))
                    print("current board inside tricks", current_board)

        flush_board()

    # Write to CSV
    fieldnames = [
        "board", "north_hand", "east_hand", "south_hand", "west_hand",
        "declarer", "first_card", "tricks"
    ]
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(boards)

    print(f"Wrote {len(boards)} boards to {output_file}")

if __name__ == "__main__":
    main()
