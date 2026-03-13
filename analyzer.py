from constants import *
from evaluator import evaluate_board
from move_orderer import get_ordered_moves

def simple_analysis(state, depth, alpha=-float('inf'), beta=float('inf')):
    winner = state.decide_winner()
    if winner != 0:
        return winner * AI_SETTINGS["MAX_SCORE"], []
    
    # 詰みチェック（並び替え済みの手を取得）
    moves = get_ordered_moves(state)
    if not moves:
        return -state.turn * AI_SETTINGS["MAX_SCORE"], []

    if depth == 0:
        return evaluate_board(state), []
    
    if state.is_repetition():
        return 0, []

    best_path = []
    if state.turn == 1:
        best_value = -float('inf')
        for m in moves:
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_state = state.make_move(m)
            res, path = simple_analysis(next_state, depth - 1, alpha, beta)
            if res > best_value:
                best_value, best_path = res, [(m, p_type)] + path
            alpha = max(alpha, best_value)
            if alpha >= beta: break
        return best_value, best_path
    else:
        best_value = float('inf')
        for m in moves:
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_state = state.make_move(m)
            res, path = simple_analysis(next_state, depth - 1, alpha, beta)
            if res < best_value:
                best_value, best_path = res, [(m, p_type)] + path
            beta = min(beta, best_value)
            if alpha >= beta: break
        return best_value, best_path