import time
from flask import Flask, render_template, jsonify
from game_state import DobutsuShogiState
from analyzer import simple_analysis, memo

app = Flask(__name__)

def get_piece_emoji(piece):
    mapping = {1:"🦁", 2:"🦒", 3: "🐘", 4: "🐥", 5: "🐔", -1: "▽🦁", -2: "▽🦒", -3: "▽🐘", -4: "▽🐥", 0: ""}
    return mapping.get(piece, "")

def format_kifu_web(path, start_turn=1):
    """Web表示用に棋譜を整形（通し番号付き）"""
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
        # 「1: ▲３二🦁」という形式にする
        kifu_steps.append(f"{i+1:2d}: {turn_mark}{target_pos}{p_emoji}{action}")
        current_turn *= -1
    return kifu_steps

@app.route('/')
def index():
    state = DobutsuShogiState()
    return render_template('index.html', board=state.board, get_emoji=get_piece_emoji)

@app.route('/analyze', methods=['POST'])
def analyze():
    state = DobutsuShogiState()
    memo.clear()
    moves = state.get_legal_moves()
    best_score = -float('inf') if state.turn == 1 else float('inf')
    best_path = []

    start_time = time.time()
    for m in moves:
        next_s = state.make_move(m)
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        score, path = simple_analysis(next_s, 4)
        
        full_path = [(m, p_type)] + path
        if (state.turn == 1 and score > best_score) or (state.turn == -1 and score < best_score):
            best_score = score
            best_path = full_path

    end_time = time.time()
    result_text = '先手必勝 🔴' if best_score == 1 else '後手必勝 🔵' if best_score == -1 else '引き分け ⚪'
    kifu = format_kifu_web(best_path, state.turn)
    
    return jsonify({
        "result": result_text,
        "time": round(end_time - start_time, 2),
        "kifu": kifu
    })

if __name__ == "__main__":
    app.run(debug=True)