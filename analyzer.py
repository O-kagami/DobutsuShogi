from constants import *

# メモ化用の辞書
memo = {}

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