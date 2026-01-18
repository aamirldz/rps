# Save this file as rock.py
# --------------------------------------------------------------------------
# ROCK PAPER SCISSORS: ULTIMATE EDITION 2.1 (FIXED)
# Features: Session-based Naming & Avatars, Smarter AI,
#           Networked 2P Rooms with Live Chat, Classic RPS
#           UI Modals for All, Button Reset Fix
# --------------------------------------------------------------------------

from flask import Flask, Response, render_template_string, jsonify, request, session
import uuid
import random
import os
import time 

# --- FLASK APP AND DATABASE SETUP ---
app = Flask(__name__)

# --- CONFIGURATION (Integrated) ---
basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    print("--- WARNING: SECRET_KEY is not set in environment. Using default. ---")
    print("--- For production, set a strong SECRET_KEY environment variable. ---")
    SECRET_KEY = 'your_strong_and_unique_secret_key_here_12345'

app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = 604800 # 7 days


# --- GLOBAL GAME STATE (For 2-Player Asynchronous Mode) ---
active_games = {}

VALID_MOVES = {'rock', 'paper', 'scissors'}

WIN_CONDITIONS_RPS = {
    ('rock', 'scissors'),
    ('paper', 'rock'),
    ('scissors', 'paper')
}

AI_COUNTERS = {
    'rock': 'paper',
    'paper': 'scissors',
    'scissors': 'rock'
}


# --- CORE SERVER LOGIC FUNCTIONS (Business Logic) ---

def generate_room_code(length=4):
    """Generates a simple, all-caps room code."""
    chars = 'ABCDEFGHIJKLMNPQRSTUVWXYZ123456789' # Removed O, 0 for clarity
    return ''.join(random.choice(chars) for _ in range(length))

def decide_winner(choice1, choice2):
    """Determines the winner based on choices (Player 1 is choice1)."""
    if choice1 == choice2: 
        return 'tie'
    if (choice1, choice2) in WIN_CONDITIONS_RPS:
        return 'win' # choice1 wins
    return 'lose' # choice1 loses (choice2 wins)

def cleanup_stale_games():
    """Iterates active_games and removes old, waiting rooms."""
    try:
        current_timestamp = time.time()
        stale_rooms = []
        for room_code, game in active_games.items():
            if (game.get('status') == 'WAITING' and 
                (current_timestamp - game.get('created_at', 0)) > 3600):
                stale_rooms.append(room_code)
        
        for room_code in stale_rooms:
            print(f"Cleaning up stale game room: {room_code}")
            del active_games[room_code]
    except Exception as e:
        print(f"Error during game cleanup: {e}")

# --- API ROUTES (HTTP Layer) ---

@app.route("/api/check_name", methods=["GET"])
def check_name_api():
    """Checks if a user is already logged in via the session."""
    username = session.get('username')
    avatar = session.get('avatar') 
    if not username or not avatar: 
        return jsonify({"success": False, "loggedIn": False})
    
    session.permanent = True 
    return jsonify({
        "success": True,
        "loggedIn": True,
        "username": username,
        "avatar": avatar 
    })

@app.route("/api/set_name", methods=["POST"])
def set_name_api():
    data = request.get_json()
    username = data.get('username', '').strip()
    avatar = data.get('avatar', '').strip() 
    
    if not username or len(username) < 2:
        return jsonify({"success": False, "message": "Name must be at least 2 characters."}), 400
    if len(username) > 20:
        return jsonify({"success": False, "message": "Name must be 20 characters or less."}), 400
    if not avatar: 
        return jsonify({"success": False, "message": "You must select an avatar."}), 400

    session['username'] = username
    session['avatar'] = avatar 
    session.permanent = True 
    return jsonify({
        "success": True,
        "username": username,
        "avatar": avatar
    })

@app.route("/api/change_name", methods=["POST"])
def change_name_api():
    session.pop('username', None)
    session.pop('avatar', None) 
    session.pop('player_moves', None) 
    return jsonify({"success": True})


@app.route("/api/play_computer", methods=["POST"])
def play_computer_api():
    data = request.get_json()
    player1_choice = data.get('p1_choice')

    if player1_choice not in VALID_MOVES:
        return jsonify({"success": False, "message": "Invalid move choice."}), 400
    
    # --- SMARTER AI LOGIC ---
    player_moves = session.get('player_moves', [])
    player_moves.append(player1_choice)
    session['player_moves'] = player_moves[-20:] 
    
    computer_choice = None
    
    if player_moves and random.random() < 0.7: # 70% smart
        try:
            most_frequent_move = max(set(player_moves), key=player_moves.count)
            computer_choice = AI_COUNTERS[most_frequent_move]
            
        except Exception as e:
            print(f"AI error: {e}") 
            
    if not computer_choice: # 30% random
        computer_choice = random.choice(list(VALID_MOVES))
    # --- END SMARTER AI LOGIC ---
    
    result = decide_winner(player1_choice, computer_choice)

    return jsonify({
        "result": result,
        "p1_choice": player1_choice,
        "p2_choice": computer_choice
    })

# --- [ NETWORKED MULTIPLAYER ROUTES ] ---

@app.route("/api/create_room", methods=["POST"])
def create_room_api():
    cleanup_stale_games()
    
    player_name = session.get('username')
    player_avatar = session.get('avatar') 
    if not player_name or not player_avatar:
        return jsonify({"success": False, "message": "Not authenticated"}), 403

    room_code = generate_room_code()
    while room_code in active_games:
        room_code = generate_room_code()
    
    active_games[room_code] = {
        'id': room_code,
        'p1_name': player_name,
        'p1_avatar': player_avatar, 
        'p2_name': None,
        'p2_avatar': None, 
        'p1_choice': None,
        'p2_choice': None,
        'status': 'WAITING', 
        'result': None,
        'created_at': time.time(),
        'chat_messages': [] 
    }
    return jsonify({"success": True, "room_code": room_code, "player_name": player_name})

@app.route("/api/join_room", methods=["POST"])
def join_room_api():
    player_name = session.get('username')
    player_avatar = session.get('avatar') 
    if not player_name or not player_avatar:
        return jsonify({"success": False, "message": "Not authenticated"}), 403
    
    data = request.get_json()
    room_code = data.get('room_code', '').upper()
    
    if room_code not in active_games:
        return jsonify({"success": False, "message": "Room code not found."}), 404
    
    game = active_games[room_code]
    
    if game['p2_name'] is not None and game['p1_name'] != player_name:
        return jsonify({"success": False, "message": "This room is already full."}), 409
    
    if game['p1_name'] == player_name:
        return jsonify({"success": False, "message": "You can't join your own game."}), 400
        
    game['p2_name'] = player_name
    game['p2_avatar'] = player_avatar 
    game['status'] = 'P1_TURN' 
    
    return jsonify({
        "success": True, 
        "room_code": room_code, 
        "p1_name": game['p1_name'], 
        "p1_avatar": game['p1_avatar'], 
        "p2_name": game['p2_name'],
        "p2_avatar": game['p2_avatar'] 
    })

@app.route("/api/game_status", methods=["GET"])
def game_status_api():
    room_code = request.args.get('room_code', '').upper()
    if room_code not in active_games:
        if room_code not in active_games:
            return jsonify({"success": False, "message": "Game not found or has expired."}), 404
        
    game_state = active_games[room_code]
    return jsonify({"success": True, "game": game_state})

@app.route("/api/reset_round", methods=["POST"])
def reset_round_api():
    room_code = request.get_json().get('room_code', '').upper()
    if room_code not in active_games:
        return jsonify({"success": False, "message": "Game not found"}), 404
    
    game = active_games[room_code]

    if game['status'] != 'RESOLVED':
        return jsonify({"success": True, "message": "Already reset or not resolved."})
    
    game['p1_choice'] = None
    game['p2_choice'] = None
    game['result'] = None
    game['status'] = 'P1_TURN' 
    
    return jsonify({"success": True})

@app.route("/api/submit_move", methods=["POST"])
def submit_move():
    player_name = session.get('username')
    if not player_name:
        return jsonify({"error": "Not authenticated"}), 403

    data = request.get_json()
    room_code = data.get('room_code', '').upper()
    choice = data.get('choice')

    if room_code not in active_games:
        return jsonify({"error": "Game not found"}), 404
    if choice not in VALID_MOVES:
        return jsonify({"error": "Invalid move choice"}), 400
    
    game = active_games[room_code]

    if game['status'] == 'P1_TURN' and player_name == game['p1_name']:
        game['p1_choice'] = choice
        game['status'] = 'P2_TURN'
    elif game['status'] == 'P2_TURN' and player_name == game['p2_name']:
        game['p2_choice'] = choice
        
        p1c = game['p1_choice']
        p2c = game['p2_choice']
        
        if not p1c or not p2c: 
             return jsonify({"error": "Waiting for both moves"}), 400
             
        result = decide_winner(p1c, p2c) 
        
        game['status'] = 'RESOLVED'
        game['result'] = result
    else:
        return jsonify({"error": "It's not your turn or game is over."}), 400

    return jsonify({"success": True, "message": "Move submitted."})

@app.route("/api/send_message", methods=["POST"])
def send_message_api():
    player_name = session.get('username')
    if not player_name:
        return jsonify({"success": False, "message": "Not authenticated"}), 403

    data = request.get_json()
    room_code = data.get('room_code', '').upper()
    message_text = data.get('message_text', '').strip()

    if not message_text:
        return jsonify({"success": False, "message": "Message cannot be empty."}), 400
    if len(message_text) > 200:
        return jsonify({"success": False, "message": "Message too long."}), 400
    if room_code not in active_games:
        return jsonify({"success": False, "message": "Game not found."}), 404

    game = active_games[room_code]
    
    chat_message = {
        "id": str(uuid.uuid4()),
        "sender": player_name,
        "text": message_text,
        "timestamp": time.time()
    }
    game['chat_messages'].append(chat_message)
    
    if len(game['chat_messages']) > 50:
        game['chat_messages'] = game['chat_messages'][-50:]

    return jsonify({"success": True})


# --- CONTENT FUNCTIONS (Cleaner Structure) ---

def get_html_content():
    """Returns the main HTML structure."""
    # FIX: Added new series-modal
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>RPS - Ultimate Edition 2.0</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css" />
</head>
<body>

<div id="toast-container"></div>

<button id="mode-toggle" class="mode-toggle">☀️</button>

<audio id="sound-click" src="https://www.soundjay.com/buttons/sounds/button-16.mp3" preload="auto"></audio>
<audio id="sound-win" src="https://www.soundjay.com/human/sounds/applause-01.mp3" preload="auto"></audio>
<audio id="sound-lose" src="https://www.soundjay.com/misc/sounds/fail-trombone-01.mp3" preload="auto"></audio>
<audio id="sound-tie" src="https://www.soundjay.com/buttons/sounds/button-10.mp3" preload="auto"></audio>

<div id="stats-box" class="stats-box" style="display:none;">
<h3>📊 Session Stats</h3> 
<p>Rounds Played: <span id="rounds-played">0</span></p>
<div class="stat-group">
<h4><span id="p1-stats-label">Player 1</span></h4>
<p>Win Rate: <span id="p1-win-rate">0.0%</span></p>
<p>Longest Streak: <span id="p1-longest-streak">0</span></p>
</div>
<div class="stat-group">
<h4><span id="p2-stats-label">Player 2</span></h4>
<p>Win Rate: <span id="p2-win-rate">0.0%</span></p>
<p>Longest Streak: <span id="p2-longest-streak">0</span></p>
</div>
</div>
<div class="modal" id="winner-modal" style="display:none;">
<div class="modal-content winner-content">
<h2 id="final-winner-message"></h2>
<button id="play-again-btn" class="clickable">Play New Series</button>
<button class="reset-btn clickable" id="exit-from-winner">Exit to Menu</button>
</div>
</div>

<div class="modal" id="name-modal">
<div class="modal-content">
<h2>Welcome!</h2>
<p>Enter your name and pick an avatar:</p>
<input type="text" id="username-input" placeholder="Your Name" maxlength="20" />
<div class="avatar-picker">
    <span class="avatar-choice selected" data-avatar="🧑">🧑</span>
    <span class="avatar-choice" data-avatar="🦸">🦸</span>
    <span class="avatar-choice" data-avatar="🧑‍🚀">🧑‍🚀</span>
    <span class="avatar-choice" data-avatar="🤖">🤖</span>
    <span class="avatar-choice" data-avatar="👻">👻</span>
    <span class="avatar-choice" data-avatar="👽">👽</span>
</div>
<button id="play-btn" class="clickable">Let's Play</button>
</div>
</div>

<div class="modal" id="mode-modal" style="display:none;">
<div class="modal-content">
<div id="profile-display" class="profile-display">
<span id="profile-avatar" class="profile-avatar">🧑</span>
<h3 id="profile-username">Player Name</h3>
</div>
<h2>Who do you want to play with?</h2>
<button id="friend-btn" class="clickable">Friend</button>
<button id="computer-btn" class="clickable">Computer (Smarter AI)</button>
<button id="change-name-btn" class="clickable">Change Name</button>
</div>
</div>

<div class="modal" id="series-modal" style="display:none;">
    <div class="modal-content">
        <h2>Select Series Length</h2>
        <p>First player to win...</p>
        <button id="series-3-btn" class="clickable series-btn" data-length="3">Best of 3 (2 Wins)</button>
        <button id="series-5-btn" class="clickable series-btn" data-length="5">Best of 5 (3 Wins)</button>
        <button id="series-7-btn" class="clickable series-btn" data-length="7">Best of 7 (4 Wins)</button>
        <button id="series-0-btn" class="clickable series-btn" data-length="0">Unlimited</button>
        <button class="back-btn clickable" data-target="mode-modal">Back</button>
    </div>
</div>

<div class="modal" id="friend-modal" style="display:none;">
    <div class="modal-content">
        <h2>Play with a Friend</h2>
        <button id="create-room-btn" class="clickable">Create Room</button>
        <button id="join-room-btn" class="clickable">Join Room</button>
        <button class="back-btn clickable" data-target="mode-modal">Back</button>
    </div>
</div>

<div class="modal" id="join-room-modal" style="display:none;">
    <div class="modal-content">
        <h2>Join Room</h2>
        <input type="text" id="room-code-input" placeholder="Enter 4-Digit Code" maxlength="4" style="text-transform: uppercase;"/>
        <button id="submit-join-room-btn" class="clickable">Join</button>
        <button class="back-btn clickable" data-target="friend-modal">Back</button>
    </div>
</div>

<div class="modal" id="waiting-modal" style="display:none;">
    <div class="modal-content">
        <h2>Waiting for Friend...</h2>
        <p>Share this code with your friend:</p>
        <h1 id="room-code-display" style="font-size: 3rem; color: #ffaf7b; letter-spacing: 5px;">----</h1>
        <p>Waiting for Player 2 to join.</p>
        <button class="back-btn clickable" data-target="friend-modal">Cancel</button>
    </div>
</div>

<div class="container" id="game-container" style="display:none;">
<button id="reset-btn-top" class="clickable">Exit Game</button>
<h1>
    <span class="title-rock">Rock</span> 
    <span class="title-paper">Paper</span> 
    <span class="title-scissors">Scissors</span> 
</h1>
<div class="series-score">
Series Target: <span id="series-target-display">Unlimited</span><br>
<strong id="player1-series-label">P1 Wins:</strong> <span id="player1-series-score">0</span>
<strong id="player2-series-label">P2 Wins:</strong> <span id="player2-series-score">0</span>
</div>

<div class="scoreboard">
<div>
    <span id="player1-avatar" class="score-avatar">🧑</span>
    <strong id="player1-label">Player 1</strong>: <span id="player1-score">0</span>
</div>
<div>
    <span id="player2-avatar" class="score-avatar">🧑‍💻</span>
    <strong id="player2-label">Player 2</strong>: <span id="player2-score">0</span>
</div>
<div><strong>Ties:</strong> <span id="ties">0</span></div>
</div>

<div class="hands">
<div class="hand" id="player1-hand">❔</div>
<div class="hand" id="player2-hand">❔</div>
</div>

<div class="message" id="message">Make your move!</div>

<div class="choices" id="choices-container">
<button class="choice-btn clickable" data-choice="rock">✊</button>
<button class="choice-btn clickable" data-choice="paper">🖐️</button>
<button class="choice-btn clickable" data-choice="scissors">✌️</button>
</div>

<div id="chat-box-container" class="chat-box-container" style="display:none;">
    <h3>Game Chat</h3>
    <div class="chat-messages" id="chat-messages">
    </div>
    <div class="chat-input-area">
        <input type="text" id="chat-input" placeholder="Say something..." maxlength="200" />
        <button id="send-chat-btn" class="clickable" aria-label="Send Message">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2 0.01 7z"/>
            </svg>
        </button>
    </div>
</div>

<button id="reset-btn" class="clickable">Reset Round Scores</button>

<div class="history-container">
<h2>Round History</h2>
<ul id="history-list"></ul>
</div>
</div>

<script src="/script.js"></script>
</body>
</html>
"""

def get_js_content():
    """Returns the main JavaScript logic (with TOAST notifications)."""
    # FIX: Replaced prompt() with series-modal
    # FIX: Added button re-enable in startGameUI()
    return """
// --- NEW TOAST NOTIFICATION FUNCTION ---
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => { toast.classList.add('show'); }, 10);
    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => {
            if (toast.parentElement) { container.removeChild(toast); }
        });
    }, duration);
}

// --- NEW: SOUND FUNCTION ---
let isMuted = false; 
function playSound(id) {
    if (isMuted) return;
    try {
        const sound = document.getElementById(id);
        sound.currentTime = 0; 
        sound.volume = (id === 'sound-click') ? 0.4 : 0.7; 
        sound.play();
    } catch (e) {
        console.warn(`Could not play sound: ${id}`, e);
    }
}
document.addEventListener('click', (e) => {
    if (e.target.matches('.clickable')) {
        playSound('sound-click');
    }
});
    
const choices = ['rock', 'paper', 'scissors'];

const player1Hand = document.getElementById('player1-hand');
const player2Hand = document.getElementById('player2-hand');
const message = document.getElementById('message');
const player1ScoreSpan = document.getElementById('player1-score');
const player2ScoreSpan = document.getElementById('player2-score');
const tiesSpan = document.getElementById('ties');
const historyList = document.getElementById('history-list');
const resetBtn = document.getElementById('reset-btn');
const buttons = document.querySelectorAll('.choice-btn');

// --- STATS VARIABLES (SESSION-ONLY) ---
let roundsPlayed = 0;
let p1Wins = 0;
let p2Wins = 0; 
let p1CurrentStreak = 0;
let p2CurrentStreak = 0;
let p1LongestStreak = 0;
let p2LongestStreak = 0;

const statsBox = document.getElementById('stats-box');
const roundsPlayedSpan = document.getElementById('rounds-played');
const p1WinRateSpan = document.getElementById('p1-win-rate');
const p2WinRateSpan = document.getElementById('p2-win-rate');
const p1LongestStreakSpan = document.getElementById('p1-longest-streak');
const p2LongestStreakSpan = document.getElementById('p2-longest-streak');
const p1StatsLabel = document.getElementById('p1-stats-label');
const p2StatsLabel = document.getElementById('p2-stats-label');

let player1Score = 0;
let player2Score = 0;
let ties = 0;
let history = [];

let player1SeriesScore = 0;
let player2SeriesScore = 0;
let seriesLength = 0;
const seriesTargetDisplay = document.getElementById('series-target-display');
const player1SeriesScoreSpan = document.getElementById('player1-series-score');
const player2SeriesScoreSpan = document.getElementById('player2-series-score');

let player1Name = "Player 1";
let player2Name = "Player 2";
let player1Avatar = "🧑"; 
let player2Avatar = "🧑‍💻"; 
let isTwoPlayer = false;
let player1Choice = null;

let currentRoomCode = null;
let myPlayerName = null; 
let pollingInterval = null; 
let currentChatMessages = []; 

const profileUsername = document.getElementById('profile-username');
const profileAvatar = document.getElementById('profile-avatar'); 

const nameModal = document.getElementById('name-modal'); 
const playBtn = document.getElementById('play-btn'); 
const usernameInput = document.getElementById('username-input'); 

const avatarPicker = document.querySelector('.avatar-picker');
const avatarChoices = document.querySelectorAll('.avatar-choice');
let selectedAvatar = '🧑'; 
avatarChoices.forEach(choice => {
    choice.addEventListener('click', () => {
        avatarChoices.forEach(c => c.classList.remove('selected'));
        choice.classList.add('selected');
        selectedAvatar = choice.dataset.avatar;
    });
});


const modeModal = document.getElementById('mode-modal');
const friendBtn = document.getElementById('friend-btn');
const computerBtn = document.getElementById('computer-btn');
const backBtns = document.querySelectorAll('.back-btn');
const backToModeBtn = document.getElementById('reset-btn-top');
const winnerModal = document.getElementById('winner-modal');
const playAgainBtn = document.getElementById('play-again-btn');
const exitFromWinnerBtn = document.getElementById('exit-from-winner');
const changeNameBtn = document.getElementById('change-name-btn'); 

// --- FIX: ADDED SERIES MODAL CONSTS ---
const seriesModal = document.getElementById('series-modal');
const seriesBtns = document.querySelectorAll('.series-btn');

const friendModal = document.getElementById('friend-modal');
const createRoomBtn = document.getElementById('create-room-btn');
const joinRoomBtn = document.getElementById('join-room-btn');
const joinRoomModal = document.getElementById('join-room-modal');
const roomCodeInput = document.getElementById('room-code-input');
const submitJoinRoomBtn = document.getElementById('submit-join-room-btn');
const waitingModal = document.getElementById('waiting-modal');
const roomCodeDisplay = document.getElementById('room-code-display');

const chatBoxContainer = document.getElementById('chat-box-container');
const chatMessagesDiv = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat-btn');


const modeToggle = document.getElementById('mode-toggle');
const body = document.body;
function setMode(mode) {
    if (mode === 'dark') {
        body.classList.add('dark-mode');
        modeToggle.textContent = '☀️';
        localStorage.setItem('mode', 'dark');
    } else {
        body.classList.remove('dark-mode');
        modeToggle.textContent = '🌙';
        localStorage.setItem('mode', 'light');
    }
}
const savedMode = localStorage.getItem('mode') || 'dark';
setMode(savedMode);
modeToggle.addEventListener('click', () => {
    playSound('sound-click'); 
    setMode(body.classList.contains('dark-mode') ? 'light' : 'dark');
});

// --- Profile and Auth Functions ---

function loadUserData(data) {
    player1Name = data.username;
    player1Avatar = data.avatar; 
    myPlayerName = data.username;
    profileUsername.textContent = data.username;
    profileAvatar.textContent = data.avatar; 
    updateStatsDisplay(); 
}

async function checkLoginStatus() {
    try {
        const response = await fetch('/api/check_name'); 
        const data = await response.json();
        
        if (data.success && data.loggedIn) {
            loadUserData(data);
            
            const savedRoomCode = localStorage.getItem('rps_roomCode');
            if (savedRoomCode) {
                showToast("Reconnecting to your game...", "info");
                try {
                    const gameResponse = await fetch(`/api/game_status?room_code=${savedRoomCode}`);
                    const gameData = await gameResponse.json();
                    
                    if (gameData.success) {
                        currentRoomCode = savedRoomCode;
                        isTwoPlayer = true;

                        if (gameData.game.status === 'WAITING') {
                            roomCodeDisplay.textContent = currentRoomCode;
                            waitingModal.style.display = 'flex';
                            startPolling();
                        } else {
                            player1Name = gameData.game.p1_name;
                            player1Avatar = gameData.game.p1_avatar; 
                            player2Name = gameData.game.p2_name;
                            player2Avatar = gameData.game.p2_avatar; 
                            seriesLength = 0;
                            startGameUI(); 
                            startPolling(); 
                        }
                    } else {
                        showToast(gameData.message || "Your previous game has expired.", "error");
                        localStorage.removeItem('rps_roomCode');
                        modeModal.style.display = 'flex'; 
                    }
                } catch (gameError) {
                    showToast("Error reconnecting to game.", "error");
                    localStorage.removeItem('rps_roomCode');
                    modeModal.style.display = 'flex'; 
                }
            } else {
                modeModal.style.display = 'flex';
            }
            nameModal.style.display = 'none'; 
            
        } else {
            nameModal.style.display = 'flex';
            localStorage.removeItem('rps_roomCode'); 
        }
    } catch (error) {
        console.error("Error checking session:", error);
        nameModal.style.display = 'flex'; 
        localStorage.removeItem('rps_roomCode'); 
    }
}

async function handleSetUsername() {
    const username = usernameInput.value.trim();
    if (username.length < 2) {
        showToast("Name must be at least 2 characters.", "error");
        return;
    }
    if (!selectedAvatar) {
        showToast("Please select an avatar.", "error");
        return;
    }
    playBtn.disabled = true;
    
    try {
        const response = await fetch('/api/set_name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, avatar: selectedAvatar }) 
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Server Error ${response.status}`);
        }
        const data = await response.json();
        if (data.success) {
            showToast(`Welcome, ${data.username}!`, "success");
            loadUserData(data);
            nameModal.style.display = 'none';
            modeModal.style.display = 'flex';
        } else {
            showToast(`Error: ${data.message}`, "error");
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, "error");
    } finally {
        playBtn.disabled = false;
    }
}
playBtn.addEventListener('click', handleSetUsername);
usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSetUsername();
    }
});


changeNameBtn.addEventListener('click', async () => {
    await fetch('/api/change_name', { method: 'POST' });
    localStorage.removeItem('rps_roomCode'); 
    
    roundsPlayed = 0;
    p1Wins = 0;
    p2Wins = 0;
    p1CurrentStreak = 0;
    p2CurrentStreak = 0;
    p1LongestStreak = 0;
    p2LongestStreak = 0;

    player1Name = "Player 1";
    player1Avatar = "🧑"; 
    usernameInput.value = "";
    profileUsername.textContent = 'Player Name';
    profileAvatar.textContent = '🧑'; 
    
    modeModal.style.display = 'none';
    nameModal.style.display = 'flex';
    resetSeries();
    showToast("Please enter your new name.", "info");
});

// --- Navigation Logic ---

friendBtn.addEventListener('click', () => {
    isTwoPlayer = true;
    myPlayerName = player1Name; 
    modeModal.style.display = 'none';
    friendModal.style.display = 'flex';
});

// --- FIX: MODIFIED computerBtn listener ---
computerBtn.addEventListener('click', () => {
    isTwoPlayer = false;
    player2Name = "Smarter AI"; 
    player2Avatar = "🤖"; 
    modeModal.style.display = 'none';
    
    // Show the new series modal instead of prompt
    seriesModal.style.display = 'flex'; 
    
    player1Name = profileUsername.textContent; 
    player1Avatar = profileAvatar.textContent; 
    // startGameUI() is now called by the seriesBtns listeners
});

// --- FIX: ADDED listeners for new series buttons ---
seriesBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        seriesLength = parseInt(btn.dataset.length) || 0;
        seriesModal.style.display = 'none';
        startGameUI(); // Now we start the game
    });
});

backBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const currentModal = btn.closest('.modal');
        const targetModal = document.getElementById(targetId);
        if (currentModal) {
            currentModal.style.display = 'none';
        }
        targetModal.style.display = 'flex';
    });
});

function exitToMenu() {
    stopPolling(); 
    localStorage.removeItem('rps_roomCode'); 
    currentRoomCode = null; 
    
    document.getElementById('game-container').style.display = 'none';
    statsBox.style.display = 'none';
    winnerModal.style.display = 'none';
    chatBoxContainer.style.display = 'none'; 
    
    resetSeries(false); 
    modeModal.style.display = 'flex';
}

backToModeBtn.addEventListener('click', exitToMenu);
exitFromWinnerBtn.addEventListener('click', exitToMenu);

playAgainBtn.addEventListener('click', () => {
    winnerModal.style.display = 'none';
    resetGame(); 
    player1SeriesScore = 0; 
    player2SeriesScore = 0;
    
    document.getElementById('game-container').style.display = 'block';
    statsBox.style.display = 'block';
    
    if (isTwoPlayer) {
        exitToMenu();
    } else {
        // For AI, we must exit to menu to re-select series length
        exitToMenu();
        // message.textContent = `${player1Name}, make your move!`;
    }
});

// --- MULTIPLAYER ROOM LOGIC ---

createRoomBtn.addEventListener('click', () => {
    friendModal.style.display = 'none';
    handleCreateRoom();
});

joinRoomBtn.addEventListener('click', () => {
    friendModal.style.display = 'none';
    joinRoomModal.style.display = 'flex';
});

submitJoinRoomBtn.addEventListener('click', () => {
    const code = roomCodeInput.value.trim().toUpperCase();
    if (code.length === 4) {
        handleJoinRoom(code);
    } else {
        showToast("Please enter a valid 4-digit code.", "error");
    }
});

waitingModal.querySelector('.back-btn').addEventListener('click', () => {
    stopPolling();
    localStorage.removeItem('rps_roomCode'); 
    currentRoomCode = null;
});


async function handleCreateRoom() {
    try {
        const response = await fetch('/api/create_room', { method: 'POST' });
        if (!response.ok) throw new Error('Server error');
        
        const data = await response.json();
        if (data.success) {
            currentRoomCode = data.room_code;
            localStorage.setItem('rps_roomCode', currentRoomCode); 
            roomCodeDisplay.textContent = currentRoomCode;
            waitingModal.style.display = 'flex';
            startPolling(); 
        } else {
            showToast(data.message, "error");
            friendModal.style.display = 'flex'; 
        }
    } catch (error) {
        showToast("Network error creating room.", "error");
        friendModal.style.display = 'flex'; 
    }
}

async function handleJoinRoom(code) {
    try {
        const response = await fetch('/api/join_room', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_code: code })
        });
        
        if (!response.ok) {
             const errorData = await response.json();
             throw new Error(errorData.message || `Server error: ${response.status}`);
        }

        const data = await response.json();
        if (data.success) {
            currentRoomCode = data.room_code;
            localStorage.setItem('rps_roomCode', currentRoomCode); 
            player1Name = data.p1_name; 
            player1Avatar = data.p1_avatar; 
            player2Name = data.p2_name;
            player2Avatar = data.p2_avatar; 
            
            joinRoomModal.style.display = 'none';
            seriesLength = 0; 
            startGameUI(); 
            startPolling(); 
        } else {
            showToast(data.message, "error");
        }
    } catch (error) {
        showToast(`Failed to join: ${error.message}`, "error");
    }
}

// --- FIX: ADDED BUTTON RE-ENABLE ---
function startGameUI() {
    document.getElementById('player1-label').textContent = player1Name;
    document.getElementById('player2-label').textContent = player2Name;
    document.getElementById('player1-avatar').textContent = player1Avatar; 
    document.getElementById('player2-avatar').textContent = player2Avatar; 
    
    document.getElementById('player1-series-label').textContent = `${player1Name} Wins:`;
    document.getElementById('player2-series-label').textContent = `${player2Name} Wins:`;
    p1StatsLabel.textContent = player1Name;
    p2StatsLabel.textContent = player2Name;
    
    // Update series display text
    let seriesText = "Unlimited";
    if (seriesLength > 0) {
        const targetWins = Math.ceil(seriesLength / 2);
        seriesText = `Best of ${seriesLength} (${targetWins} Wins)`;
    }
    seriesTargetDisplay.textContent = seriesText;
    
    waitingModal.style.display = 'none';
    joinRoomModal.style.display = 'none';
    friendModal.style.display = 'none';
    modeModal.style.display = 'none';
    nameModal.style.display = 'none';
    
    document.getElementById('game-container').style.display = 'block';
    statsBox.style.display = 'block';
    
    if (isTwoPlayer) {
        chatBoxContainer.style.display = 'block';
    } else {
        chatBoxContainer.style.display = 'none';
    }
    
    // --- THIS IS THE FIX for Problem 3 ---
    // Explicitly re-enable buttons when starting a new game
    buttons.forEach(btn => btn.disabled = false);
    // --- END FIX ---
    
    resetGame(); 
    
    if(!isTwoPlayer) {
        message.textContent = `${player1Name}, make your move!`;
    }
}

function startPolling() {
    if (pollingInterval) return; 
    checkGameStatus(); 
    pollingInterval = setInterval(checkGameStatus, 2500); 
}

function stopPolling() {
    clearInterval(pollingInterval);
    pollingInterval = null;
}

async function checkGameStatus() {
    if (!currentRoomCode) {
        stopPolling();
        return;
    }
    
    try {
        const response = await fetch(`/api/game_status?room_code=${currentRoomCode}`);
        if (!response.ok) {
            stopPolling();
            localStorage.removeItem('rps_roomCode'); 
            const errorData = await response.json();
            showToast(errorData.message || "Lost connection to game room.", "error");
            exitToMenu(); 
            return;
        }
        
        const data = await response.json();
        if (data.success) {
            handleGameUpdate(data.game); 
        }
    } catch (error) {
        console.error("Polling error:", error);
    }
}

function updateChat(messages) {
    if (messages.length === currentChatMessages.length) {
        return; 
    }

    const shouldScroll = chatMessagesDiv.scrollTop + chatMessagesDiv.clientHeight >= chatMessagesDiv.scrollHeight - 20;

    const newMessages = messages.slice(currentChatMessages.length);
    
    newMessages.forEach(msg => {
        const msgWrapper = document.createElement('div');
        msgWrapper.className = 'chat-message';
        
        const msgBubble = document.createElement('div');
        msgBubble.className = 'message-bubble';
        
        const senderName = document.createElement('div');
        senderName.className = 'sender-name';
        senderName.textContent = msg.sender;
        
        const msgText = document.createElement('div');
        msgText.className = 'message-text';
        msgText.textContent = msg.text;
        
        msgBubble.appendChild(senderName);
        msgBubble.appendChild(msgText);
        msgWrapper.appendChild(msgBubble);

        if (msg.sender === myPlayerName) {
            msgWrapper.classList.add('my-message');
        } else {
            msgWrapper.classList.add('other-message');
        }
        
        chatMessagesDiv.appendChild(msgWrapper);
    });

    currentChatMessages = messages; 

    if (shouldScroll) {
        chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    }
}


function handleGameUpdate(game) {
    if (game.status !== 'WAITING' && waitingModal.style.display === 'flex') {
        player1Name = game.p1_name;
        player1Avatar = game.p1_avatar; 
        player2Name = game.p2_name;
        player2Avatar = game.p2_avatar; 
        startGameUI();
    }
    
    if (isTwoPlayer) {
        updateChat(game.chat_messages);
    }

    const isMyTurn = (game.status === 'P1_TURN' && myPlayerName === game.p1_name) ||
                     (game.status === 'P2_TURN' && myPlayerName === game.p2_name);

    if (game.status === 'P1_TURN' || game.status === 'P2_TURN') {
        player1Hand.textContent = game.p1_choice ? '✅' : '❔';
        player2Hand.textContent = game.p2_choice ? '✅' : '❔';
        
        player1Hand.classList.toggle('shaking', !game.p1_choice);
        player2Hand.classList.toggle('shaking', !game.p2_choice);
        
        if (isMyTurn) {
            message.textContent = "It's your turn. Make your move!";
            buttons.forEach(btn => btn.disabled = false);
        } else {
            const waitingFor = (myPlayerName === game.p1_name) ? game.p2_name : game.p1_name;
            message.textContent = `Waiting for ${waitingFor} to move...`;
            buttons.forEach(btn => btn.disabled = true);
        }
    }
    
    if (game.status === 'RESOLVED') {
        buttons.forEach(btn => btn.disabled = true);
        player1Hand.classList.remove('shaking'); 
        player2Hand.classList.remove('shaking'); 
        
        if (!message.textContent.includes("Win") && !message.textContent.includes("Lose") && !message.textContent.includes("Tie")) { 
            player1Hand.textContent = choiceToEmoji(game.p1_choice);
            player2Hand.textContent = choiceToEmoji(game.p2_choice);
            
            let roundResult = game.result;
            let resultMsg = "";
            let p1Won = false;
            let tie = false;
            
            if (roundResult === 'tie') {
                resultMsg = "It's a Tie! 🤝";
                tie = true;
                playSound('sound-tie'); 
            } else if ((roundResult === 'win' && myPlayerName === game.p1_name) ||
                       (roundResult === 'lose' && myPlayerName === game.p2_name)) {
                resultMsg = "You Win the Round! 🥇";
                p1Won = true; 
                playSound('sound-win'); 
            } else {
                resultMsg = "You Lose the Round... 🥈";
                p1Won = false; 
                playSound('sound-lose'); 
            }
            
            message.textContent = resultMsg;
            
            // --- PLAYER STATS FIX ---
            roundsPlayed++;
            if (game.result === 'tie') {
                ties++;
                p1CurrentStreak = 0;
                p2CurrentStreak = 0;
            } else if (game.result === 'win') { // P1 (session holder) won
                p1Wins++;
                player1SeriesScore++; // Update series score
                p1CurrentStreak++;
                p2CurrentStreak = 0;
                if(p1CurrentStreak > p1LongestStreak) p1LongestStreak = p1LongestStreak;
            } else { // P2 won (game.result === 'lose')
                player2SeriesScore++; // Update series score
                p2CurrentStreak++;
                p1CurrentStreak = 0;
                if(p2CurrentStreak > p2LongestStreak) p2LongestStreak = p2LongestStreak;
            }
            updateStatsDisplay(); 
            // --- END STATS FIX ---
            
            if (roundResult === 'win') { 
                player1Hand.classList.add('win-hand');
                player2Hand.classList.add('lose-hand');
            } else if (roundResult === 'lose') { 
                player2Hand.classList.add('win-hand');
                player1Hand.classList.add('lose-hand');
            }
            
            if(!tie) {
                if(game.result === 'win') player1Score++;
                if(game.result === 'lose') player2Score++;
            }
            
            updateScoreboard(); 
            addToHistory({
                player1: game.p1_name, player2: game.p2_name,
                choice1: game.p1_choice, choice2: game.p2_choice,
                result: game.result
            });
            
            // Check for series winner AFTER updating scores
            const seriesOver = checkSeriesWinner(); 

            if (!seriesOver && myPlayerName === game.p1_name) {
                setTimeout(resetRound, 3000); 
            }
        }
    }
}

async function resetRound() {
    if (!currentRoomCode) return;
    try {
        await fetch('/api/reset_round', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({ room_code: currentRoomCode })
        });
        player1Hand.classList.remove('win-hand', 'lose-hand'); 
        player2Hand.classList.remove('win-hand', 'lose-hand'); 
    } catch (error) {
        showToast("Error starting next round.", "error");
    }
}

async function sendChatMessage() {
    const messageText = chatInput.value.trim();
    if (!messageText || !currentRoomCode) {
        return;
    }
    
    const tempChatId = `temp_${Math.random()}`; 
    chatInput.value = ''; 
    
    const messages = [
        ...currentChatMessages,
        { id: tempChatId, sender: myPlayerName, text: messageText }
    ];
    updateChat(messages);

    try {
        const response = await fetch('/api/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_code: currentRoomCode,
                message_text: messageText
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message);
        }
        
    } catch (error) {
        showToast(`Error sending message: ${error.message}`, "error");
        chatInput.value = messageText; 
        currentChatMessages = currentChatMessages.filter(m => m.id !== tempChatId);
        chatMessagesDiv.innerHTML = ''; 
        updateChat(currentChatMessages); 
    }
}

sendChatBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
});


// --- Core Game/Stat Functions ---

function updateStatsDisplay() {
    let p2SessionWins;
    if (isTwoPlayer) {
        // In 2P, p1Wins is *my* wins. p2Wins is calculated from total.
        p2SessionWins = roundsPlayed - p1Wins - ties;
    } else {
        // In AI, p1Wins is *my* wins, and p2Wins is *AI* wins. Both are tracked.
        p2SessionWins = p2Wins; 
    }
    
    roundsPlayedSpan.textContent = roundsPlayed;
    const p1WinRate = roundsPlayed > 0 ? ((p1Wins / roundsPlayed) * 100).toFixed(1) : 0.0;
    const p2WinRate = roundsPlayed > 0 ? ((p2SessionWins / roundsPlayed) * 100).toFixed(1) : 0.0;
    p1WinRateSpan.textContent = `${p1WinRate}%`;
    p2WinRateSpan.textContent = `${p2WinRate}%`;
    p1LongestStreakSpan.textContent = p1LongestStreak;
    p2LongestStreakSpan.textContent = p2LongestStreak;
}

function choiceToEmoji(choice) {
    switch(choice) {
        case 'rock': return '✊';
        case 'paper': return '🖐️';
        case 'scissors': return '✌️';
    }
    return '❔';
}

function updateScoreboard() {
    player1ScoreSpan.textContent = player1Score;
    player2ScoreSpan.textContent = player2Score;
    player1SeriesScoreSpan.textContent = player1SeriesScore;
    player2SeriesScoreSpan.textContent = player2SeriesScore;
}

function addToHistory(round) {
    history.push(round);
    if(history.length > 10) history.shift();
    historyList.innerHTML = '';
    [...history].reverse().forEach((r, index) => {
        const li = document.createElement('li');
        let resultText = '';
        const p1e = choiceToEmoji(r.choice1);
        const p2e = choiceToEmoji(r.choice2);
        
        if(r.result === 'win') {
            resultText = `${r.player1} Wins (${p1e} vs ${p2e})`;
        } else if(r.result === 'lose') {
            resultText = `${r.player2} Wins (${p2e} vs ${p1e})`;
        } else {
            resultText = `Tie (${p1e} vs ${p2e})`;
        }
        li.textContent = `Round ${history.length - index}: ${resultText}`;
        li.className = r.result;
        historyList.appendChild(li);
    });
}

function checkSeriesWinner() {
    // This function is now called by BOTH AI and 2P games
    if (seriesLength === 0) return false; // Not a series game
    
    const target = Math.ceil(seriesLength / 2);
    let winner = null;
    
    if (player1SeriesScore >= target) {
        winner = player1Name;
    } else if (player2SeriesScore >= target) {
        winner = player2Name;
    }
    
    if (winner) {
        document.getElementById('final-winner-message').textContent = `${winner} wins the Best of ${seriesLength} series! 🏆`;
        winnerModal.style.display = 'flex';
        buttons.forEach(btn => btn.disabled = true); // Disable buttons
        return true;
    }
    return false;
}

// This function is now ONLY used for AI games. 2P game logic is in handleGameUpdate
function incrementAISeriesScore(winner) {
    if (winner === 'player1') {
        player1SeriesScore++;
    } else {
        player2SeriesScore++;
    }
    return checkSeriesWinner();
}

async function handleChoice(choice) {
    player1Hand.classList.remove('win-hand', 'lose-hand');
    player2Hand.classList.remove('win-hand', 'lose-hand');

    if (isTwoPlayer) {
        if (!currentRoomCode) return; 
        
        buttons.forEach(btn => btn.disabled = true);
        message.textContent = "Move submitted. Waiting for opponent...";
        player1Hand.classList.add('shaking'); 
        
        try {
            await fetch('/api/submit_move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    room_code: currentRoomCode,
                    choice: choice
                })
            });
        } catch (error) {
            showToast("Failed to submit move. Please try again.", "error");
            buttons.forEach(btn => btn.disabled = false); 
            player1Hand.classList.remove('shaking');
        }
    } else {
        playComputerRound(choice);
    }
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function runCountdownAnimation() {
    message.textContent = "3...";
    player1Hand.textContent = '✊';
    player2Hand.textContent = '✊';
    player1Hand.classList.add('shaking');
    player2Hand.classList.add('shaking');
    await wait(700);
    
    message.textContent = "2...";
    await wait(700);
    
    message.textContent = "1...";
    await wait(700);
    
    message.textContent = "SHOOT!";
    player1Hand.classList.remove('shaking');
    player2Hand.classList.remove('shaking');
}

async function playComputerRound(playerChoice) {
    buttons.forEach(btn => btn.disabled = true);
    
    await runCountdownAnimation();

    try {
        const response = await fetch('/api/play_computer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                p1_choice: playerChoice
            })
        });
        if (!response.ok) { throw new Error(`Server error: ${response.status}`); }
        const data = await response.json();
        
        const result = data.result;
        const choice1 = data.p1_choice;
        const choice2 = data.p2_choice;

        player1Hand.textContent = choiceToEmoji(choice1);
        player2Hand.textContent = choiceToEmoji(choice2);

        let seriesWin = false;
        roundsPlayed++; 

        if(result === 'win') {
            message.textContent = `${player1Name} Wins the Round! 🥇`;
            player1Score++;
            p1Wins++; 
            p1CurrentStreak++;
            p2CurrentStreak = 0;
            if(p1CurrentStreak > p1LongestStreak) p1LongestStreak = p1LongestStreak;
            player1Hand.classList.add('win-hand'); 
            player2Hand.classList.add('lose-hand');
            seriesWin = incrementAISeriesScore('player1');
            playSound('sound-win'); 
        } else if(result === 'lose') {
            message.textContent = `${player2Name} Wins the Round! 🥈`;
            player2Score++;
            p2Wins++; 
            p2CurrentStreak++;
            p1CurrentStreak = 0;
            if(p2CurrentStreak > p2LongestStreak) p2LongestStreak = p2LongestStreak;
            player2Hand.classList.add('win-hand'); 
            player1Hand.classList.add('lose-hand');
            seriesWin = incrementAISeriesScore('player2');
            playSound('sound-lose'); 
        } else {
            message.textContent = "It's a Tie! 🤝";
            ties++;
            p1CurrentStreak = 0;
            p2CurrentStreak = 0;
            playSound('sound-tie'); 
        }

        updateScoreboard();
        updateStatsDisplay(); 
        addToHistory({
            player1: player1Name, player2: player2Name,
            choice1, choice2, result
        });
        if (!seriesWin) {
            setTimeout(() => {
                buttons.forEach(btn => btn.disabled = false);
                message.textContent = `${player1Name}, make your next move!`;
                player1Hand.classList.remove('win-hand', 'lose-hand');
                player2Hand.classList.remove('win-hand', 'lose-hand');
            }, 2000); 
        }
    } catch (error) {
        console.error("Error playing computer round:", error);
        showToast("Failed to play round due to a server error.", "error");
        buttons.forEach(btn => btn.disabled = false);
        player1Hand.classList.remove('shaking');
        player2Hand.classList.remove('shaking');
        message.textContent = `${player1Name}, an error occurred. Try again.`;
    }
}

function resetGame() {
    player1Score = 0;
    player2Score = 0;
    ties = 0;
    updateScoreboard();
    history = [];
    historyList.innerHTML = '';
    player1Hand.textContent = '❔';
    player2Hand.textContent = '❔';
    player1Hand.classList.remove('win-hand', 'lose-hand');
    player2Hand.classList.remove('win-hand', 'lose-hand');
    
    currentChatMessages = [];
    chatMessagesDiv.innerHTML = '';
    
    if(isTwoPlayer) {
        player1Hand.classList.add('shaking');
        player2Hand.classList.add('shaking');
    } else {
        message.textContent = `${player1Name}, make your move!`;
    }
}

function resetSeries(resetPersistent = true) {
    player1SeriesScore = 0;
    player2SeriesScore = 0;
    seriesLength = 0;
    seriesTargetDisplay.textContent = 'Unlimited';
    // buttons.forEach(btn => btn.disabled = false); // This is now handled by startGameUI
    
    if (resetPersistent) {
        roundsPlayed = 0;
        p1Wins = 0;
        p2Wins = 0;
        p1CurrentStreak = 0;
        p2CurrentStreak = 0; 
        p1LongestStreak = 0;
        p2LongestStreak = 0;
    }
    
    updateStatsDisplay();
    resetGame();
}

buttons.forEach(btn => {
    btn.addEventListener('click', () => handleChoice(btn.dataset.choice));
});

resetBtn.addEventListener('click', resetGame);

document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();
});

updateStatsDisplay(); 
"""

def get_css_content():
    """Returns the main CSS styling (with TOAST notifications)."""
    # FIX: Added styles for series-modal
    return """/* Reset */
* {
margin: 0;
padding: 0;
box-sizing: border-box;
font-family: 'Poppins', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

@keyframes animated-gradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

body {
background: linear-gradient(-45deg, #3a1c71, #d76d77, #ffaf7b, #23a6d5, #23d5ab);
background-size: 400% 400%;
animation: animated-gradient 20s ease infinite;
min-height: 100vh;
display: flex;
justify-content: center;
align-items: center;
padding: 20px;
color: #fff;
overflow-x: hidden;
position: relative;
}

.container {
background: rgba(255, 255, 255, 0.15);
backdrop-filter: blur(8px);
border-radius: 20px;
border: 1px solid rgba(255, 255, 255, 0.3);
padding: 30px 40px;
max-width: 450px;
width: 100%;
box-shadow:
0 4px 30px rgba(0,0,0,0.1),
inset 0 0 40px rgba(255,255,255,0.05);
text-align: center;
}

body.dark-mode {
background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e, #121212);
background-size: 400% 400%;
animation: animated-gradient 25s ease infinite;
color: #e0e0e0;
}

body.dark-mode .container {
background: rgba(0,0,0,0.4);
backdrop-filter: blur(8px);
border: 1px solid rgba(255, 255, 255, 0.1);
box-shadow: 0 4px 30px rgba(0,0,0,0.4);
}

body.dark-mode .modal-content {
background: #1e1e1e;
box-shadow: 0 0 20px rgba(255,255,255,0.2);
}

.avatar-picker {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 15px 0;
}
.avatar-choice {
    font-size: 1.8rem;
    padding: 5px;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.3s ease;
    opacity: 0.6;
}
.avatar-choice:hover {
    opacity: 1;
    transform: scale(1.2);
}
.avatar-choice.selected {
    opacity: 1;
    transform: scale(1.2);
    box-shadow: 0 0 15px #ffaf7b;
}

.profile-display {
display: flex;
flex-direction: column;
align-items: center;
margin-bottom: 20px;
padding: 10px;
border-bottom: 2px solid rgba(255, 255, 255, 0.3);
}
.profile-avatar {
    font-size: 3rem;
    line-height: 1;
    margin-bottom: 5px;
}
.profile-display h3 {
margin: 0;
font-size: 1.5rem; 
font-weight: 600; 
color: #fff;
}

.stats-box {
position: fixed;
top: 65px;
left: 15px;
right: auto;
width: 250px;
background: rgba(0, 0, 0, 0.75);
backdrop-filter: blur(5px);
border-radius: 15px;
border: 1px solid rgba(255, 255, 255, 0.2);
padding: 15px;
z-index: 999;
text-align: left;
font-size: 0.9rem;
box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
color: #fff;
}
.stats-box h3 {
text-align: center;
margin-bottom: 10px;
color: #ffaf7b;
font-size: 1.1rem;
font-weight: 600;
}
.stats-box p {
line-height: 1.4;
margin-left: 5px;
}
.stat-group {
margin: 10px 0;
padding: 5px 0;
border-top: 1px dashed rgba(255, 255, 255, 0.15);
}
.stat-group h4 {
margin: 5px 0;
font-size: 1rem;
color: #d76d77;
font-weight: 600;
}
body.dark-mode .stats-box {
background: rgba(0, 0, 0, 0.85);
border: 1px solid rgba(255, 255, 255, 0.1);
}
@media (max-width: 768px) {
.stats-box {
position: static;
margin: 20px auto 0;
width: 90%;
max-width: 400px;
}
}

.series-score {
font-size: 0.9rem;
font-weight: 500;
margin-bottom: 20px;
background: rgba(255, 255, 255, 0.1);
border-radius: 10px;
padding: 10px;
border: 1px solid rgba(255, 255, 255, 0.2);
line-height: 1.6;
}
.series-score strong {
font-weight: 700;
margin: 0 8px;
color: #ffaf7b;
}

@keyframes glow-win {
    0% { box-shadow: 0 0 10px #4caf50, 0 0 20px #4caf50; }
    50% { box-shadow: 0 0 30px #4caf50, 0 0 50px #4caf50, 0 0 10px #fff; }
    100% { box-shadow: 0 0 10px #4caf50, 0 0 20px #4caf50; }
}

.hand.win-hand {
border-color: #4caf50;
animation: glow-win 1.5s ease-in-out infinite;
transform: scale(1.05);
}
.hand.lose-hand {
border-color: #f44336;
opacity: 0.7;
transform: scale(0.95);
}

.winner-content {
background: linear-gradient(135deg, #1abc9c, #2ecc71);
color: white;
padding: 40px;
border-radius: 25px;
box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
#final-winner-message {
font-size: 1.8rem;
font-weight: 700; 
margin-bottom: 25px;
text-shadow: 2px 2px 5px rgba(0,0,0,0.6);
}
#play-again-btn { background: #3498db; margin: 10px; }
#play-again-btn:hover { background: #2980b9; box-shadow: 0 0 30px #2980b9; }
#exit-from-winner { background: #e74c3c; margin: 10px; }
#exit-from-winner:hover { background: #c0392b; box-shadow: 0 0 30px #c0392b; }

.mode-toggle {
position: fixed;
top: 15px;
background: rgba(255, 255, 255, 0.2);
border: none;
border-radius: 50%;
width: 40px;
height: 40px;
font-size: 1.2rem;
cursor: pointer;
z-index: 1001;
box-shadow: 0 2px 10px rgba(0,0,0,0.3);
transition: background 0.3s;
}
.mode-toggle:hover {
background: rgba(255, 255, 255, 0.4);
}
body.dark-mode .mode-toggle { background: rgba(255, 255, 255, 0.1); }
body.dark-mode .mode-toggle:hover { background: rgba(255, 255, 255, 0.2); }
.mode-toggle { right: 15px; }

#reset-btn-top {
padding: 8px 18px;
font-weight: 700;
font-size: 0.9rem;
background: #ff5f6d;
border: none;
border-radius: 50px;
cursor: pointer;
color: white;
box-shadow: 0 0 10px #ff5f6d;
transition: all 0.3s ease;
position: absolute;
top: 10px;
left: 10px;
z-index: 900;
}
#reset-btn-top:hover {
background: #ff424c;
box-shadow: 0 0 30px #ff424c;
transform: scale(1.05);
}

@keyframes pulse-title {
    0% { text-shadow: 2px 2px 8px rgba(0,0,0,0.7); }
    50% { text-shadow: 2px 2px 16px rgba(0,0,0,1), 0 0 30px #ffaf7b; }
    100% { text-shadow: 2px 2px 8px rgba(0,0,0,0.7); }
}

h1 {
font-weight: 900;
font-size: 2.5rem;
margin-bottom: 20px;
letter-spacing: 2px;
text-shadow: 2px 2px 8px rgba(0,0,0,0.7);
animation: pulse-title 4s ease-in-out infinite;
}
.title-rock { color: #ffaf7b; }
.title-paper { color: #d76d77; }
.title-scissors { color: #3a1c71; }
body.dark-mode .title-scissors { color: #e0e0e0; }


.scoreboard {
display: flex;
justify-content: space-around;
margin-bottom: 15px;
font-size: 1.1rem;
font-weight: 600; 
text-shadow: 1px 1px 4px rgba(0,0,0,0.5);
align-items: center; 
}
.score-avatar {
    font-size: 1.5rem;
    margin-right: 8px;
    vertical-align: middle;
}
.scoreboard div {
    display: flex; 
    align-items: center; 
}

.hands {
display: flex;
justify-content: space-around;
margin-bottom: 20px;
perspective: 800px;
}

.hand {
font-size: 6rem;
width: 130px;
height: 130px;
background: rgba(255,255,255,0.15);
border-radius: 20px;
box-shadow: 0 4px 20px rgba(0,0,0,0.5);
display: flex;
justify-content: center;
align-items: center;
user-select: none;
border: 3px solid rgba(255,255,255,0.4);
transform-style: preserve-3d;
transition: transform 0.7s ease, background 0.3s ease, box-shadow 0.5s ease, border-color 0.5s ease;
position: relative;
}

@keyframes shakeHand {
0%, 100% { transform: rotate(0deg); }
20% { transform: rotate(15deg); }
40% { transform: rotate(-15deg); }
60% { transform: rotate(15deg); }
80% { transform: rotate(-15deg); }
}

.hand.shaking {
animation: shakeHand 0.7s cubic-bezier(.36,.07,.19,.97) infinite both;
}

.message {
font-size: 1.3rem;
font-weight: 700;
margin-bottom: 25px;
min-height: 40px;
text-shadow: 1px 1px 4px rgba(0,0,0,0.5);
}

.choices {
display: flex;
justify-content: center;
gap: 25px;
margin-bottom: 30px;
}

.choice-btn {
font-size: 2.5rem;
background: rgba(255,255,255,0.25);
border: 2.5px solid #fff;
padding: 15px 25px;
border-radius: 50%;
color: white;
cursor: pointer;
transition: all 0.3s ease;
box-shadow: 0 0 15px rgba(255,255,255,0.3);
user-select: none;
}

.choice-btn:hover {
background: #fff;
color: #3a1c71;
transform: scale(1.3);
box-shadow: 0 0 15px #fff, 0 0 40px #ffaf7b;
}
.choice-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
    box-shadow: 0 0 15px rgba(255,255,255,0.3);
}

#reset-btn {
padding: 10px 30px;
font-weight: 700;
font-size: 1rem;
background: #ff5f6d;
border: none;
border-radius: 50px;
cursor: pointer;
color: white;
box-shadow: 0 0 15px #ff5f6d;
transition: all 0.3s ease;
margin-top: 20px; 
}
#reset-btn:hover {
background: #ff424c;
box-shadow: 0 0 40px #ff424c;
transform: scale(1.05);
}

.history-container {
margin-top: 30px;
text-align: left;
max-height: 180px;
overflow-y: auto;
background: rgba(255, 255, 255, 0.12);
border-radius: 12px;
padding: 15px 20px;
box-shadow: inset 0 0 15px rgba(0,0,0,0.25);
}
.history-container h2 {
margin-bottom: 10px;
font-weight: 700;
font-size: 1.2rem;
color: #ffaf7b;
text-shadow: 0 0 6px #ffaf7b;
}
#history-list { list-style-type: none; }
#history-list li {
padding: 6px 0;
border-bottom: 1px solid rgba(255,255,255,0.2);
font-size: 0.95rem;
text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
}
.win { color: #50fa7b; } 
.lose { color: #ff5555; } 
.tie { color: #f1fa8c; } 

#history-list::-webkit-scrollbar { width: 8px; }
#history-list::-webkit-scrollbar-track { background: transparent; }
#history-list::-webkit-scrollbar-thumb { background-color: #ffaf7b; border-radius: 20px; }

@keyframes modal-swoop {
    from {
        opacity: 0;
        transform: scale(0.8) translateY(50px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

.modal {
position: fixed;
top: 0;
left: 0;
width: 100%;
height: 100%;
background: rgba(0,0,0,0.7);
display: none; 
justify-content: center;
align-items: center;
z-index: 1000;
}
.modal[style*="display: flex;"] {
    display: flex !important;
}

.modal-content {
background: rgba(0,0,0,0.85);
padding: 30px;
border-radius: 20px;
text-align: center;
width: 90%;
max-width: 350px; 
box-shadow: 0 0 20px #fff;
animation: modal-swoop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

body.dark-mode .modal-content {
background: #1e1e1e;
box-shadow: 0 0 20px rgba(255,255,255,0.2);
}
.modal-content h2 {
margin-bottom: 20px;
color: #ffaf7b;
font-weight: 600;
}
.modal-content p {
    margin-bottom: 15px;
    font-size: 0.95rem;
}
.modal-content input {
display: block;
width: 90%;
margin: 10px auto;
padding: 10px;
border-radius: 10px;
border: none;
font-size: 1rem;
background: #fff;
color: #333;
}
body.dark-mode .modal-content input {
    background: #333;
    color: #eee;
}
.modal-content button {
padding: 10px 20px;
font-size: 1rem;
font-weight: 700;
background: #ff5f6d;
border: none;
border-radius: 50px;
color: white;
cursor: pointer;
margin: 10px;
box-shadow: 0 0 15px #ff5f6d;
transition: all 0.3s ease;
}
.modal-content button:hover {
background: #ff424c;
box-shadow: 0 0 30px #ff424c;
transform: scale(1.05);
}

/* --- FIX: Styles for new series buttons --- */
.modal-content button.series-btn {
    display: block;
    width: 90%;
    margin: 10px auto;
    background: #3498db; /* Blue to differentiate */
    font-size: 0.9rem;
    box-shadow: 0 0 15px #3498db;
}
.modal-content button.series-btn:hover {
    background: #2980b9;
    box-shadow: 0 0 30px #2980b9;
}


.chat-box-container {
    width: 100%;
    margin-top: 30px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 15px 20px;
    box-shadow: inset 0 0 15px rgba(0,0,0,0.25);
    text-align: left;
}
.chat-box-container h3 {
    margin-bottom: 10px;
    font-weight: 700;
    font-size: 1.2rem;
    color: #ffaf7b;
    text-shadow: 0 0 6px #ffaf7b;
    text-align: center;
}
.chat-messages {
    height: 150px;
    overflow-y: auto;
    padding: 10px 5px; 
    margin-bottom: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px; 
}
.chat-message { display: flex; width: 100%; }
.chat-message.my-message { justify-content: flex-end; }
.chat-message.other-message { justify-content: flex-start; }
.message-bubble {
    padding: 8px 14px;
    border-radius: 18px;
    max-width: 80%;
    word-wrap: break-word;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
.other-message .message-bubble {
    background: rgba(255, 255, 255, 0.2);
    border-bottom-left-radius: 4px; 
    color: #fff;
}
.my-message .message-bubble {
    background: #ffaf7b;
    border-bottom-right-radius: 4px; 
    color: #3a1c71;
    font-weight: 500;
}
.sender-name {
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 3px;
    color: #d76d77;
}
.my-message .sender-name { display: none; }
.message-text { font-size: 0.95rem; line-height: 1.4; }
.chat-input-area { display: flex; gap: 10px; align-items: center; }
#chat-input {
    flex-grow: 1;
    padding: 10px 15px; 
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 20px;
    background: rgba(255,255,255,0.2);
    color: #fff;
    font-size: 0.9rem;
}
#chat-input::placeholder { color: rgba(255,255,255,0.6); }
#send-chat-btn {
    flex-shrink: 0; 
    width: 40px;
    height: 40px;
    padding: 0; 
    font-weight: 700;
    font-size: 0.9rem;
    background: #ffaf7b;
    border: none;
    border-radius: 50%; 
    cursor: pointer;
    color: #3a1c71;
    transition: all 0.3s ease;
    display: flex; 
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 15px rgba(255, 175, 123, 0.5);
}
#send-chat-btn:hover {
    box-shadow: 0 0 25px #ffaf7b;
    transform: scale(1.05);
}
#send-chat-btn svg { width: 20px; height: 20px; fill: #3a1c71; margin-left: 2px; }
body.dark-mode .chat-box-container { background: rgba(0,0,0,0.3); }
body.dark-mode .other-message .message-bubble { background: #3a3a3a; }
body.dark-mode .my-message .message-bubble { background: #d76d77; color: #fff; }
body.dark-mode .sender-name { color: #ffaf7b; }
body.dark-mode #chat-input { background: rgba(0,0,0,0.2); border-color: rgba(255,255,255,0.1); }
body.dark-mode #chat-input::placeholder { color: rgba(255,255,255,0.4); }
body.dark-mode #send-chat-btn { background: #d76d77; box-shadow: 0 0 15px rgba(215, 109, 119, 0.5); }
body.dark-mode #send-chat-btn:hover { box-shadow: 0 0 25px #d76d77; }
body.dark-mode #send-chat-btn svg { fill: #fff; }
.chat-messages::-webkit-scrollbar { width: 8px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }
.chat-messages::-webkit-scrollbar-thumb { background-color: #ffaf7b; border-radius: 20px; }
/* --- End Chat Styles --- */

@media (max-width: 500px) {
.hands { flex-direction: column; gap: 15px; }
.hand { width: 100px; height: 100px; font-size: 4.5rem; }
.choice-btn { font-size: 2rem; padding: 12px 20px; }
h1 { font-size: 1.8rem; }
}

/* --- TOAST NOTIFICATION STYLES (Unchanged) --- */
#toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}
.toast {
    background: #fff;
    color: #333;
    padding: 15px 20px;
    border-radius: 8px;
    margin-bottom: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.5s cubic-bezier(0.68, -0.55, 0.27, 1.55);
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
}
.toast.show { opacity: 1; transform: translateX(0); }
.toast.success { background-color: #4caf50; color: white; }
.toast.error { background-color: #f44336; color: white; }
.toast.info { background-color: #2196F3; color: white; }
"""


# --- FLASK ROUTES FOR SERVING CONTENT ---

@app.route("/")
def index():
    return render_template_string(get_html_content())

@app.route("/styles.css")
def styles():
    return Response(get_css_content(), mimetype="text/css")

@app.route("/script.js")
def script():
    return Response(get_js_content(), mimetype="application/javascript")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)