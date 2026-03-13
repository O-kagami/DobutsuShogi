from constants import *

def get_ordered_moves(state):
    moves = state.get_legal_moves()
    
    def move_priority(m):
        score = 0
        
        if m[0] == 'move':
            from_r, from_c, to_r, to_c = m[1], m[2], m[3], m[4]
            target_piece = state.board[to_r][to_c]
            my_piece = abs(state.board[from_r][from_c])
            
            # 1. 相手の駒を取る手 (MVV-LVA風)
            if target_piece != EMPTY:
                # 「取れる駒の価値」から「取る駒の価値」を引くことで、
                # 安い駒で高い駒を取る手を優先する
                score += 100 + (PIECE_SCORES.get(abs(target_piece), 0) // 10)
            
            # 2. 成る手を優先
            if my_piece == CHICK and ((state.turn == 1 and to_r == 0) or (state.turn == -1 and to_r == 3)):
                score += 50

        elif m[0] == 'drop':
            # 3. 持ち駒を打つ手は、盤面を埋めるため少しだけ優先度を下げる（移動を優先）
            score += 10
            
        return score
    
    # スコアが高い順にソート
    moves.sort(key=move_priority, reverse=True)
    return moves