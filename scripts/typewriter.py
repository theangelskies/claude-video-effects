#!/usr/bin/env python3
"""Add typewriter key strikes (one per letter) and a bell to a video, on top of its own audio.

usage: python typewriter.py input.mp4 output.mp4 --start 1.0 --letters 4 [--gap 0.18] [--volume 0.7] [--no-bell]
Matches `backdrop-word` with `type=1`: use the same start and gap, and the word's length as --letters.
The sound is synthesized here, nothing is downloaded.
"""
import argparse, os, subprocess, tempfile, wave
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--start', type=float, required=True); ap.add_argument('--letters', type=int, required=True)
ap.add_argument('--gap', type=float, default=0.18); ap.add_argument('--volume', type=float, default=0.7)
ap.add_argument('--no-bell', action='store_true')
a = ap.parse_args()

sr = 48000; rng = np.random.default_rng(7)
buf = np.zeros(int(sr * (a.start + a.gap * a.letters + 1.5)))

def strike(t0, pitch):
    L = int(sr * 0.12); t = np.arange(L) / sr
    noise = rng.standard_normal(L)
    click = np.diff(noise, prepend=0) * np.exp(-t / 0.004)              # bright mechanical click
    thunk = np.sin(2 * np.pi * 140 * pitch * t) * np.exp(-t / 0.025)    # type bar hitting the platen
    rattle = noise * np.exp(-((t - 0.018) / 0.006) ** 2) * 0.35         # second small knock
    i = int(t0 * sr); buf[i:i + L] += 0.9 * click + 0.6 * thunk + rattle

def bell(t0):
    L = int(sr * 1.2); t = np.arange(L) / sr
    s = sum(amp * np.sin(2 * np.pi * f * t) for f, amp in [(2093, 1), (4186, .35), (5300, .2), (6280, .12)])
    i = int(t0 * sr); buf[i:i + L] += 0.35 * s * np.exp(-t / 0.35)

for k in range(a.letters): strike(a.start + k * a.gap, 1 + 0.08 * rng.standard_normal())
if not a.no_bell: bell(a.start + (a.letters - 1) * a.gap + 0.14)
buf = buf / np.abs(buf).max() * 0.8

with tempfile.TemporaryDirectory() as tmp:
    wav = os.path.join(tmp, 'typewriter.wav')
    w = wave.open(wav, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((buf * 32767).astype('<i2').tobytes()); w.close()
    mix = (f'[1:a]aresample=48000,volume={a.volume},pan=stereo|c0=c0|c1=c0[t];[0:a]aresample=48000[v];'
           '[v][t]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.src, '-i', wav, '-filter_complex', mix, '-map', '0:v', '-map', '[a]',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', a.dst], check=True)
print(f'Done: {a.dst}')
