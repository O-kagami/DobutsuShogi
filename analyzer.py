from constants import *

def evaluate_board(state):
    """盤面の有利・不利をPIECE_SCORESに基づいて計算（先手有利ならプラス）"""
    score = 0
    # 盤上の駒を計算
    for r in range(4):
        for c in range(3):
            p = state.board[r][c]
            if p != EMPTY:
                val = PIECE_SCORES.get(abs(p), 0)
                score += val if p > 0 else -val
                
    # 持ち駒を計算
    for p, count in state.hand_p1.items():
        score += PIECE_SCORES.get(p, 0) * count
    for p, count in state.hand_p2.items():
        score -= PIECE_SCORES.get(p, 0) * count
        
    return score

def simple_analysis(state, depth, alpha=-float('inf'), beta=float('inf')):
    """アルファ・ベータ法を用いた探索関数"""
    winner = state.decide_winner()
    if winner != 0:
        return winner * AI_SETTINGS["MAX_SCORE"], []

    if depth == 0:
        return evaluate_board(state), []

    if state.is_repetition():
        return 0, []

    moves = state.get_legal_moves()
    if not moves:
        # 指し手がない場合は詰み
        return -state.turn * AI_SETTINGS["MAX_SCORE"], []

    best_path = []

    if state.turn == 1: # 先手のターン（スコア最大化）
        best_value = -float('inf')
        for m in moves:
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_state = state.make_move(m)
            res, path = simple_analysis(next_state, depth - 1, alpha, beta)
            if res > best_value:
                best_value = res
                best_path = [(m, p_type)] + path
            alpha = max(alpha, best_value)
            if alpha >= beta: break
        return best_value, best_path
    else: # 後手のターン（スコア最小化）
        best_value = float('inf')
        for m in moves:
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_state = state.make_move(m)
            res, path = simple_analysis(next_state, depth - 1, alpha, beta)
            if res < best_value:
                best_value = res
                best_path = [(m, p_type)] + path
            beta = min(beta, best_value)
            if alpha >= beta: break
        return best_value, best_path