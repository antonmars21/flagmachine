"""Feature 6b: spoken countdown (English) for the RO via speechSynthesis.

- Cue points speak: "one minute"/"three minutes", "thirty seconds",
  "twenty seconds", "ten seconds", "five, four, three, two, one".
- Horn at flag drop UNCHANGED (cuts through wind noise; a LOUD horn for the
  sailors on the water is separate future development - this audio is for the
  race officers sitting at the laptop only).
- Each phrase interrupts the previous one so the final seconds stay on beat.
- Falls back to the beeps if speechSynthesis is unavailable.
- Same Sound On/Off button governs voice + horn.
"""
import sys

BASE = r'C:\Users\anton\flagmachine\drag-drop-app'
p = BASE + r'\\static\\js\\app.js'
with open(p, 'rb') as f:
    d = f.read()


def rep(old, new, label):
    global d
    old_b, new_b = old.encode(), new.encode()
    if d.count(old_b) == 1:
        d = d.replace(old_b, new_b)
        return
    old_crlf = old_b.replace(b'\n', b'\r\n')
    if d.count(old_crlf) == 1:
        d = d.replace(old_crlf, new_b.replace(b'\n', b'\r\n'))
        return
    sys.exit('MATCH FAIL [%s]: LF=%d CRLF=%d' % (label, d.count(old_b), d.count(old_crlf)))


# 1. Cue functions: spoken words with beep fallback
rep("""// Whole-minute mark: single mid beep. 30/20/10s: double beep.
// Final 5,4,3,2,1: short tick. 0 / flag down: long low horn.
function cueMinute()  { beep(880, 0.15); }
function cueWarning() { beep(660, 0.12); beep(660, 0.12, 0.18); }
function cueTick()    { beep(1320, 0.07); }
function cueHorn()    { beep(220, 1.2, 0, 0.5); beep(220, 1.2, 0.02, 0.4); }
""", """// Spoken countdown (browser speechSynthesis, Windows voices). Falls back to
// the beep pattern if speech synthesis is unavailable. Each phrase interrupts
// the previous one so rapid cues (5,4,3,2,1) stay on the beat.
let speechVoice = null;
function initSpeechVoice() {
    if (!('speechSynthesis' in window)) return;
    const pick = () => {
        const voices = speechSynthesis.getVoices();
        if (!voices.length) return;
        speechVoice = voices.find(v => /^en[-_](GB)/i.test(v.lang))
            || voices.find(v => /^en[-_](AU|NZ)/i.test(v.lang))
            || voices.find(v => /^en/i.test(v.lang))
            || null;
    };
    pick();
    speechSynthesis.onvoiceschanged = pick;
}
initSpeechVoice();

function say(text) {
    if (!soundEnabled || !('speechSynthesis' in window)) return false;
    try {
        speechSynthesis.cancel();  // interrupt any phrase still speaking
        const u = new SpeechSynthesisUtterance(text);
        if (speechVoice) u.voice = speechVoice;
        u.rate = 1.1;
        u.volume = 1;
        speechSynthesis.speak(u);
        return true;
    } catch (e) {
        return false;
    }
}

// Whole-minute mark, 30/20/10s warnings, final 5,4,3,2,1: spoken (beep
// fallback). 0 / flag down: long low horn - unchanged, it cuts through wind
// noise and is unmistakable.
const NUM_WORDS = { 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
                    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten' };
const WARN_WORDS = { 30: 'thirty seconds', 20: 'twenty seconds', 10: 'ten seconds' };

function cueMinute(sec) {
    const m = Math.round(sec / 60);
    if (!say((NUM_WORDS[m] || String(m)) + (m === 1 ? ' minute' : ' minutes'))) beep(880, 0.15);
}
function cueWarning(sec) {
    if (!say(WARN_WORDS[sec])) { beep(660, 0.12); beep(660, 0.12, 0.18); }
}
function cueTick(sec) {
    if (!say(NUM_WORDS[sec])) beep(1320, 0.07);
}
function cueHorn()    { beep(220, 1.2, 0, 0.5); beep(220, 1.2, 0.02, 0.4); }
""", 'spoken cue functions')

# 2. Pass the cue second into the cue functions
rep("""    if (cueSec > 0 && cueSec % 60 === 0) {
        cueMinute();
    } else if (cueSec === 30 || cueSec === 20 || cueSec === 10) {
        cueWarning();
    } else if (cueSec >= 1 && cueSec <= 5) {
        cueTick();
    }
""", """    if (cueSec > 0 && cueSec % 60 === 0) {
        cueMinute(cueSec);
    } else if (cueSec === 30 || cueSec === 20 || cueSec === 10) {
        cueWarning(cueSec);
    } else if (cueSec >= 1 && cueSec <= 5) {
        cueTick(cueSec);
    }
""", 'cue call sites')

# 3. Toggle confirmation cue
rep("""            if (soundEnabled) cueMinute();  // audible confirmation
""", """            if (soundEnabled) cueMinute(60);  // audible confirmation
""", 'toggle confirmation')

with open(p, 'wb') as f:
    f.write(d)
print('PATCH 8 (spoken countdown) APPLIED OK')
