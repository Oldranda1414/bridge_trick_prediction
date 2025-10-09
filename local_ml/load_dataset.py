# bridge_onehot_loader.py
import re
from typing import List, Tuple, Dict
import numpy as np
import pandas as pd

# ---- constants ----
SUITS = ['S', 'H', 'D', 'C']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
ALL_CARDS = [s + r for s in SUITS for r in RANKS]  # 52 cards
CARD_TO_IDX: Dict[str, int] = {card: i for i, card in enumerate(ALL_CARDS)}

# new: trumps
TRUMPS = ['S', 'H', 'D', 'C', 'NT']
TRUMP_TO_IDX = {t: i for i, t in enumerate(TRUMPS)}

# seat and partnership logic (unchanged)
SEAT_NAMES = ['south', 'west', 'north', 'east']
OPPOSITE_PAIR = {
    'south': ['west', 'east'],
    'north': ['west', 'east'],
    'west':  ['south', 'north'],
    'east':  ['south', 'north'],
}
RIGHT_OF = {
    'south': 'west',
    'west':  'north',
    'north': 'east',
    'east':  'south',
}
PARTNER = {
    'south': 'north',
    'north': 'south',
    'east':  'west',
    'west':  'east',
}

# ---- parsing utilities ----
def strip_leading_int(s: str) -> str:
    return re.sub(r'^\d+', '', s)

def parse_hand(hand_str: str) -> List[str]:
    if not isinstance(hand_str, str) or hand_str.strip() == '':
        return []
    s = strip_leading_int(hand_str.strip().upper())
    cards = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in SUITS:
            current_suit = ch
            i += 1
            while i < len(s) and s[i] not in SUITS:
                rank = s[i]
                if rank not in RANKS:
                    raise ValueError(f"Unexpected rank '{rank}' in hand string: {hand_str}")
                cards.append(current_suit + rank)
                i += 1
        else:
            raise ValueError(f"Malformed hand string '{hand_str}' at pos {i}")
    return cards

def one_hot_cards(cards: List[str]) -> np.ndarray:
    vec = np.zeros(len(ALL_CARDS), dtype=np.float32)
    for c in cards:
        vec[CARD_TO_IDX[c]] = 1.0
    return vec

def one_hot_card(card: str) -> np.ndarray:
    vec = np.zeros(len(ALL_CARDS), dtype=np.float32)
    c = card.strip().upper()
    if c not in CARD_TO_IDX:
        raise ValueError(f"Unknown card code '{card}'")
    vec[CARD_TO_IDX[c]] = 1.0
    return vec

def one_hot_trump(trump: str) -> np.ndarray:
    """One-hot encode trump (S,H,D,C,NT)."""
    vec = np.zeros(len(TRUMPS), dtype=np.float32)
    t = str(trump).strip().upper()
    if t not in TRUMP_TO_IDX:
        raise ValueError(f"Unknown trump '{trump}'")
    vec[TRUMP_TO_IDX[t]] = 1.0
    return vec

# ---- high-level encoding ----
def encode_row_to_input(row: pd.Series) -> Tuple[np.ndarray, int]:
    """
    Expected columns:
        south_hand, west_hand, north_hand, east_hand, first_card, tricks, trump
    Output:
        x_vector (shape 161), y_tricks (int)
    """
    # parse all hands
    hands_raw = {
        'south': row['south_hand'],
        'west':  row['west_hand'],
        'north': row['north_hand'],
        'east':  row['east_hand'],
    }
    parsed = {seat: parse_hand(h) for seat, h in hands_raw.items()}

    # find first card's owner
    first_card = str(row['first_card']).strip().upper()
    owner = None
    for seat in SEAT_NAMES:
        if first_card in parsed[seat]:
            owner = seat
            break
    if owner is None:
        raise ValueError(f"first_card '{first_card}' not found in any hand for row: {row.to_dict()}")

    bidding_player = RIGHT_OF[owner]
    partner = PARTNER[bidding_player]

    # encode
    hand_bidding = one_hot_cards(parsed[bidding_player])
    hand_partner = one_hot_cards(parsed[partner])
    first_card_vec = one_hot_card(first_card)
    trump_vec = one_hot_trump(row['trump'])

    # concat: (52 + 52 + 52 + 5) = 161
    x = np.concatenate([hand_bidding, hand_partner, first_card_vec, trump_vec])
    y = int(row['tricks'])
    return x, y

def load_csv_to_dataset(path: str) -> Tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    xs, ys = [], []
    skipped_rows = []

    for idx, row in df.iterrows():
        try:
            x, y = encode_row_to_input(row)
            xs.append(x)
            ys.append(y)
        except Exception as e:
            skipped_rows.append(idx)
            print(f"⚠ Skipping row {idx} due to error: {e}")
            continue  # just skip this row

    if len(skipped_rows) > 0:
        print(f"\nTotal skipped rows: {len(skipped_rows)}")
    
    X = np.vstack(xs).astype(np.float32)
    y = np.array(ys, dtype=np.int32)
    return X, y

# ---- testing ----
def simple_test():
    example = {
        "south_hand": "3S2HA76DAQT84CQ875",
        "west_hand": "SAT984HQT542D93C2",
        "north_hand": "S753H9DK7652CJT93",
        "east_hand": "SKQJ6HKJ83DJCAK64",
        "first_card": "h9",
        "tricks": 9,
        "trump": "S"
    }
    row = pd.Series(example)
    x, y = encode_row_to_input(row)
    print("Vector length:", len(x))   # should be 161
    print("Ones count:", x.sum())     # 13 + 13 + 1 + 1 = 28
    print("Trump slice (last 5):", x[-5:])

if __name__ == "__main__":
    path = "bridge_data.csv"
    X, y = load_csv_to_dataset(path)
    print("Loaded dataset shapes:", X.shape, y.shape)
    simple_test()
