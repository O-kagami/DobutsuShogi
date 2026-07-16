import gzip
import json
from collections import deque
import time
from tqdm import tqdm

# 駒の定義
EMPTY = 0
LION, GIRAFFE, ELEPHANT, CHICK, HEN = 1, 2, 3, 4, 5

PIECE_TO_CHAR = {
    0: '.',
    1: 'L', 2: 'G', 3: 'E', 4: 'C', 5: 'H',
    -1: 'l', -2: 'g', -3: 'e', -4: 'c', -5: 'h'
}
CHAR_TO_PIECE = {v: k for k, v in PIECE_TO_CHAR.items()}

from state_utils import (
    PIECE_TO_VAL,
    pack_state_raw,
    get_symmetric_state,
    get_canonical_state,
    get_active_perspective_state,
    state_to_key
)

def get_piece_moves_light(r, c, piece, board, turn):
    p_abs = abs(piece)
    if p_abs == LION:
        dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    elif p_abs == GIRAFFE:
        dirs = [(-1,0),(1,0),(0,-1),(0,1)]
    elif p_abs == ELEPHANT:
        dirs = [(-1,-1),(-1,1),(1,-1),(1,1)]
    elif p_abs == CHICK:
        dirs = [(-1,0)] if piece > 0 else [(1,0)]
    elif p_abs == HEN:
        if piece > 0: # 先手
            dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1)]
        else: # 後手
            dirs = [(-1,0),(1,0),(0,-1),(0,1),(1,-1),(1,1)]
    else:
        return []

    moves = []
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        if 0 <= nr < 4 and 0 <= nc < 3:
            if board[nr][nc] * turn <= 0:
                moves.append(('move', r, c, nr, nc))
    return moves

def is_check_light(board, turn):
    # turn側のライオンの座標を探す
    lr, lc = -1, -1
    for r in range(4):
        for c in range(3):
            if board[r][c] == LION * turn:
                lr, lc = r, c
                break
        if lr != -1:
            break
            
    if lr == -1:
        return False

    enemy = -turn
    # ライオンの周囲8マスを調べる (スライド駒がないため、王手は隣接マスからのみ発生する)
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        er, ec = lr + dr, lc + dc
        if 0 <= er < 4 and 0 <= ec < 3:
            piece = board[er][ec]
            if piece * enemy > 0:
                p_abs = abs(piece)
                tr, tc = -dr, -dc # 敵からライオンへの相対座標
                
                if p_abs == LION:
                    return True
                elif p_abs == GIRAFFE:
                    if (abs(tr) == 1 and tc == 0) or (tr == 0 and abs(tc) == 1):
                        return True
                elif p_abs == ELEPHANT:
                    if abs(tr) == 1 and abs(tc) == 1:
                        return True
                elif p_abs == CHICK:
                    if piece == CHICK: # 先手ひよこ
                        if tr == -1 and tc == 0:
                            return True
                    else: # 後手ひよこ
                        if tr == 1 and tc == 0:
                            return True
                elif p_abs == HEN:
                    if piece > 0: # 先手金
                        if (tr, tc) in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1)]:
                            return True
                    else: # 後手金
                        if (tr, tc) in [(-1,0), (1,0), (0,-1), (0,1), (1,-1), (1,1)]:
                            return True
    return False

def can_capture_enemy_lion(state):
    board, hand1, hand2, turn = state
    enemy_lion = -turn * LION
    el_pos = None
    for r in range(4):
        for c in range(3):
            if board[r][c] == enemy_lion:
                el_pos = (r, c)
                break
        if el_pos:
            break
            
    if el_pos is None:
        return True
        
    for r in range(4):
        for c in range(3):
            piece = board[r][c]
            if piece * turn > 0:
                moves = get_piece_moves_light(r, c, piece, board, turn)
                for m in moves:
                    if (m[3], m[4]) == el_pos:
                        return True
    return False

def decide_winner_light(state):
    board, hand1, hand2, turn = state
    
    # 1. 勝ち確定局面の判定 (手番のプレイヤーが敵のライオンを捕まえられる)
    if can_capture_enemy_lion(state):
        return turn
        
    # 2. 負け確定局面の判定 (敵のライオンが自陣にいる)
    enemy_lion = -turn * LION
    own_home_row = 3 if turn == 1 else 0
    for c in range(3):
        if board[own_home_row][c] == enemy_lion:
            return -turn
            
    return 0

def make_move_light(state, move):
    board, hand1, hand2, turn = state
    new_board = [list(row) for row in board]
    new_hand1 = list(hand1)
    new_hand2 = list(hand2)

    if move[0] == 'move':
        _, fr, fc, tr, tc = move
        piece = new_board[fr][fc]
        target = new_board[tr][tc]
        
        if target != EMPTY:
            captured = abs(target)
            if captured == HEN:
                captured = CHICK
            if captured != LION:
                idx = captured - 2 # GIRAFFE(2)->0, ELEPHANT(3)->1, CHICK(4)->2
                if turn == 1:
                    new_hand1[idx] += 1
                else:
                    new_hand2[idx] += 1
                    
        new_board[tr][tc] = piece
        new_board[fr][fc] = EMPTY
        
        # プロモーション
        if abs(piece) == CHICK:
            if (turn == 1 and tr == 0) or (turn == -1 and tr == 3):
                new_board[tr][tc] = HEN * turn

    elif move[0] == 'drop':
        _, p_type, tr, tc = move
        new_board[tr][tc] = p_type * turn
        idx = p_type - 2
        if turn == 1:
            new_hand1[idx] -= 1
        else:
            new_hand2[idx] -= 1

    board_tuple = tuple(tuple(row) for row in new_board)
    return (board_tuple, tuple(new_hand1), tuple(new_hand2), -turn)

def get_legal_moves_light(state):
    board, hand1, hand2, turn = state
    
    if decide_winner_light(state) != 0:
        return []

    # 💡 最適化：現在王手されているか
    in_check = is_check_light(board, turn)

    all_moves = []
    for r in range(4):
        for c in range(3):
            piece = board[r][c]
            if piece * turn > 0:
                all_moves.extend(get_piece_moves_light(r, c, piece, board, turn))
                
    hand = hand1 if turn == 1 else hand2
    for idx, count in enumerate(hand):
        if count > 0:
            p_type = idx + 2
            for r in range(4):
                for c in range(3):
                    if board[r][c] == EMPTY:
                        all_moves.append(('drop', p_type, r, c))

    legal_moves = []
    board_lst = [list(row) for row in board]
    for move in all_moves:
        if move[0] == 'move':
            _, fr, fc, tr, tc = move
            piece = board_lst[fr][fc]
            
            # 💡 最適化: 王手されていないなら、ライオン以外の移動で自殺手にならない
            if abs(piece) != LION and not in_check:
                legal_moves.append(move)
                continue
            
            orig_from = board_lst[fr][fc]
            orig_to = board_lst[tr][tc]
            
            board_lst[tr][tc] = orig_from
            board_lst[fr][fc] = EMPTY
            
            check = is_check_light(board_lst, turn)
            
            board_lst[fr][fc] = orig_from
            board_lst[tr][tc] = orig_to
            
            if not check:
                legal_moves.append(move)
        elif move[0] == 'drop':
            # 💡 打ち込みはライオンではないため、現在王手されていないならチェック不要
            if not in_check:
                legal_moves.append(move)
                continue
                
            _, p_type, tr, tc = move
            board_lst[tr][tc] = p_type * turn
            
            check = is_check_light(board_lst, turn)
            
            board_lst[tr][tc] = EMPTY
            
            if not check:
                legal_moves.append(move)
            
    return legal_moves

def solve():
    print("🐾 どうぶつ将棋 完全解析開始 (ウルトラ最適化版) 🐾")
    start_time = time.time()
    
    initial_board = (
        (-GIRAFFE, -LION, -ELEPHANT),
        (EMPTY, -CHICK, EMPTY),
        (EMPTY, CHICK, EMPTY),
        (ELEPHANT, LION, GIRAFFE)
    )
    initial_state = (initial_board, (0, 0, 0), (0, 0, 0), 1)
    
    # 1. 状態空間の列挙 (BFS)
    print("1. 状態空間の列挙中...")
    init_packed = pack_state_raw(initial_state)
    state_to_id = {init_packed: 0}
    id_to_state = [initial_state]
    queue = deque([0])
    next_ids = []
    
    pbar = tqdm(desc="  列挙済み", unit="局面")
    while queue:
        u_id = queue.popleft()
        u_state = id_to_state[u_id]
        
        legal_moves = get_legal_moves_light(u_state)
        u_nexts = []
        for m in legal_moves:
            next_state = make_move_light(u_state, m)
            packed_next = pack_state_raw(next_state)
            if packed_next not in state_to_id:
                next_id = len(id_to_state)
                state_to_id[packed_next] = next_id
                id_to_state.append(next_state)
                queue.append(next_id)
            else:
                next_id = state_to_id[packed_next]
            u_nexts.append(next_id)
            
        next_ids.append(u_nexts)
        pbar.update(1)
        pbar.set_postfix(discovered=len(id_to_state))
    pbar.close()

    N = len(id_to_state)
    print(f"  状態空間の列挙完了。総局面数: {N}")
    print(f"  時間: {time.time() - start_time:.2f}秒")
    
    # 2. 逆遷移 (prev_ids) の構築
    print("2. 逆遷移グラフの構築中...")
    prev_ids = [[] for _ in range(N)]
    for u in tqdm(range(N), desc="  グラフ構築", unit="局面"):
        for v in next_ids[u]:
            prev_ids[v].append(u)
            
    print(f"  時間: {time.time() - start_time:.2f}秒")

    # 3. 後退解析 (Retrograde Analysis)
    print("3. 後退解析の実行中...")
    V = [None] * N
    dist = [float('inf')] * N
    out_degree = [len(next_ids[u]) for u in range(N)]
    
    Q = deque()
    
    # 初期確定局面
    for u in range(N):
        state = id_to_state[u]
        winner = decide_winner_light(state)
        if winner != 0:
            V[u] = winner
            dist[u] = 0
            Q.append(u)
        elif out_degree[u] == 0:
            turn = state[3]
            V[u] = -turn
            dist[u] = 0
            Q.append(u)

    print(f"  初期確定局面数: {len(Q)}")
    
    pbar = tqdm(total=N, desc="  解析済み", unit="局面")
    pbar.update(len(Q))
    
    while Q:
        u = Q.popleft()
        
        val_u = V[u]
        dist_u = dist[u]
        
        for v in prev_ids[u]:
            if V[v] is not None:
                continue
                
            v_state = id_to_state[v]
            v_turn = v_state[3]
            
            if val_u == v_turn:
                V[v] = v_turn
                dist[v] = dist_u + 1
                Q.append(v)
                pbar.update(1)
            else:
                out_degree[v] -= 1
                if out_degree[v] == 0:
                    V[v] = -v_turn
                    max_d = 0
                    for w in next_ids[v]:
                        if dist[w] > max_d:
                            max_d = dist[w]
                    dist[v] = max_d + 1
                    Q.append(v)
                    pbar.update(1)

    pbar.close()

    print("  後退解析完了。未確定局面（引き分け）の処理中...")
    draw_count = 0
    win_p1 = 0
    win_p2 = 0
    for u in range(N):
        if V[u] is None:
            V[u] = 0
            dist[u] = 999
            draw_count += 1
        elif V[u] == 1:
            win_p1 += 1
        elif V[u] == -1:
            win_p2 += 1
            
    print(f"  解析結果: 先手勝ち={win_p1}, 後手勝ち={win_p2}, 引き分け={draw_count}")
    print(f"  時間: {time.time() - start_time:.2f}秒")
    
    # 初期局面の検証
    init_val = V[0]
    init_dist = dist[0]
    print(f"💡 初期局面の理論値: {'先手必勝' if init_val == 1 else '後手必勝' if init_val == -1 else '引き分け'} (手数: {init_dist})")
    
    # 4. データベースの保存
    print("4. データベースの保存中...")
    db = {}
    for u in tqdm(range(N), desc="  DB構築", unit="局面"):
        state = id_to_state[u]
        val = V[u]
        d = dist[u]
        
        turn = state[3]
        val_canonical = val * turn if val != 0 else 0
        
        key = state_to_key(state)
        db[key] = (val_canonical, d)
        
    db_file = "solved_db.json.gz"
    with gzip.open(db_file, "wt", encoding="utf-8") as f:
        json.dump(db, f)
        
    print(f"🎉 データベースを {db_file} に保存しました！(総キー数: {len(db)})")
    print(f"⏱️ 総実行時間: {time.time() - start_time:.2f}秒")

if __name__ == "__main__":
    solve()
