import gzip
import json
import time
import os
import gc
import numpy as np
from numba import njit
import multiprocessing

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

# 階乗テーブル (Numbaから引けるようにグローバルなNumPy配列にする)
FACT = np.array([1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800, 39916800, 479001600], dtype=np.int64)

# 持ち駒の組み合わせ (先手, 後手)
HAND_PAIRS = [(0,0), (0,1), (1,0), (1,1), (0,2), (2,0)]
HAND_PAIRS_ARR = np.array(HAND_PAIRS, dtype=np.int8)

# シンボル定義
SYM_EMPTY = 0
SYM_L1 = 1
SYM_L2 = 2
SYM_G = 3
SYM_E = 4
SYM_C = 5

# 駒の値（-5から5）に対する (sym, info) のルックアップテーブル (Numba用)
LOOKUP_SYM = np.array([5, 5, 4, 3, 2, 0, 1, 3, 4, 5, 5], dtype=np.int8)
LOOKUP_INFO = np.array([3, 2, 1, 1, 0, 0, 0, 0, 0, 0, 1], dtype=np.int8)

# 方向ベクトルの定義 (Numba用)
LION_DIRS = np.array([(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)], dtype=np.int8)
GIRAFFE_DIRS = np.array([(-1,0),(1,0),(0,-1),(0,1),(0,0),(0,0),(0,0),(0,0)], dtype=np.int8)
ELEPHANT_DIRS = np.array([(-1,-1),(-1,1),(1,-1),(1,1),(0,0),(0,0),(0,0),(0,0)], dtype=np.int8)

def precompute_offsets():
    offsets = []
    current_offset = 0
    for i_G in range(6):
        hG1, hG2 = HAND_PAIRS[i_G]
        bG = 2 - hG1 - hG2
        for i_E in range(6):
            hE1, hE2 = HAND_PAIRS[i_E]
            bE = 2 - hE1 - hE2
            for i_C in range(6):
                hC1, hC2 = HAND_PAIRS[i_C]
                bC = 2 - hC1 - hC2
                
                n_empty = 12 - (2 + bG + bE + bC)
                num_perm = FACT[12] // (FACT[n_empty] * FACT[bG] * FACT[bE] * FACT[bC])
                variants = (1 << bG) * (1 << bE) * (1 << (2 * bC))
                
                size = num_perm * variants
                offsets.append(current_offset)
                current_offset += size
                
    offsets.append(current_offset)
    return np.array(offsets, dtype=np.int64)

OFFSETS = precompute_offsets()

@njit
def find_pair_idx(h1, h2):
    for i in range(6):
        if HAND_PAIRS_ARR[i, 0] == h1 and HAND_PAIRS_ARR[i, 1] == h2:
            return i
    return -1

@njit
def state_to_index(state):
    board, hand1, hand2, turn = state
    
    i_G = find_pair_idx(hand1[0], hand2[0])
    i_E = find_pair_idx(hand1[1], hand2[1])
    i_C = find_pair_idx(hand1[2], hand2[2])
    i_hand = i_G * 36 + i_E * 6 + i_C
    
    offset = OFFSETS[i_hand]
    
    flat_board = np.zeros(12, dtype=np.int8)
    idx = 0
    for r in range(4):
        for c in range(3):
            flat_board[idx] = board[r][c]
            idx += 1
            
    enc_G = 0
    enc_E = 0
    enc_C = 0
    bG = 0
    bE = 0
    bC = 0
    
    syms = np.zeros(12, dtype=np.int8)
    counts = np.zeros(6, dtype=np.int8)
    
    for idx in range(12):
        p = flat_board[idx]
        sym = LOOKUP_SYM[p + 5]
        info = LOOKUP_INFO[p + 5]
        syms[idx] = sym
        counts[sym] += 1
        if sym == SYM_G:
            enc_G = (enc_G << 1) | info
            bG += 1
        elif sym == SYM_E:
            enc_E = (enc_E << 1) | info
            bE += 1
        elif sym == SYM_C:
            enc_C = (enc_C << 2) | info
            bC += 1
            
    info_val = (enc_C << (bG + bE)) | (enc_E << bG) | enc_G
    info_mod = (1 << bG) * (1 << bE) * (1 << (2 * bC))
    
    rank = 0
    for i in range(12):
        actual_sym = syms[i]
        for s in range(actual_sym):
            if counts[s] > 0:
                counts[s] -= 1
                rem_len = 11 - i
                denom = 1
                for c in counts:
                    denom *= FACT[c]
                num_perm = FACT[rem_len] // denom
                rank += num_perm
                counts[s] += 1
        counts[actual_sym] -= 1
        
    return offset + rank * info_mod + info_val

@njit
def index_to_state(index):
    # OFFSETS 内のインデックスを二分探索
    # bisect_rightに相当するロジックを Numba で手動記述
    low = 0
    high = len(OFFSETS)
    while low < high:
        mid = (low + high) // 2
        if OFFSETS[mid] <= index:
            low = mid + 1
        else:
            high = mid
    i_hand = low - 1
    
    local_idx = index - OFFSETS[i_hand]
    
    i_G = i_hand // 36
    i_E = (i_hand // 6) % 6
    i_C = i_hand % 6
    
    hG1, hG2 = HAND_PAIRS_ARR[i_G, 0], HAND_PAIRS_ARR[i_G, 1]
    hE1, hE2 = HAND_PAIRS_ARR[i_E, 0], HAND_PAIRS_ARR[i_E, 1]
    hC1, hC2 = HAND_PAIRS_ARR[i_C, 0], HAND_PAIRS_ARR[i_C, 1]
    
    hand1 = (hG1, hE1, hC1)
    hand2 = (hG2, hE2, hC2)
    
    bG = 2 - hG1 - hG2
    bE = 2 - hE1 - hE2
    bC = 2 - hC1 - hC2
    
    info_mod = (1 << bG) * (1 << bE) * (1 << (2 * bC))
    rank = local_idx // info_mod
    info_val = local_idx % info_mod
    
    enc_G = info_val & ((1 << bG) - 1)
    enc_E = (info_val >> bG) & ((1 << bE) - 1)
    enc_C = (info_val >> (bG + bE)) & ((1 << (2 * bC)) - 1)
    
    info_G = [0] * bG
    for i in range(bG):
        info_G[bG - 1 - i] = enc_G & 1
        enc_G >>= 1
    
    info_E = [0] * bE
    for i in range(bE):
        info_E[bE - 1 - i] = enc_E & 1
        enc_E >>= 1
    
    info_C = [0] * bC
    for i in range(bC):
        info_C[bC - 1 - i] = enc_C & 3
        enc_C >>= 2
    
    counts = [0] * 6
    counts[SYM_EMPTY] = 12 - (2 + bG + bE + bC)
    counts[SYM_L1] = 1
    counts[SYM_L2] = 1
    counts[SYM_G] = bG
    counts[SYM_E] = bE
    counts[SYM_C] = bC
    
    syms = [0] * 12
    for i in range(12):
        for s in range(6):
            if counts[s] > 0:
                counts[s] -= 1
                rem_len = 11 - i
                denom = 1
                for c in counts:
                    denom *= FACT[c]
                num_perm = FACT[rem_len] // denom
                if rank < num_perm:
                    syms[i] = s
                    break
                else:
                    rank -= num_perm
                    counts[s] += 1
                    
    board_flat = [0] * 12
    idx_G = 0
    idx_E = 0
    idx_C = 0
    for i in range(12):
        s = syms[i]
        if s == SYM_G:
            board_flat[i] = GIRAFFE if info_G[idx_G] == 0 else -GIRAFFE
            idx_G += 1
        elif s == SYM_E:
            board_flat[i] = ELEPHANT if info_E[idx_E] == 0 else -ELEPHANT
            idx_E += 1
        elif s == SYM_C:
            info = info_C[idx_C]
            if info == 0: board_flat[i] = CHICK
            elif info == 1: board_flat[i] = HEN
            elif info == 2: board_flat[i] = -CHICK
            elif info == 3: board_flat[i] = -HEN
            idx_C += 1
        elif s == SYM_L1:
            board_flat[i] = LION
        elif s == SYM_L2:
            board_flat[i] = -LION
        else:
            board_flat[i] = EMPTY
            
    board = (
        (board_flat[0], board_flat[1], board_flat[2]),
        (board_flat[3], board_flat[4], board_flat[5]),
        (board_flat[6], board_flat[7], board_flat[8]),
        (board_flat[9], board_flat[10], board_flat[11])
    )
    return (board, hand1, hand2, 1)

@njit
def get_piece_moves_light(r, c, piece, board, turn, out_moves, start_idx):
    p_abs = abs(piece)
    idx = start_idx
    
    if p_abs == LION:
        for i in range(8):
            dr, dc = LION_DIRS[i, 0], LION_DIRS[i, 1]
            nr, nc = r + dr, c + dc
            if 0 <= nr < 4 and 0 <= nc < 3:
                if board[nr][nc] * turn <= 0:
                    out_moves[idx, 0] = 0 # move
                    out_moves[idx, 1] = r
                    out_moves[idx, 2] = c
                    out_moves[idx, 3] = nr
                    out_moves[idx, 4] = nc
                    idx += 1
    elif p_abs == GIRAFFE:
        for i in range(4):
            dr, dc = GIRAFFE_DIRS[i, 0], GIRAFFE_DIRS[i, 1]
            nr, nc = r + dr, c + dc
            if 0 <= nr < 4 and 0 <= nc < 3:
                if board[nr][nc] * turn <= 0:
                    out_moves[idx, 0] = 0
                    out_moves[idx, 1] = r
                    out_moves[idx, 2] = c
                    out_moves[idx, 3] = nr
                    out_moves[idx, 4] = nc
                    idx += 1
    elif p_abs == ELEPHANT:
        for i in range(4):
            dr, dc = ELEPHANT_DIRS[i, 0], ELEPHANT_DIRS[i, 1]
            nr, nc = r + dr, c + dc
            if 0 <= nr < 4 and 0 <= nc < 3:
                if board[nr][nc] * turn <= 0:
                    out_moves[idx, 0] = 0
                    out_moves[idx, 1] = r
                    out_moves[idx, 2] = c
                    out_moves[idx, 3] = nr
                    out_moves[idx, 4] = nc
                    idx += 1
    elif p_abs == CHICK:
        dr = -1 if piece > 0 else 1
        nr, nc = r + dr, c
        if 0 <= nr < 4 and 0 <= nc < 3:
            if board[nr][nc] * turn <= 0:
                out_moves[idx, 0] = 0
                out_moves[idx, 1] = r
                out_moves[idx, 2] = c
                out_moves[idx, 3] = nr
                out_moves[idx, 4] = nc
                idx += 1
    elif p_abs == HEN:
        for i in range(8):
            if piece > 0:
                if i >= 6: break
                dr, dc = LION_DIRS[i, 0], LION_DIRS[i, 1]
            else:
                if i == 4 or i == 5: continue
                dr, dc = LION_DIRS[i, 0], LION_DIRS[i, 1]
            nr, nc = r + dr, c + dc
            if 0 <= nr < 4 and 0 <= nc < 3:
                if board[nr][nc] * turn <= 0:
                    out_moves[idx, 0] = 0
                    out_moves[idx, 1] = r
                    out_moves[idx, 2] = c
                    out_moves[idx, 3] = nr
                    out_moves[idx, 4] = nc
                    idx += 1
    return idx

@njit
def is_check_light(board, turn):
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
    for i in range(8):
        dr, dc = LION_DIRS[i, 0], LION_DIRS[i, 1]
        er, ec = lr + dr, lc + dc
        if 0 <= er < 4 and 0 <= ec < 3:
            piece = board[er][ec]
            if piece * enemy > 0:
                p_abs = abs(piece)
                tr, tc = -dr, -dc
                
                if p_abs == LION:
                    return True
                elif p_abs == GIRAFFE:
                    if (abs(tr) == 1 and tc == 0) or (tr == 0 and abs(tc) == 1):
                        return True
                elif p_abs == ELEPHANT:
                    if abs(tr) == 1 and abs(tc) == 1:
                        return True
                elif p_abs == CHICK:
                    if piece == CHICK:
                        if tr == -1 and tc == 0:
                            return True
                    else:
                        if tr == 1 and tc == 0:
                            return True
                elif p_abs == HEN:
                    if piece > 0:
                        if (tr == -1 and tc == 0) or (tr == 1 and tc == 0) or (tr == 0 and tc == -1) or (tr == 0 and tc == 1) or (tr == -1 and tc == -1) or (tr == -1 and tc == 1):
                            return True
                    else:
                        if (tr == -1 and tc == 0) or (tr == 1 and tc == 0) or (tr == 0 and tc == -1) or (tr == 0 and tc == 1) or (tr == 1 and tc == -1) or (tr == 1 and tc == 1):
                            return True
    return False

# マニュアルでの board 更新用関数
@njit
def set_board_val(board, r, c, val):
    r0, r1, r2, r3 = board
    p00, p01, p02 = r0
    p10, p11, p12 = r1
    p20, p21, p22 = r2
    p30, p31, p32 = r3
    
    if r == 0:
        if c == 0: p00 = val
        elif c == 1: p01 = val
        elif c == 2: p02 = val
    elif r == 1:
        if c == 0: p10 = val
        elif c == 1: p11 = val
        elif c == 2: p12 = val
    elif r == 2:
        if c == 0: p20 = val
        elif c == 1: p21 = val
        elif c == 2: p22 = val
    elif r == 3:
        if c == 0: p30 = val
        elif c == 1: p31 = val
        elif c == 2: p32 = val
        
    return (
        (p00, p01, p02),
        (p10, p11, p12),
        (p20, p21, p22),
        (p30, p31, p32)
    )

@njit
def can_capture_enemy_lion(state):
    board, hand1, hand2, turn = state
    enemy_lion = -turn * LION
    el_pos_r, el_pos_c = -1, -1
    for r in range(4):
        for c in range(3):
            if board[r][c] == enemy_lion:
                el_pos_r, el_pos_c = r, c
                break
        if el_pos_r != -1:
            break
            
    if el_pos_r == -1:
        return True
        
    # 一時移動バッファを用意
    tmp_moves = np.zeros((40, 5), dtype=np.int8)
    for r in range(4):
        for c in range(3):
            piece = board[r][c]
            if piece * turn > 0:
                count = get_piece_moves_light(r, c, piece, board, turn, tmp_moves, 0)
                for i in range(count):
                    if tmp_moves[i, 3] == el_pos_r and tmp_moves[i, 4] == el_pos_c:
                        return True
    return False

@njit
def decide_winner_light(state):
    board, hand1, hand2, turn = state
    if can_capture_enemy_lion(state):
        return turn
    enemy_lion = -turn * LION
    own_home_row = 3 if turn == 1 else 0
    for c in range(3):
        if board[own_home_row][c] == enemy_lion:
            return -turn
    return 0

@njit
def make_move_light(state, move):
    board, hand1, hand2, turn = state
    m_type = move[0]
    new_board = board
    new_hand1 = hand1
    new_hand2 = hand2
    
    if m_type == 0: # move
        fr, fc, tr, tc = move[1], move[2], move[3], move[4]
        piece = board[fr][fc]
        target = board[tr][tc]
        
        if target != 0:
            captured = abs(target)
            if captured == HEN:
                captured = CHICK
            idx = captured - 2
            if turn == 1:
                h0, h1, h2 = hand1
                if idx == 0: h0 += 1
                elif idx == 1: h1 += 1
                elif idx == 2: h2 += 1
                new_hand1 = (h0, h1, h2)
            else:
                h0, h1, h2 = hand2
                if idx == 0: h0 += 1
                elif idx == 1: h1 += 1
                elif idx == 2: h2 += 1
                new_hand2 = (h0, h1, h2)
                
        new_board = set_board_val(new_board, fr, fc, 0)
        if abs(piece) == CHICK and ((turn == 1 and tr == 0) or (turn == -1 and tr == 3)):
            new_board = set_board_val(new_board, tr, tc, HEN * turn)
        else:
            new_board = set_board_val(new_board, tr, tc, piece)
            
    elif m_type == 1: # drop
        p_type, tr, tc = move[1], move[2], move[3]
        new_board = set_board_val(new_board, tr, tc, p_type * turn)
        idx = p_type - 2
        if turn == 1:
            h0, h1, h2 = hand1
            if idx == 0: h0 -= 1
            elif idx == 1: h1 -= 1
            elif idx == 2: h2 -= 1
            new_hand1 = (h0, h1, h2)
        else:
            h0, h1, h2 = hand2
            if idx == 0: h0 -= 1
            elif idx == 1: h1 -= 1
            elif idx == 2: h2 -= 1
            new_hand2 = (h0, h1, h2)
            
    return (new_board, new_hand1, new_hand2, -turn)

@njit
def get_legal_moves_light(state, out_moves):
    board, hand1, hand2, turn = state
    if decide_winner_light(state) != 0:
        return 0

    in_check = is_check_light(board, turn)
    
    # 1. 盤上の動きを一時バッファに生成
    all_count = 0
    for r in range(4):
        for c in range(3):
            piece = board[r][c]
            if piece * turn > 0:
                all_count = get_piece_moves_light(r, c, piece, board, turn, out_moves, all_count)
                
    # 2. 持ち駒のドロップを生成
    hand = hand1 if turn == 1 else hand2
    for idx in range(3):
        count = hand[idx]
        if count > 0:
            p_type = idx + 2
            for r in range(4):
                for c in range(3):
                    if board[r][c] == EMPTY:
                        out_moves[all_count, 0] = 1 # drop
                        out_moves[all_count, 1] = p_type
                        out_moves[all_count, 2] = r
                        out_moves[all_count, 3] = c
                        out_moves[all_count, 4] = 0
                        all_count += 1

    # 3. 王手回避と自殺手のチェック
    legal_count = 0
    tmp_out = np.zeros((40, 5), dtype=np.int8)
    
    # boardを書き換えるための一時的な変数
    for i in range(all_count):
        m_type = out_moves[i, 0]
        if m_type == 0: # move
            fr, fc, tr, tc = out_moves[i, 1], out_moves[i, 2], out_moves[i, 3], out_moves[i, 4]
            piece = board[fr][fc]
            
            if abs(piece) != LION and not in_check:
                tmp_out[legal_count] = out_moves[i]
                legal_count += 1
                continue
                
            orig_from = board[fr][fc]
            orig_to = board[tr][tc]
            
            # 仮着手
            temp_board = set_board_val(board, tr, tc, orig_from)
            temp_board = set_board_val(temp_board, fr, fc, 0)
            
            check = is_check_light(temp_board, turn)
            if not check:
                tmp_out[legal_count] = out_moves[i]
                legal_count += 1
                
        elif m_type == 1: # drop
            if not in_check:
                tmp_out[legal_count] = out_moves[i]
                legal_count += 1
                continue
                
            p_type, tr, tc = out_moves[i, 1], out_moves[i, 2], out_moves[i, 3]
            temp_board = set_board_val(board, tr, tc, p_type * turn)
            
            check = is_check_light(temp_board, turn)
            if not check:
                tmp_out[legal_count] = out_moves[i]
                legal_count += 1
                
    for i in range(legal_count):
        out_moves[i] = tmp_out[i]
        
    return legal_count

@njit
def is_terminal_state(state):
    winner = decide_winner_light(state)
    if winner != 0:
        return winner
    tmp_moves = np.zeros((40, 5), dtype=np.int8)
    count = get_legal_moves_light(state, tmp_moves)
    if count == 0:
        return -state[3]
    return 0

# BFS探索ループのNumba最適化 (チャンク処理)
# キュー、global_to_local、edges_from, edges_toなどのバッファを高速処理する
@njit
def run_bfs_chunk(queue_arr, head, tail, global_to_local, local_to_global_arr, local_count,
                  edges_from_buf, edges_to_buf, buf_idx, out_degrees, has_winning_terminal, max_edges):
    
    # チャンク内で処理する局面数上限 (オーバーフロー防止)
    chunk_limit = 200000
    processed = 0
    
    tmp_moves = np.zeros((40, 5), dtype=np.int8)
    
    while head != tail and processed < chunk_limit and buf_idx < max_edges - 100:
        u_local = queue_arr[head]
        head = (head + 1) % len(queue_arr)
        processed += 1
        
        # インデックスから状態を復元
        u_global = local_to_global_arr[u_local]
        u_state = index_to_state(u_global)
        
        legal_count = get_legal_moves_light(u_state, tmp_moves)
        for i in range(legal_count):
            move = tmp_moves[i]
            next_state = make_move_light(u_state, move)
            normalized_next = get_canonical_state(get_active_perspective_state(next_state))
            term = is_terminal_state(normalized_next)
            
            if term != 0:
                if term == 1:
                    has_winning_terminal[u_local] = True
                continue
                
            # 非末端
            out_degrees[u_local] += 1
            g_next = state_to_index(normalized_next)
            l_next = global_to_local[g_next]
            
            if l_next == 0xFFFFFFFF:
                l_next = local_count
                global_to_local[g_next] = l_next
                local_to_global_arr[l_next] = g_next
                local_count += 1
                
                # キューに追加
                queue_arr[tail] = l_next
                tail = (tail + 1) % len(queue_arr)
                
            # エッジをバッファに追加 (u_local から l_next への遷移)
            edges_from_buf[buf_idx] = u_local
            edges_to_buf[buf_idx] = l_next
            buf_idx += 1
            
    return head, tail, local_count, buf_idx

# 後退解析ループのNumba最適化
@njit
def run_retrograde_analysis(M, has_winning_terminal, out_degrees, edge_starts, edge_from_csr, V, dist, max_dist_next):
    # キューをリングバッファで実装
    Q_arr = np.zeros(M + 100, dtype=np.uint32)
    q_head = 0
    q_tail = 0
    
    # 初期確定局面の設定
    for i in range(M):
        if has_winning_terminal[i]:
            V[i] = 1
            dist[i] = 1
            Q_arr[q_tail] = i
            q_tail += 1
        elif out_degrees[i] == 0:
            V[i] = -1
            dist[i] = 1
            Q_arr[q_tail] = i
            q_tail += 1
            
    resolved_count = q_tail
    
    while q_head != q_tail:
        u = Q_arr[q_head]
        q_head += 1
        
        val_u = V[u]
        dist_u = dist[u]
        
        start = edge_starts[u]
        end = edge_starts[u+1]
        for idx in range(start, end):
            p = edge_from_csr[idx]
            if V[p] != 0:
                continue
                
            if val_u == -1:
                # 相手番が負け -> 自分が勝ち
                V[p] = 1
                dist[p] = dist_u + 1
                Q_arr[q_tail] = p
                q_tail += 1
                resolved_count += 1
            else:
                # 相手番が勝ち -> 自分が負けになる手
                out_degrees[p] -= 1
                if dist_u > max_dist_next[p]:
                    max_dist_next[p] = dist_u
                    
                if out_degrees[p] == 0 and not has_winning_terminal[p]:
                    V[p] = -1
                    dist[p] = max_dist_next[p] + 1
                    Q_arr[q_tail] = p
                    q_tail += 1
                    resolved_count += 1
                    
    return resolved_count

def solve():
    print("🐾 どうぶつ将棋 完全解析開始 (Numba + マルチプロセス超最適化版) 🐾")
    start_time = time.time()
    
    initial_board = (
        (-GIRAFFE, -LION, -ELEPHANT),
        (EMPTY, -CHICK, EMPTY),
        (EMPTY, CHICK, EMPTY),
        (ELEPHANT, LION, GIRAFFE)
    )
    initial_state = (initial_board, (0, 0, 0), (0, 0, 0), 1)
    
    init_normalized = get_canonical_state(get_active_perspective_state(initial_state))
    init_idx = state_to_index(init_normalized)
    
    # 1. 状態空間の列挙 (BFS)
    print("1. 状態空間の列挙中...")
    global_to_local = np.full(1567925964, 0xFFFFFFFF, dtype=np.uint32)
    
    # local_to_globalをNumbaに渡しやすくするため十分大きな固定長配列にする
    MAX_NODES = 80000000 # 最大8000万局面を想定
    local_to_global_arr = np.zeros(MAX_NODES, dtype=np.uint32)
    
    global_to_local[init_idx] = 0
    local_to_global_arr[0] = init_idx
    local_count = 1
    
    # キュー用配列 (リングバッファ)
    queue_arr = np.zeros(5000000, dtype=np.uint32)
    queue_arr[0] = 0
    q_head = 0
    q_tail = 1
    
    # エッジ一時書き出しの準備
    edges_file = "edges.bin"
    if os.path.exists(edges_file):
        os.remove(edges_file)
        
    buf_size = 20000000 # 20Mペア
    edges_from_buf = np.zeros(buf_size, dtype=np.uint32)
    edges_to_buf = np.zeros(buf_size, dtype=np.uint32)
    buf_idx = 0
    
    # BFS用に出次数と末端判定を記録する配列
    out_degrees = np.zeros(MAX_NODES, dtype=np.uint8)
    has_winning_terminal = np.zeros(MAX_NODES, dtype=bool)
    
    last_reported = 0
    report_interval = 2.0 # 秒
    last_report_time = time.time()
    
    while q_head != q_tail:
        # Numbaで高速にBFSチャンクを実行
        q_head, q_tail, local_count, buf_idx = run_bfs_chunk(
            queue_arr, q_head, q_tail,
            global_to_local, local_to_global_arr, local_count,
            edges_from_buf, edges_to_buf, buf_idx,
            out_degrees, has_winning_terminal, buf_size
        )
        
        # エッジバッファがいっぱいになったらディスクにフラッシュ
        if buf_idx >= buf_size - 10000:
            with open(edges_file, "ab") as f:
                # 交互に格納されるようにパックして書き出し
                flat_edges = np.empty(buf_idx * 2, dtype=np.uint32)
                flat_edges[0::2] = edges_from_buf[:buf_idx]
                flat_edges[1::2] = edges_to_buf[:buf_idx]
                f.write(flat_edges.tobytes())
            buf_idx = 0
            
        current_time = time.time()
        if current_time - last_report_time > report_interval:
            nps = (local_count - last_reported) / (current_time - last_report_time)
            print(f"\r  発見済み局面: {local_count:,} (NPS: {nps:.0f} 局面/秒)", end="", flush=True)
            last_reported = local_count
            last_report_time = current_time
            
    # 残りのバッファを書き出す
    if buf_idx > 0:
        with open(edges_file, "ab") as f:
            flat_edges = np.empty(buf_idx * 2, dtype=np.uint32)
            flat_edges[0::2] = edges_from_buf[:buf_idx]
            flat_edges[1::2] = edges_to_buf[:buf_idx]
            f.write(flat_edges.tobytes())
            
    print()  # 進捗表示の行を確定するための改行
    M = local_count
    print(f"  非末端局面の列挙完了。ノード数 M: {M:,}")
    print(f"  時間: {time.time() - start_time:.2f}秒")
    
    # 配列を実サイズに切り詰める
    out_degrees = out_degrees[:M]
    has_winning_terminal = has_winning_terminal[:M]
    local_to_global = local_to_global_arr[:M].copy()
    
    # メモリ解放
    del global_to_local
    del local_to_global_arr
    gc.collect()
    
    # 2. 逆遷移グラフの構築
    print("2. 逆遷移グラフの構築中...")
    file_size = os.path.getsize(edges_file)
    E = file_size // 8
    print(f"  総辺数 E: {E:,}")
    
    edges_flat = np.fromfile(edges_file, dtype=np.uint32)
    edges_from = edges_flat[0::2]
    edges_to = edges_flat[1::2]
    
    in_degrees = np.bincount(edges_to, minlength=M)
    edge_starts = np.zeros(M + 1, dtype=np.uint32)
    edge_starts[1:] = np.cumsum(in_degrees)
    
    print("  辺のソート中...")
    idx_sort = np.argsort(edges_to)
    edge_from_csr = edges_from[idx_sort]
    
    # メモリ解放と一時ファイルの削除
    del edges_flat, edges_from, edges_to, idx_sort
    gc.collect()
    if os.path.exists(edges_file):
        os.remove(edges_file)
        
    print(f"  構築完了。時間: {time.time() - start_time:.2f}秒")
    
    # 3. 後退解析 (Retrograde Analysis)
    print("3. 後退解析の実行中...")
    V = np.zeros(M, dtype=np.int8)  # 0: 未確定, 1: 勝ち, -1: 負け
    dist = np.full(M, 255, dtype=np.uint8)
    max_dist_next = np.zeros(M, dtype=np.uint8)
    
    resolved = run_retrograde_analysis(M, has_winning_terminal, out_degrees, edge_starts, edge_from_csr, V, dist, max_dist_next)
    print(f"  確定局面数: {resolved:,} / {M:,}")
    
    # 集計
    draw_count = np.sum(V == 0)
    win_p1 = np.sum(V == 1)
    win_p2 = np.sum(V == -1)
    print(f"  非末端局面結果: 勝ち={win_p1:,}, 負け={win_p2:,}, 引き分け={draw_count:,}")
    print(f"  時間: {time.time() - start_time:.2f}秒")
    
    # 初期局面の理論値
    init_val = V[0]
    init_dist = dist[0]
    print(f"💡 初期局面の理論値: {'先手必勝' if init_val == 1 else '後手必勝' if init_val == -1 else '引き分け'} (手数: {init_dist})")
    
    # 4. データベースの保存 (マルチプロセスによる並列Gzip書き出し)
    db_file = "solved_db.json.gz"
    print(f"4. データベースの保存中 ({db_file})...")
    
    # マルチプロセス書き出しを実行
    save_database_multiprocess(M, local_to_global, V, dist, db_file)
    
    print(f"🎉 データベースを {db_file} に保存しました！")
    print(f"⏱️ 総実行時間: {time.time() - start_time:.2f}秒")

# 1プロセスが担当する書き出しチャンク処理
def save_chunk_worker(worker_id, M, local_to_global_chunk, V_chunk, dist_chunk, out_dir):
    part_file = os.path.join(out_dir, f"part_{worker_id}.json.gz")
    
    # 各プロセス内での末端判定用にNumba関数を呼ぶため、型の一貫性を維持する
    # 末端局面の重複チェック用の配列をローカルに確保 (15億ビットは大きすぎるので、
    # 探索時と同様のuint32インデックスチェック用のセットまたは配列を用いるが、
    # 各プロセスが自分の管轄内で見つけた末端局面だけを書き出せば、マージ時に一貫します)
    # ここではローカルのHashSetを使用
    term_written = set()
    
    # 指し手一時バッファ
    tmp_moves = np.zeros((40, 5), dtype=np.int8)
    
    with gzip.open(part_file, "wt", encoding="utf-8") as f:
        # JSONの断片をカンマ区切りで書き出す (先頭と末尾の {} は削る)
        first = True
        for i in range(len(local_to_global_chunk)):
            g_idx = local_to_global_chunk[i]
            state = index_to_state(g_idx)
            
            packed = pack_state_raw(state) & ((1 << 60) - 1)
            key = f"{packed:015x}"
            
            val = int(V_chunk[i])
            d = int(dist_chunk[i])
            if val == 0:
                d = 999
                
            if not first:
                f.write(",")
            f.write(f'"{key}":[{val},{d}]')
            first = False
            
            # 遷移先の末端局面も追加で書き出す
            legal_count = get_legal_moves_light(state, tmp_moves)
            for m_idx in range(legal_count):
                move = tmp_moves[m_idx]
                next_state = make_move_light(state, move)
                normalized_next = get_canonical_state(get_active_perspective_state(next_state))
                term = is_terminal_state(normalized_next)
                if term != 0:
                    term_g = state_to_index(normalized_next)
                    if term_g not in term_written:
                        term_written.add(term_g)
                        term_packed = pack_state_raw(normalized_next) & ((1 << 60) - 1)
                        term_key = f"{term_packed:015x}"
                        f.write(f',"{term_key}":[{int(term)},0]')

def save_database_multiprocess(M, local_to_global, V, dist, output_file):
    num_workers = min(multiprocessing.cpu_count(), 16)
    print(f"  マルチプロセス保存を実行します (使用コア数: {num_workers})")
    
    # チャンクに分割
    indices = np.array_split(np.arange(M), num_workers)
    
    # 一時保存用ディレクトリ
    temp_dir = "temp_db_parts"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    processes = []
    for w_id in range(num_workers):
        chunk_idx = indices[w_id]
        if len(chunk_idx) == 0:
            continue
            
        g_chunk = local_to_global[chunk_idx]
        V_chunk = V[chunk_idx]
        dist_chunk = dist[chunk_idx]
        
        p = multiprocessing.Process(
            target=save_chunk_worker,
            args=(w_id, M, g_chunk, V_chunk, dist_chunk, temp_dir)
        )
        p.start()
        processes.append(p)
        
    for p in processes:
        p.join()
        
    print("  全プロセスの書き出し完了。マージ処理を実行中...")
    
    # 各パーツファイルを読み込んで1つにマージ (解凍・再圧縮せずに
    # 文字列ストリームの結合で超高速マージを行う)
    # 重複キーを排除するため、すでにマージされたキーを追跡するためのハッシュセット(または辞書)を使うが、
    # データベースサイズが大きいので、メモリ消費を抑えながら処理します。
    # 実際には、末端局面キーの重複のみが発生するため、末端局面キーのセットをメモリに保持します。
    term_keys_written = set()
    
    with gzip.open(output_file, "wt", encoding="utf-8") as out_f:
        out_f.write("{")
        first = True
        
        for w_id in range(num_workers):
            part_path = os.path.join(temp_dir, f"part_{w_id}.json.gz")
            if not os.path.exists(part_path):
                continue
                
            print(f"\r    マージ中: {part_path} ({w_id+1}/{num_workers})", end="", flush=True)
            with gzip.open(part_path, "rt", encoding="utf-8") as in_f:
                content = in_f.read().strip()
                if not content:
                    continue
                
                # 重複した末端局面キーなどを削りながら書き込む
                # 各エントリーは `"key":[val,dist]` の形式
                entries = content.split(",")
                for entry in entries:
                    if not entry:
                        continue
                    
                    # キー部分の抽出
                    key_end = entry.find('"')
                    key_start = entry.find('"', key_end + 1)
                    if key_start == -1:
                        # 不完全なエントリーはスキップ
                        continue
                    
                    key = entry[key_end+1 : key_start]
                    
                    # 既に書き込み済みのキー（特に末端局面）ならスキップ
                    if key in term_keys_written:
                        continue
                    
                    # 記録
                    term_keys_written.add(key)
                    
                    if not first:
                        out_f.write(",")
                    out_f.write(entry)
                    first = False
                    
            # 一時ファイルの削除
            os.remove(part_path)
            
        print()  # マージ中表示の行を確定するための改行
        out_f.write("}")
        
    # 一時ディレクトリの削除
    os.rmdir(temp_dir)
    print("  マージ完了。一時ディレクトリを削除しました。")

if __name__ == "__main__":
    solve()
