from constants import *

def get_human_move(state):
    """
    人間がキーボードから手を選択するための関数です。
    指せる手を一覧表示し、その番号を入力させます。
    """
    moves = state.get_legal_moves()
    
    print("\n" + "="*25)
    print("      👉 あなたの番です")
    print("="*25)
    print("指せる手の一覧:")
    
    # 駒の名前の定義（表示用）
    piece_names = {1: "🦁", 2: "🦒", 3: "🐘", 4: "🐥", 5: "🐔"}
    cols = ["３", "２", "１"]
    rows = ["一", "二", "三", "四"]

    for i, m in enumerate(moves):
        if m[0] == 'move':
            # m = ('move', fr, fc, tr, tc)
            p_type = abs(state.board[m[1]][m[2]])
            p_name = piece_names.get(p_type, "？")
            from_pos = f"{cols[m[2]]}{rows[m[1]]}"
            to_pos = f"{cols[m[4]]}{rows[m[3]]}"
            print(f"{i:2d}: {p_name} ({from_pos} -> {to_pos})")
        elif m[0] == 'drop':
            # m = ('drop', p_type, tr, tc)
            p_name = piece_names.get(m[1], "？")
            to_pos = f"{cols[m[3]]}{rows[m[2]]}"
            print(f"{i:2d}: {p_name} を {to_pos} に打つ")

    while True:
        try:
            user_input = input("\n指したい手の番号を入力してください: ")
            choice = int(user_input)
            if 0 <= choice < len(moves):
                return moves[choice]
            else:
                print(f"❌ 0 から {len(moves)-1} の範囲で入力してください。")
        except ValueError:
            print("❌ 半角数字で番号を入力してください。")