import os
from flask import Flask, render_template, request, jsonify, session
from game_state import DobutsuShogiState
from analyzer import time_limited_analysis
from constants import *

app = Flask(__name__)
app.secret_key = "shogi_web_public_secret_key" # 汎用的なキーに変更

def get_piece_emoji(piece):
    # 向きで判断するため記号なし
    mapping = {1:"🦁", 2:"🦒", 3:"🐘", 4:"🐥", 5:"🐔", -1:"🦁", -2:"🦒", -3:"🐘", -4:"🐥", -5:"🐔", 0:""}
    return mapping.get(piece, "")

def serialize_hand(hand): return {str(k): v for k, v in hand.items()}
def deserialize_hand(hand): return {int(k): v for k, v in hand.items()}

def get_rich_moves(state):
    moves = state.get_legal_moves()
    rich_moves = []
    for i, m in enumerate(moves):
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        rich_moves.append({
            "id": i, "type": m[0],
            "from_r": m[1] if m[0]=='move' else -1, "from_c": m[2] if m[0]=='move' else -1,
            "to_r": m[3] if m[0]=='move' else m[2], "to_c": m[4] if m[0]=='move' else m[3],
            "p_type": p_type
        })
    return rich_moves

@app.route('/')
def index():
    state = DobutsuShogiState()
    session['board'], session['turn'] = state.board, state.turn
    session['hand_p1'], session['hand_p2'] = serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
    session['history'] = []
    session['rep_history'] = []
    return render_template('index.html', board=state.board, hand1=state.hand_p1, hand2=state.hand_p2, move_options=get_rich_moves(state), get_emoji=get_piece_emoji)

@app.route('/battle', methods=['POST'])
def battle():
    try:
        data = request.json
        history = session.get('history', [])
        history.append({
            "board": session['board'],
            "turn": session['turn'],
            "hand_p1": session['hand_p1'],
            "hand_p2": session['hand_p2'],
            "rep_history": session.get('rep_history', [])
        })
        session['history'] = history

        state = DobutsuShogiState(
            session['board'],
            deserialize_hand(session['hand_p1']),
            deserialize_hand(session['hand_p2']),
            session['turn'],
            history=session.get('rep_history', [])
        )
        
        moves = state.get_legal_moves()
        state = state.make_move(moves[int(data['move_idx'])])
        mid_data = {"board": [row[:] for row in state.board], "hand1": serialize_hand(state.hand_p1), "hand2": serialize_hand(state.hand_p2)}
        
        if state.decide_winner() != 0:
            return jsonify({**mid_data, "winner": state.decide_winner(), "mid_board": mid_data["board"]})

        # 時間制限付き探索でAIの手を決定
        _, ai_path = time_limited_analysis(state, AI_SETTINGS.get("TIME_LIMIT_SEC", 1.0))
        if ai_path:
            state = state.make_move(ai_path[0][0])
        
        session['board'], session['turn'] = state.board, state.turn
        session['hand_p1'], session['hand_p2'] = serialize_hand(state.hand_p1), serialize_hand(state.hand_p2)
        session['rep_history'] = state.history
        
        return jsonify({
            "mid_board": mid_data["board"], "mid_hand1": mid_data["hand1"], "mid_hand2": mid_data["hand2"],
            "board": state.board, "hand1": session['hand_p1'], "hand2": session['hand_p2'],
            "winner": state.decide_winner(), "next_options": get_rich_moves(state)
        })
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/undo', methods=['POST'])
def undo():
    history = session.get('history', [])
    if history:
        last = history.pop()
        session.update({
            'board': last['board'],
            'turn': last['turn'],
            'hand_p1': last['hand_p1'],
            'hand_p2': last['hand_p2'],
            'rep_history': last.get('rep_history', []),
            'history': history
        })
        state = DobutsuShogiState(session['board'], deserialize_hand(session['hand_p1']), deserialize_hand(session['hand_p2']), session['turn'])
        return jsonify({"board": state.board, "hand1": session['hand_p1'], "hand2": session['hand_p2'], "winner": 0, "next_options": get_rich_moves(state)})
    return jsonify({"error": "No history"}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)