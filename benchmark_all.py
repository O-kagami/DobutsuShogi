import time
import os
import gzip
import numpy as np
import multiprocessing
from numba import njit

# solve.py および state_utils からインデクサーとヘルパーをインポート
from solve import (
    EMPTY, LION, GIRAFFE, ELEPHANT, CHICK, HEN,
    index_to_state, state_to_index, get_legal_moves_light, make_move_light,
    decide_winner_light, is_check_light, is_terminal_state,
    get_canonical_state, get_active_perspective_state
)
from state_utils import pack_state_raw

# ユーザー指定の局面数
TOTAL_INDEX_SPACE = 1567925964  # インデックス全体の範囲
TOTAL_FEASIBLE_STATES = 246803167  # 対称性を考慮しない実現可能局面数
M_MAX = 123401583  # 対称性（左右反転など）を考慮した、実際に solve.py が保持する非末端局面ノード数 (M)
E_MAX = M_MAX * 5  # 平均合法手数を 5 と仮定したときのエッジ総数 (E)

@njit
def _benchmark_bfs_inner(n_iter, dummy_idx, tmp_moves):
    for _ in range(n_iter):
        u_state = index_to_state(dummy_idx)
        legal_count = get_legal_moves_light(u_state, tmp_moves)
        for i in range(legal_count):
            move = tmp_moves[i]
            next_state = make_move_light(u_state, move)
            normalized_next = get_canonical_state(get_active_perspective_state(next_state))
            term = is_terminal_state(normalized_next)
            if term == 0:
                _ = state_to_index(normalized_next)

def benchmark_bfs_cpu_loop(n_iter):
    dummy_idx = 374195338
    tmp_moves = np.zeros((40, 5), dtype=np.int8)
    
    # ウォームアップ
    _benchmark_bfs_inner(1, dummy_idx, tmp_moves)
    
    t0 = time.time()
    _benchmark_bfs_inner(n_iter, dummy_idx, tmp_moves)
    t1 = time.time()
    return t1 - t0

@njit
def _benchmark_retro_inner(M, edge_starts, edge_from_csr, V, dist, max_dist_next, Q_arr, q_head, q_tail, has_winning_terminal, out_degrees):
    # 後退解析ループ
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
                V[p] = 1
                dist[p] = dist_u + 1
                Q_arr[q_tail] = p
                q_tail += 1
            else:
                out_degrees[p] -= 1
                if dist_u > max_dist_next[p]:
                    max_dist_next[p] = dist_u
                if out_degrees[p] == 0 and not has_winning_terminal[p]:
                    V[p] = -1
                    dist[p] = max_dist_next[p] + 1
                    Q_arr[q_tail] = p
                    q_tail += 1

def benchmark_retrograde_propagation(M, edge_starts, edge_from_csr, has_winning_terminal, out_degrees):
    # 伝播ループの速度測定用のダミー変数
    V = np.zeros(M, dtype=np.int8)
    dist = np.full(M, 255, dtype=np.uint8)
    max_dist_next = np.zeros(M, dtype=np.uint8)
    
    Q_arr = np.zeros(M + 100, dtype=np.uint32)
    q_head = 0
    q_tail = 0
    
    # 初期確定
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
            
    t0 = time.time()
    _benchmark_retro_inner(M, edge_starts, edge_from_csr, V, dist, max_dist_next, Q_arr, q_head, q_tail, has_winning_terminal, out_degrees)
    t1 = time.time()
    return t1 - t0

def benchmark_gzip_saving(n_iter):
    temp_file = "temp_bench_db.json.gz"
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    t0 = time.time()
    with gzip.open(temp_file, "wt", encoding="utf-8") as f:
        first = True
        for i in range(n_iter):
            # ダミーの書き出しデータ作成
            g_idx = 374195338
            state = index_to_state(g_idx)
            packed = pack_state_raw(state) & ((1 << 60) - 1)
            key = f"{packed:015x}"
            val = 1
            d = 5
            
            if not first:
                f.write(",")
            f.write(f'"{key}":[{val},{d}]')
            first = False
            
            # 末端局面の追記（実際の save_chunk_worker に合わせる）
            f.write(f',"{key}_t":[-1,0]')
            
    t1 = time.time()
    if os.path.exists(temp_file):
        os.remove(temp_file)
    return t1 - t0

def run_all_benchmarks():
    print("====================================================")
    print("🐾 どうぶつ将棋 完全解析全ステップベンチマーク 🐾")
    print(f"想定する総局面空間数 (Sum): {TOTAL_INDEX_SPACE:,}")
    print(f"対称性を考慮しない実現可能局面数: {TOTAL_FEASIBLE_STATES:,}")
    print(f"実質的な非末端局面ノード数 M: {M_MAX:,} (対称性考慮)")
    print(f"想定エッジ数 E: {E_MAX:,} (平均合法手 5 手と仮定)")
    print("====================================================\n")

    # ----------------------------------------------------
    # ステップ 1: 状態空間の列挙 (JIT BFS 遷移計算)
    # ----------------------------------------------------
    print("1. [ステップ 1: 状態空間の列挙] のベンチマーク中...")
    # JIT コンパイルをトリガーするために一度ウォームアップ実行
    _ = benchmark_bfs_cpu_loop(10)
    
    n_bfs_iter = 100000
    t_bfs = benchmark_bfs_cpu_loop(n_bfs_iter)
    bfs_speed = n_bfs_iter / t_bfs
    est_step1_time = M_MAX / bfs_speed
    print(f"  - 遷移計算速度: {bfs_speed:.0f} 局面/秒")
    print(f"  - 純粋な遷移計算の推定総時間: {est_step1_time:.2f} 秒 ({est_step1_time/60:.2f} 分)")
    print("  ※ 注意: メモリ確保や `global_to_local` 配列(約6GB)へのランダムアクセス、")
    print("    ディスクへの一時エッジファイルの書き出しオーバーヘッドにより、実際の処理時間は約1.5倍〜2倍になります。")
    print(f"    (実質的なステップ1の推定時間: {est_step1_time * 1.7 / 60:.2f} 分)\n")

    # ----------------------------------------------------
    # ステップ 2: 逆遷移グラフの構築 (NumPy Argsort)
    # ----------------------------------------------------
    print("2. [ステップ 2: 逆遷移グラフの構築] のベンチマーク中...")
    E_test = 2000000  # 200万エッジで測定
    t0 = time.time()
    # ダミーエッジデータの作成
    edges_to = np.random.randint(0, M_MAX, size=E_test, dtype=np.uint32)
    edges_from = np.random.randint(0, M_MAX, size=E_test, dtype=np.uint32)
    
    in_degrees = np.bincount(edges_to, minlength=M_MAX)
    edge_starts = np.zeros(M_MAX + 1, dtype=np.uint32)
    edge_starts[1:] = np.cumsum(in_degrees)
    
    idx_sort = np.argsort(edges_to)
    edge_from_csr = edges_from[idx_sort]
    t_step2_test = time.time() - t0
    
    # argsort (O(N log N)) のスケーリング計算
    # T_max = T_test * (E_max * log2(E_max)) / (E_test * log2(E_test))
    ratio = (E_MAX * np.log2(E_MAX)) / (E_test * np.log2(E_test))
    est_step2_time = t_step2_test * ratio
    print(f"  - 200万エッジでのソート・グラフ構築時間: {t_step2_test:.4f} 秒")
    print(f"  - {E_MAX:,} エッジへのスケールアップ推定時間: {est_step2_time:.2f} 秒 ({est_step2_time/60:.2f} 分)\n")

    # ----------------------------------------------------
    # ステップ 3: 後退解析 (Retrograde Analysis)
    # ----------------------------------------------------
    print("3. [ステップ 3: 後退解析] のベンチマーク中...")
    # 測定用に小規模なダミーグラフを生成
    M_test = 50000
    E_test_retro = M_test * 5
    
    # グラフのトポロジーを適当に構築
    dummy_to = np.random.randint(0, M_test, size=E_test_retro, dtype=np.uint32)
    dummy_from = np.random.randint(0, M_test, size=E_test_retro, dtype=np.uint32)
    
    d_in_degrees = np.bincount(dummy_to, minlength=M_test)
    d_edge_starts = np.zeros(M_test + 1, dtype=np.uint32)
    d_edge_starts[1:] = np.cumsum(d_in_degrees)
    
    d_idx_sort = np.argsort(dummy_to)
    d_edge_from_csr = dummy_from[d_idx_sort]
    
    d_out_degrees = np.random.randint(1, 10, size=M_test, dtype=np.uint8)
    d_has_winning_terminal = np.random.choice([True, False], size=M_test, p=[0.1, 0.9])
    
    # ウォームアップ
    _ = benchmark_retrograde_propagation(M_test, d_edge_starts, d_edge_from_csr, d_has_winning_terminal, d_out_degrees.copy())
    
    # 測定
    t_retro_test = benchmark_retrograde_propagation(M_test, d_edge_starts, d_edge_from_csr, d_has_winning_terminal, d_out_degrees.copy())
    
    # スケールアップ (O(M+E) 線形)
    est_step3_time = t_retro_test * (M_MAX / M_test)
    print(f"  - {M_test:,} ノードでの後退解析伝播時間: {t_retro_test:.4f} 秒")
    print(f"  - {M_MAX:,} ノードへのスケールアップ推定時間: {est_step3_time:.2f} 秒 ({est_step3_time/60:.2f} 分)\n")

    # ----------------------------------------------------
    # ステップ 4: データベースの保存 (Gzip JSON 書き出し)
    # ----------------------------------------------------
    print("4. [ステップ 4: データベースの保存] のベンチマーク中...")
    n_save_iter = 10000
    t_save_test = benchmark_gzip_saving(n_save_iter)
    save_speed = n_save_iter / t_save_test
    
    num_workers = min(multiprocessing.cpu_count(), 16)
    est_step4_time = M_MAX / (save_speed * num_workers)
    
    print(f"  - 1コアあたりのデータベース書き出し速度: {save_speed:.0f} 局面/秒")
    print(f"  - 使用可能なCPUコア数 (並列度): {num_workers}")
    print(f"  - 並列処理時の推定総保存時間: {est_step4_time:.2f} 秒 ({est_step4_time/60:.2f} 分)")
    print("  ※ 注意: 各パーツファイルをマージする最後のI/O処理があるため、")
    print("    実際はこれに数分程度追加されます。\n")

    # ----------------------------------------------------
    # 総合時間の算出とまとめ
    # ----------------------------------------------------
    # 実際のステップ1時間を現実的な値 (1.7倍) に調整
    real_step1_time = est_step1_time * 1.7
    total_est_seconds = real_step1_time + est_step2_time + est_step3_time + est_step4_time
    total_est_hours = total_est_seconds / 3600

    print("====================================================")
    print("🏁 推定される完全解析の総所要時間まとめ")
    print("====================================================")
    print(f"  - ステップ 1 (状態空間列挙): {real_step1_time/60:.2f} 分 (I/O, メモリランダムアクセス含む)")
    print(f"  - ステップ 2 (逆遷移グラフ構築): {est_step2_time/60:.2f} 分 (Argsort ソート等)")
    print(f"  - ステップ 3 (後退解析伝播): {est_step3_time/60:.2f} 分")
    print(f"  - ステップ 4 (並列DB Gzip保存): {est_step4_time/60:.2f} 分 (マージ処理含む)")
    print("  --------------------------------------------------")
    print(f"  🔥 推定合計時間: {total_est_seconds/60:.2f} 分 ({total_est_hours:.2f} 時間)")
    print("====================================================")
    print("※ この予測は CPU 計算パワー、ディスクI/O、NumbaのJIT最適化が")
    print("   全ステージで理想的に働いた場合に基づいています。")
    print("   メモリ使用量 (約6〜8GB) が搭載RAM上限を超えてスワップが発生した場合、")
    print("   ディスクアクセスにより処理が大幅に遅延する可能性があります。")

if __name__ == "__main__":
    run_all_benchmarks()
