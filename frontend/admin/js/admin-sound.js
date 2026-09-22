/**
 * DINOS Pizzaria — Admin Web Audio API Sound Synthesizer
 * Generates programmatic dual-tone notification chimes without external audio assets.
 * Complies with browser autoplay policies via lazy resume on user interaction.
 */

const STORAGE_KEY = 'dinos_admin_sound';

let audioCtx = null;
let isMuted = false;

/**
 * Initialize sound subsystem and attach user interaction listener to unlock AudioContext
 */
export function initSound() {
  const stored = localStorage.getItem(STORAGE_KEY);
  isMuted = stored === 'false';

  const unlockAudio = () => {
    getAudioContext();
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }
    // Remove listeners once unlocked
    document.removeEventListener('click', unlockAudio);
    document.removeEventListener('keydown', unlockAudio);
    document.removeEventListener('touchstart', unlockAudio);
  };

  document.addEventListener('click', unlockAudio, { passive: true, once: true });
  document.addEventListener('keydown', unlockAudio, { passive: true, once: true });
  document.addEventListener('touchstart', unlockAudio, { passive: true, once: true });

  return !isMuted;
}

/**
 * Lazy initialization of AudioContext
 */
function getAudioContext() {
  if (!audioCtx) {
    const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
    if (AudioCtxClass) {
      audioCtx = new AudioCtxClass();
    }
  }
  return audioCtx;
}

/**
 * Toggle sound mute status and persist in localStorage
 * @returns {boolean} true if sound is enabled (unmuted), false if muted
 */
export function toggleSound() {
  isMuted = !isMuted;
  localStorage.setItem(STORAGE_KEY, String(!isMuted));
  return !isMuted;
}

/**
 * Check if sound is currently muted
 * @returns {boolean}
 */
export function isSoundMuted() {
  return isMuted;
}

/**
 * Synthesize and play a pleasant dual-tone chime (D5: 587.33 Hz followed by A5: 880.00 Hz)
 */
export function playNewOrderSound() {
  if (isMuted) return;

  const ctx = getAudioContext();
  if (!ctx) return;

  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {});
  }

  try {
    const now = ctx.currentTime;

    // First Tone: D5 (587.33 Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();

    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(587.33, now);

    gain1.gain.setValueAtTime(0.001, now);
    gain1.gain.exponentialRampToValueAtTime(0.28, now + 0.03);
    gain1.gain.exponentialRampToValueAtTime(0.0001, now + 0.28);

    osc1.connect(gain1);
    gain1.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.3);

    // Second Tone: A5 (880.00 Hz) - starts slightly offset
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();

    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(880.00, now + 0.12);

    gain2.gain.setValueAtTime(0.001, now + 0.12);
    gain2.gain.exponentialRampToValueAtTime(0.35, now + 0.16);
    gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.55);

    osc2.connect(gain2);
    gain2.connect(ctx.destination);

    osc2.start(now + 0.12);
    osc2.stop(now + 0.58);
  } catch (err) {
    console.warn('Falha ao reproduzir alerta sonoro:', err);
  }
}
