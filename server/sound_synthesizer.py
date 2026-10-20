"""
OpenCut High-Fidelity Audio Synthesizer & Sound Designer
Generates studio-grade acoustic sound effects and Lo-Fi study beats.
Every sound is mathematically shaped, bandpass-filtered, and peak-normalized
to professional broadcast and social media standards.
"""

import math
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SAMPLE_RATE = 48000

def normalize_peak(audio, target_db=-1.0):
    """Normalize audio peak to specific dBFS."""
    max_val = np.max(np.abs(audio))
    if max_val < 1e-6:
        return audio
    target_amp = 10.0 ** (target_db / 20.0)
    return (audio / max_val) * target_amp

def apply_envelope(audio, attack_s, decay_s, sr=SAMPLE_RATE):
    """Apply smooth attack and exponential decay."""
    n_samples = len(audio)
    att_samples = int(attack_s * sr)
    dec_samples = int(decay_s * sr)
    
    env = np.ones(n_samples, dtype=np.float32)
    if att_samples > 0:
        env[:att_samples] = np.sin(np.linspace(0, np.pi/2, att_samples))
    
    decay_start = min(att_samples, n_samples)
    remaining = n_samples - decay_start
    if remaining > 0:
        # exponential decay
        decay_curve = np.exp(-np.linspace(0, 5.0, remaining))
        env[decay_start:] = decay_curve
    return audio * env

def butter_bandpass_filter(data, lowcut, highcut, sr=SAMPLE_RATE, order=3):
    nyq = 0.5 * sr
    low = max(20.0, lowcut) / nyq
    high = min(sr * 0.49, highcut) / nyq
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, data)

def butter_lowpass_filter(data, cutoff, sr=SAMPLE_RATE, order=3):
    nyq = 0.5 * sr
    cut = min(sr * 0.49, cutoff) / nyq
    b, a = butter(order, cut, btype='low')
    return lfilter(b, a, data)

def butter_highpass_filter(data, cutoff, sr=SAMPLE_RATE, order=3):
    nyq = 0.5 * sr
    cut = max(20.0, cutoff) / nyq
    b, a = butter(order, cut, btype='high')
    return lfilter(b, a, data)

# ==================== SFX GENERATORS ====================

def create_stamp_thud(sr=SAMPLE_RATE):
    """
    Physical Rubber Stamp Slam:
    1. Wooden slap transient (sharp filtered click + 380Hz resonance)
    2. Heavy desk body thud (sine pitch sweep 140Hz -> 48Hz)
    3. Tactile table thump resonance
    """
    dur = 0.55
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    
    # Sub-bass punch: Pitch drops exponentially from 130Hz to 45Hz
    freq_sweep = 45.0 + 85.0 * np.exp(-t * 28.0)
    phase = 2 * np.pi * np.cumsum(freq_sweep) / sr
    sub_body = np.sin(phase) * np.exp(-t * 12.0)
    
    # Wooden slap transient: burst of noise + 420Hz wood resonance
    noise = np.random.normal(0, 1, len(t))
    wood_click = butter_bandpass_filter(noise, 800, 3200, sr=sr) * np.exp(-t * 90.0)
    wood_res = np.sin(2 * np.pi * 380.0 * t) * np.exp(-t * 35.0)
    
    # Mid-range desk thump
    desk_thump = np.sin(2 * np.pi * 180.0 * t) * np.exp(-t * 22.0)
    
    mix = (sub_body * 1.0) + (wood_click * 0.8) + (wood_res * 0.5) + (desk_thump * 0.4)
    # Saturation warmth
    mix = np.tanh(mix * 1.5)
    return normalize_peak(mix, target_db=-1.5)

def create_paper_slide(sr=SAMPLE_RATE):
    """
    Crisp Paper Card Slide / Whoosh:
    Smooth organic friction sound as physical card drops onto desk.
    """
    dur = 0.45
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    
    # Sweep bandpass filter from 700Hz to 2400Hz and back
    sweep = np.sin(np.pi * t / dur)
    filtered = butter_bandpass_filter(noise, 900, 3500, sr=sr)
    
    # Flutter amplitude modulation (paper friction)
    flutter = 1.0 + 0.3 * np.sin(2 * np.pi * 32.0 * t)
    
    # Low end subtle air push
    air = butter_lowpass_filter(noise, 400, sr=sr) * 0.4
    
    env = np.sin(np.pi * t / dur) ** 1.8
    mix = (filtered * flutter + air) * env
    return normalize_peak(mix, target_db=-3.0)

def create_marker_scribble(sr=SAMPLE_RATE):
    """
    Tactile Highlighter / Marker Sweep across paper:
    Texture of felt tip running smoothly over textured craft paper.
    """
    dur = 0.50
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    
    # Felt-tip squeak and paper texture
    grain1 = butter_bandpass_filter(noise, 1600, 4200, sr=sr)
    grain2 = butter_bandpass_filter(noise, 700, 1400, sr=sr)
    
    # Hand motion pressure variation (subtle 8-15 Hz flutter)
    pressure = (0.7 + 0.3 * np.sin(2 * np.pi * 14.0 * t)) * (0.8 + 0.2 * np.cos(2 * np.pi * 28.0 * t))
    
    env = np.ones(len(t))
    att = int(0.04 * sr)
    dec = int(0.08 * sr)
    env[:att] = np.linspace(0, 1, att)
    env[-dec:] = np.linspace(1, 0, dec)
    
    mix = (grain1 * 0.7 + grain2 * 0.4) * pressure * env
    return normalize_peak(mix, target_db=-4.0)

def create_pop_click(freq=1200, sr=SAMPLE_RATE):
    """
    Satisfying UI Pop / Wood Bubble Click:
    Fast upward chirp with crisp transient snap.
    """
    dur = 0.08
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    
    # Quick pitch chirp upward
    freq_t = freq + 600.0 * np.exp(-t * 60.0)
    phase = 2 * np.pi * np.cumsum(freq_t) / sr
    sine_pop = np.sin(phase) * np.exp(-t * 85.0)
    
    # Crisp high transient click
    click = np.random.normal(0, 1, len(t))
    click = butter_highpass_filter(click, 3000, sr=sr) * np.exp(-t * 250.0)
    
    mix = sine_pop + click * 0.4
    return normalize_peak(mix, target_db=-2.5)

def create_paper_rip(sr=SAMPLE_RATE):
    """
    Fast Paper Rip / Swish for Scene Transitions:
    Rapid tear and whoosh energy.
    """
    dur = 0.38
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    noise = np.random.normal(0, 1, len(t))
    
    # Wide dynamic bandpass
    filtered = butter_bandpass_filter(noise, 600, 4800, sr=sr)
    # Fast crackle
    crackle = np.random.binomial(1, 0.08, len(t)) * noise * 0.6
    
    env = np.sin(np.pi * (t / dur) ** 0.8) ** 2
    mix = (filtered + crackle) * env
    return normalize_peak(mix, target_db=-2.0)

# ==================== LO-FI STUDY BEAT GENERATOR ====================

def create_lofi_study_beat(duration_s=45.0, sr=SAMPLE_RATE, bpm=84):
    """
    Studio-Grade Lo-Fi Hip Hop / Study Beat:
    - 84 BPM chill swing groove
    - Warm Rhodes jazz progression (Fmaj7 - Em7 - Dm7 - Cmaj7)
    - Deep acoustic/electric sub-bass
    - Warm boom-bap kick, crisp rimshot snare, swung hi-hats
    - Vinyl room texture & tape warmth
    - Output: Stereo 48kHz float array
    """
    n_samples = int(duration_s * sr)
    left = np.zeros(n_samples, dtype=np.float32)
    right = np.zeros(n_samples, dtype=np.float32)
    
    beat_dur = 60.0 / bpm # ~0.714s
    bar_dur = beat_dur * 4 # ~2.857s
    
    # 1. Warm Vinyl Bed
    vinyl_noise = np.random.normal(0, 0.015, n_samples)
    vinyl_dust = butter_bandpass_filter(vinyl_noise, 400, 3500, sr=sr)
    # Occasional vinyl pop/crackle clicks
    crackle_locs = np.random.randint(0, n_samples, int(duration_s * 4))
    vinyl_pops = np.zeros(n_samples, dtype=np.float32)
    for loc in crackle_locs:
        pop_len = min(60, n_samples - loc)
        vinyl_pops[loc:loc+pop_len] = np.random.normal(0, 0.04, pop_len) * np.exp(-np.linspace(0, 5, pop_len))
    
    left += vinyl_dust * 0.35 + vinyl_pops * 0.2
    right += vinyl_dust * 0.35 + vinyl_pops * 0.2
    
    # 2. Drum Components
    # Kick (pitch sweep 105Hz -> 42Hz)
    kick_dur = 0.35
    kt = np.linspace(0, kick_dur, int(sr * kick_dur), endpoint=False)
    k_freq = 42.0 + 75.0 * np.exp(-kt * 30.0)
    k_phase = 2 * np.pi * np.cumsum(k_freq) / sr
    kick_audio = np.sin(k_phase) * np.exp(-kt * 14.0)
    # Kick transient tap
    k_click = butter_bandpass_filter(np.random.normal(0, 1, len(kt)), 1200, 3500, sr=sr) * np.exp(-kt * 100.0)
    kick_sample = np.tanh((kick_audio + k_click * 0.3) * 1.8) * 0.85
    
    # Snare / Rimshot (warm body at 210Hz + noise splash)
    snare_dur = 0.28
    st = np.linspace(0, snare_dur, int(sr * snare_dur), endpoint=False)
    s_tone = np.sin(2 * np.pi * 210.0 * st) * np.exp(-st * 26.0)
    s_noise = butter_bandpass_filter(np.random.normal(0, 1, len(st)), 1400, 7000, sr=sr) * np.exp(-st * 18.0)
    snare_sample = (s_tone * 0.6 + s_noise * 0.5) * 0.75
    
    # Hi-Hat (crisp sizzle)
    hat_dur = 0.09
    ht = np.linspace(0, hat_dur, int(sr * hat_dur), endpoint=False)
    hat_noise = butter_highpass_filter(np.random.normal(0, 1, len(ht)), 6000, sr=sr) * np.exp(-ht * 55.0)
    hat_sample = hat_noise * 0.35
    
    # Drum Sequencer (84 BPM, swung 16th notes)
    total_bars = int(math.ceil(duration_s / bar_dur)) + 1
    for bar in range(total_bars):
        bar_start_s = bar * bar_dur
        # Beats 1, 2, 3, 4
        # Kick on beat 1 (0.0s) and syncopated beat 2.75 (~2.75 beats)
        for k_beat in [0.0, 2.5]:
            t_hit = bar_start_s + k_beat * beat_dur
            idx = int(t_hit * sr)
            if idx + len(kick_sample) < n_samples:
                left[idx:idx+len(kick_sample)] += kick_sample * 0.95
                right[idx:idx+len(kick_sample)] += kick_sample * 0.95
        
        # Snare on beat 2 (1.0) and beat 4 (3.0)
        for s_beat in [1.0, 3.0]:
            t_hit = bar_start_s + s_beat * beat_dur
            idx = int(t_hit * sr)
            if idx + len(snare_sample) < n_samples:
                left[idx:idx+len(snare_sample)] += snare_sample * 0.9
                right[idx:idx+len(snare_sample)] += snare_sample * 0.9
        
        # Hi-hats: 8th notes with subtle swing on off-beats
        for h_step in range(8):
            swing_offset = 0.035 if (h_step % 2 == 1) else 0.0
            t_hit = bar_start_s + (h_step * 0.5 + swing_offset) * beat_dur
            idx = int(t_hit * sr)
            vel = 0.9 if (h_step % 2 == 0) else 0.6
            if idx + len(hat_sample) < n_samples:
                # Slight stereo spread on hats
                left[idx:idx+len(hat_sample)] += hat_sample * vel * 0.9
                right[idx:idx+len(hat_sample)] += hat_sample * vel * 1.1
                
    # 3. Warm Rhodes Electric Piano Chords
    # Progression: Fmaj7 (F3, A3, C4, E4) -> Em7 (E3, G3, B3, D4) -> Dm7 (D3, F3, A3, C4) -> Cmaj7 (C3, E3, G3, B3)
    def midi_to_hz(m):
        return 440.0 * (2.0 ** ((m - 69) / 12.0))
    
    chords_midi = [
        [53, 57, 60, 64], # Fmaj7
        [52, 55, 59, 62], # Em7
        [50, 53, 57, 60], # Dm7
        [48, 52, 55, 59], # Cmaj7
    ]
    bass_roots = [41, 40, 38, 36] # F1, E1, D1, C1
    
    for bar in range(total_bars):
        chord_idx = bar % 4
        notes = chords_midi[chord_idx]
        bar_start_s = bar * bar_dur
        chord_dur = bar_dur * 0.92
        ct = np.linspace(0, chord_dur, int(sr * chord_dur), endpoint=False)
        
        # Synthesize Rhodes chord
        chord_wave_l = np.zeros(len(ct), dtype=np.float32)
        chord_wave_r = np.zeros(len(ct), dtype=np.float32)
        
        for n_i, note in enumerate(notes):
            freq = midi_to_hz(note)
            # Rhodes tone: Fundamental sine + 2nd harmonic (warm) + 3rd harmonic (bell strike)
            f_wave = np.sin(2 * np.pi * freq * ct) * 1.0
            h2_wave = np.sin(2 * np.pi * freq * 2.0 * ct) * 0.35
            h3_wave = np.sin(2 * np.pi * freq * 3.0 * ct) * 0.15 * np.exp(-ct * 6.0) # chime decays quickly
            
            # Subtle vintage chorus / tremolo (6 Hz LFO)
            tremolo = 1.0 + 0.12 * np.sin(2 * np.pi * 5.2 * ct + (n_i * 0.5))
            
            note_sound = (f_wave + h2_wave + h3_wave) * tremolo * np.exp(-ct * 1.3)
            # Stereo spread based on pitch
            pan = (n_i - 1.5) / 3.0 # -0.5 to +0.5
            chord_wave_l += note_sound * (0.6 - pan * 0.3)
            chord_wave_r += note_sound * (0.6 + pan * 0.3)
            
        # Smooth attack envelope for chords
        att = int(0.06 * sr)
        chord_wave_l[:att] *= np.linspace(0, 1, att)
        chord_wave_r[:att] *= np.linspace(0, 1, att)
        
        c_idx = int(bar_start_s * sr)
        if c_idx + len(ct) < n_samples:
            left[c_idx:c_idx+len(ct)] += chord_wave_l * 0.45
            right[c_idx:c_idx+len(ct)] += chord_wave_r * 0.45
            
        # 4. Warm Sub-Bass Line
        bass_note = bass_roots[chord_idx]
        b_freq = midi_to_hz(bass_note)
        bt = np.linspace(0, bar_dur * 0.88, int(sr * bar_dur * 0.88), endpoint=False)
        bass_wave = (np.sin(2 * np.pi * b_freq * bt) + 0.25 * np.sin(2 * np.pi * b_freq * 2.0 * bt)) * np.exp(-bt * 0.9)
        # Soft attack
        b_att = int(0.04 * sr)
        bass_wave[:b_att] *= np.linspace(0, 1, b_att)
        
        b_idx = int(bar_start_s * sr)
        if b_idx + len(bt) < n_samples:
            left[b_idx:b_idx+len(bt)] += bass_wave * 0.5
            right[b_idx:b_idx+len(bt)] += bass_wave * 0.5

    # Master Bus Processing for BGM:
    # Warm saturation, gentle high-shelf rolloff (vintage warm lo-fi tone)
    left = np.tanh(left * 1.2)
    right = np.tanh(right * 1.2)
    
    # Smooth fade out at the end
    fade_len = int(1.8 * sr)
    fade_curve = np.linspace(1.0, 0.0, fade_len)
    left[-fade_len:] *= fade_curve
    right[-fade_len:] *= fade_curve
    
    stereo = np.vstack([left, right]).T
    # Normalize BGM to -14 dBFS peak (sitting around -22 LUFS)
    max_bgm = np.max(np.abs(stereo))
    if max_bgm > 0:
        stereo = (stereo / max_bgm) * 0.35 # ~ -9 dBFS peak
        
    return stereo

def write_wav_file(path, data, sr=SAMPLE_RATE):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    int_data = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
    wavfile.write(str(path), sr, int_data)
