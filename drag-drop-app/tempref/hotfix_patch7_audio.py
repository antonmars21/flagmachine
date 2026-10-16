"""Feature 6: countdown audio for the RO (2026-10-16).

Web Audio API beeps synthesized in JS - no audio files, no backend, no API
changes. Cue pattern per ACTIVE sub-timer row, from the spec:
- each whole-minute mark: single mid beep (also fires as the row starts)
- final minute: 30s / 20s / 10s: double beep
- final 5 seconds: 5,4,3,2,1: short tick each second
- 0 (flag down, row CLEAR): long horn
Sound toggle button in the RO header, saved in localStorage, default ON.
AudioContext is armed on any pointer/key gesture (browser autoplay policy),
so the START click enables audio before the first cue.
"""
import sys

BASE = r'C:\Users\anton\flagmachine\drag-drop-app'


def load(path):
    with open(path, 'rb') as f:
        return f.read()


def save(path, data):
    with open(path, 'wb') as f:
        f.write(data)


def rep(data, old, new, label):
    old_b, new_b = old.encode(), new.encode()
    if data.count(old_b) == 1:
        return data.replace(old_b, new_b)
    old_crlf = old_b.replace(b'\n', b'\r\n')
    if data.count(old_crlf) == 1:
        return data.replace(old_crlf, new_b.replace(b'\n', b'\r\n'))
    sys.exit('MATCH FAIL [%s]: LF count=%d CRLF count=%d' % (
        label, data.count(old_b), data.count(old_crlf)))


# ---------------- app.js: audio engine, cue scheduler, toggle ----------------
p = BASE + r'\static\js\app.js'
d = load(p)

# 1. Audio engine + cue sounds, inserted after the grid color helpers
d = rep(d, """function getGridIndexFromColorClass(colorClass) {
    const index = gridColorClasses.indexOf(colorClass);
    return index >= 0 ? index + 1 : 1;
}
""", """function getGridIndexFromColorClass(colorClass) {
    const index = gridColorClasses.indexOf(colorClass);
    return index >= 0 ? index + 1 : 1;
}

// ===== Countdown audio (Feature 6) - RO watches the startline, not the screen =====
let audioCtx = null;
let soundEnabled = localStorage.getItem('fm_sound_enabled') !== 'off';
const audioCues = {};  // row id -> { second: true } cues already played this run

// Browsers refuse audio until a user gesture - arm on any click/keypress so
// the START button click enables sound before the first cue fires.
function ensureAudioContext() {
    if (!audioCtx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) audioCtx = new AC();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume().catch(() => {});
    }
}
document.addEventListener('pointerdown', ensureAudioContext);
document.addEventListener('keydown', ensureAudioContext);

function beep(freq, duration, delay = 0, gain = 0.35) {
    if (!soundEnabled || !audioCtx) return;
    const t = audioCtx.currentTime + delay;
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    g.gain.setValueAtTime(gain, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + duration);
    osc.connect(g);
    g.connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + duration);
}

// Whole-minute mark: single mid beep. 30/20/10s: double beep.
// Final 5,4,3,2,1: short tick. 0 / flag down: long low horn.
function cueMinute()  { beep(880, 0.15); }
function cueWarning() { beep(660, 0.12); beep(660, 0.12, 0.18); }
function cueTick()    { beep(1320, 0.07); }
function cueHorn()    { beep(220, 1.2, 0, 0.5); beep(220, 1.2, 0.02, 0.4); }

function resetAudioCues() {
    Object.keys(audioCues).forEach(k => delete audioCues[k]);
}

function playCountdownCues(item, rem) {
    if (!soundEnabled) return;
    const cueSec = Math.ceil(rem);
    const fired = audioCues[item.id] || (audioCues[item.id] = {});
    if (fired[cueSec]) return;
    fired[cueSec] = true;
    if (cueSec > 0 && cueSec % 60 === 0) {
        cueMinute();
    } else if (cueSec === 30 || cueSec === 20 || cueSec === 10) {
        cueWarning();
    } else if (cueSec >= 1 && cueSec <= 5) {
        cueTick();
    }
}
""", 'audio engine')

# 2. Cue scheduler hook in updateCountdown's row loop
d = rep(d, """        it.status = e < start ? 'PENDING' : e < end ? 'ACTIVE' : 'CLEAR';
        it.current_remaining_seconds = it.status === 'PENDING' ? dur : it.status === 'ACTIVE' ? rem : 0;
        if (it.status === 'ACTIVE' || it.status === 'PENDING') hasAnyActive = true;
""", """        it.status = e < start ? 'PENDING' : e < end ? 'ACTIVE' : 'CLEAR';
        it.current_remaining_seconds = it.status === 'PENDING' ? dur : it.status === 'ACTIVE' ? rem : 0;
        if (it.status === 'ACTIVE' || it.status === 'PENDING') hasAnyActive = true;
        if (it.status === 'ACTIVE') playCountdownCues(it, rem);
""", 'cue scheduler hook')

# 3. Horn when a sub-timer completes (flag goes down)
d = rep(d, """        if (os !== 'CLEAR' && it.status === 'CLEAR') {
            // A sub-timer completed. The class START is the end of the start
""", """        if (os !== 'CLEAR' && it.status === 'CLEAR') {
            cueHorn();  // flag down - the RO hears the sub-timer finish
            // A sub-timer completed. The class START is the end of the start
""", 'horn on clear')

# 4. Reset cues when the race restarts or resets
d = rep(d, """    document.getElementById('btn-start').addEventListener('click', () => {
        if (state.isRunning || state.sequence.length === 0) return;
        state.isRunning = true;
""", """    document.getElementById('btn-start').addEventListener('click', () => {
        if (state.isRunning || state.sequence.length === 0) return;
        resetAudioCues();
        state.isRunning = true;
""", 'reset cues on start')
d = rep(d, """    document.getElementById('btn-reset').addEventListener('click', () => {
        state.isRunning = false;
""", """    document.getElementById('btn-reset').addEventListener('click', () => {
        resetAudioCues();
        state.isRunning = false;
""", 'reset cues on reset')

# 5. Sound toggle button handler
d = rep(d, """    document.getElementById('master-start-input').addEventListener('change', e => { state.masterStartTime = e.target.value; });
""", """    document.getElementById('master-start-input').addEventListener('change', e => { state.masterStartTime = e.target.value; });

    // Sound on/off toggle (Feature 6) - remembered between sessions
    const soundBtn = document.getElementById('btn-sound');
    function updateSoundBtn() {
        if (soundBtn) soundBtn.textContent = soundEnabled ? '🔊 Sound On' : '🔇 Sound Off';
    }
    if (soundBtn) {
        updateSoundBtn();
        soundBtn.addEventListener('click', () => {
            soundEnabled = !soundEnabled;
            localStorage.setItem('fm_sound_enabled', soundEnabled ? 'on' : 'off');
            ensureAudioContext();
            updateSoundBtn();
            if (soundEnabled) cueMinute();  // audible confirmation
        });
    }
""", 'sound toggle')
save(p, d)

# ---------------- index.html: Sound button in the header ----------------
p = BASE + r'\templates\index.html'
d = load(p)
d = rep(d, """            <button id="btn-end-race" class="btn btn-blue" style="background-color: #007acc; color: white;">🏁 End Race</button>
""", """            <button id="btn-end-race" class="btn btn-blue" style="background-color: #007acc; color: white;">🏁 End Race</button>
            <button id="btn-sound" class="btn btn-gray" title="Countdown audio on/off">🔊 Sound On</button>
""", 'sound button')
save(p, d)

print('PATCH 7 (Feature 6 audio) APPLIED OK')
