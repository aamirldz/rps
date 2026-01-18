/**
 * RPS Ultimate 2.0 - Client Side Port
 * Original logic ported from Python to JS for Cloudflare Pages
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

    // Game
    computerBtn: document.getElementById('computer-btn'),
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

    // Utility
    modeToggle: document.getElementById('mode-toggle')
};

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

    // Update Stats Display
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

    // Start Mode -> Series Selection
    dom.computerBtn.addEventListener('click', () => {
        dom.modeModal.style.display = 'none';
        dom.seriesModal.style.display = 'flex';
    });

    // Series Length Selection
    dom.seriesBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            seriesLength = parseInt(btn.dataset.length) || 0;
            dom.seriesModal.style.display = 'none';
            startGame();
        });
    });

    // Gameplay Choices
    dom.buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            playRound(btn.dataset.choice);
        });
    });

    // Back Buttons
    document.querySelectorAll('.back-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            btn.closest('.modal').style.display = 'none';
            document.getElementById(targetId).style.display = 'flex';
        });
    });

    // Reset / Exit
    dom.resetBtn.addEventListener('click', resetBoardScores);
    dom.resetBtnTop.addEventListener('click', exitToMenu);
    dom.exitFromWinnerBtn.addEventListener('click', exitToMenu);

    dom.playAgainBtn.addEventListener('click', () => {
        dom.winnerModal.style.display = 'none';
        resetBoardScores();
        // Go back to series selection for "New Series"
        dom.gameContainer.style.display = 'none';
        dom.seriesModal.style.display = 'flex';
    });
}

// --- Game Logic ---

function startGame() {
    currentGame.p1Name = APP_STATE.username;
    currentGame.p1Avatar = APP_STATE.avatar;
    currentGame.p2Name = "Smarter AI";
    currentGame.p2Avatar = "🤖";
    currentGame.p1SeriesScore = 0;
    currentGame.p2SeriesScore = 0;

    // Update UI Labels
    dom.player1Label.textContent = currentGame.p1Name;
    dom.player1Avatar.textContent = currentGame.p1Avatar;
    dom.player2Label.textContent = currentGame.p2Name;
    dom.player2Avatar.textContent = currentGame.p2Avatar;

    document.getElementById('player1-series-label').textContent = "P1 Wins:";
    document.getElementById('player2-series-label').textContent = "AI Wins:";
    document.getElementById('p1-stats-label').textContent = currentGame.p1Name;
    document.getElementById('p2-stats-label').textContent = currentGame.p2Name;

    let seriesText = "Unlimited";
    if (seriesLength > 0) {
        const targetWins = Math.ceil(seriesLength / 2);
        seriesText = `Best of ${seriesLength} (${targetWins} Wins)`;
    }
    dom.seriesTargetDisplay.textContent = seriesText;

    dom.gameContainer.style.display = 'block';
    dom.statsBox.style.display = 'block';

    resetBoardScores();
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

function getAIThinkingMove() {
    // --- SMARTER AI LOGIC (Ported) ---
    // 70% chance to counter player's most frequent move
    // 30% random
    const history = APP_STATE.playerMoves;
    let choice = null;

    if (history.length > 0 && Math.random() < 0.7) {
        // Find most frequent move
        const counts = history.reduce((acc, move) => {
            acc[move] = (acc[move] || 0) + 1;
            return acc;
        }, {});

        const mostFrequent = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
        choice = AI_COUNTERS[mostFrequent];
    }

    if (!choice) {
        choice = VALID_MOVES[Math.floor(Math.random() * VALID_MOVES.length)];
    }

    return choice;
}

async function playRound(playerChoice) {
    // 1. Lock UI
    dom.buttons.forEach(b => b.disabled = true);

    // 2. Countdown Animation
    dom.message.textContent = "3...";
    dom.player1Hand.textContent = '✊';
    dom.player2Hand.textContent = '✊';
    dom.player1Hand.classList.add('shaking');
    dom.player2Hand.classList.add('shaking');

    await wait(700);
    dom.message.textContent = "2...";
    await wait(700);
    dom.message.textContent = "1...";
    await wait(700);
    dom.message.textContent = "SHOOT!";

    dom.player1Hand.classList.remove('shaking');
    dom.player2Hand.classList.remove('shaking');

    // 3. Logic
    const aiChoice = getAIThinkingMove();

    // Record player move
    APP_STATE.playerMoves.push(playerChoice);
    if (APP_STATE.playerMoves.length > 20) APP_STATE.playerMoves.shift();

    // Determine winner
    let result = 'lose'; // default to player lost
    if (playerChoice === aiChoice) result = 'tie';
    else if (WIN_CONDITIONS[playerChoice] === aiChoice) result = 'win';

    // 4. Update UI
    const emojiMap = { 'rock': '✊', 'paper': '🖐️', 'scissors': '✌️' };
    dom.player1Hand.textContent = emojiMap[playerChoice];
    dom.player2Hand.textContent = emojiMap[aiChoice];

    handleRoundResult(result, playerChoice, aiChoice);
}

function handleRoundResult(result, p1Move, p2Move) {
    APP_STATE.roundsPlayed++;
    APP_STATE.totalRounds++;

    let msg = "";

    if (result === 'win') {
        msg = "You Win the Round! 🥇";
        playSound('sound-win');
        dom.player1Hand.classList.add('win-hand');
        dom.player2Hand.classList.add('lose-hand');

        currentGame.p1Score++;
        currentGame.p1SeriesScore++;
        APP_STATE.wins++;
        APP_STATE.streak++;
        if (APP_STATE.streak > APP_STATE.longestStreak) {
            APP_STATE.longestStreak = APP_STATE.streak;
            localStorage.setItem('rps_longestStreak', APP_STATE.longestStreak);
        }
    } else if (result === 'lose') {
        msg = "Computer Wins the Round! 🥈";
        playSound('sound-lose');
        dom.player2Hand.classList.add('win-hand');
        dom.player1Hand.classList.add('lose-hand');

        currentGame.p2Score++;
        currentGame.p2SeriesScore++;
        APP_STATE.losses++;
        APP_STATE.streak = 0;
    } else {
        msg = "It's a Tie! 🤝";
        playSound('sound-tie');
        currentGame.ties++;
        APP_STATE.ties++;
    }

    // Save Persistent Stats
    localStorage.setItem('rps_wins', APP_STATE.wins);
    localStorage.setItem('rps_losses', APP_STATE.losses);
    localStorage.setItem('rps_ties', APP_STATE.ties);

    dom.message.textContent = msg;
    updateScoreUI();
    updateStatsUI();
    addToHistory(result, p1Move, p2Move);

    // Check Series Winner
    if (checkSeriesWinner()) {
        return; // Don't unlock buttons
    }

    // Unlock buttons after delay
    setTimeout(() => {
        dom.buttons.forEach(b => b.disabled = false);
        dom.message.textContent = "Make your next move!";
        dom.player1Hand.classList.remove('win-hand', 'lose-hand');
        dom.player2Hand.classList.remove('win-hand', 'lose-hand');
    }, 2000);
}

function checkSeriesWinner() {
    if (seriesLength === 0) return false;

    const target = Math.ceil(seriesLength / 2);
    let winner = null;

    if (currentGame.p1SeriesScore >= target) winner = APP_STATE.username;
    else if (currentGame.p2SeriesScore >= target) winner = "Smarter AI";

    if (winner) {
        document.getElementById('final-winner-message').textContent = `${winner} wins the Best of ${seriesLength} series! 🏆`;
        dom.winnerModal.style.display = 'flex';
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

    // P1 Stats (User)
    const total = APP_STATE.wins + APP_STATE.losses + APP_STATE.ties;
    const rate = total > 0 ? ((APP_STATE.wins / total) * 100).toFixed(1) : 0.0;
    dom.p1WinRate.textContent = `${rate}%`;
    dom.p1LongestStreak.textContent = APP_STATE.streak; // Showing current streak for session context or best?
    // Let's match original: "Longest Streak" = highest recorded
    dom.p1LongestStreak.textContent = APP_STATE.longestStreak;

    // P2 Stats (AI - Session only really makes sense here visually)
    const aiRate = total > 0 ? ((APP_STATE.losses / total) * 100).toFixed(1) : 0.0;
    dom.p2WinRate.textContent = `${aiRate}%`;
    dom.statsBox.querySelector('#p2-longest-streak').textContent = "-";
}

function addToHistory(result, p1, p2) {
    const li = document.createElement('li');
    const p1e = iToE(p1);
    const p2e = iToE(p2);

    let text = "";
    if (result === 'win') text = `${APP_STATE.username} Wins (${p1e} vs ${p2e})`;
    else if (result === 'lose') text = `AI Wins (${p2e} vs ${p1e})`;
    else text = `Tie (${p1e} vs ${p2e})`;

    li.textContent = text;
    li.className = result;

    dom.historyList.prepend(li);
    if (dom.historyList.children.length > 10) dom.historyList.lastChild.remove();
}

// --- Utilities ---

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
    dom.modeModal.style.display = 'flex';
}

// Start
init();
