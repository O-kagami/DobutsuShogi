"""
State utility functions for Dobutsu Shogi.
Operates on lightweight tuple representations of game states to maximize performance.
"""

from typing import Tuple, List, Union

# Board representation is a 4x3 tuple/list of ints
BoardType = Union[Tuple[Tuple[int, ...], ...], List[List[int]]]
# Hand representation is a 3-tuple/list of ints: (GIRAFFE, ELEPHANT, CHICK)
HandType = Union[Tuple[int, int, int], List[int]]
# State tuple is (board, hand1, hand2, turn)
StateTupleType = Tuple[BoardType, HandType, HandType, int]

PIECE_TO_VAL = {
    0: 0,
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5,       # P1 (LION, GIRAFFE, ELEPHANT, CHICK, HEN)
    -1: 6, -2: 7, -3: 8, -4: 9, -5: 10   # P2 (LION, GIRAFFE, ELEPHANT, CHICK, HEN)
}

def pack_state_raw(state: StateTupleType) -> int:
    """
    Packs a state tuple into a single 64-bit integer.
    """
    board, hand1, hand2, turn = state
    packed = 0
    i = 0
    for row in board:
        for piece in row:
            packed |= (PIECE_TO_VAL[piece] << i)
            i += 4
    packed |= (hand1[0] << 48)
    packed |= (hand1[1] << 50)
    packed |= (hand1[2] << 52)
    packed |= (hand2[0] << 54)
    packed |= (hand2[1] << 56)
    packed |= (hand2[2] << 58)
    if turn == 1:
        packed |= (1 << 60)
    return packed

def get_symmetric_state(state: StateTupleType) -> StateTupleType:
    """
    Returns the horizontally reflected symmetric state of the given state.
    """
    board, hand1, hand2, turn = state
    sym_board = tuple(
        (row[2], row[1], row[0]) for row in board
    )
    return (sym_board, hand1, hand2, turn)

def get_canonical_state(state: StateTupleType) -> StateTupleType:
    """
    Returns the canonical (normalized) state by choosing the one with the
    smaller packed raw value between the state and its symmetric reflection.
    """
    sym_state = get_symmetric_state(state)
    if pack_state_raw(state) <= pack_state_raw(sym_state):
        return state
    else:
        return sym_state

def get_active_perspective_state(state: StateTupleType) -> StateTupleType:
    """
    Flips the board perspective if it is Player 2's turn, so that the player
    whose turn it is always plays from Player 1's perspective (turn=1).
    """
    board, hand1, hand2, turn = state
    if turn == 1:
        return state
    # Flip board vertically and invert pieces to see from P1's perspective:
    flipped_board = tuple(
        tuple(-board[3 - r][c] for c in range(3))
        for r in range(4)
    )
    return (flipped_board, hand2, hand1, 1)

def state_to_key(state: StateTupleType) -> str:
    """
    Converts a state tuple to a canonical, normalized string key (15-char hex).
    """
    normalized = get_canonical_state(get_active_perspective_state(state))
    packed = pack_state_raw(normalized) & ((1 << 60) - 1)
    return f"{packed:015x}"
