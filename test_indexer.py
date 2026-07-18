import math

# 階乗テーブル
FACT = [1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800, 39916800, 479001600]

# 持ち駒の組み合わせ (先手, 後手)
HAND_PAIRS = [(0,0), (0,1), (1,0), (1,1), (0,2), (2,0)]
PAIR_TO_IDX = {p: i for i, p in enumerate(HAND_PAIRS)}

# 駒の定義
EMPTY = 0
LION, GIRAFFE, ELEPHANT, CHICK, HEN = 1, 2, 3, 4, 5

# シンボル定義
SYM_EMPTY = 0
SYM_L1 = 1
SYM_L2 = 2
SYM_G = 3
SYM_E = 4
SYM_C = 5

# 状態 -> シンボルと追加情報
def get_sym_and_info(piece):
    if piece == EMPTY:
        return SYM_EMPTY, 0
    elif piece == LION:
        return SYM_L1, 0
    elif piece == -LION:
        return SYM_L2, 0
    elif piece == GIRAFFE:
        return SYM_G, 0  # 先手きりん (info=0)
    elif piece == -GIRAFFE:
        return SYM_G, 1  # 後手きりん (info=1)
    elif piece == ELEPHANT:
        return SYM_E, 0  # 先手ぞう (info=0)
    elif piece == -ELEPHANT:
        return SYM_E, 1  # 後手ぞう (info=1)
    elif piece == CHICK:
        return SYM_C, 0  # 先手ひよこ (info=0)
    elif piece == HEN:
        return SYM_C, 1  # 先手にわとり (info=1)
    elif piece == -CHICK:
        return SYM_C, 2  # 後手ひよこ (info=2)
    elif piece == -HEN:
        return SYM_C, 3  # 後手にわとり (info=3)
    raise ValueError(f"Invalid piece: {piece}")

def make_piece_from_sym(sym, info):
    if sym == SYM_EMPTY:
        return EMPTY
    elif sym == SYM_L1:
        return LION
    elif sym == SYM_L2:
        return -LION
    elif sym == SYM_G:
        return GIRAFFE if info == 0 else -GIRAFFE
    elif sym == SYM_E:
        return ELEPHANT if info == 0 else -ELEPHANT
    elif sym == SYM_C:
        if info == 0: return CHICK
        elif info == 1: return HEN
        elif info == 2: return -CHICK
        elif info == 3: return -HEN
    raise ValueError(f"Invalid sym/info: {sym}, {info}")

def precompute_offsets():
    offsets = []
    current_offset = 0
    pattern_sizes = []
    
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
                pattern_sizes.append(size)
                current_offset += size
                
    offsets.append(current_offset)
    return offsets, pattern_sizes

OFFSETS, SIZES = precompute_offsets()

# 駒の値（-5から5）に対する (sym, info) のルックアップテーブル
LOOKUP_SYM = [0] * 11
LOOKUP_INFO = [0] * 11

for _p in range(-5, 6):
    if _p == EMPTY:
        _s, _inf = SYM_EMPTY, 0
    elif _p == LION:
        _s, _inf = SYM_L1, 0
    elif _p == -LION:
        _s, _inf = SYM_L2, 0
    elif _p == GIRAFFE:
        _s, _inf = SYM_G, 0
    elif _p == -GIRAFFE:
        _s, _inf = SYM_G, 1
    elif _p == ELEPHANT:
        _s, _inf = SYM_E, 0
    elif _p == -ELEPHANT:
        _s, _inf = SYM_E, 1
    elif _p == CHICK:
        _s, _inf = SYM_C, 0
    elif _p == HEN:
        _s, _inf = SYM_C, 1
    elif _p == -CHICK:
        _s, _inf = SYM_C, 2
    elif _p == -HEN:
        _s, _inf = SYM_C, 3
    LOOKUP_SYM[_p + 5] = _s
    LOOKUP_INFO[_p + 5] = _inf

def state_to_index(state):
    board, hand1, hand2, turn = state
    
    # 1. 持ち駒インデックスの取得
    i_G = PAIR_TO_IDX[(hand1[0], hand2[0])]
    i_E = PAIR_TO_IDX[(hand1[1], hand2[1])]
    i_C = PAIR_TO_IDX[(hand1[2], hand2[2])]
    i_hand = i_G * 36 + i_E * 6 + i_C
    
    offset = OFFSETS[i_hand]
    
    flat_board = board[0] + board[1] + board[2] + board[3]
    
    enc_G = 0
    enc_E = 0
    enc_C = 0
    bG = 0
    bE = 0
    bC = 0
    
    syms = [0] * 12
    counts = [0, 0, 0, 0, 0, 0]
    
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
    
    # マルチセットのRank計算
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

def index_to_state(index):
    # 1. 持ち駒パターンの特定 (二分探索)
    import bisect
    i_hand = bisect.bisect_right(OFFSETS, index) - 1
    local_idx = index - OFFSETS[i_hand]
    
    # 持ち駒の復元
    i_G = i_hand // 36
    i_E = (i_hand // 6) % 6
    i_C = i_hand % 6
    
    hG1, hG2 = HAND_PAIRS[i_G]
    hE1, hE2 = HAND_PAIRS[i_E]
    hC1, hC2 = HAND_PAIRS[i_C]
    
    hand1 = (hG1, hE1, hC1)
    hand2 = (hG2, hE2, hC2)
    
    bG = 2 - hG1 - hG2
    bE = 2 - hE1 - hE2
    bC = 2 - hC1 - hC2
    
    info_mod = (1 << bG) * (1 << bE) * (1 << (2 * bC))
    rank = local_idx // info_mod
    info_val = local_idx % info_mod
    
    # 追加情報のデコード
    enc_G = info_val & ((1 << bG) - 1)
    enc_E = (info_val >> bG) & ((1 << bE) - 1)
    enc_C = (info_val >> (bG + bE)) & ((1 << (2 * bC)) - 1)
    
    info_G = []
    for _ in range(bG):
        info_G.append(enc_G & 1)
        enc_G >>= 1
    info_G.reverse()
    
    info_E = []
    for _ in range(bE):
        info_E.append(enc_E & 1)
        enc_E >>= 1
    info_E.reverse()
    
    info_C = []
    for _ in range(bC):
        info_C.append(enc_C & 3)
        enc_C >>= 2
    info_C.reverse()
    
    # マルチセットのUnrank
    counts = [0] * 6
    counts[SYM_EMPTY] = 12 - (2 + bG + bE + bC)
    counts[SYM_L1] = 1
    counts[SYM_L2] = 1
    counts[SYM_G] = bG
    counts[SYM_E] = bE
    counts[SYM_C] = bC
    
    syms = []
    for i in range(12):
        for s in range(6):
            if counts[s] > 0:
                counts[s] -= 1
                rem_len = 12 - 1 - i
                denom = 1
                for c in counts:
                    denom *= FACT[c]
                num_perm = FACT[rem_len] // denom
                if rank < num_perm:
                    syms.append(s)
                    break
                else:
                    rank -= num_perm
                    counts[s] += 1
                    
    # 盤面の復元
    board_flat = []
    idx_G = 0
    idx_E = 0
    idx_C = 0
    for s in syms:
        if s == SYM_G:
            board_flat.append(make_piece_from_sym(s, info_G[idx_G]))
            idx_G += 1
        elif s == SYM_E:
            board_flat.append(make_piece_from_sym(s, info_E[idx_E]))
            idx_E += 1
        elif s == SYM_C:
            board_flat.append(make_piece_from_sym(s, info_C[idx_C]))
            idx_C += 1
        else:
            board_flat.append(make_piece_from_sym(s, 0))
            
    board = []
    for r in range(4):
        board.append(tuple(board_flat[r*3 : r*3+3]))
        
    return (tuple(board), hand1, hand2, 1)

# テスト
if __name__ == "__main__":
    initial_board = (
        (-GIRAFFE, -LION, -ELEPHANT),
        (EMPTY, -CHICK, EMPTY),
        (EMPTY, CHICK, EMPTY),
        (ELEPHANT, LION, GIRAFFE)
    )
    initial_state = (initial_board, (0, 0, 0), (0, 0, 0), 1)
    
    idx = state_to_index(initial_state)
    print(f"初期局面のインデックス: {idx}")
    
    restored = index_to_state(idx)
    print(f"復元された状態: {restored}")
    
    assert restored == initial_state
    print("アサーション成功: 相互変換が正しく機能しています！")
    
    # 別の複雑な状態のテスト (駒の合計数が整合しているもの)
    # 持ち駒: 先手はきりん1個、ひよこ1個。後手はぞう1個、ひよこ1個。
    # 盤面には: 先手ライオン(1), 後手ライオン(-1), 先手きりん(2), 後手ぞう(-3)
    test_board = (
        (EMPTY, -LION, EMPTY),
        (EMPTY, EMPTY, EMPTY),
        (EMPTY, GIRAFFE, EMPTY),
        (EMPTY, LION, -ELEPHANT)
    )
    test_state = (test_board, (1, 0, 1), (0, 1, 1), 1)
    
    idx2 = state_to_index(test_state)
    restored2 = index_to_state(idx2)
    if restored2 != test_state:
        print("Test 2 failed!")
        print("Original:", test_state)
        print("Restored:", restored2)
    assert restored2 == test_state
    print("テスト2成功！")
    
def run_benchmark():
    # 速度ベンチマーク
    import time
    print("速度ベンチマーク開始...")
    
    # テスト用の状態を再定義または作成
    test_board = (
        (EMPTY, -LION, EMPTY),
        (EMPTY, EMPTY, EMPTY),
        (EMPTY, GIRAFFE, EMPTY),
        (EMPTY, LION, -ELEPHANT)
    )
    test_state = (test_board, (1, 0, 1), (0, 1, 1), 1)
    idx2 = state_to_index(test_state)

    # state_to_index のベンチマーク
    t0 = time.time()
    n_iter = 100000
    for _ in range(n_iter):
        _ = state_to_index(test_state)
    t1 = time.time()
    speed_to = n_iter / (t1 - t0)
    print(f"state_to_index: {speed_to:.2f} 回/秒 (1回あたり {1000000*(t1-t0)/n_iter:.2f} μs)")
    
    # index_to_state のベンチマーク
    t0 = time.time()
    for _ in range(n_iter):
        _ = index_to_state(idx2)
    t1 = time.time()
    speed_from = n_iter / (t1 - t0)
    print(f"index_to_state: {speed_from:.2f} 回/秒 (1回あたり {1000000*(t1-t0)/n_iter:.2f} μs)")

    # 解析時間推定の計算
    # どうぶつ将棋の対称性を考慮した総局面数 (理論値) は約 1.2億局面。
    # ここでは、探索可能な実質的な非末端局面数を約 5,000,000 〜 10,000,000 局面、
    # 辺の数 (遷移数) を 20,000,000 程度 (実際の edges.bin のサイズより) として見積もります。
    # 2.5億局面をフルに考慮した場合の見積もりも併記します。
    
    # 1. 実際の edges.bin に基づく実質ノード数での見積もり (M=500万, E=2000万)
    M_real = 5000000
    E_real = 20000000
    time_py_real = (M_real / speed_from) + (E_real / speed_to)
    
    # 2. 理論上の最大状態空間 (M=1.2億, E=6億)
    M_max = 120000000
    E_max = 600000000
    time_py_max = (M_max / speed_from) + (E_max / speed_to)
    
    # Numba JIT の加速率 (一般的に 10倍〜20倍程度高速)
    speed_up = 10.0
    time_numba_real = time_py_real / speed_up
    time_numba_max = time_py_max / speed_up
    
    print("\n--- 📊 完全解析時間 (後退解析) の推定値 ---")
    print(f"【見積りA: 実質探索範囲 (edges.bin 準拠 / M={M_real:,}, E={E_real:,})】")
    print(f"  - Python実行時の純粋変換時間 : {time_py_real:.2f} 秒 ({time_py_real/60:.2f} 分)")
    print(f"  - Numba JIT化後の推定変換時間 (約{speed_up}倍速): {time_numba_real:.2f} 秒 ({time_numba_real/60:.2f} 分)")
    print(f"【見積りB: 理論上の最大盤面空間 (M={M_max:,}, E={E_max:,})】")
    print(f"  - Python実行時の純粋変換時間 : {time_py_max/3600:.2f} 時間")
    print(f"  - Numba JIT化後の推定変換時間 (約{speed_up}倍速): {time_numba_max/3600:.2f} 時間")
    print("\n※実際の完全解析 (solve.py) は Numba + マルチプロセス超最適化されているため、")
    print("  マルチコア (CPU数) に応じた並列化により、インデックス変換自体はさらに高速に行われます。")
    print("  ただし、逆遷移グラフのソートやデータベースのGzip圧縮保存などのI/Oオーバーヘッドが追加されます。")

# テスト
if __name__ == "__main__":
    initial_board = (
        (-GIRAFFE, -LION, -ELEPHANT),
        (EMPTY, -CHICK, EMPTY),
        (EMPTY, CHICK, EMPTY),
        (ELEPHANT, LION, GIRAFFE)
    )
    initial_state = (initial_board, (0, 0, 0), (0, 0, 0), 1)
    
    idx = state_to_index(initial_state)
    print(f"初期局面のインデックス: {idx}")
    
    restored = index_to_state(idx)
    print(f"復元された状態: {restored}")
    
    assert restored == initial_state
    print("アサーション成功: 相互変換が正しく機能しています！")
    
    # 別の複雑な状態のテスト (駒の合計数が整合しているもの)
    # 持ち駒: 先手はきりん1個、ひよこ1個。後手はぞう1個、ひよこ1個。
    # 盤面には: 先手ライオン(1), 後手ライオン(-1), 先手きりん(2), 後手ぞう(-3)
    test_board = (
        (EMPTY, -LION, EMPTY),
        (EMPTY, EMPTY, EMPTY),
        (EMPTY, GIRAFFE, EMPTY),
        (EMPTY, LION, -ELEPHANT)
    )
    test_state = (test_board, (1, 0, 1), (0, 1, 1), 1)
    
    idx2 = state_to_index(test_state)
    restored2 = index_to_state(idx2)
    if restored2 != test_state:
        print("Test 2 failed!")
        print("Original:", test_state)
        print("Restored:", restored2)
        assert False
    print("テスト2成功！")
    
    run_benchmark()
