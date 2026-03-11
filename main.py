import time
from flask import Flask, render_template, request, jsonify, session
from game_state import DobutsuShogiState
from analyzer import simple_analysis, memo

app = Flask(__name__)
app.secret_key = "taiki_shogi_secret_key"

def get_piece_emoji(piece):
    mapping = {
        1:"🦁", 2:"🦒", 3: "🐘", 4: "🐥", 5: "🐔",
        -1: "▽🦁", -2: "▽🦒", -3: "▽🐘", -4: "▽🐥", -5: "▽🐔",
        0: ""
    }
    return mapping.get(piece, "")

def format_single_move(move, p_type, turn):
    piece_names = {1: "🦁", 2: "🦒", 3: "🐘", 4: "🐥", 5: "🐔"}
    cols = ["３", "２", "１"]
    rows = ["一", "二", "三", "四"]
    turn_mark = "▲" if turn == 1 else "△"
    p_emoji = piece_names.get(p_type, "？")
    tr, tc = (move[3], move[4]) if move[0] == 'move' else (move[2], move[3])
    target_pos = f"{cols[tc]}{rows[tr]}"
    action = "打" if move[0] == 'drop' else ""
    return f"{turn_mark}{target_pos}{p_emoji}{action}"

# 🌟 セッション保存用のヘルパー（数値キーを文字列にする）
def serialize_hand(hand):
    return {str(k): v for k, v in hand.items()}

# 🌟 復元用のヘルパー（文字列キーを数値に戻す）
def deserialize_hand(hand):
    return {int(k): v for k, v in hand.items()}

@app.route('/')
def index():
    state = DobutsuShogiState()
    session['board'] = state.board
    session['turn'] = state.turn
    session['hand_p1'] = serialize_hand(state.hand_p1) # 🌟 修正
    session['hand_p2'] = serialize_hand(state.hand_p2) # 🌟 修正
    
    moves = state.get_legal_moves()
    move_options = []
    for i, m in enumerate(moves):
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        move_options.append({"id": i, "text": format_single_move(m, p_type, state.turn)})
        
    return render_template('index.html', board=state.board, move_options=move_options, get_emoji=get_piece_emoji)

@app.route('/battle', methods=['POST'])
def battle():
    try: # 🌟 エラー内容を捕捉できるようにする
        data = request.json
        move_idx = int(data.get('move_idx'))
        
        state = DobutsuShogiState(
            board=session['board'],
            hand_p1=deserialize_hand(session['hand_p1']), # 🌟 修正
            hand_p2=deserialize_hand(session['hand_p2']), # 🌟 修正
            turn=session['turn']
        )
        
        moves = state.get_legal_moves()
        state = state.make_move(moves[move_idx])
        
        winner = state.decide_winner()
        if winner != 0:
            return jsonify({"board": state.board, "winner": winner})

        memo.clear()
        ai_moves = state.get_legal_moves()
        if not ai_moves:
            return jsonify({"board": state.board, "winner": 1})

        best_score = float('inf')
        best_move = ai_moves[0]
        for m in ai_moves:
            score, _ = simple_analysis(state.make_move(m), 4)
            if score < best_score:
                best_score = score
                best_move = m
                
        state = state.make_move(best_move)
        winner = state.decide_winner()

        session['board'] = state.board
        session['turn'] = state.turn
        session['hand_p1'] = serialize_hand(state.hand_p1) # 🌟 修正
        session['hand_p2'] = serialize_hand(state.hand_p2) # 🌟 修正
        
        next_moves = state.get_legal_moves()
        next_options = []
        for i, m in enumerate(next_moves):
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_options.append({"id": i, "text": format_single_move(m, p_type, state.turn)})

        return jsonify({
            "board": state.board,
            "winner": winner,
            "next_options": next_options
        })
    except Exception as e:
        print(f"Server Error: {e}") # ターミナルにエラー内容を表示
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)