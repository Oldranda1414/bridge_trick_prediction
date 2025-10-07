#!/usr/bin/env python3
"""
Parse the bridge match text format and extract per-board rows into CSV.

Extracted fields per row:
 - board
 - north_hand, east_hand, south_hand, west_hand
 - declarer (N/E/S/W)  -- determined from bidding using the correct dealer rotation
 - final_contract       -- the last non-pass level/suit bid (e.g. 4S, 6NTx, 2C!)
 - first_card           -- the very first played card (first pc tag encountered)
 - tricks               -- integer from mc|...|

This version DOES NOT assume that tags are at the start of lines and supports
multiple tags on the same line. It also correctly handles cases where bids
appear before the md (deal) tag by buffering unassigned bids and assigning
players once the dealer is known.

Usage:
    python bridge_parser_to_csv.py input.txt output.csv

"""

import csv
import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"([a-z]{1,3})\|([^|]*)\|", re.IGNORECASE)
BASE_ORDER = ["N", "E", "S", "W"]


def rotated_players(start_index: int):
    return BASE_ORDER[start_index:] + BASE_ORDER[:start_index]


def parse_file(infile_path):
    boards = []

    current_board = {}
    # assigned bids: list of (bid_str, player)
    bids_with_players = []
    # unassigned bids (strings) when dealer/player order not known yet
    unassigned_bids = []
    player_order = None

    def flush_board():
        nonlocal current_board, bids_with_players, unassigned_bids, player_order
        if not current_board:
            return

        # If dealer known now, assign any buffered bids
        if player_order is not None and unassigned_bids:
            for i, bid in enumerate(unassigned_bids):
                assigned_player = player_order[(len(bids_with_players) + i) % 4]
                bids_with_players.append((bid, assigned_player))
            unassigned_bids.clear()

        # Determine declarer and final_contract (last bid that starts with a digit)
        declarer = None
        final_contract = None
        for bid, player in reversed(bids_with_players):
            if re.match(r"^\d", bid):
                declarer = player
                final_contract = bid
                break

        if declarer is not None:
            current_board["declarer"] = declarer
            current_board["final_contract"] = final_contract

        # Only append boards that have the minimal data requested
        if "north_hand" in current_board and "tricks" in current_board:
            boards.append(current_board.copy())

        # reset board-level state
        current_board = {}
        bids_with_players = []
        unassigned_bids = []

    # Open and parse
    with open(infile_path, "r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")

            for m in TAG_RE.finditer(line):
                tag = m.group(1).lower()
                val = m.group(2)

                if tag == "qx":
                    # new board -- flush previous
                    flush_board()
                    # start new board
                    current_board = {}
                    bids_with_players = []
                    unassigned_bids = []
                    player_order = None

                    current_board["board"] = val

                elif tag == "md":
                    full_md = val.strip()
                    # md may start with dealer code 1-4
                    dm = re.match(r"^([1-4])(.*)$", full_md)
                    if dm:
                        dealer_code = int(dm.group(1))
                        hands_str = dm.group(2)
                        player_order = rotated_players(dealer_code - 1)
                    else:
                        hands_str = full_md

                    # split into 4 hands (N,E,S,W ordering in file)
                    hands = [h.strip() for h in hands_str.split(",") if h.strip() != ""]
                    if len(hands) == 4:
                        current_board["north_hand"] = hands[0]
                        current_board["east_hand"] = hands[1]
                        current_board["south_hand"] = hands[2]
                        current_board["west_hand"] = hands[3]

                    # if we just discovered player_order, assign buffered bids
                    if player_order is not None and unassigned_bids:
                        for i, bid in enumerate(unassigned_bids):
                            assigned_player = player_order[(len(bids_with_players) + i) % 4]
                            bids_with_players.append((bid, assigned_player))
                        unassigned_bids.clear()

                elif tag == "mb":
                    bid = val.strip()
                    if not bid:
                        continue
                    if player_order is None:
                        unassigned_bids.append(bid)
                    else:
                        assigned_player = player_order[len(bids_with_players) % 4]
                        bids_with_players.append((bid, assigned_player))

                elif tag == "pc":
                    card = val.strip()
                    if card and "first_card" not in current_board:
                        current_board["first_card"] = card

                elif tag == "mc":
                    num = val.strip()
                    try:
                        current_board["tricks"] = int(num)
                    except ValueError:
                        # ignore malformed
                        pass

                # other tags are ignored for this extraction

    # EOF flush
    flush_board()
    return boards


def write_csv(rows, outpath):
    fieldnames = [
        "board",
        "north_hand",
        "east_hand",
        "south_hand",
        "west_hand",
        "declarer",
        "final_contract",
        "first_card",
        "tricks",
    ]
    with open(outpath, "w", newline="", encoding="utf-8") as ofh:
        writer = csv.DictWriter(ofh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            # ensure all keys present (empty string if missing)
            out = {k: r.get(k, "") for k in fieldnames}
            writer.writerow(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python bridge_parser_to_csv.py input.txt output.csv")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Input file does not exist: {input_path}")
        sys.exit(2)

    rows = parse_file(input_path)
    write_csv(rows, output_path)
    print(f"Wrote {len(rows)} boards to {output_path}")
