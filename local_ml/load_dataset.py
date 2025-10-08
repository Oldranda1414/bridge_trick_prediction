# bridge_onehot_loader.py
import re
from typing import List, Tuple, Dict
import numpy as np
import pandas as pd

# ---- constants ----
SUITS = ['S', 'H', 'D', 'C']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
ALL_CARDS = [s + r for s in SUITS for r in RANKS]  # order: S2..SA, H2..HA, D2..DA, C2..CA
CARD_TO_IDX: Dict[str, int] = {card: i for i, card in enumerate(ALL_CARDS)}

# mapping for seat names in CSV -> partner grouping
SEAT_NAMES = ['south', 'west', 'north', 'east']

# function to get the opposite partnership given owner's seat:
# if owner is 'south' or 'north' => the other pair is ['west','east']
# if owner is 'west' or 'east' => other pair is ['south','north']
OPPOSITE_PAIR = {
    'south': ['west', 'east'],
    'north': ['west', 'east'],
    'west':  ['south', 'north'],
    'east':  ['south', 'north'],
}

# mapping circular table: each player -> player to their right
RIGHT_OF = {
    'south': 'west',  # to the right of South is West
    'west':  'north',
    'north': 'east',
    'east':  'south',
}

# mapping from each player to their partner (across the table)
PARTNER = {
    'south': 'north',
    'north': 'south',
    'east':  'west',
    'west':  'east',
}

# ---- parsing utilities ----
def strip_leading_int(s: str) -> str:
    """Remove leading integer(s) if present (e.g. '3S2HA...' -> 'S2HA...')."""
    return re.sub(r'^\d+', '', s)

def parse_hand(hand_str: str) -> List[str]:
    """
    Parse a hand string like "3S2HA76DAQT84CQ875" (or "S2HA76..." without the leading integer)
    into a list of card codes like ["S2", "HA", "S7", ...] (actual order will be suit-block order).
    """
    if not isinstance(hand_str, str) or hand_str.strip() == '':
        return []
    s = strip_leading_int(hand_str.strip().upper())
    cards = []
    current_suit = None
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in SUITS:
            current_suit = ch
            i += 1
            # consume subsequent rank characters until next suit or end
            while i < len(s) and s[i] not in SUITS:
                rank = s[i]
                # Sanity: only allow known rank characters
                if rank not in RANKS:
                    raise ValueError(f"Unexpected rank character '{rank}' in hand string: {hand_str}")
                cards.append(current_suit + rank)
                i += 1
        else:
            # Found a rank without an explicit suit first: this is malformed input
            # but it can happen if input isn't separated nicely. We'll be strict and error.
            raise ValueError(f"Malformed hand string at position {i}: '{hand_str}' (char '{ch}')")
    return cards

def one_hot_cards(cards: List[str]) -> np.ndarray:
    """Return a 52-dim binary vector for the given list of card codes."""
    vec = np.zeros(len(ALL_CARDS), dtype=np.float32)
    for c in cards:
        if c not in CARD_TO_IDX:
            raise ValueError(f"Unknown card code '{c}'")
        vec[CARD_TO_IDX[c]] = 1.0
    return vec

def one_hot_card(card: str) -> np.ndarray:
    """One-hot encode a single card code (e.g., 'H9')."""
    vec = np.zeros(len(ALL_CARDS), dtype=np.float32)
    u = card.strip().upper()
    if u not in CARD_TO_IDX:
        raise ValueError(f"Unknown first_card '{card}'")
    vec[CARD_TO_IDX[u]] = 1.0
    return vec

# ---- high-level loader ----
def encode_row_to_input(row: pd.Series) -> Tuple[np.ndarray, int]:
    """
    Given a DataFrame row with columns:
        south_hand, west_hand, north_hand, east_hand, first_card, tricks
    Parse and return (x_vector, y_tricks).

    x_vector: [bidding_player_hand(52), partner_hand(52), first_card(52)]
      - bidding player = player to the RIGHT of first-card owner
      - partner = player opposite bidding player
    """
    # parse all hands
    hands_raw = {
        'south': row['south_hand'],
        'west':  row['west_hand'],
        'north': row['north_hand'],
        'east':  row['east_hand'],
    }
    parsed = {seat: parse_hand(h) for seat, h in hands_raw.items()}

    # find who played the first card
    first_card = str(row['first_card']).strip().upper()
    owner = None
    for seat in SEAT_NAMES:
        if first_card in parsed[seat]:
            owner = seat
            break
    if owner is None:
        raise ValueError(f"first_card '{first_card}' not found in any hand for row: {row.to_dict()}")

    # determine bidding player (to the right of first_card owner)
    bidding_player = RIGHT_OF[owner]
    partner = PARTNER[bidding_player]

    # encode
    hand_bidding = one_hot_cards(parsed[bidding_player])
    hand_partner = one_hot_cards(parsed[partner])
    first_card_vec = one_hot_card(first_card)

    # concatenate into single vector
    x = np.concatenate([hand_bidding, hand_partner, first_card_vec])
    y = int(row['tricks'])
    return x, y

def load_csv_to_dataset(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load the CSV file at `path` and return (X, y).
    X shape: (N, 156)
    y shape: (N,)
    """
    df = pd.read_csv(path)
    xs = []
    ys = []
    for idx, row in df.iterrows():
        try:
            x, y = encode_row_to_input(row)
            xs.append(x)
            ys.append(y)
        except Exception as e:
            # You may prefer to log or collect bad rows rather than stop.
            # For now we'll raise so you see problematic rows immediately.
            raise RuntimeError(f"Error processing row {idx}: {e}") from e

    X = np.vstack(xs).astype(np.float32)
    y = np.array(ys, dtype=np.int32)
    return X, y

def simple_test():
    example = {
        "south_hand": "3S2HA76DAQT84CQ875",
        "west_hand": "SAT984HQT542D93C2",
        "north_hand": "S753H9DK7652CJT93",
        "east_hand": "SKQJ6HKJ83DJCAK64",
        "first_card": "h9",
        "tricks": 9,
    }

    row = pd.Series(example)
    x, y = encode_row_to_input(row)

    print("Vector length:", len(x))  # should be 156
    print("Ones count:", x.sum())    # 13 + 13 + 1 = 27

# ---- example usage ----
if __name__ == "__main__":
    path = "bridge_data.csv"
    X, y = load_csv_to_dataset(path)
    print("Loaded dataset shapes:", X.shape, y.shape)
    print("Sample X row (sum counts):", X[0].sum())  # should usually be 13+13+1=27

    simple_test()

