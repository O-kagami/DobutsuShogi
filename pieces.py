from constants import *

def get_piece_moves(r, c, piece, board, turn):
    """特定の駒が動ける座標をリストで返す"""
    moves = []
    p_abs = abs(piece)
    directions = []
    
    if p_abs == LION:
        directions = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    elif p_abs == GIRAFFE:
        directions = [(-1,0),(1,0),(0,-1),(0,1)]
    elif p_abs == ELEPHANT:
        directions = [(-1,-1),(-1,1),(1,-1),(1,1)]
    elif p_abs == CHICK:
        directions = [(-1,0)] if piece > 0 else [(1,0)]
    elif p_abs == HEN:
        if piece > 0: # 先手
            directions = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1)]
        else: # 後手
            directions = [(-1,0),(1,0),(0,-1),(0,1),(1,-1),(1,1)]

    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        if 0 <= nr < 4 and 0 <= nc < 3:
            # 味方の駒がいない場所なら動ける
            if board[nr][nc] * turn <= 0:
                moves.append(('move', r, c, nr, nc))
    return moves