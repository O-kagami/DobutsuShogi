import gzip
import json
from collections import deque
import time

# 駒の定義
EMPTY = 0
LION, GIRAFFE, ELEPHANT, CHICK, HEN = 1, 2, 3, 4, 5

PIECE_TO_CHAR = {
    0: '.',
    1: 'L', 2: 'G', 3: 'E', 4: 'C', 5: 'H',
    -1: 'l', -2: 'g', -3: 'e', -4: 'c', -5: 'h'
}
CHAR_TO_PIECE = {v: k for k, v in PIECE_TO_CHAR.items()}

def state_to_key(state):
    board, hand1, hand2, turn = state
    board_chars = []
    for r in range(4):
        for c in range(3):
            board_chars.append(PIECE_TO_CHAR[board[r][c]])
    board_str = "".join(board_chars)
    
    h1_str = "".join(str(x) for x in hand1)
    h2_str = "".join(str(x) for x in hand2)
    turn_str = "+" if turn == 1 else "-"
    
    return f"{board_str}_{h1_str}_{h2_str}_{turn_str}"

def key_to_state(key):
    parts = key.split('_')
    board_str, h1_str, h2_str, turn_str = parts
    
    board = []
    for r in range(4):
        row = []
        for c in range(3):
            row.append(CHAR_TO_PIECE[board_str[r*3 + c]])
        board.append(tuple(row))
    board_tuple = tuple(board)
    
    hand1 = tuple(int(x) for x in h1_str)
    hand2 = tuple(int(x) for x in h2_str)
    turn = 1 if turn_str == "+" else -1
    
    return (board_tuple, hand1, hand2, turn)

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
    for r in range(4):
        for c in range(3):
            piece = board[r][c]
            if piece * enemy > 0:
                dr, dc = lr - r, lc - c
                p_abs = abs(piece)
                if p_abs == LION:
                    if abs(dr) <= 1 and abs(dc) <= 1:
                        return True
                elif p_abs == GIRAFFE:
                    if (abs(dr) == 1 and dc == 0) or (dr == 0 and abs(dc) == 1):
                        return True
                elif p_abs == ELEPHANT:
                    if abs(dr) == 1 and abs(dc) == 1:
                        return True
                elif p_abs == CHICK:
                    if piece == CHICK: # 先手ひよこ
                        if dr == -1 and dc == 0:
                            return True
                    else: # 後手ひよこ
                        if dr == 1 and dc == 0:
                            return True
                elif p_abs == HEN:
                    if piece > 0: # 先手鶏の動き
                        if (dr, dc) in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1)]:
                            return True
                    else: # 後手鶏
                        if (dr, dc) in [(-1,0), (1,0), (0,-1), (0,1), (1,-1), (1,1)]:
                            return True
    return False

def decide_winner_light(state):
    board, hand1, hand2, turn = state
    
    l1, l2 = None, None
    for r in range(4):
        for c in range(3):
            if board[r][c] == LION:
                l1 = (r, c)
            elif board[r][c] == -LION:
                l2 = (r, c)
                
    # 1. キャッチ
    if l2 is None:
        return 1
    if l1 is None:
        return -1
        
    # 2. トライ
    if l1[0] == 0 and not is_check_light(board, 1):
        return 1
    if l2[0] == 3 and not is_check_light(board, -1):
        return -1
        
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
    # ボードコピーを一回だけ作成し、差分更新でチェックを高速化
    board_lst = [list(row) for row in board]
    for move in all_moves:
        if move[0] == 'move':
            _, fr, fc, tr, tc = move
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
            _, p_type, tr, tc = move
            board_lst[tr][tc] = p_type * turn
            
            check = is_check_light(board_lst, turn)
            
            board_lst[tr][tc] = EMPTY
            
            if not check:
                legal_moves.append(move)
            
    return legal_moves

def solve():
    print("🐾 どうぶつ将棋 完全解析開始 (最適化版) 🐾")
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
    state_to_id = {initial_state: 0}
    id_to_state = [initial_state]
    queue = deque([0])
    next_ids = []
    
    step = 0
    while queue:
        u_id = queue.popleft()
        u_state = id_to_state[u_id]
        
        legal_moves = get_legal_moves_light(u_state)
        u_nexts = []
        for m in legal_moves:
            next_state = make_move_light(u_state, m)
            if next_state not in state_to_id:
                next_id = len(id_to_state)
                state_to_id[next_state] = next_id
                id_to_state.append(next_state)
                queue.append(next_id)
            else:
                next_id = state_to_id[next_state]
            u_nexts.append(next_id)
            
        next_ids.append(u_nexts)
        
        step += 1
        if step % 200000 == 0:
            print(f"  探索済み局面数: {step} / 発見した局面数: {len(id_to_state)}")

    N = len(id_to_state)
    print(f"  状態空間の列挙完了。総局面数: {N}")
    print(f"  時間: {time.time() - start_time:.2f}秒")
    
    # 2. 逆遷移 (prev_ids) の構築
    print("2. 逆遷移グラフの構築中...")
    prev_ids = [[] for _ in range(N)]
    for u in range(N):
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
    
    resolved_count = 0
    while Q:
        u = Q.popleft()
        resolved_count += 1
        
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

        if resolved_count % 200000 == 0:
            print(f"  解析済み局面数: {resolved_count} / {N}")

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
    for u in range(N):
        key = state_to_key(id_to_state[u])
        db[key] = (V[u], dist[u])
        
    db_file = "solved_db.json.gz"
    with gzip.open(db_file, "wt", encoding="utf-8") as f:
        json.dump(db, f)
        
    print(f"🎉 データベースを {db_file} に保存しました！")
    print(f"⏱️ 総実行時間: {time.time() - start_time:.2f}秒")

if __name__ == "__main__":
    solve()
