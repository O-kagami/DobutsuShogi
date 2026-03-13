let allMoves = [];
let currentBoard = [];
let currentHand1 = {};
let currentHand2 = {};
let selected = null;
const emojis = { 1: "🦁", 2: "🦒", 3: "🐘", 4: "🐥", 5: "🐔", "-1": "🦁", "-2": "🦒", "-3": "🐘", "-4": "🐥", "-5": "🐔", 0: "" };

function initGame(moves, board, h1, h2) {
    allMoves = moves;
    currentHand1 = h1;
    currentHand2 = h2;
    renderAll(board, h1, h2);
}

function renderAll(board, h1, h2) {
    currentBoard = board;
    const bDiv = document.getElementById('board');
    bDiv.innerHTML = '';
    board.forEach((row, r) => row.forEach((cell, c) => {
        const d = document.createElement('div');
        d.className = `cell ${cell < 0 ? 'opponent' : ''}`;
        d.innerText = emojis[cell];
        d.onclick = () => handleCellClick(r, c);
        bDiv.appendChild(d);
    }));
    renderHand('hand1', h1, 1);
    renderHand('hand2', h2, -1);
}

function renderHand(id, hand, owner) {
    const el = document.getElementById(id);
    el.innerHTML = '';
    for (let p in hand) {
        for (let i = 0; i < hand[p]; i++) {
            const s = document.createElement('span');
            s.className = 'hand-piece';
            s.innerText = emojis[p];
            if (owner === 1) {
                s.onclick = (e) => { e.stopPropagation(); handleHandPieceClick(parseInt(p), s); };
            }
            el.appendChild(s);
        }
    }
}

function handleCellClick(r, c) {
    if (selected) {
        const move = allMoves.find(m => m.to_r === r && m.to_c === c && m.type === selected.type && (selected.type === 'move' ? (m.from_r === selected.r && m.from_c === selected.c) : (m.p_type === selected.p_type)));
        if (move) { executeMove(move.id); return; }
    }
    if (currentBoard[r][c] > 0) selectPiece('move', r, c, currentBoard[r][c]);
    else clearSelection();
}

function handleHandPieceClick(p_type, element) { selectPiece('drop', -1, -1, p_type); element.classList.add('selected'); }

function selectPiece(type, r, c, p_type) {
    clearSelection();
    selected = { type, r, c, p_type };
    if (type === 'move') document.querySelectorAll('.cell')[r * 3 + c].classList.add('selected');
    allMoves.filter(m => m.type === type && m.p_type === p_type && (type === 'drop' || (m.from_r === r && m.from_c === c)))
            .forEach(m => document.querySelectorAll('.cell')[m.to_r * 3 + m.to_c].classList.add('highlight'));
}

function clearSelection() {
    selected = null;
    document.querySelectorAll('.cell').forEach(el => el.classList.remove('selected', 'highlight'));
    document.querySelectorAll('.hand-piece').forEach(el => el.classList.remove('selected'));
}

async function executeMove(idx) {
    const status = document.getElementById('status-text');
    const boardEl = document.getElementById('board');
    const progContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    
    // 自分の手を反映（楽観的UI更新）
    const userMove = allMoves.find(m => m.id === idx);
    applyMoveToClient(userMove);
    clearSelection();
    
    // UIをロックして思考中表示
    boardEl.style.pointerEvents = 'none';
    status.innerText = "🤖 AIが考えています...";
    progContainer.style.display = 'block';
    progressBar.style.width = '0%';

    // AIの計算を開始
    const resPromise = fetch('/battle', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ move_idx: idx }) 
    });

    // バーをアニメーションさせる（1.2秒）
    const duration = 1200;
    const startTime = Date.now();
    const timer = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min((elapsed / duration) * 100, 100);
        progressBar.style.width = progress + "%";
        if (elapsed >= duration) clearInterval(timer);
    }, 20);

    const res = await resPromise;
    const data = await res.json();

    // 最低限の演出時間を確保
    const alreadyElapsed = Date.now() - startTime;
    if (alreadyElapsed < duration) {
        await new Promise(r => setTimeout(r, duration - alreadyElapsed));
    }

    progContainer.style.display = 'none';
    updateUI(data);
}

function applyMoveToClient(move) {
    if (move.type === 'move') {
        const piece = currentBoard[move.from_r][move.from_c];
        currentBoard[move.from_r][move.from_c] = 0;
        currentBoard[move.to_r][move.to_c] = piece;
    } else if (move.type === 'drop') {
        currentBoard[move.to_r][move.to_c] = move.p_type;
        if (currentHand1[move.p_type] > 0) currentHand1[move.p_type] -= 1;
    }
    renderAll(currentBoard, currentHand1, currentHand2);
}

function updateUI(data) {
    currentHand1 = data.hand1;
    currentHand2 = data.hand2;
    renderAll(data.board, data.hand1, data.hand2);
    allMoves = data.next_options || [];
    if (data.winner !== 0) {
        const msg = document.getElementById('win-message');
        if (data.winner === 2) msg.innerText = "引き分け（千日手）";
        else msg.innerText = data.winner === 1 ? "🎉 あなたの勝ち！やったね" : "😱 AIの勝ち！あなたの負け🤣";
        msg.style.display = 'block';
        document.getElementById('status-text').innerText = "対局終了";
    } else {
        document.getElementById('board').style.pointerEvents = 'auto';
        document.getElementById('status-text').innerText = "あなたの番です";
    }
}

async function undoMove() {
    const res = await fetch('/undo', { method: 'POST' });
    if (res.ok) {
        const data = await res.json();
        updateUI(data);
        document.getElementById('win-message').style.display = 'none';
    }
}