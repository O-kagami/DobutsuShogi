from constants import *
from pieces import get_piece_moves

def is_check(state, turn):
    """指定した手番のライオンが狙われているか判定"""
    lion_pos = None
    for r in range(4):
        for c in range(3):
            if state.board[r][c] == LION * turn:
                lion_pos = (r, c)
                break
    
    if lion_pos is None: return False

    enemy_turn = -turn
    for r in range(4):
        for c in range(3):
            piece = state.board[r][c]
            if piece * enemy_turn > 0:
                # 相手の駒の動きをチェック
                moves = get_piece_moves(r, c, piece, state.board, enemy_turn)
                for m in moves:
                    # m = ('move', fr, fc, tr, tc) なので、インデックス 3, 4 が移動先
                    if (m[3], m[4]) == lion_pos:
                        return True
    return False

def decide_winner(state):
    """勝敗判定（新定義：勝ち確定局面と負け確定局面）"""
    # 千日手（引き分け）
    if getattr(state, "is_repetition", None) and state.is_repetition():
        return DRAW

    # 1. 勝ち確定局面の判定 (手番のプレイヤーが敵のライオンを捕まえられる)
    enemy_lion = -state.turn * LION
    el_pos = None
    for r in range(4):
        for c in range(3):
            if state.board[r][c] == enemy_lion:
                el_pos = (r, c)
                break
        if el_pos:
            break
            
    if el_pos is None:
        return state.turn

    for r in range(4):
        for c in range(3):
            piece = state.board[r][c]
            if piece * state.turn > 0:
                moves = get_piece_moves(r, c, piece, state.board, state.turn)
                for m in moves:
                    if (m[3], m[4]) == el_pos:
                        return state.turn

    # 2. 負け確定局面の判定 (敵のライオンが自陣にいる)
    own_home_row = 3 if state.turn == 1 else 0
    for c in range(3):
        if state.board[own_home_row][c] == enemy_lion:
            return -state.turn

    # 3. 動けない（詰み）の判定
    if not state.get_legal_moves():
        return -state.turn

    return 0