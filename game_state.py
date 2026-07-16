import pandas as pd
from tabulate import tabulate
import copy
from constants import *
from pieces import get_piece_moves
from judge import decide_winner, is_check

class DobutsuShogiState:
    def __init__(self, board=None, hand_p1=None, hand_p2=None, turn=1, history=None):
        self.board = board if board else [[-2, -1, -3], [0, -4, 0], [0, 4, 0], [3, 1, 2]]
        self.hand_p1 = hand_p1 if hand_p1 else {2:0, 3:0, 4:0}
        self.hand_p2 = hand_p2 if hand_p2 else {2:0, 3:0, 4:0}
        self.turn = turn
        self.history = history if history else []
        
        # 履歴・メモ用のキー作成
        board_tuple = tuple(tuple(row) for row in self.board)
        hand_p1_tuple = tuple(sorted(self.hand_p1.items()))
        hand_p2_tuple = tuple(sorted(self.hand_p2.items()))
        self.current_state_key = (board_tuple, hand_p1_tuple, hand_p2_tuple, self.turn)

    def display(self):
        # 駒の番号をかわいい絵文字に変換する辞書
        # 後手の駒（負数）には「▽」などをつけて区別しやすくします
        p_chars = {
            EMPTY: "．",
            LION: "🦁", GIRAFFE: "🦒", ELEPHANT: "🐘", CHICK: "🐥", HEN: "🐔",
            -LION: "▽🦁", -GIRAFFE: "▽🦒", -ELEPHANT: "▽🐘", -CHICK: "▽🐥", -HEN: "▽🐔"
        }

        # 1. 持ち駒の表示（後手）
        h2_list = []
        for p, count in self.hand_p2.items():
            if count > 0:
                h2_list.append(f"{p_chars[-p]}×{count}")
        print(f"\n【後手の持ち駒】: {' '.join(h2_list) if h2_list else 'なし'}")

        # 2. 盤面の作成
        # pandasを使って、見た目を整えます
        display_board = []
        for row in self.board:
            display_board.append([p_chars[p] for p in row])
        
        df = pd.DataFrame(display_board, index=['一', '二', '三', '四'], columns=['３', '２', '１'])
        
        # tabulateで表形式にして表示
        print(tabulate(df, headers='keys', tablefmt='grid', stralign="center"))

        # 3. 持ち駒の表示（先手）
        h1_list = []
        for p, count in self.hand_p1.items():
            if count > 0:
                h1_list.append(f"{p_chars[p]}×{count}")
        print(f"【先手の持ち駒】: {' '.join(h1_list) if h1_list else 'なし'}")
        
        # 4. 現在の手番
        turn_mark = "▲先手（あなた）" if self.turn == 1 else "△後手（AI）"
        print(f"手番: {turn_mark}\n")

    def get_legal_moves(self):
            all_moves = []
            # --- 今までの処理（駒の移動と持ち駒打ち） ---
            for r in range(4):
                for c in range(3):
                    piece = self.board[r][c]
                    if piece * self.turn > 0:
                        all_moves.extend(get_piece_moves(r, c, piece, self.board, self.turn))
            
            hand = self.hand_p1 if self.turn == 1 else self.hand_p2
            for p_type, count in hand.items():
                if count > 0:
                    for r in range(4):
                        for c in range(3):
                            if self.board[r][c] == EMPTY:
                                all_moves.append(('drop', p_type, r, c))

            # 🌟 ここが重要！「王手放置」になる手を除外する
            legal_moves = []
            for move in all_moves:
                # 1. とりあえずその手を指してみる
                next_state = self.make_move(move)
                
                # 2. その結果、自分のライオンが取られる状態（王手）になっていないか？
                # make_move後は手番が入れ替わっているので、self.turnの安全を確認します
                if not next_state.is_check(self.turn):
                    legal_moves.append(move)
            
            return legal_moves

    def make_move(self, move):
        new_board = [row[:] for row in self.board]
        new_h1, new_h2 = self.hand_p1.copy(), self.hand_p2.copy()
        
        if move[0] == 'move':
            _, fr, fc, tr, tc = move
            piece = new_board[fr][fc]
            target = new_board[tr][tc]
            if target != EMPTY:
                captured = abs(target)
                if captured == HEN: captured = CHICK
                if captured != LION:
                    if self.turn == 1: new_h1[captured] += 1
                    else: new_h2[captured] += 1
            new_board[tr][tc], new_board[fr][fc] = piece, EMPTY
            if abs(piece) == CHICK and ((self.turn == 1 and tr == 0) or (self.turn == -1 and tr == 3)):
                new_board[tr][tc] = HEN * self.turn
        elif move[0] == 'drop':
            _, p_type, tr, tc = move
            new_board[tr][tc] = p_type * self.turn
            if self.turn == 1: new_h1[p_type] -= 1
            else: new_h2[p_type] -= 1

        return DobutsuShogiState(new_board, new_h1, new_h2, -self.turn, self.history + [self.current_state_key])

    def is_repetition(self):
        return self.history.count(self.current_state_key) >= 2

    # judge.pyの関数をメソッドとして呼び出せるようにする
    def is_check(self, turn): return is_check(self, turn)
    def decide_winner(self): return decide_winner(self)