import os
from flask import Flask, render_template, request, jsonify, session
from game_state import DobutsuShogiState
from analyzer import simple_analysis
from constants import *

app = Flask(__name__)
app.secret_key = "taiki_tuned_ai_v1"

def get_piece_emoji(piece):
    mapping = {1:"🦁", 2:"🦒", 3:"🐘", 4:"🐥", 5:"🐔", -1:"🦁", -2:"🦒", -3:"🐘", -4:"🐥", -5:"🐔", 0:""}
    return mapping.get(piece, "")

def format_single_move(move, p_type, turn):
    piece_names = {1:"🦁", 2:"🦒", 3:"🐘", 4:"🐥", 5:"🐔"}
    cols, rows = ["３", "２", "１"], ["一", "二", "三", "四"]
    tr, tc = (move[3], move[4]) if move[0] == 'move' else (move[2], move[3])
    return f"{'▲' if turn == 1 else '△'}{cols[tc]}{rows[tr]}{piece_names.get(p_type, '？')}{'打' if move[0] == 'drop' else ''}"

def serialize_hand(hand): return {str(k): v for k, v in hand.items()}
def deserialize_hand(hand): return {int(k): v for k, v in hand.items()}

@app.route('/')
def index():
    state = DobutsuShogiState()
    session['board'], session['turn'] = state.board, state.turn
    session['hand_p1'], session['hand_p2'] = serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
    session['history'] = []
    
    moves = state.get_legal_moves()
    move_options = [{"id": i, "text": format_single_move(m, abs(state.board[m[1]][m[2]]) if m[0]=='move' else m[1], state.turn)} for i, m in enumerate(moves)]
    return render_template('index.html', board=state.board, hand1=state.hand_p1, hand2=state.hand_p2, move_options=move_options, get_emoji=get_piece_emoji)

@app.route('/battle', methods=['POST'])
def battle():
    try:
        data = request.json
        history = session.get('history', [])
        history.append({"board": session['board'], "turn": session['turn'], "hand_p1": session['hand_p1'], "hand_p2": session['hand_p2']})
        session['history'] = history

        state = DobutsuShogiState(session['board'], deserialize_hand(session['hand_p1']), deserialize_hand(session['hand_p2']), session['turn'])
        
        # 1. プレイヤーの手を適用
        moves = state.get_legal_moves()
        state = state.make_move(moves[int(data['move_idx'])])
        mid_board, mid_h1, mid_h2 = [row[:] for row in state.board], serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
        
        if state.decide_winner() != 0:
            return jsonify({"board": state.board, "hand1": mid_h1, "hand2": mid_h2, "winner": state.decide_winner(), "mid_board": mid_board})

        # 2. AIの思考（AI_SETTINGS["DEPTH"] を参照）
        _, ai_path = simple_analysis(state, AI_SETTINGS["DEPTH"])
        if ai_path: state = state.make_move(ai_path[0][0])
        
        session['board'], session['turn'] = state.board, state.turn
        session['hand_p1'], session['hand_p2'] = serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
        next_options = [{"id": i, "text": format_single_move(m, abs(state.board[m[1]][m[2]]) if m[0]=='move' else m[1], state.turn)} for i, m in enumerate(state.get_legal_moves())]

        return jsonify({"mid_board": mid_board, "mid_hand1": mid_h1, "mid_hand2": mid_h2, "board": state.board, "hand1": session['hand_p1'], "hand2": session['hand_p2'], "winner": state.decide_winner(), "next_options": next_options})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/undo', methods=['POST'])
def undo():
    history = session.get('history', [])
    if history:
        last = history.pop()
        session.update({'board': last['board'], 'turn': last['turn'], 'hand_p1': last['hand_p1'], 'hand_p2': last['hand_p2'], 'history': history})
        state = DobutsuShogiState(session['board'], deserialize_hand(session['hand_p1']), deserialize_hand(session['hand_p2']), session['turn'])
        next_options = [{"id": i, "text": format_single_move(m, abs(state.board[m[1]][m[2]]) if m[0]=='move' else m[1], state.turn)} for i, m in enumerate(state.get_legal_moves())]
        return jsonify({"board": state.board, "hand1": session['hand_p1'], "hand2": session['hand_p2'], "winner": 0, "next_options": next_options})
    return jsonify({"error": "No history"}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)