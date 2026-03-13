# 駒の定義
EMPTY = 0
LION, GIRAFFE, ELEPHANT, CHICK, HEN = 1, 2, 3, 4, 5

# AIの強さ設定
AI_SETTINGS = {
    "DEPTH": 5,          # 6以上にするとかなり手強くなります
    "MAX_SCORE": 100000
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