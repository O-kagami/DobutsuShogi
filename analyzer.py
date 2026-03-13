from constants import *
from evaluator import evaluate_board
from move_orderer import get_ordered_moves
import time


def simple_analysis(state, depth, alpha=-float('inf'), beta=float('inf')):
    winner = state.decide_winner()
    if winner == DRAW:
        return 0, []
    if winner != 0:
        return winner * AI_SETTINGS["MAX_SCORE"], []
    
    # 詰みチェック（並び替え済みの手を取得）
    moves = get_ordered_moves(state)
    if not moves:
        return -state.turn * AI_SETTINGS["MAX_SCORE"], []

    if depth == 0:
        return evaluate_board(state), []
    
    # 途中局面での千日手は引き分け扱い
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
            if alpha >= beta:
                break
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
            if alpha >= beta:
                break
        return best_value, best_path


def _timed_search(state, depth, deadline, alpha=-float('inf'), beta=float('inf')):
    """時間制限付きのミニマックス（アルファベータ）"""
    if time.time() > deadline:
        raise TimeoutError

    winner = state.decide_winner()
    if winner == DRAW:
        return 0, []
    if winner != 0:
        return winner * AI_SETTINGS["MAX_SCORE"], []

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
            if time.time() > deadline:
                raise TimeoutError
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_state = state.make_move(m)
            res, path = _timed_search(next_state, depth - 1, deadline, alpha, beta)
            if res > best_value:
                best_value, best_path = res, [(m, p_type)] + path
            alpha = max(alpha, best_value)
            if alpha >= beta:
                break
        return best_value, best_path
    else:
        best_value = float('inf')
        for m in moves:
            if time.time() > deadline:
                raise TimeoutError
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_state = state.make_move(m)
            res, path = _timed_search(next_state, depth - 1, deadline, alpha, beta)
            if res < best_value:
                best_value, best_path = res, [(m, p_type)] + path
            beta = min(beta, best_value)
            if alpha >= beta:
                break
        return best_value, best_path


def time_limited_analysis(state, max_time_sec):
    """時間で探索量を制限した反復深化探索"""
    start = time.time()
    deadline = start + max_time_sec
    best_value = None
    best_path = []

    max_depth = AI_SETTINGS.get("DEPTH", 5)
    depth = 1
    while depth <= max_depth:
        try:
            value, path = _timed_search(state, depth, deadline)
            best_value, best_path = value, path
            depth += 1
        except TimeoutError:
            break

        if time.time() >= deadline:
            break

    if best_value is None:
        # まったく読めなかった場合は静的評価にフォールバック
        return evaluate_board(state), []

    return best_value, best_path