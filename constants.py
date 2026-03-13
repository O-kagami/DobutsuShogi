# 駒の定義
EMPTY = 0
LION, GIRAFFE, ELEPHANT, CHICK, HEN = 1, 2, 3, 4, 5

# 勝敗コード
#  1: 先手勝ち, -1: 後手勝ち, 0: 継続, 2: 引き分け（千日手など）
DRAW = 2

# AIの強さ設定
AI_SETTINGS = {
    # 探索の最大深さ（時間制限付き反復深化の上限）
    "DEPTH": 6,
    "MAX_SCORE": 100000,
    # 1手あたりの思考時間（秒）
    "TIME_LIMIT_SEC": 5.0,
}

# 駒の基本価値
PIECE_SCORES = {
    LION: 100000,
    GIRAFFE: 450,
    ELEPHANT: 400,
    CHICK: 100,
    HEN: 800
}

# 🌟 位置によるボーナス（先手用）
# ライオンをトライに近づけたり、キリンを中央に配置したりすると加点
POSITION_BONUS = [
    [100, 100, 100], # 敵陣1段目（トライに近い）
    [50,  50,  50],
    [10,  20,  10],
    [0,   0,   0]   # 自陣
]