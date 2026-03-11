import time
from flask import Flask, render_template, request, jsonify, session
from game_state import DobutsuShogiState
from analyzer import simple_analysis

app = Flask(__name__)
app.secret_key = "shogi_ultimate_key"

def get_piece_emoji(piece):
    mapping = {1:"🦁", 2:"🦒", 3:"🐘", 4:"🐥", 5:"🐔", -1:"▽🦁", -2:"▽🦒", -3:"▽🐘", -4:"▽🐥", -5:"▽🐔", 0:""}
    return mapping.get(piece, "")

def format_single_move(move, p_type, turn):
    piece_names = {1:"🦁", 2:"🦒", 3:"🐘", 4:"🐥", 5:"🐔"}
    cols, rows = ["３", "２", "１"], ["一", "二", "三", "四"]
    tr, tc = (move[3], move[4]) if move[0] == 'move' else (move[2], move[3])
    return f"{'▲' if turn == 1 else '△'}{cols[tc]}{rows[tr]}{piece_names.get(p_type, '？')}{'打' if move[0] == 'drop' else ''}"

def serialize_hand(hand): return {str(k): v for k, v in hand.items()}
def deserialize_hand(hand): return {int(k): v for k, v in hand.items()}

def save_to_history():
    """現在の状態を履歴スタックに保存"""
    history = session.get('history', [])
    current_state = {
        "board": session['board'],
        "turn": session['turn'],
        "hand_p1": session['hand_p1'],
        "hand_p2": session['hand_p2']
    }
    history.append(current_state)
    session['history'] = history

@app.route('/')
def index():
    state = DobutsuShogiState()
    session['board'], session['turn'] = state.board, state.turn
    session['hand_p1'], session['hand_p2'] = serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
    session['history'] = []
    
    moves = state.get_legal_moves()
    move_options = []
    for i, m in enumerate(moves):
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        move_options.append({"id": i, "text": format_single_move(m, p_type, state.turn)})
        
    return render_template('index.html', board=state.board, hand1=state.hand_p1, hand2=state.hand_p2, move_options=move_options, get_emoji=get_piece_emoji)

@app.route('/battle', methods=['POST'])
def battle():
    try:
        data = request.json
        # 1. 指す前の状態を保存
        save_to_history()
        
        state = DobutsuShogiState(session['board'], deserialize_hand(session['hand_p1']), deserialize_hand(session['hand_p2']), session['turn'])
        moves = state.get_legal_moves()
        state = state.make_move(moves[int(data['move_idx'])])
        
        winner = state.decide_winner()
        if winner != 0:
            return jsonify({"board": state.board, "hand1": state.hand_p1, "hand2": state.hand_p2, "winner": winner})

        # 2. AIの思考
        ai_score, ai_path = simple_analysis(state, 5)
        if ai_path:
            state = state.make_move(ai_path[0][0])
        
        winner = state.decide_winner()
        session['board'], session['turn'] = state.board, state.turn
        session['hand_p1'], session['hand_p2'] = serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
        
        next_options = []
        for i, m in enumerate(state.get_legal_moves()):
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_options.append({"id": i, "text": format_single_move(m, p_type, state.turn)})

        return jsonify({"board": state.board, "hand1": state.hand_p1, "hand2": state.hand_p2, "winner": winner, "next_options": next_options})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/undo', methods=['POST'])
def undo():
    history = session.get('history', [])
    if len(history) >= 1:
        # 人間の番の直前まで戻す
        last_state = history.pop()
        session['board'], session['turn'] = last_state['board'], last_state['turn']
        session['hand_p1'], session['hand_p2'] = last_state['hand_p1'], last_state['hand_p2']
        session['history'] = history
        
        state = DobutsuShogiState(session['board'], deserialize_hand(session['hand_p1']), deserialize_hand(session['hand_p2']), session['turn'])
        next_options = [{"id": i, "text": format_single_move(m, abs(state.board[m[1]][m[2]]) if m[0]=='move' else m[1], state.turn)} for i, m in enumerate(state.get_legal_moves())]
        
        return jsonify({"board": state.board, "hand1": state.hand_p1, "hand2": state.hand_p2, "winner": 0, "next_options": next_options})
    return jsonify({"error": "No history"}), 400

if __name__ == "__main__":
    app.run(debug=True)