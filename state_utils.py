"""
State utility functions for Dobutsu Shogi.
Operates on lightweight tuple representations of game states to maximize performance.
Optimized with Numba JIT.
"""

from typing import Tuple, List, Union
import numpy as np
from numba import njit

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

# 高速ルックアップ用のリスト (-5 から 5 までの値を 0 から 10 にマッピング)
# Numbaからアクセス可能なnumpy配列として定義
PIECE_TO_VAL_LST = np.array([0, 6, 7, 8, 9, 10, 0, 1, 2, 3, 4, 5], dtype=np.int8)

@njit
def pack_state_raw(state: StateTupleType) -> int:
    """
    Packs a state tuple into a single 64-bit integer. (Optimized with Numba)
    """
    board, hand1, hand2, turn = state
    r0, r1, r2, r3 = board
    
    # -5 から 5 までの値を 0 から 10 にマッピング (インデックスは + 5)
    p0 = PIECE_TO_VAL_LST[r0[0] + 5]
    p1 = PIECE_TO_VAL_LST[r0[1] + 5]
    p2 = PIECE_TO_VAL_LST[r0[2] + 5]
    
    p3 = PIECE_TO_VAL_LST[r1[0] + 5]
    p4 = PIECE_TO_VAL_LST[r1[1] + 5]
    p5 = PIECE_TO_VAL_LST[r1[2] + 5]
    
    p6 = PIECE_TO_VAL_LST[r2[0] + 5]
    p7 = PIECE_TO_VAL_LST[r2[1] + 5]
    p8 = PIECE_TO_VAL_LST[r2[2] + 5]
    
    p9 = PIECE_TO_VAL_LST[r3[0] + 5]
    p10 = PIECE_TO_VAL_LST[r3[1] + 5]
    p11 = PIECE_TO_VAL_LST[r3[2] + 5]
    
    packed = (p0 | (p1 << 4) | (p2 << 8) |
              (p3 << 12) | (p4 << 16) | (p5 << 20) |
              (p6 << 24) | (p7 << 28) | (p8 << 32) |
              (p9 << 36) | (p10 << 40) | (p11 << 44))
              
    packed |= (hand1[0] << 48)
    packed |= (hand1[1] << 50)
    packed |= (hand1[2] << 52)
    packed |= (hand2[0] << 54)
    packed |= (hand2[1] << 56)
    packed |= (hand2[2] << 58)
    if turn == 1:
        packed |= (1 << 60)
    return packed

@njit
def get_symmetric_state(state: StateTupleType) -> StateTupleType:
    """
    Returns the horizontally reflected symmetric state of the given state. (Optimized with Numba)
    """
    board, hand1, hand2, turn = state
    r0, r1, r2, r3 = board
    
    sym_board = (
        (r0[2], r0[1], r0[0]),
        (r1[2], r1[1], r1[0]),
        (r2[2], r2[1], r2[0]),
        (r3[2], r3[1], r3[0])
    )
    return (sym_board, hand1, hand2, turn)

@njit
def get_canonical_state(state: StateTupleType) -> StateTupleType:
    """
    Returns the canonical (normalized) state by choosing the one with the
    smaller packed raw value between the state and its symmetric reflection. (Optimized with Numba)
    """
    sym_state = get_symmetric_state(state)
    if pack_state_raw(state) <= pack_state_raw(sym_state):
        return state
    else:
        return sym_state

@njit
def get_active_perspective_state(state: StateTupleType) -> StateTupleType:
    """
    Flips the board perspective if it is Player 2's turn, so that the player
    whose turn it is always plays from Player 1's perspective (turn=1). (Optimized with Numba)
    """
    board, hand1, hand2, turn = state
    if turn == 1:
        return state
        
    r0, r1, r2, r3 = board
    flipped_board = (
        (-r3[0], -r3[1], -r3[2]),
        (-r2[0], -r2[1], -r2[2]),
        (-r1[0], -r1[1], -r1[2]),
        (-r0[0], -r0[1], -r0[2])
    )
    return (flipped_board, hand2, hand1, 1)

# state_to_key自体はJIT化せずPythonラッパーのままにしておく（文字列フォーマット処理を含むため）
def state_to_key(state: StateTupleType) -> str:
    """
    Converts a state tuple to a canonical, normalized string key (15-char hex).
    """
    normalized = get_canonical_state(get_active_perspective_state(state))
    packed = pack_state_raw(normalized) & ((1 << 60) - 1)
    return f"{packed:015x}"
