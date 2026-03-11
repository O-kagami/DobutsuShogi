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
    """勝敗判定（キャッチ・トライ・詰み）"""
    l1_pos, l2_pos = None, None
    for r in range(4):
        for c in range(3):
            if state.board[r][c] == LION: l1_pos = (r, c)
            elif state.board[r][c] == -LION: l2_pos = (r, c)

    # 1. キャッチ（ライオンが取られた）
    if l2_pos is None: return 1
    if l1_pos is None: return -1

    # 2. トライ（敵陣の最奥に到達し、かつ次の手で取られない）
    if l1_pos[0] == 0 and not is_check(state, 1): return 1
    if l2_pos[0] == 3 and not is_check(state, -1): return -1

    # 🌟 3. 動けない（詰み）の判定を追加
    # 現在の手番のプレイヤーに動かせる手（合法手）が一つもなければ、その人の負け
    if not state.get_legal_moves():
        return -state.turn # 先手(1)が動けなければ -1(後手勝ち)、逆なら 1

    return 0