from flask import Flask, render_template, request, jsonify, session
from game_state import DobutsuShogiState
from analyzer import simple_analysis, memo

app = Flask(__name__)
app.secret_key = "taiki_shogi_secret"

def get_piece_emoji(piece):
    mapping = {1:"🦁", 2:"🦒", 3: "🐘", 4: "🐥", 5: "🐔", -1: "▽🦁", -2: "▽🦒", -3: "▽🐘", -4: "▽🐥", 0: ""}
    return mapping.get(piece, "")

def format_single_move(move, p_type, turn):
    """1つの指し手を『▲３一🦒』の形式に整形する"""
    piece_names = {1: "🦁", 2: "🦒", 3: "🐘", 4: "🐥", 5: "🐔"}
    cols = ["３", "２", "１"]
    rows = ["一", "二", "三", "四"]
    turn_mark = "▲" if turn == 1 else "△"
    p_emoji = piece_names.get(p_type, "？")
    
    # 移動先座標
    tr, tc = (move[3], move[4]) if move[0] == 'move' else (move[2], move[3])
    target_pos = f"{cols[tc]}{rows[tr]}"
    action = "打" if move[0] == 'drop' else ""
    return f"{turn_mark}{target_pos}{p_emoji}{action}"

@app.route('/')
def index():
    state = DobutsuShogiState()
    session['board'] = state.board
    session['turn'] = state.turn
    session['hand_p1'] = state.hand_p1
    session['hand_p2'] = state.hand_p2
    
    moves = state.get_legal_moves()
    # ボタンに表示する名前のリストを作成
    move_names = []
    for m in moves:
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        move_names.append(format_single_move(m, p_type, state.turn))
        
    return render_template('index.html', board=state.board, move_names=move_names, get_emoji=get_piece_emoji)

@app.route('/move', methods=['POST'])
def move():
    data = request.json
    move_idx = int(data.get('move_idx'))
    
    state = DobutsuShogiState(board=session['board'], hand_p1=session['hand_p1'], hand_p2=session['hand_p2'], turn=session['turn'])
    moves = state.get_legal_moves()
    state = state.make_move(moves[move_idx])

    if state.decide_winner() != 0:
        return jsonify({"board": state.board, "winner": state.decide_winner()})

    # AI思考
    memo.clear()
    ai_moves = state.get_legal_moves()
    best_score = float('inf')
    best_move = ai_moves[0]
    for m in ai_moves:
        score, _ = simple_analysis(state.make_move(m), 4)
        if score < best_score:
            best_score = score
            best_move = m
    
    state = state.make_move(best_move)
    session['board'], session['turn'], session['hand_p1'], session['hand_p2'] = state.board, state.turn, state.hand_p1, state.hand_p2
    
    # 次の人間側の手を整形
    next_moves = state.get_legal_moves()
    next_move_names = []
    for m in next_moves:
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        next_move_names.append(format_single_move(m, p_type, state.turn))
    
    return jsonify({
        "board": state.board, 
        "winner": state.decide_winner(), 
        "next_move_names": next_move_names
    })

if __name__ == "__main__":
    app.run(debug=True)