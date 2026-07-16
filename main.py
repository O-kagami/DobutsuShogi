import time
from tqdm import tqdm
from game_state import DobutsuShogiState
from analyzer import simple_analysis, solved_analysis, solved_db, load_db, get_state_key
from player import get_human_move

def format_kifu(path, start_turn=1):
    """棋譜を美しい絵文字形式に変換します"""
    piece_names = {1: "🦁", 2: "🦒", 3: "🐘", 4: "🐥", 5: "🐔"}
    cols = ["３", "２", "１"]
    rows = ["一", "二", "三", "四"]
    
    kifu_steps = []
    current_turn = start_turn
    for i, (move, p_type) in enumerate(path):
        turn_mark = "▲" if current_turn == 1 else "△"
        p_emoji = piece_names.get(p_type, "？")
        tr, tc = (move[3], move[4]) if move[0] == 'move' else (move[2], move[3])
        target_pos = f"{cols[tc]}{rows[tr]}"
        action = "打" if move[0] == 'drop' else ""
        kifu_steps.append(f"{i+1:2d} {turn_mark}{target_pos}{p_emoji}{action}")
        current_turn *= -1
    return "\n".join(kifu_steps)

def run_analysis():
    """解析モードの実行"""
    print("\n--- 🔍 解析モード ---")
    state = DobutsuShogiState() 
    state.display()
    
    start_time = time.time()
    
    if solved_db is not None:
        print("💡 完全解析データベースを使用して解析中...")
        best_score, best_path = solved_analysis(state)
        key = get_state_key(state)
        _, dist = solved_db.get(key, (0, 0))
        dist_str = f" ({dist} 手詰)" if best_score != 0 and dist != 999 else ""
    else:
        print("⚠️ 完全解析データベースが見つからないため、ミニマックス法で探索します。")
        memo.clear()
        moves = state.get_legal_moves()
        best_score = -float('inf') if state.turn == 1 else float('inf')
        best_path = []

        for m in tqdm(moves, desc="全手解析中"):
            next_s = state.make_move(m)
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            score, path = simple_analysis(next_s, 4)
            
            full_path = [(m, p_type)] + path
            if (state.turn == 1 and score > best_score) or (state.turn == -1 and score < best_score):
                best_score = score
                best_path = full_path
        dist_str = ""

    end_time = time.time()
    print("\n" + "="*30)
    print(f"📈 判定: {'先手必勝 🔴' if best_score == 1 else '後手必勝 🔵' if best_score == -1 else '引き分け ⚪'}{dist_str}")
    print(f"⏱️ 解析時間: {end_time - start_time:.4f} 秒")
    print("-" * 30)
    print("📜 AIの推奨手順:")
    print(format_kifu(best_path, state.turn))
    print("="*30)

def run_battle():
    """対戦モード (人間 vs AI) の実行"""
    print("\n--- ⚔️ 対戦モード ---")
    state = DobutsuShogiState()
    
    while True:
        state.display()
        winner = state.decide_winner()
        if winner != 0:
            if winner == 1: print("\n🎉 【先手 ▲】の勝ちです！おめでとうございます！")
            else: print("\n😱 【後手 △】の勝ちです！AIが勝利しました。")
            break

        if state.turn == 1:
            # 人間のターン
            move = get_human_move(state)
            state = state.make_move(move)
        else:
            # AIのターン
            print("\n🤖 AIが考え中...")
            
            if solved_db is not None:
                # データベースがある場合：solved_analysisを利用して一瞬で最善手を選択
                _, best_path = solved_analysis(state)
                if best_path:
                    best_move = best_path[0][0]
                else:
                    best_move = state.get_legal_moves()[0]
            else:
                from analyzer import memo
                memo.clear()
                moves = state.get_legal_moves()
                best_score = float('inf') # AIは後手
                best_move = moves[0]
                
                for m in tqdm(moves, desc="AI思考中", leave=False):
                    score, _ = simple_analysis(state.make_move(m), 2) # 対戦は深さ6で高速化
                    if score < best_score:
                        best_score = score
                        best_move = m
            
            # AIの指し手を棋譜形式で1手だけ表示
            p_type = abs(state.board[best_move[1]][best_move[2]]) if best_move[0]=='move' else best_move[1]
            print(f"🤖 AIの指し手: {format_kifu([(best_move, p_type)], -1)}")
            state = state.make_move(best_move)

def main():
    while True:
        if solved_db is None:
            load_db()
            
        print("\n🐾 どうぶつ将棋 メインメニュー 🐾")
        print(f"データベース状態: {'Loaded ✅' if solved_db is not None else 'Not Found ❌'}")
        print("1: AIと対戦する (人間 ▲ vs AI △)")
        print("2: 現在の局面（初期配置）を解析する")
        if solved_db is None:
            print("3: 後退解析を実行して完全解析データベースを生成する")
        else:
            print("3: 完全解析データベースを再生成する")
        print("q: 終了する")
        mode = input("選択してください: ").lower()

        if mode == "1":
            run_battle()
        elif mode == "2":
            run_analysis()
        elif mode == "3":
            print("\n🚨 完全解析を実行します。これには約1分程度かかります。")
            confirm = input("実行しますか？ (y/n): ").lower()
            if confirm == 'y':
                import solve
                solve.solve()
                load_db()
        elif mode == "q":
            print("バイバイ！")
            break
        else:
            print("❌ 正しい番号を入力してください。")

if __name__ == "__main__":
    main()