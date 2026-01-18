/**
 * RPS Ultimate 2.0 - Client Side Port with PeerJS (Serverless Multiplayer)
 */

// --- Global State ---
let APP_STATE = {
    username: localStorage.getItem('rps_username') || null,
    avatar: localStorage.getItem('rps_avatar') || null,
    playerMoves: [], // For AI analysis
    wins: parseInt(localStorage.getItem('rps_wins') || 0),
    losses: parseInt(localStorage.getItem('rps_losses') || 0),
    ties: parseInt(localStorage.getItem('rps_ties') || 0),
    streak: 0,
    longestStreak: parseInt(localStorage.getItem('rps_longestStreak') || 0),
    roundsPlayed: 0
};

const VALID_MOVES = ['rock', 'paper', 'scissors'];
const WIN_CONDITIONS = {
    'rock': 'scissors',
    'paper': 'rock',
    'scissors': 'paper'
};
const AI_COUNTERS = {
    'rock': 'paper',
    'paper': 'scissors',
    'scissors': 'rock'
};

// --- DOM Elements ---
const dom = {
    // Modals
    nameModal: document.getElementById('name-modal'),
    modeModal: document.getElementById('mode-modal'),
    friendModal: document.getElementById('friend-modal'),
    joinRoomModal: document.getElementById('join-room-modal'),
    waitingModal: document.getElementById('waiting-modal'),
    gameContainer: document.getElementById('game-container'),
    winnerModal: document.getElementById('winner-modal'),
    seriesModal: document.getElementById('series-modal'),

    // Inputs
    usernameInput: document.getElementById('username-input'),
    avatarChoices: document.querySelectorAll('.avatar-choice'),
    playBtn: document.getElementById('play-btn'),

    // Profile
    profileUsername: document.getElementById('profile-username'),
    profileAvatar: document.getElementById('profile-avatar'),
    changeNameBtn: document.getElementById('change-name-btn'),

    // Game Mode Buttons
    computerBtn: document.getElementById('computer-btn'),
    friendBtn: document.getElementById('friend-btn'),
    createRoomBtn: document.getElementById('create-room-btn'),
    joinRoomBtn: document.getElementById('join-room-btn'),
    submitJoinRoomBtn: document.getElementById('submit-join-room-btn'),
    roomCodeInput: document.getElementById('room-code-input'),
    roomCodeDisplay: document.getElementById('room-code-display'),

    seriesBtns: document.querySelectorAll('.series-btn'),

    // In-Game
    player1Label: document.getElementById('player1-label'),
    player2Label: document.getElementById('player2-label'),
    player1Avatar: document.getElementById('player1-avatar'),
    player2Avatar: document.getElementById('player2-avatar'),
    player1Score: document.getElementById('player1-score'),
    player2Score: document.getElementById('player2-score'),
    player1SeriesScore: document.getElementById('player1-series-score'),
    player2SeriesScore: document.getElementById('player2-series-score'),
    seriesTargetDisplay: document.getElementById('series-target-display'),
    message: document.getElementById('message'),
    player1Hand: document.getElementById('player1-hand'),
    player2Hand: document.getElementById('player2-hand'),
    buttons: document.querySelectorAll('.choice-btn'),
    resetBtn: document.getElementById('reset-btn'),
    resetBtnTop: document.getElementById('reset-btn-top'),
    playAgainBtn: document.getElementById('play-again-btn'),
    exitFromWinnerBtn: document.getElementById('exit-from-winner'),

    // Stats
    statsBox: document.getElementById('stats-box'),
    roundsPlayed: document.getElementById('rounds-played'),
    p1WinRate: document.getElementById('p1-win-rate'),
    p2WinRate: document.getElementById('p2-win-rate'),
    p1LongestStreak: document.getElementById('p1-longest-streak'),
    historyList: document.getElementById('history-list'),

    // Chat
    chatContainer: document.getElementById('chat-box-container'),
    chatMessages: document.getElementById('chat-messages'),
    chatInput: document.getElementById('chat-input'),
    sendChatBtn: document.getElementById('send-chat-btn'),

    // Utility
    modeToggle: document.getElementById('mode-toggle')
};

// --- Multiplayer State (PeerJS) ---
let peer = null;
let conn = null;
let isHost = false;
let myMove = null;
let opponentMove = null;
let isMultiplayer = false;

// --- Initialization ---

let selectedAvatar = '🧑';
let seriesLength = 0;
let currentGame = {
    p1Name: "Player 1",
    p2Name: "Computer",
    p1Avatar: "🧑",
    p2Avatar: "🤖",
    p1Score: 0,
    p2Score: 0,
    p1SeriesScore: 0,
    p2SeriesScore: 0,
    ties: 0
};

function init() {
    setupTheme();
    setupEventListeners();
    checkAuth();
}

function setupTheme() {
    const savedMode = localStorage.getItem('mode') || 'dark';
    if (savedMode === 'dark') document.body.classList.add('dark-mode');
    dom.modeToggle.textContent = savedMode === 'dark' ? '☀️' : '🌙';

    dom.modeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        dom.modeToggle.textContent = isDark ? '☀️' : '🌙';
        localStorage.setItem('mode', isDark ? 'dark' : 'light');
        playSound('sound-click');
    });

    // --- RIPPLE EFFECT HANDLER ---
    document.addEventListener('click', (e) => {
        if (e.target.closest('.clickable')) {
            const btn = e.target.closest('.clickable');
            createRipple(e, btn);
        }
    });
}

function createRipple(event, button) {
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;

    const rect = button.getBoundingClientRect();

    // Check if it's a keyboard trigger or actual click
    let x, y;
    if (event.clientX === 0 && event.clientY === 0) {
        x = rect.width / 2 - radius;
        y = rect.height / 2 - radius;
    } else {
        x = event.clientX - rect.left - radius;
        y = event.clientY - rect.top - radius;
    }

    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${x}px`;
    circle.style.top = `${y}px`;
    circle.classList.add('ripple');

    const ripple = button.getElementsByClassName('ripple')[0];
    if (ripple) {
        ripple.remove();
    }

    button.appendChild(circle);
}

function checkAuth() {
    if (APP_STATE.username && APP_STATE.avatar) {
        showModeSelection();
    } else {
        dom.nameModal.style.display = 'flex';
    }
}

function showModeSelection() {
    dom.nameModal.style.display = 'none';
    dom.profileUsername.textContent = APP_STATE.username;
    dom.profileAvatar.textContent = APP_STATE.avatar;
    dom.modeModal.style.display = 'flex';
    updateStatsUI();
}

function setupEventListeners() {
    // Avatar Selection
    dom.avatarChoices.forEach(choice => {
        choice.addEventListener('click', () => {
            dom.avatarChoices.forEach(c => c.classList.remove('selected'));
            choice.classList.add('selected');
            selectedAvatar = choice.dataset.avatar;
        });
    });

    // Set Name
    dom.playBtn.addEventListener('click', () => {
        const name = dom.usernameInput.value.trim();
        if (name.length < 2) {
            showToast("Name must be at least 2 characters.", "error");
            return;
        }
        APP_STATE.username = name;
        APP_STATE.avatar = selectedAvatar;
        localStorage.setItem('rps_username', name);
        localStorage.setItem('rps_avatar', selectedAvatar);

        showToast(`Welcome, ${name}!`, "success");
        showModeSelection();
    });

    // Change Name
    dom.changeNameBtn.addEventListener('click', () => {
        APP_STATE.username = null;
        APP_STATE.avatar = null;
        APP_STATE.playerMoves = [];
        localStorage.removeItem('rps_username');
        localStorage.removeItem('rps_avatar');
        dom.modeModal.style.display = 'none';
        dom.nameModal.style.display = 'flex';
        dom.usernameInput.value = "";
    });

    // --- GAME MODES ---

    // AI Mode
    dom.computerBtn.addEventListener('click', () => {
        isMultiplayer = false;
        dom.modeModal.style.display = 'none';
        dom.seriesModal.style.display = 'flex';
    });

    // Friend Mode
    dom.friendBtn.addEventListener('click', () => {
        isMultiplayer = true;
        seriesLength = 5; // Default for friend mode or ask? Let's use 5 for now.
        dom.modeModal.style.display = 'none';
        dom.friendModal.style.display = 'flex';
    });

    // Create Room
    dom.createRoomBtn.addEventListener('click', () => {
        initializePeer(true);
    });

    // Join Room UI
    dom.joinRoomBtn.addEventListener('click', () => {
        dom.friendModal.style.display = 'none';
        dom.joinRoomModal.style.display = 'flex';
    });

    // Submit Join Code
    dom.submitJoinRoomBtn.addEventListener('click', () => {
        const code = dom.roomCodeInput.value.trim().toUpperCase();
        if (code.length !== 4) return showToast("Code must be 4 characters", "error");
        initializePeer(false, code);
    });

    // Series Length Selection (AI Only currently)
    dom.seriesBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            seriesLength = parseInt(btn.dataset.length) || 0;
            dom.seriesModal.style.display = 'none';
            if (!isMultiplayer) startGameAI();
        });
    });

    // Gameplay Choices
    dom.buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (isMultiplayer) playRoundMultiplayer(btn.dataset.choice);
            else playRoundAI(btn.dataset.choice);
        });
    });

    // Back Buttons
    document.querySelectorAll('.back-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            btn.closest('.modal').style.display = 'none';
            document.getElementById(targetId).style.display = 'flex';

            // Cleanup Peer if backing out of waiting or join
            if (peer) { peer.destroy(); peer = null; }
        });
    });

    // Reset / Exit
    dom.resetBtn.addEventListener('click', resetBoardScores);
    dom.resetBtnTop.addEventListener('click', () => {
        if (isMultiplayer && conn) { conn.send({ type: 'left' }); conn.close(); }
        exitToMenu();
    });
    dom.exitFromWinnerBtn.addEventListener('click', exitToMenu);

    dom.playAgainBtn.addEventListener('click', () => {
        dom.winnerModal.style.display = 'none';
        resetBoardScores();

        if (isMultiplayer) {
            // Send Restart Request
            if (conn) conn.send({ type: 'restart_request' });
            showToast("Waiting for opponent...", "info");
        } else {
            dom.gameContainer.style.display = 'none';
            dom.seriesModal.style.display = 'flex';
        }
    });

    // Chat
    dom.sendChatBtn.addEventListener('click', sendChatMessage);
    dom.chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

// --- PEER JS MULTIPLAYER LOGIC ---

function generateRoomCode() {
    return Math.random().toString(36).substring(2, 6).toUpperCase();
}

function initializePeer(isHostParam, roomCodeParam = null) {
    isHost = isHostParam;
    const myId = isHost ? generateRoomCode() : null; // Host gets generated ID, Joiner gets auto ID

    // Show loading or waiting
    if (isHost) {
        dom.friendModal.style.display = 'none';
        dom.waitingModal.style.display = 'flex';
        dom.roomCodeDisplay.textContent = myId;
    }

    peer = new Peer(myId, {
        debug: 1
    });

    peer.on('open', (id) => {
        console.log('My Peer ID:', id);
        if (!isHost) {
            // If joiner, connect to host
            connectToPeer(roomCodeParam);
        }
    });

    peer.on('connection', (c) => {
        // Host receives connection
        if (isHost) {
            conn = c;
            setupConnection();
            dom.waitingModal.style.display = 'none';
            // Start Game
            startGameMultiplayer();
        }
    });

    peer.on('error', (err) => {
        console.error(err);
        showToast("Connection Error: " + err.type, "error");
        if (dom.joinRoomModal.style.display === 'flex') {
            dom.roomCodeInput.value = '';
        }
    });
}

function connectToPeer(hostId) {
    conn = peer.connect(hostId);
    conn.on('open', () => {
        setupConnection();
        dom.joinRoomModal.style.display = 'none';
        startGameMultiplayer();
    });
    conn.on('error', (err) => showToast("Could not connect to room", "error"));
}

function setupConnection() {
    conn.on('data', (data) => {
        handleIncomingData(data);
    });
    conn.on('close', () => {
        showToast("Opponent disconnected", "error");
        setTimeout(exitToMenu, 2000);
    });
}

function handleIncomingData(data) {
    switch (data.type) {
        case 'info':
            // Opponent sent name/avatar
            currentGame.p2Name = data.name;
            currentGame.p2Avatar = data.avatar;
            updateGameUIHeader();
            break;
        case 'move':
            opponentMove = data.move;
            checkMultiplayerRound();
            break;
        case 'chat':
            addChatMessage(data.message, false);
            break;
        case 'restart_request':
            showToast("Opponent wants to play again!", "success");
            // If both accept/logic here clearly simplified
            resetBoardScores();
            break;
        case 'left':
            showToast("Opponent left the game", "info");
            setTimeout(exitToMenu, 2000);
            break;
    }
}

function startGameMultiplayer() {
    isMultiplayer = true;
    seriesLength = 5; // Default

    currentGame.p1Name = APP_STATE.username;
    currentGame.p1Avatar = APP_STATE.avatar;
    currentGame.p2Name = "Opponent"; // Will update
    currentGame.p2Avatar = "❓";

    currentGame.p1SeriesScore = 0;
    currentGame.p2SeriesScore = 0;

    dom.gameContainer.style.display = 'block';
    dom.statsBox.style.display = 'block';
    dom.chatContainer.style.display = 'block'; // Show Chat

    // Send my info
    conn.send({
        type: 'info',
        name: APP_STATE.username,
        avatar: APP_STATE.avatar
    });

    updateGameUIHeader();
    resetBoardScores();
}

function playRoundMultiplayer(choice) {
    if (myMove) return; // Already picked

    myMove = choice;
    // Lock buttons
    dom.buttons.forEach(b => b.disabled = true);
    dom.message.textContent = "Waiting for opponent...";
    dom.player1Hand.textContent = iToE(choice); // Show my choice? Or hide until reveal?
    // Usually hide. But let's show "?" for now or just my choice
    dom.player1Hand.textContent = '✔️';

    // Send move (hashed or just move, local trust)
    conn.send({ type: 'move', move: choice });

    checkMultiplayerRound();
}

async function checkMultiplayerRound() {
    if (myMove && opponentMove) {
        // Both moved
        // Animation
        dom.player1Hand.textContent = '✊';
        dom.player2Hand.textContent = '✊';
        dom.player1Hand.classList.add('shaking');
        dom.player2Hand.classList.add('shaking');

        await wait(500);

        dom.player1Hand.classList.remove('shaking');
        dom.player2Hand.classList.remove('shaking');

        // Determine Winner
        let result = 'lose';
        if (myMove === opponentMove) result = 'tie';
        else if (WIN_CONDITIONS[myMove] === opponentMove) result = 'win';

        // Update UI
        dom.player1Hand.textContent = iToE(myMove);
        dom.player2Hand.textContent = iToE(opponentMove);

        handleRoundResult(result, myMove, opponentMove);

        // Reset moves
        myMove = null;
        opponentMove = null;
    }
}


function sendChatMessage() {
    const text = dom.chatInput.value.trim();
    if (!text || !conn) return;

    conn.send({ type: 'chat', message: text });
    addChatMessage(text, true);
    dom.chatInput.value = '';
}

function addChatMessage(text, isMe) {
    const div = document.createElement('div');
    div.className = `chat-message ${isMe ? 'my-message' : 'other-message'}`;
    div.innerHTML = `
        <div class="message-bubble">
            <div class="sender-name">${isMe ? 'You' : currentGame.p2Name}</div>
            <div class="message-text">${text}</div>
        </div>
    `;
    dom.chatMessages.appendChild(div);
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}


// --- AI GAME LOGIC ---

function startGameAI() {
    currentGame.p1Name = APP_STATE.username;
    currentGame.p1Avatar = APP_STATE.avatar;
    currentGame.p2Name = "Smarter AI";
    currentGame.p2Avatar = "🤖";
    currentGame.p1SeriesScore = 0;
    currentGame.p2SeriesScore = 0;

    dom.chatContainer.style.display = 'none'; // Hide Chat
    updateGameUIHeader();
    dom.gameContainer.style.display = 'block';
    dom.statsBox.style.display = 'block';
    resetBoardScores();
}

function getAIThinkingMove() {
    const history = APP_STATE.playerMoves;
    let choice = null;
    if (history.length > 0 && Math.random() < 0.7) {
        const counts = history.reduce((acc, move) => { acc[move] = (acc[move] || 0) + 1; return acc; }, {});
        const mostFrequent = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
        choice = AI_COUNTERS[mostFrequent];
    }
    return choice || VALID_MOVES[Math.floor(Math.random() * VALID_MOVES.length)];
}

async function playRoundAI(playerChoice) {
    dom.buttons.forEach(b => b.disabled = true);

    dom.message.textContent = "3...";
    dom.player1Hand.textContent = '✊'; dom.player2Hand.textContent = '✊';
    dom.player1Hand.classList.add('shaking'); dom.player2Hand.classList.add('shaking');
    await wait(700);
    dom.message.textContent = "2..."; await wait(700);
    dom.message.textContent = "1..."; await wait(700);
    dom.message.textContent = "SHOOT!";

    dom.player1Hand.classList.remove('shaking'); dom.player2Hand.classList.remove('shaking');

    const aiChoice = getAIThinkingMove();
    APP_STATE.playerMoves.push(playerChoice);
    if (APP_STATE.playerMoves.length > 20) APP_STATE.playerMoves.shift();

    let result = 'lose';
    if (playerChoice === aiChoice) result = 'tie';
    else if (WIN_CONDITIONS[playerChoice] === aiChoice) result = 'win';

    dom.player1Hand.textContent = iToE(playerChoice);
    dom.player2Hand.textContent = iToE(aiChoice);

    handleRoundResult(result, playerChoice, aiChoice);
}


// --- SHARED UI LOGIC ---

function updateGameUIHeader() {
    dom.player1Label.textContent = currentGame.p1Name;
    dom.player1Avatar.textContent = currentGame.p1Avatar;
    dom.player2Label.textContent = currentGame.p2Name;
    dom.player2Avatar.textContent = currentGame.p2Avatar;

    document.getElementById('player1-series-label').textContent = "P1 Wins:";
    document.getElementById('player2-series-label').textContent = isMultiplayer ? "P2 Wins:" : "AI Wins:";
    document.getElementById('p1-stats-label').textContent = currentGame.p1Name;
    document.getElementById('p2-stats-label').textContent = currentGame.p2Name;

    let seriesText = "Unlimited";
    if (seriesLength > 0) {
        const targetWins = Math.ceil(seriesLength / 2);
        seriesText = `Best of ${seriesLength} (${targetWins} Wins)`;
    }
    dom.seriesTargetDisplay.textContent = seriesText;
}


function handleRoundResult(result, p1Move, p2Move) {
    APP_STATE.roundsPlayed++;
    let msg = "";

    if (result === 'win') {
        msg = "You Win the Round! 🥇";
        playSound('sound-win');
        dom.player1Hand.classList.add('win-hand');
        dom.player2Hand.classList.add('lose-hand');

        // --- CONFETTI (Small Burst) ---
        confetti({
            particleCount: 50,
            spread: 60,
            origin: { y: 0.7 },
            colors: ['#ffaf7b', '#d76d77', '#3a1c71']
        });

        currentGame.p1Score++;
        currentGame.p1SeriesScore++;
        APP_STATE.wins++;
        APP_STATE.streak++;
        if (APP_STATE.streak > APP_STATE.longestStreak) {
            APP_STATE.longestStreak = APP_STATE.streak;
            localStorage.setItem('rps_longestStreak', APP_STATE.longestStreak);
        }

        // --- STREAK GLOW ---
        if (APP_STATE.streak >= 3) {
            dom.player1Avatar.classList.add('avatar-streak-glow');
        }

    } else if (result === 'lose') {
        msg = isMultiplayer ? "Opponent Wins the Round! 🥈" : "Computer Wins the Round! 🥈";
        playSound('sound-lose');
        dom.player2Hand.classList.add('win-hand');
        dom.player1Hand.classList.add('lose-hand');
        currentGame.p2Score++;
        currentGame.p2SeriesScore++;
        APP_STATE.losses++;
        APP_STATE.streak = 0;

        dom.player1Avatar.classList.remove('avatar-streak-glow');

    } else {
        msg = "It's a Tie! 🤝";
        playSound('sound-tie');
        currentGame.ties++;
        APP_STATE.ties++;
    }

    localStorage.setItem('rps_wins', APP_STATE.wins);
    localStorage.setItem('rps_losses', APP_STATE.losses);
    localStorage.setItem('rps_ties', APP_STATE.ties);

    dom.message.textContent = msg;
    updateScoreUI();
    updateStatsUI();
    addToHistory(result, p1Move, p2Move);

    if (checkSeriesWinner()) return;

    setTimeout(() => {
        dom.buttons.forEach(b => b.disabled = false);
        dom.message.textContent = "Make your next move!";
        dom.player1Hand.classList.remove('win-hand', 'lose-hand');
        dom.player2Hand.classList.remove('win-hand', 'lose-hand');

        // Reset Multiplayer Hands
        if (isMultiplayer) {
            dom.player1Hand.textContent = '❔';
            dom.player2Hand.textContent = '❔';
        }
    }, 2000);
}

function resetBoardScores() {
    currentGame.p1Score = 0;
    currentGame.p2Score = 0;
    currentGame.ties = 0;
    dom.historyList.innerHTML = '';

    dom.player1Score.textContent = 0;
    dom.player2Score.textContent = 0;
    document.getElementById('ties').textContent = 0;

    dom.player1Hand.textContent = '❔';
    dom.player2Hand.textContent = '❔';
    dom.player1Hand.className = 'hand';
    dom.player2Hand.className = 'hand';

    dom.message.textContent = "Make your move!";
    dom.buttons.forEach(b => b.disabled = false);
}

function checkSeriesWinner() {
    if (seriesLength === 0) return false;
    const target = Math.ceil(seriesLength / 2);
    let winner = null;

    if (currentGame.p1SeriesScore >= target) winner = APP_STATE.username;
    else if (currentGame.p2SeriesScore >= target) winner = currentGame.p2Name;

    if (winner) {
        document.getElementById('final-winner-message').textContent = `${winner} wins the Best of ${seriesLength} series! 🏆`;
        dom.winnerModal.style.display = 'flex';

        // --- HUGE CONFETTI BLAST ---
        if (winner === APP_STATE.username) {
            var duration = 3000;
            var end = Date.now() + duration;

            (function frame() {
                confetti({
                    particleCount: 5,
                    angle: 60,
                    spread: 55,
                    origin: { x: 0 },
                    colors: ['#ffaf7b', '#d76d77', '#3a1c71']
                });
                confetti({
                    particleCount: 5,
                    angle: 120,
                    spread: 55,
                    origin: { x: 1 },
                    colors: ['#ffaf7b', '#d76d77', '#3a1c71']
                });

                if (Date.now() < end) {
                    requestAnimationFrame(frame);
                }
            }());
        }

        return true;
    }
    return false;
}

function updateScoreUI() {
    dom.player1Score.textContent = currentGame.p1Score;
    dom.player2Score.textContent = currentGame.p2Score;
    document.getElementById('ties').textContent = currentGame.ties;
    dom.player1SeriesScore.textContent = currentGame.p1SeriesScore;
    dom.player2SeriesScore.textContent = currentGame.p2SeriesScore;
}

function updateStatsUI() {
    dom.roundsPlayed.textContent = APP_STATE.roundsPlayed;
    const total = APP_STATE.wins + APP_STATE.losses + APP_STATE.ties;
    const rate = total > 0 ? ((APP_STATE.wins / total) * 100).toFixed(1) : 0.0;
    dom.p1WinRate.textContent = `${rate}%`;
    dom.p1LongestStreak.textContent = APP_STATE.longestStreak;
    const aiRate = total > 0 ? ((APP_STATE.losses / total) * 100).toFixed(1) : 0.0;
    dom.p2WinRate.textContent = `${aiRate}%`;
}

function addToHistory(result, p1, p2) {
    const li = document.createElement('li');
    const p1e = iToE(p1);
    const p2e = iToE(p2);
    let text = "";
    if (result === 'win') text = `${APP_STATE.username} Wins (${p1e} vs ${p2e})`;
    else if (result === 'lose') text = `${currentGame.p2Name} Wins (${p2e} vs ${p1e})`;
    else text = `Tie (${p1e} vs ${p2e})`;
    li.textContent = text;
    li.className = result;
    dom.historyList.prepend(li);
    if (dom.historyList.children.length > 10) dom.historyList.lastChild.remove();
}

function iToE(move) {
    const emojiMap = { 'rock': '✊', 'paper': '🖐️', 'scissors': '✌️' };
    return emojiMap[move] || '❓';
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function playSound(id) {
    const audio = document.getElementById(id);
    if (audio) {
        audio.currentTime = 0;
        audio.play().catch(e => console.log("Audio block", e));
    }
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

function exitToMenu() {
    dom.gameContainer.style.display = 'none';
    dom.statsBox.style.display = 'none';
    dom.winnerModal.style.display = 'none';
    dom.waitingModal.style.display = 'none';

    // Stop Peer
    if (conn) { conn.close(); conn = null; }
    if (peer) { peer.destroy(); peer = null; }

    dom.modeModal.style.display = 'flex';
}

// Start
init();
