import time
from flask import Flask, render_template, request, jsonify, session
from game_state import DobutsuShogiState
from analyzer import simple_analysis, memo

# Flaskアプリの定義
app = Flask(__name__)
app.secret_key = "taiki_shogi_secret_key_2026"

def get_piece_emoji(piece):
    """駒の数値から絵文字への変換"""
    mapping = {
        1:"🦁", 2:"🦒", 3: "🐘", 4: "🐥", 5: "🐔",
        -1: "▽🦁", -2: "▽🦒", -3: "▽🐘", -4: "▽🐥", -5: "▽🐔",
        0: ""
    }
    return mapping.get(piece, "")

def format_single_move(move, p_type, turn):
    """ボタン表示用に指し手を整形 (例: ▲３一🦒)"""
    piece_names = {1: "🦁", 2: "🦒", 3: "🐘", 4: "🐥", 5: "🐔"}
    cols = ["３", "２", "１"]
    rows = ["一", "二", "三", "四"]
    turn_mark = "▲" if turn == 1 else "△"
    p_emoji = piece_names.get(p_type, "？")
    tr, tc = (move[3], move[4]) if move[0] == 'move' else (move[2], move[3])
    target_pos = f"{cols[tc]}{rows[tr]}"
    action = "打" if move[0] == 'drop' else ""
    return f"{turn_mark}{target_pos}{p_emoji}{action}"

def serialize_hand(hand):
    """セッション保存用に辞書のキーを文字列に変換"""
    return {str(k): v for k, v in hand.items()}

def deserialize_hand(hand):
    """セッションから復元する際にキーを数値に戻す"""
    return {int(k): v for k, v in hand.items()}

@app.route('/')
def index():
    """初期画面の表示とセッションの初期化"""
    state = DobutsuShogiState()
    session['board'] = state.board
    session['turn'] = state.turn
    session['hand_p1'] = serialize_hand(state.hand_p1)
    session['hand_p2'] = serialize_hand(state.hand_p2)
    
    moves = state.get_legal_moves()
    move_options = []
    for i, m in enumerate(moves):
        p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
        move_options.append({"id": i, "text": format_single_move(m, p_type, state.turn)})
        
    return render_template('index.html', 
                           board=state.board, 
                           hand1=state.hand_p1,
                           hand2=state.hand_p2,
                           move_options=move_options, 
                           get_emoji=get_piece_emoji)

@app.route('/battle', methods=['POST'])
def battle():
    """対局の進行処理"""
    try:
        data = request.json
        move_idx = int(data.get('move_idx'))
        
        # セッションから現在の状態を復元
        state = DobutsuShogiState(
            board=session['board'],
            hand_p1=deserialize_hand(session['hand_p1']),
            hand_p2=deserialize_hand(session['hand_p2']),
            turn=session['turn']
        )
        
        # 1. 人間の手を適用
        moves = state.get_legal_moves()
        state = state.make_move(moves[move_idx])
        
        # 人間の手で決着がついたかチェック
        winner = state.decide_winner()
        if winner != 0:
            return jsonify({
                "board": state.board, 
                "hand1": state.hand_p1, 
                "hand2": state.hand_p2, 
                "winner": winner
            })

        # 2. AIの思考 (後手)
        memo.clear()
        ai_moves = state.get_legal_moves()
        if not ai_moves:
            return jsonify({"board": state.board, "hand1": state.hand_p1, "hand2": state.hand_p2, "winner": 1})

        best_score = float('inf')
        best_move = ai_moves[0]
        for m in ai_moves:
            # 深さ4で探索
            score, _ = simple_analysis(state.make_move(m), 4)
            if score < best_score:
                best_score = score
                best_move = m
                
        # AIの手を適用
        state = state.make_move(best_move)
        winner = state.decide_winner()

        # セッションを最新状態に更新
        session['board'] = state.board
        session['turn'] = state.turn
        session['hand_p1'] = serialize_hand(state.hand_p1)
        session['hand_p2'] = serialize_hand(state.hand_p2)
        
        # 次の人間が指せる手を準備
        next_options = []
        for i, m in enumerate(state.get_legal_moves()):
            p_type = abs(state.board[m[1]][m[2]]) if m[0] == 'move' else m[1]
            next_options.append({"id": i, "text": format_single_move(m, p_type, state.turn)})

        return jsonify({
            "board": state.board,
            "hand1": state.hand_p1,
            "hand2": state.hand_p2,
            "winner": winner,
            "next_options": next_options
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)