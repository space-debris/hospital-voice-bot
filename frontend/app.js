/**
 * City General Hospital — Chat UI Application
 * Handles WebSocket communication, chat interface, voice engine, and login flow
 */

// ── State ──────────────────────────────────────────
const state = {
    sessionId: sessionStorage.getItem('cgh_session_id') || null,
    ws: null,
    connected: false,
    userType: 'guest',
    verified: false,
    patientName: null,
    loginPhone: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    voiceMode: false,       // auto-read bot responses
};

// ── DOM References ─────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const chatArea = $('#chat-area');
const messagesContainer = $('#messages-container');
const messageInput = $('#message-input');
const sendBtn = $('#send-btn');
const typingIndicator = $('#typing-indicator');
const welcomeCard = $('#welcome-card');
const loginBtn = $('#login-btn');
const loginModal = $('#login-modal');
const modalClose = $('#modal-close');
const phoneInput = $('#phone-input');
const otpInput = $('#otp-input');
const sendOtpBtn = $('#send-otp-btn');
const verifyOtpBtn = $('#verify-otp-btn');
const resendOtpBtn = $('#resend-otp-btn');
const loginStepPhone = $('#login-step-phone');
const loginStepOtp = $('#login-step-otp');
const modalStatus = $('#modal-status');
const sessionBadge = $('#session-badge');
const connectionStatus = $('#connection-status');
const otpHint = $('#otp-hint');
const voiceToggle = $('#voice-toggle');
const micBtn = $('#mic-btn');
const voiceStatus = $('#voice-status');
const voiceStatusText = $('#voice-status-text');
const voiceStopBtn = $('#voice-stop-btn');

// ═══════════════════════════════════════════════════
// ── Voice Engine (Web Speech API) ─────────────────
// ═══════════════════════════════════════════════════
class VoiceEngine {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis || null;
        this.isListening = false;
        this.isSpeaking = false;
        this.supported = false;
        this.currentUtterance = null;
        this.lastBotMessageEl = null;

        this._initRecognition();
    }

    _initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('Speech Recognition not supported in this browser.');
            if (micBtn) micBtn.title = 'Voice not supported in this browser';
            return;
        }

        this.supported = true;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'en-IN';       // English (India)
        this.recognition.continuous = false;     // Stop after a pause
        this.recognition.interimResults = true;  // Show partial results
        this.recognition.maxAlternatives = 1;

        // ── Recognition Events ──
        this.recognition.onstart = () => {
            this.isListening = true;
            micBtn.classList.add('listening');
            voiceStatus.classList.add('visible');
            voiceStatus.classList.remove('speaking');
            voiceStatusText.textContent = 'Listening...';
        };

        this.recognition.onresult = (event) => {
            let transcript = '';
            let isFinal = false;

            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    isFinal = true;
                }
            }

            // Show interim transcript in the input box
            messageInput.value = transcript;
            autoResize();
            sendBtn.disabled = !transcript.trim();

            // If final, auto-send the message
            if (isFinal && transcript.trim()) {
                voiceStatusText.textContent = 'Processing...';
                setTimeout(() => {
                    sendMessage();
                    this._hideStatus();
                }, 300);
            }
        };

        this.recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            this.isListening = false;
            micBtn.classList.remove('listening');

            if (event.error === 'no-speech') {
                voiceStatusText.textContent = 'No speech detected. Try again.';
                setTimeout(() => this._hideStatus(), 2000);
            } else if (event.error === 'not-allowed') {
                voiceStatusText.textContent = 'Mic access denied. Check browser permissions.';
                setTimeout(() => this._hideStatus(), 3000);
            } else {
                this._hideStatus();
            }
        };

        this.recognition.onend = () => {
            this.isListening = false;
            micBtn.classList.remove('listening');
            // Status bar hides after result is processed or on error
        };
    }

    // ── Start Listening ──
    startListening() {
        if (!this.supported || this.isListening) return;

        // Stop any ongoing TTS first
        this.stopSpeaking();

        try {
            this.recognition.start();
        } catch (e) {
            console.warn('Recognition start error:', e);
        }
    }

    // ── Stop Listening ──
    stopListening() {
        if (!this.recognition || !this.isListening) return;
        this.recognition.stop();
        this._hideStatus();
    }

    // ── Speak Text (TTS) ──
    speak(text, messageEl) {
        if (!this.synthesis || !state.voiceMode) return;

        // Stop any ongoing speech
        this.stopSpeaking();

        // Clean text for TTS (remove markdown, special chars)
        const cleanText = text
            .replace(/\*\*(.+?)\*\*/g, '$1')  // bold
            .replace(/\*(.+?)\*/g, '$1')      // italic
            .replace(/`(.+?)`/g, '$1')        // code
            .replace(/^[#]+\s/gm, '')         // headers
            .replace(/^[\-\*]\s/gm, '')       // bullets
            .replace(/^\d+\.\s/gm, '')        // numbered
            .replace(/\|/g, ', ')             // table pipes
            .replace(/\-{3,}/g, '')           // horizontal rules
            .replace(/\n+/g, '. ')            // newlines to pauses
            .trim();

        if (!cleanText) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-IN';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        // Try to pick a good voice
        const voices = this.synthesis.getVoices();
        const preferred = voices.find(v =>
            v.lang.startsWith('en') && (v.name.includes('Female') || v.name.includes('Zira') || v.name.includes('Google'))
        ) || voices.find(v => v.lang.startsWith('en'));

        if (preferred) utterance.voice = preferred;

        this.currentUtterance = utterance;
        this.lastBotMessageEl = messageEl;

        utterance.onstart = () => {
            this.isSpeaking = true;
            voiceStatus.classList.add('visible', 'speaking');
            voiceStatusText.textContent = 'Speaking...';
            if (messageEl) messageEl.classList.add('speaking');
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            this._hideStatus();
            if (messageEl) messageEl.classList.remove('speaking');
        };

        utterance.onerror = () => {
            this.isSpeaking = false;
            this._hideStatus();
            if (messageEl) messageEl.classList.remove('speaking');
        };

        this.synthesis.speak(utterance);
    }

    // ── Stop Speaking ──
    stopSpeaking() {
        if (!this.synthesis) return;
        this.synthesis.cancel();
        this.isSpeaking = false;
        if (this.lastBotMessageEl) {
            this.lastBotMessageEl.classList.remove('speaking');
        }
        this._hideStatus();
    }

    _hideStatus() {
        voiceStatus.classList.remove('visible', 'speaking');
    }
}

// Create global voice engine instance
const voice = new VoiceEngine();

// ── WebSocket Connection ───────────────────────────
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
        state.connected = true;
        state.reconnectAttempts = 0;
        connectionStatus.classList.remove('visible');

        // Initialize session
        state.ws.send(JSON.stringify({
            type: 'init',
            session_id: state.sessionId,
        }));
    };

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWSMessage(data);
    };

    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        state.connected = false;
        connectionStatus.classList.add('visible');

        // Reconnect logic
        if (state.reconnectAttempts < state.maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 10000);
            state.reconnectAttempts++;
            setTimeout(connectWebSocket, delay);
        }
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// ── Handle WebSocket Messages ──────────────────────
function handleWSMessage(data) {
    switch (data.type) {
        case 'init':
            state.sessionId = data.session_id;
            state.userType = data.user_type;
            state.verified = data.verified;
            state.patientName = data.patient_name;
            sessionStorage.setItem('cgh_session_id', data.session_id);
            updateSessionUI();
            break;

        case 'chat_response':
            hideTyping();
            const msgEl = addMessage('bot', data.reply);
            state.userType = data.user_type;
            state.verified = data.verified;
            state.sessionId = data.session_id;
            sessionStorage.setItem('cgh_session_id', data.session_id);
            updateSessionUI();

            // Auto-read if voice mode is on
            if (state.voiceMode && msgEl) {
                voice.speak(data.reply, msgEl);
            }
            break;

        case 'typing':
            if (data.status) showTyping();
            else hideTyping();
            break;

        case 'login_response':
            handleLoginResponse(data);
            break;

        case 'otp_response':
            handleOtpResponse(data);
            break;

        case 'pong':
            break;

        case 'error':
            hideTyping();
            addSystemMessage(data.message || 'An error occurred.', 'error');
            break;
    }
}

// ── Send Message ───────────────────────────────────
function sendMessage(text) {
    const message = (text || messageInput.value).trim();
    if (!message || !state.connected) return;

    // Hide welcome card on first message
    if (welcomeCard) {
        welcomeCard.style.display = 'none';
    }

    // Add user message to UI
    addMessage('user', message);

    // Send via WebSocket
    state.ws.send(JSON.stringify({
        type: 'chat',
        message: message,
        session_id: state.sessionId,
    }));

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Show typing indicator
    showTyping();
}

// ── Message UI ─────────────────────────────────────
function addMessage(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;

    const avatar = role === 'bot' ? '🤖' : '👤';
    const formattedContent = formatMarkdown(content);

    // Speaker button for bot messages
    const speakerBtn = role === 'bot'
        ? `<button class="msg-speak-btn" title="Read aloud" onclick="voice.speak(\`${content.replace(/`/g, '\\`').replace(/\\/g, '\\\\')}\`, this.closest('.message'))">🔊</button>`
        : '';

    messageEl.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div>
            <div class="message-bubble">${formattedContent}</div>
            <div class="message-meta">
                <span class="message-time">${formatTime(new Date())}</span>
                ${speakerBtn}
            </div>
        </div>
    `;

    messagesContainer.appendChild(messageEl);
    scrollToBottom();
    return messageEl;
}

function addSystemMessage(text, type = 'info') {
    const el = document.createElement('div');
    el.className = `system-message ${type}`;
    el.innerHTML = `<span>${text}</span>`;
    messagesContainer.appendChild(el);
    scrollToBottom();
}

function showTyping() {
    typingIndicator.classList.add('visible');
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.classList.remove('visible');
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    });
}

// ── Markdown Formatting (Improved) ─────────────────
function formatMarkdown(text) {
    if (!text) return '';

    // Escape HTML first
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Headers: ### text
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Inline code: `text`
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');

    // Horizontal rules: ---
    html = html.replace(/^-{3,}$/gm, '<hr>');

    // Tables: | col | col |
    html = html.replace(/((?:^\|.+\|$\n?)+)/gm, (match) => {
        const rows = match.trim().split('\n').filter(r => r.trim());
        if (rows.length < 2) return match;

        let table = '<table>';
        rows.forEach((row, i) => {
            // Skip separator row (|---|---|)
            if (/^\|[\s\-:]+\|$/.test(row.trim())) return;

            const cells = row.split('|').filter(c => c.trim() !== '');
            const tag = i === 0 ? 'th' : 'td';
            const rowTag = i === 0 ? 'thead' : '';

            if (i === 0) table += '<thead>';
            if (i === 2 || (i === 1 && !/[\-:]{3,}/.test(rows[1]))) table += '<tbody>';

            table += '<tr>';
            cells.forEach(cell => {
                table += `<${tag}>${cell.trim()}</${tag}>`;
            });
            table += '</tr>';

            if (i === 0) table += '</thead>';
        });
        table += '</tbody></table>';
        return table;
    });

    // Bullet lists: - item or * item
    html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Numbered lists: 1. item
    html = html.replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>');

    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph if needed
    if (!html.startsWith('<')) {
        html = `<p>${html}</p>`;
    }

    return html;
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

// ── Login Flow ─────────────────────────────────────
function openLoginModal() {
    loginModal.classList.add('open');
    loginStepPhone.classList.remove('hidden');
    loginStepOtp.classList.add('hidden');
    hideModalStatus();
    phoneInput.value = '';
    otpInput.value = '';
    phoneInput.focus();
}

function closeLoginModal() {
    loginModal.classList.remove('open');
}

function sendOtp() {
    const phone = phoneInput.value.trim();
    if (phone.length !== 10 || !/^\d{10}$/.test(phone)) {
        showModalStatus('Please enter a valid 10-digit phone number.', 'error');
        return;
    }

    state.loginPhone = phone;
    sendOtpBtn.disabled = true;
    sendOtpBtn.textContent = 'Sending...';

    state.ws.send(JSON.stringify({
        type: 'login',
        phone: phone,
        session_id: state.sessionId,
    }));
}

function handleLoginResponse(data) {
    sendOtpBtn.disabled = false;
    sendOtpBtn.textContent = 'Send OTP';

    if (data.success) {
        state.sessionId = data.session_id || state.sessionId;
        sessionStorage.setItem('cgh_session_id', state.sessionId);
        loginStepPhone.classList.add('hidden');
        loginStepOtp.classList.remove('hidden');
        otpHint.textContent = data.message;
        hideModalStatus();
        otpInput.focus();
    } else {
        showModalStatus(data.message, 'error');
    }
}

function verifyOtp() {
    const otp = otpInput.value.trim();
    if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
        showModalStatus('Please enter a valid 6-digit OTP.', 'error');
        return;
    }

    verifyOtpBtn.disabled = true;
    verifyOtpBtn.textContent = 'Verifying...';

    state.ws.send(JSON.stringify({
        type: 'verify_otp',
        phone: state.loginPhone,
        otp: otp,
        session_id: state.sessionId,
    }));
}

function handleOtpResponse(data) {
    verifyOtpBtn.disabled = false;
    verifyOtpBtn.textContent = 'Verify OTP';

    if (data.success) {
        state.verified = true;
        state.userType = 'registered';
        state.patientName = data.patient_name;
        updateSessionUI();

        // Close modal after a brief success display
        showModalStatus(`✅ ${data.message}`, 'success');
        setTimeout(() => {
            closeLoginModal();
            addSystemMessage(`✅ Logged in as ${data.patient_name} (${data.patient_code})`, 'success');
        }, 1000);
    } else {
        showModalStatus(data.message, 'error');
    }
}

function showModalStatus(message, type) {
    modalStatus.textContent = message;
    modalStatus.className = `modal-status show ${type}`;
}

function hideModalStatus() {
    modalStatus.className = 'modal-status';
}

// ── Session UI Updates ─────────────────────────────
function updateSessionUI() {
    const badgeText = sessionBadge.querySelector('.badge-text');

    if (state.verified && state.patientName) {
        sessionBadge.classList.add('verified');
        badgeText.textContent = state.patientName;
        loginBtn.classList.add('logged-in');
        loginBtn.querySelector('span').textContent = 'Verified';
    } else {
        sessionBadge.classList.remove('verified');
        badgeText.textContent = 'Guest';
        loginBtn.classList.remove('logged-in');
        loginBtn.querySelector('span').textContent = 'Login';
    }
}

// ── Auto-resize Textarea ───────────────────────────
function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

// ═══════════════════════════════════════════════════
// ── Event Listeners ───────────────────────────────
// ═══════════════════════════════════════════════════

// Send message
sendBtn.addEventListener('click', () => sendMessage());

messageInput.addEventListener('input', () => {
    sendBtn.disabled = !messageInput.value.trim();
    autoResize();
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (messageInput.value.trim()) {
            sendMessage();
        }
    }
});

// Quick-action chips
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const msg = chip.getAttribute('data-message');
        if (msg) sendMessage(msg);
    });
});

// ── Voice Controls ─────────────────────────────────
// Voice mode toggle (header)
voiceToggle.addEventListener('click', () => {
    state.voiceMode = !state.voiceMode;
    voiceToggle.classList.toggle('active', state.voiceMode);

    if (!state.voiceMode) {
        voice.stopSpeaking();
    }

    // Show brief notification
    const modeText = state.voiceMode ? '🔊 Voice mode ON — bot will read responses aloud' : '🔇 Voice mode OFF';
    addSystemMessage(modeText, 'info');
});

// Mic button — click to toggle listening
micBtn.addEventListener('click', () => {
    if (!voice.supported) {
        addSystemMessage('⚠️ Voice input not supported in this browser. Try Chrome or Edge.', 'error');
        return;
    }

    if (voice.isListening) {
        voice.stopListening();
    } else {
        voice.startListening();
    }
});

// Stop button in voice status bar
voiceStopBtn.addEventListener('click', () => {
    if (voice.isListening) {
        voice.stopListening();
    }
    if (voice.isSpeaking) {
        voice.stopSpeaking();
    }
});

// ── Login modal ────────────────────────────────────
loginBtn.addEventListener('click', () => {
    if (!state.verified) openLoginModal();
});
modalClose.addEventListener('click', closeLoginModal);
loginModal.addEventListener('click', (e) => {
    if (e.target === loginModal) closeLoginModal();
});

// OTP flow
sendOtpBtn.addEventListener('click', sendOtp);
phoneInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendOtp();
});

verifyOtpBtn.addEventListener('click', verifyOtp);
otpInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') verifyOtp();
});

resendOtpBtn.addEventListener('click', () => {
    loginStepOtp.classList.add('hidden');
    loginStepPhone.classList.remove('hidden');
    hideModalStatus();
    phoneInput.focus();
});

// Escape key closes modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLoginModal();
});

// ── Keepalive Ping ─────────────────────────────────
setInterval(() => {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 25000);

// Preload TTS voices (some browsers load them async)
if (window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
    };
}

// ── Initialize ─────────────────────────────────────
connectWebSocket();
