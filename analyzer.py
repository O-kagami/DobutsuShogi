import os
import gzip
import json
from constants import *

solved_db = None
DB_FILE = "solved_db.json.gz"

def load_db():
    global solved_db
    if os.path.exists(DB_FILE):
        try:
            with gzip.open(DB_FILE, "rt", encoding="utf-8") as f:
                solved_db = json.load(f)
        except Exception as e:
            print(f"❌ データベースのロード中にエラーが発生しました: {e}")
            solved_db = None

# 初期ロード
load_db()

# メモ化用の辞書
memo = {}

PIECE_TO_CHAR = {
    0: '.',
    1: 'L', 2: 'G', 3: 'E', 4: 'C', 5: 'H',
    -1: 'l', -2: 'g', -3: 'e', -4: 'c', -5: 'h'
}

def get_state_key(state):
    board_chars = []
    for r in range(4):
        for c in range(3):
            board_chars.append(PIECE_TO_CHAR[state.board[r][c]])
    board_str = "".join(board_chars)
    
    h1_str = f"{state.hand_p1.get(2,0)}{state.hand_p1.get(3,0)}{state.hand_p1.get(4,0)}"
    h2_str = f"{state.hand_p2.get(2,0)}{state.hand_p2.get(3,0)}{state.hand_p2.get(4,0)}"
    turn_str = "+" if state.turn == 1 else "-"
    
    return f"{board_str}_{h1_str}_{h2_str}_{turn_str}"

def solved_analysis(state):
    """
    完全解析データベースを用いて、現在の局面からの最善手順を返します。
    (評価値, 最善手順のリスト)
    ※戻り値のフォーマットは simple_analysis と同一にします。
    """
    if solved_db is None:
        return None
        
    key = get_state_key(state)
    if key not in solved_db:
        return None
        
    val, dist = solved_db[key]
    
    if state.decide_winner() != 0:
        return val, []
        
    path = []
    current = state
    visited_keys = {key}
    
    for _ in range(200):
        curr_key = get_state_key(current)
        if current.decide_winner() != 0:
            break
        curr_moves = current.get_legal_moves()
        if not curr_moves:
            break
            
        curr_candidates = []
        for m in curr_moves:
            ns = current.make_move(m)
            nk = get_state_key(ns)
            if nk in solved_db:
                nv, nd = solved_db[nk]
                curr_candidates.append((m, nv, nd, ns, nk))
                
        if not curr_candidates:
            break
            
        if current.turn == 1:
            curr_candidates.sort(
                key=lambda x: (1000 - x[2] if x[1] == 1 else (0 if x[1] == 0 else -1000 + x[2])),
                reverse=True
            )
        else:
            curr_candidates.sort(
                key=lambda x: (1000 - x[2] if x[1] == -1 else (0 if x[1] == 0 else -1000 + x[2])),
                reverse=True
            )
            
        best_cand = curr_candidates[0]
        if best_cand[4] in visited_keys:
            break
            
        m = best_cand[0]
        pt = abs(current.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        path.append((m, pt))
        
        visited_keys.add(best_cand[4])
        current = best_cand[3]
        
    return val, path

def simple_analysis(state, depth):
    """
    ミニマックス法による解析関数。
    (評価値, 最善手順のリスト) を返します。
    """
    # 1. ベースケース：千日手(2回繰り返し)なら引き分け
    if state.is_repetition():
        return 0, []

    # 2. 勝敗判定（キャッチ・トライ）
    winner = state.decide_winner()
    if winner != 0:
        return winner, []

    # 3. 合法手を取得
    moves = state.get_legal_moves()
    
    # 💡 指せる手がない（詰み）なら、手番側の負け
    if not moves:
        return -state.turn, []

    # メモ化のチェック（盤面、手番、深さをキーにする）
    board_key = (tuple(tuple(r) for r in state.board), state.turn, depth)
    # ※手順を正確に作り直すため、ここでは評価値だけを利用するのではなく、探索を行います。

    if state.turn == 1: # 先手番（最大化）
        best_value = -float('inf')
        best_path = []
        for m in moves:
            # 駒の種類の特定
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            
            next_state = state.make_move(m)
            if depth > 0:
                res, path = simple_analysis(next_state, depth - 1)
            else:
                res = next_state.decide_winner()
                path = []

            if res > best_value:
                best_value = res
                best_path = [(m, p_type)] + path
            
            if best_value == 1: # 勝利確定なら枝刈り
                break
    else: # 後手番（最小化）
        best_value = float('inf')
        best_path = []
        for m in moves:
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            
            next_state = state.make_move(m)
            if depth > 0:
                res, path = simple_analysis(next_state, depth - 1)
            else:
                res = next_state.decide_winner()
                path = []

            if res < best_value:
                best_value = res
                best_path = [(m, p_type)] + path
            
            if best_value == -1: # 勝利確定なら枝刈り
                break

    return best_value, best_path