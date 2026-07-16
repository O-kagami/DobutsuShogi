import os
import gzip
import json
from constants import *
from state_utils import state_to_key

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

def get_state_key(state):
    """
    DobutsuShogiState オブジェクトをシリアライズ可能な状態タプルに変換し、
    一意の正規化された状態キー（15文字の16進数文字列）を生成します。
    """
    board_tuple = tuple(tuple(row) for row in state.board)
    h1 = (state.hand_p1.get(2, 0), state.hand_p1.get(3, 0), state.hand_p1.get(4, 0))
    h2 = (state.hand_p2.get(2, 0), state.hand_p2.get(3, 0), state.hand_p2.get(4, 0))
    state_tuple = (board_tuple, h1, h2, state.turn)
    return state_to_key(state_tuple)

def get_db_value(state):
    if solved_db is None:
        return None
    key = get_state_key(state)
    if key not in solved_db:
        return None
    val, dist = solved_db[key]
    if state.turn == -1 and val != 0:
        val = -val
    return val, dist

def solved_analysis(state):
    """
    完全解析データベースを用いて、現在の局面からの最善手順を返します。
    (評価値, 最善手順のリスト)
    ※戻り値のフォーマットは simple_analysis と同一にします。
    """
    db_res = get_db_value(state)
    if db_res is None:
        return None
        
    val, dist = db_res
    if state.decide_winner() != 0:
        return val, []
        
    path = []
    current = state
    key = get_state_key(state)
    visited_keys = {key}
    
    for _ in range(200):
        if current.decide_winner() != 0:
            break
        curr_moves = current.get_legal_moves()
        if not curr_moves:
            break
            
        curr_candidates = []
        for m in curr_moves:
            ns = current.make_move(m)
            db_res = get_db_value(ns)
            if db_res is not None:
                nv, nd = db_res
                nk = get_state_key(ns)
                curr_candidates.append((m, nv, nd, ns, nk))
                
        if not curr_candidates:
            break
            
        # 手番側の視点からの評価値と距離に基づいて候補手をソート
        moving_player = current.turn
        def get_sort_key(candidate):
            # candidate = (move, nv, nd, ns, nk)
            _, nv, nd, _, _ = candidate
            perspective_val = nv * moving_player
            if perspective_val == 1:
                return 1000 - nd
            elif perspective_val == 0:
                return 0
            else:
                return -1000 + nd

        curr_candidates.sort(key=get_sort_key, reverse=True)
            
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

    # メモ化のチェック
    key = (state.current_state_key, depth)
    if key in memo:
        return memo[key]

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

    memo[key] = (best_value, best_path)
    return best_value, best_path