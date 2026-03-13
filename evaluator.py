from constants import *

def evaluate_board(state):
    """位置ボーナスと駒の価値を組み合わせた高度な評価"""
    score = 0
    # 盤面の駒評価
    for r in range(4):
        for c in range(3):
            p = state.board[r][c]
            if p == EMPTY: continue
            
            val = PIECE_SCORES.get(abs(p), 0)
            # 位置ボーナス（先手はそのまま、後手は盤面を反転して計算）
            pos_r = r if p > 0 else (3 - r)
            b = POSITION_BONUS[pos_r][c]
            
            if p > 0:
                score += (val + b)
            else:
                score -= (val + b)
                
    # 持ち駒評価
    for p, count in state.hand_p1.items():
        score += PIECE_SCORES.get(p, 0) * count
    for p, count in state.hand_p2.items():
        score -= PIECE_SCORES.get(p, 0) * count
        
    return score