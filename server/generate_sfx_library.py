"""
OpenCut Sound Effects Generator
Generates studio-grade WAV sound effects using Python standard library (wave, math, struct, random).
Zero external dependencies required.
"""

import os
import math
import struct
import random
import wave
from pathlib import Path

SFX_DIR = Path("E:/autocut/assets/sfx")
SFX_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_RATE = 44100

def write_wav(filename: str, samples: list[float]):
    filepath = SFX_DIR / filename
    with wave.open(str(filepath), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        raw_data = bytearray()
        for s in samples:
            # Clamp between -1.0 and 1.0
            clamped = max(-1.0, min(1.0, s))
            int_sample = int(clamped * 32767.0)
            raw_data.extend(struct.pack('<h', int_sample))
        wav.writeframes(raw_data)
    print(f"Generated {filename} ({len(samples)/SAMPLE_RATE:.2f}s)")

def gen_vine_boom():
    dur = 1.4
    num_samples = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Heavy sub drop starting at 90Hz sliding down to 35Hz
        freq = 90.0 * math.exp(-3.5 * t) + 35.0
        # Envelope with fast punch attack and long decay
        env = math.exp(-2.2 * t)
        # Fundamental sine + second harmonic for distortion
        s = math.sin(2.0 * math.pi * freq * t) * 0.8
        s += math.sin(4.0 * math.pi * freq * t) * 0.35
        # Soft saturation
        s = math.tanh(s * 2.2) * env
        samples.append(s)
    write_wav("vine_boom.wav", samples)

def gen_whooshes():
    # 1. Whoosh fast
    dur = 0.45
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        # Bell curve envelope
        env = math.sin(math.pi * (i / num)) ** 2
        # Center frequency sweep 300Hz -> 2800Hz -> 400Hz
        sweep = math.sin(math.pi * (i / num))
        f_c = 300.0 + 2500.0 * sweep
        noise = (random.random() * 2.0 - 1.0)
        s = noise * math.sin(2.0 * math.pi * f_c * t) * env
        samples.append(s * 0.85)
    write_wav("whoosh_fast.wav", samples)

    # 2. Whoosh air
    dur = 0.65
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (i / num)) ** 3
        noise = (random.random() * 2.0 - 1.0)
        f_c = 450.0 + 1600.0 * math.sin(math.pi * (i / num))
        s = noise * math.sin(2.0 * math.pi * f_c * t) * env
        samples.append(s * 0.75)
    write_wav("whoosh_air.wav", samples)

    # 3. Whoosh whip
    dur = 0.3
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (i / num)) ** 1.8
        f_c = 600.0 + 4000.0 * (i / num)
        noise = (random.random() * 2.0 - 1.0)
        s = noise * math.sin(2.0 * math.pi * f_c * t) * env
        samples.append(math.tanh(s * 1.5) * 0.9)
    write_wav("whoosh_whip.wav", samples)

    # 4. Cinematic whoosh
    dur = 0.9
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (i / num)) ** 2
        noise = (random.random() * 2.0 - 1.0)
        sub = math.sin(2.0 * math.pi * (60.0 + 100.0 * math.sin(math.pi * (i / num))) * t)
        s = (noise * 0.6 + sub * 0.5) * env
        samples.append(s * 0.9)
    write_wav("whoosh_cinematic.wav", samples)

def gen_clicks_foley():
    # 1. Camera shutter
    dur = 0.28
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        s = 0.0
        # Click 1 at t=0
        if t < 0.08:
            env1 = math.exp(-75.0 * t)
            s += (random.random() * 2.0 - 1.0) * env1 * 0.9
            s += math.sin(2.0 * math.pi * 3200.0 * t) * env1 * 0.4
        # Click 2 (shutter curtain) at t=0.10
        if t >= 0.09:
            t2 = t - 0.09
            env2 = math.exp(-60.0 * t2)
            s += (random.random() * 2.0 - 1.0) * env2 * 0.8
            s += math.sin(2.0 * math.pi * 2400.0 * t2) * env2 * 0.35
        samples.append(s)
    write_wav("camera_shutter.wav", samples)

    # 2. Mouse click
    dur = 0.08
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.exp(-90.0 * t)
        s = (random.random() * 2.0 - 1.0) * 0.7 + math.sin(2.0 * math.pi * 2800.0 * t) * 0.5
        samples.append(s * env * 0.8)
    write_wav("mouse_click.wav", samples)

    # 3. Mouse double click
    dur = 0.22
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        s = 0.0
        if t < 0.08:
            env = math.exp(-90.0 * t)
            s += ((random.random() * 2.0 - 1.0) * 0.7 + math.sin(2.0 * math.pi * 2800.0 * t) * 0.5) * env
        if t >= 0.10 and t < 0.18:
            t2 = t - 0.10
            env = math.exp(-90.0 * t2)
            s += ((random.random() * 2.0 - 1.0) * 0.7 + math.sin(2.0 * math.pi * 3000.0 * t2) * 0.5) * env
        samples.append(s * 0.8)
    write_wav("mouse_double_click.wav", samples)

    # 4. Keyboard typing loop
    dur = 0.75
    num = int(SAMPLE_RATE * dur)
    samples = [0.0] * num
    key_times = [0.02, 0.15, 0.28, 0.42, 0.58]
    for kt in key_times:
        freq = random.choice([2200.0, 2600.0, 1900.0, 3100.0])
        start_idx = int(kt * SAMPLE_RATE)
        for j in range(int(0.06 * SAMPLE_RATE)):
            idx = start_idx + j
            if idx < num:
                t_key = j / SAMPLE_RATE
                env = math.exp(-80.0 * t_key)
                s = ((random.random() * 2.0 - 1.0) * 0.6 + math.sin(2.0 * math.pi * freq * t_key) * 0.4) * env * 0.7
                samples[idx] += s
    write_wav("keyboard_typing.wav", samples)

def gen_bells_chimes():
    # 1. Bell Ding
    dur = 0.85
    num = int(SAMPLE_RATE * dur)
    samples = []
    f0 = 1760.0 # A6
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.exp(-4.5 * t)
        s = math.sin(2.0 * math.pi * f0 * t) * 0.7
        s += math.sin(2.0 * math.pi * (f0 * 2.76) * t) * 0.25 * math.exp(-8.0 * t)
        s += math.sin(2.0 * math.pi * (f0 * 5.4) * t) * 0.15 * math.exp(-12.0 * t)
        samples.append(s * env)
    write_wav("bell_ding.wav", samples)

    # 2. Success Chime (Major upward arpeggio: C5 - E5 - G5 - C6)
    dur = 0.75
    num = int(SAMPLE_RATE * dur)
    notes = [523.25, 659.25, 783.99, 1046.50]
    samples = [0.0] * num
    for idx_note, freq in enumerate(notes):
        start_t = idx_note * 0.11
        start_sample = int(start_t * SAMPLE_RATE)
        note_dur = dur - start_t
        for j in range(int(note_dur * SAMPLE_RATE)):
            pos = start_sample + j
            if pos < num:
                t_note = j / SAMPLE_RATE
                env = math.exp(-4.2 * t_note)
                s = (math.sin(2.0 * math.pi * freq * t_note) * 0.5 + 
                     math.sin(4.0 * math.pi * freq * t_note) * 0.15) * env
                samples[pos] += s * 0.55
    write_wav("success_chime.wav", samples)

    # 3. Cash Register (Cha-Ching)
    dur = 0.8
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        # Ring at 2400Hz + coin clatter
        env = math.exp(-5.0 * t)
        bell = math.sin(2.0 * math.pi * 2350.0 * t) * 0.5
        bell += math.sin(2.0 * math.pi * 3520.0 * t) * 0.3
        # Metal clink at t=0.12
        coins = 0.0
        if t >= 0.08:
            t_coin = t - 0.08
            coins = (random.random() * 2.0 - 1.0) * math.exp(-18.0 * t_coin) * 0.5
        s = (bell * env + coins) * 0.8
        samples.append(s)
    write_wav("cash_register.wav", samples)

def gen_risers_trailers():
    # 1. Tension Riser
    dur = 2.0
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        prog = i / num
        t = i / SAMPLE_RATE
        # Exponential pitch rise from 150Hz to 1800Hz
        freq = 150.0 * math.exp(2.48 * prog)
        env = prog ** 1.8 # volume swells up
        noise = (random.random() * 2.0 - 1.0) * 0.3 * prog
        s = (math.sin(2.0 * math.pi * freq * t) * 0.7 + noise) * env
        samples.append(s * 0.8)
    write_wav("tension_riser.wav", samples)

    # 2. Cinematic Braam (Trailer Horn)
    dur = 2.2
    num = int(SAMPLE_RATE * dur)
    samples = []
    f_brass = 55.0 # Low A1
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.exp(-1.4 * t)
        # Heavy distorted harmonics (saw-like brass)
        s = math.sin(2.0 * math.pi * f_brass * t) * 0.6
        s += math.sin(4.0 * math.pi * f_brass * t) * 0.4
        s += math.sin(6.0 * math.pi * f_brass * t) * 0.35
        s += math.sin(8.0 * math.pi * f_brass * t) * 0.25
        # Distortion saturation
        s = math.tanh(s * 3.0) * env
        samples.append(s * 0.85)
    write_wav("cinematic_braam.wav", samples)

    # 3. Error Buzzer
    dur = 0.45
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        env = math.exp(-2.5 * t)
        # Dissonant dual square waves (150Hz + 158Hz)
        s1 = 1.0 if math.sin(2.0 * math.pi * 150.0 * t) > 0 else -1.0
        s2 = 1.0 if math.sin(2.0 * math.pi * 158.0 * t) > 0 else -1.0
        s = (s1 + s2) * 0.35 * env
        samples.append(s)
    write_wav("error_buzzer.wav", samples)

    # 4. Vinyl Scratch / Stop
    dur = 0.4
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        # Rapid downward frequency slide
        freq = 1200.0 * math.exp(-12.0 * t) + 80.0
        env = math.exp(-4.0 * t)
        noise = (random.random() * 2.0 - 1.0) * 0.4
        s = (math.sin(2.0 * math.pi * freq * t) * 0.6 + noise) * env
        samples.append(math.tanh(s * 2.0) * 0.75)
    write_wav("vinyl_scratch.wav", samples)

    # 5. Heartbeat
    dur = 1.1
    num = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(num):
        t = i / SAMPLE_RATE
        s = 0.0
        # Pulse 1 at t=0
        if t < 0.25:
            env1 = math.sin(math.pi * (t / 0.25)) ** 2
            s += math.sin(2.0 * math.pi * 55.0 * t) * env1 * 0.9
        # Pulse 2 at t=0.28
        if t >= 0.28 and t < 0.52:
            t2 = t - 0.28
            env2 = math.sin(math.pi * (t2 / 0.24)) ** 2
            s += math.sin(2.0 * math.pi * 60.0 * t2) * env2 * 0.75
        samples.append(s)
    write_wav("heartbeat.wav", samples)

def main():
    print("Generating comprehensive creator sound library in assets/sfx...")
    gen_vine_boom()
    gen_whooshes()
    gen_clicks_foley()
    gen_bells_chimes()
    gen_risers_trailers()
    print("All sound effects generated successfully!")

if __name__ == "__main__":
    main()
