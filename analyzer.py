from constants import *

def evaluate_board(state):
    """位置ボーナスと駒の価値を組み合わせた高度な評価"""
    score = 0
    for r in range(4):
        for c in range(3):
            p = state.board[r][c]
            if p == EMPTY: continue
            
            val = PIECE_SCORES.get(abs(p), 0)    
    # 持ち駒評価
    for p, count in state.hand_p1.items():
        score += PIECE_SCORES.get(p, 0) * count
    for p, count in state.hand_p2.items():
        score -= PIECE_SCORES.get(p, 0) * count
        
    return score

def simple_analysis(state, depth, alpha=-float('inf'), beta=float('inf')):
    winner = state.decide_winner()
    if winner != 0:
        return winner * AI_SETTINGS["MAX_SCORE"], []
    
    # 指し手がない（詰み）のチェック
    moves = state.get_legal_moves()
    if not moves:
        return -state.turn * AI_SETTINGS["MAX_SCORE"], []

    if depth == 0:
        return evaluate_board(state), []
    
    if state.is_repetition():
        return 0, []

    # 🌟 指し手の並び替え（Move Ordering）
    # 駒を取る手を先に探索すると、αβ法の効率が劇的に上がります
    def move_priority(m):
        if m[0] == 'move' and state.board[m[3]][m[4]] != 0:
            return 100 # 駒を取る手を優先
        return 0
    
    moves.sort(key=move_priority, reverse=True)

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