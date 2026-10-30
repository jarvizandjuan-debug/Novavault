"""Chiptune score, retro SFX and voice-over mix -> mix.wav (44.1 kHz stereo)."""
import subprocess
import wave

import numpy as np

from timeline import *

SR = 44100
N = int(DURATION * SR)
rng = np.random.default_rng(7)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(n):
    return np.arange(n) / SR


def add(buf, t, sig, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    sig = sig[: len(buf) - i]
    buf[i : i + len(sig)] += sig * gain


def env(n, a=0.003, decay=None, release=0.01):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    if decay:
        e *= np.exp(-tt(n) / decay)
    nr = min(n, max(1, int(release * SR)))
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def pulse(f, dur, duty=0.5, vib=0.0, vib_rate=6.0):
    n = int(dur * SR)
    t = tt(n)
    fr = f * (1 + vib * np.sin(2 * np.pi * vib_rate * t)) if vib else np.full(n, f)
    ph = np.cumsum(fr) / SR
    return np.where(ph % 1 < duty, 1.0, -1.0)


def tri(f, dur):
    n = int(dur * SR)
    ph = (f * tt(n)) % 1
    x = 4 * np.abs(ph - 0.5) - 1
    return np.round((x + 1) * 7.5) / 7.5 - 1  # 4-bit stepped like old sound chips


def sweep(f0, f1, dur, duty=0.5, exp=True):
    n = int(dur * SR)
    k = np.linspace(0, 1, n)
    fr = f0 * (f1 / f0) ** k if exp else f0 + (f1 - f0) * k
    ph = np.cumsum(fr) / SR
    return np.where(ph % 1 < duty, 1.0, -1.0)


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def hp(x):
    return np.diff(x, prepend=0.0)


def lp_fast(x, cutoff):
    # one-pole low-pass to tame aliasing on the pulse channels
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    step = 4096
    for s in range(0, len(x), step):
        seg = x[s : s + step]
        out = np.empty_like(seg)
        for i, v in enumerate(seg):
            acc += a * (v - acc)
            out[i] = acc
        y[s : s + step] = out
    return y


# ---------------------------------------------------------------- drums
def kick():
    d = 0.16
    n = int(d * SR)
    t = tt(n)
    f = 45 + 130 * np.exp(-t / 0.025)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.07)
    s[:60] += np.linspace(0.6, 0, 60)
    return s


def snare():
    d = 0.18
    nz = hp(noise(d)) * env(int(d * SR), decay=0.055)
    tone = tri(190, d) * env(int(d * SR), decay=0.03)
    return nz * 0.9 + tone * 0.5


def hat(open_=False):
    d = 0.16 if open_ else 0.04
    return hp(hp(noise(d))) * env(int(d * SR), decay=0.05 if open_ else 0.012) * 0.5


def crash():
    d = 1.4
    return hp(noise(d)) * env(int(d * SR), decay=0.45) * 0.6


# ---------------------------------------------------------------- score
AM, F, C, G = "Am", "F", "C", "G"
BASS = {"Am": 45, "F": 41, "C": 48, "G": 43, "E": 40}
ARP = {"Am": [69, 72, 76, 81], "F": [65, 69, 72, 77], "C": [72, 76, 79, 84], "G": [67, 71, 74, 79]}

MEL_A = {
    "Am": [76, "-", 76, 81, "-", 79, 76, "-"],
    "F": [77, "-", 77, 81, "-", 84, 81, "-"],
    "C": [79, "-", 79, 84, "-", 83, 79, "-"],
    "G": [86, "-", 83, "-", 79, "-", 83, 86],
}
MEL_B = {
    "Am": [81, 79, 76, 79, 81, "-", 84, "-"],
    "F": [84, 81, 77, 81, 84, "-", 86, "-"],
    "C": [88, 86, 84, 79, 84, "-", 83, "-"],
    "G": [86, "-", 86, 88, 86, 83, 79, 83],
}

# bar k starts at beat 7 + 4k  (k = -2..17); (chord, transpose, style)
BARS = {
    0: (AM, 0, "A"), 1: (F, 0, "A"), 2: (C, 0, "A"), 3: (G, 0, "A"),
    4: (AM, 0, "B"), 5: (F, 0, "B"), 6: (C, 0, "B"), 7: (G, 0, "B"),
    8: (AM, 0, "tension"), 9: (F, 0, "tension"), 10: (G, 0, "build"), 11: (AM, 0, "A"),
    12: (F, 2, "warp"),
    13: (AM, 2, "A2"), 14: (F, 2, "A2"), 15: (G, 2, "A2"),
    16: (F, 2, "A2"), 17: (G, 2, "A2"),
}


def bar_t(k):
    return tb(7 + 4 * k)


def lead_note(m, dur, gain=0.32, duty=0.25):
    s = pulse(midi(m), dur, duty, vib=0.004, vib_rate=5.5)
    return s * env(len(s), a=0.004, decay=0.45, release=0.02) * gain


def build_music():
    mus = np.zeros(N)
    e8 = BEAT / 2
    e16 = BEAT / 4

    # Intro (0-3 s): drone + rising arp + noise riser
    t0 = 0.0
    drone = (pulse(midi(57), 3.0, 0.5) + pulse(midi(64), 3.0, 0.5) * 0.7)
    drone *= np.linspace(0.04, 0.12, len(drone)) * (1 + 0.3 * np.sin(2 * np.pi * 4 * tt(len(drone))))
    add(mus, t0, drone)
    for i in range(int((3.0 - tb(3)) / e16)):
        t = tb(3) + i * e16
        m = ARP["Am"][i % 4] + (12 if i >= 8 else 0)
        s = pulse(midi(m), e16 * 0.9, 0.125)
        add(mus, t, s * env(len(s), decay=0.06) * (0.05 + 0.1 * i / 14))
    rz = hp(noise(1.2)) * np.linspace(0, 1, int(1.2 * SR)) ** 2 * 0.35
    add(mus, 3.0 - 1.2, rz)

    for k, (ch, tr, style) in BARS.items():
        bt = bar_t(k)
        if style == "warp":
            # sustained chord with a rising bend, no drums
            for j, m in enumerate([BASS["F"] + 12, 69, 72, 77]):
                n = int(4 * BEAT * SR)
                bend = np.linspace(0, 2, n)  # semitones up into the new key
                fr = midi(m) * 2 ** (bend / 12)
                ph = np.cumsum(fr) / SR
                s = np.where(ph % 1 < (0.5 if j == 0 else 0.25), 1.0, -1.0)
                add(mus, bt, s * env(n, a=0.05, release=0.05) * (0.14 if j == 0 else 0.07))
            for i in range(16):
                m = ARP["F"][i % 4] + tr + 12 * (i // 8)
                s = pulse(midi(m), e16 * 0.9, 0.125)
                add(mus, bt + i * e16, s * env(len(s), decay=0.05) * 0.08)
            continue

        root = BASS[ch] + tr
        # bass: 8ths, octave jumps
        for i in range(8):
            if style == "tension":
                m = BASS["E"] + (12 if i % 2 else 0)
            else:
                m = root + (12 if i % 2 else 0)
            s = tri(midi(m), e8 * 0.92)
            add(mus, bt + i * e8, s * env(len(s), release=0.01) * 0.55)
        # arp: 16ths
        for i in range(16):
            notes = ARP[ch]
            m = notes[i % 4] + tr + (12 if style == "build" and i >= 8 else 0)
            s = pulse(midi(m), e16 * 0.85, 0.125)
            add(mus, bt + i * e16, s * env(len(s), decay=0.07) * 0.09)
        # drums
        for b in range(4):
            t = bt + b * BEAT
            if style == "build":
                add(mus, t, kick(), 0.9 if b == 0 else 0.5)
                rolls = 2 if b < 2 else 4
                for r in range(rolls):
                    add(mus, t + r * BEAT / rolls, snare(), 0.25 + 0.15 * b)
                continue
            if style == "tension":
                add(mus, t, kick(), 0.8)
            elif b in (0, 2):
                add(mus, t, kick(), 0.9)
            if style != "tension" and b == 2 and k % 2:
                add(mus, t + e8, kick(), 0.6)
            if b in (1, 3):
                add(mus, t, snare(), 0.55)
            hats = 4 if style in ("A2", "tension") else 2
            for h in range(hats):
                op = style == "B" and h == 1
                add(mus, t + h * BEAT / hats, hat(op), 0.35 if op else 0.28)
        # lead
        mel = None
        if style in ("A", "A2"):
            mel = MEL_A[ch]
        elif style == "B":
            mel = MEL_B[ch]
        if mel:
            i = 0
            while i < 8:
                m = mel[i]
                if m == "-" or m is None:
                    i += 1
                    continue
                j = i + 1
                while j < 8 and mel[j] == "-":
                    j += 1
                add(mus, bt + i * e8, lead_note(m + tr, (j - i) * e8 * 0.95))
                # echo channel, an octave down and late, for width
                add(mus, bt + i * e8 + e16 * 3, lead_note(m + tr - 12, (j - i) * e8 * 0.6, gain=0.08, duty=0.5))
                i = j
        if style == "tension":
            m = (76 if ch == AM else 77)
            s = pulse(midi(m), 4 * BEAT * 0.97, 0.25, vib=0.012, vib_rate=7)
            add(mus, bt, s * env(len(s), a=0.08, release=0.1) * 0.15)

    # crashes on section downbeats
    for b in (7, 23, 51, 59, 71):
        add(mus, tb(b), crash(), 0.7)
        add(mus, tb(b), kick(), 1.0)

    return mus


# ---------------------------------------------------------------- sfx
def blip(f, dur=0.03, duty=0.25):
    s = pulse(f, dur, duty)
    return s * env(len(s), release=0.006)


def arp_up(notes, step=0.035, duty=0.5, last=0.2):
    out = []
    for i, m in enumerate(notes):
        d = last if i == len(notes) - 1 else step
        s = pulse(midi(m), d, duty)
        out.append(s * env(len(s), decay=(0.12 if i == len(notes) - 1 else None), release=0.005))
    return np.concatenate(out)


def whoosh(dur=0.28):
    n = int(dur * SR)
    x = hp(noise(dur))
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    return x * shape * 0.5


def thump():
    d = 0.4
    n = int(d * SR)
    t = tt(n)
    s = np.sin(2 * np.pi * np.cumsum(40 + 80 * np.exp(-t / 0.04)) / SR) * np.exp(-t / 0.14)
    nz = noise(d) * np.exp(-t / 0.05) * 0.5
    return s + nz


def explosion():
    d = 0.6
    n = int(d * SR)
    x = noise(d)
    x = np.repeat(x[::6], 6)[:n]  # crunchy sample-and-hold
    return x * np.exp(-tt(n) / 0.16) * 0.6


def build_sfx():
    sfx = np.zeros(N)
    # Scene 1: typing
    for i, t in enumerate(char_times(CMD_T, len(CMD))):
        if i % 2 == 0:
            add(sfx, t, blip(rng.choice([1320, 1480, 1760]), 0.018), 0.10)
    head = "".join(HEAD)
    for t in char_times(HEAD_T, len(head)):
        add(sfx, t, blip(rng.choice([880, 988, 1175, 1319]), 0.026), 0.16)
    gold = "".join(GOLD_LINES)
    for t in char_times(GOLD_T, len(gold)):
        add(sfx, t, blip(rng.choice([1047, 1175, 1319]), 0.022, 0.5), 0.13)
    add(sfx, GOLD_T[1] + 0.03, arp_up([72, 76, 79, 84, 88, 91, 96], 0.03, 0.5, 0.25), 0.22)
    # glitch into scene 2
    g = np.concatenate([pulse(rng.uniform(200, 2000), 0.02, 0.5) for _ in range(7)])
    add(sfx, 2.85, g * 0.5 + noise(len(g) / SR)[: len(g)] * 0.4, 0.3)

    for t in (S2, CUT_2B, CUT_2C, S3, CUT_3B, S4, S5, CUT_5B):
        add(sfx, t - 0.12, whoosh(), 0.35)

    # scan chatter
    t = CUT_2B
    while t < 9.75:
        add(sfx, t, blip(rng.uniform(1600, 2800), 0.014, 0.5), 0.06)
        t += BEAT / 4 if t < CUT_2C else BEAT / 8
    add(sfx, 9.62, arp_up([84, 91], 0.06, 0.25, 0.18), 0.2)

    # Scene 3
    s = sweep(1800, 600, 0.4, 0.5)
    add(sfx, S3 + 0.03, s * env(len(s), release=0.02), 0.08)
    add(sfx, 10.45, arp_up([83, 88], 0.06, 0.25, 0.1), 0.25)              # select
    add(sfx, 10.55, arp_up([79, 84, 88, 91, 96], 0.045, 0.5, 0.3), 0.2)   # setup jingle
    for i in range(4):                                                    # news alert
        add(sfx, POPUP + i * 0.09, blip(1568 if i % 2 == 0 else 1175, 0.08, 0.5), 0.2)
    s = sweep(250, 1400, 0.35, 0.5)
    add(sfx, JUMP, s * env(len(s), release=0.03), 0.18)
    add(sfx, JUMP, thump(), 0.5)
    s = sweep(1200, 400, 0.12, 0.25)
    add(sfx, POPUP_OUT, s * env(len(s)), 0.12)

    # Scene 4: health bars
    for t0, f0 in ((STOP_FILL, 330), (TGT_FILL, 520)):
        for i in range(14):
            add(sfx, t0 + i * 0.034, blip(f0 * 2 ** (i / 14), 0.022, 0.5), 0.12)
    add(sfx, RR_BADGE, arp_up([88, 93], 0.05, 0.25, 0.08), 0.16)
    for t in COUNT:
        s = pulse(880, 0.14, 0.5)
        add(sfx, t, s * env(len(s), release=0.02), 0.22)
    s = pulse(1760, 0.38, 0.5)
    add(sfx, GO, s * env(len(s), decay=0.2), 0.24)
    add(sfx, GO, thump(), 0.5)

    # Scene 5: warp, counter ticks, results
    n = int((CUT_5B - S5) * SR)
    k = np.linspace(0, 1, n)
    fr = 90 * (1800 / 90) ** (k ** 1.6) * (1 + 0.06 * np.sin(2 * np.pi * 11 * tt(n)))
    s = np.where((np.cumsum(fr) / SR) % 1 < 0.5, 1.0, -1.0) * env(n, a=0.05, release=0.05)
    add(sfx, S5, s, 0.12)
    add(sfx, S5, hp(noise(n / SR)) * k ** 2, 0.12)
    t = CUT_5B
    while t < RES_1 - 0.02:
        p = (t - CUT_5B) / (RES_1 - CUT_5B)
        add(sfx, t, blip(2200 + 600 * p, 0.012, 0.5), 0.07)
        t += 0.07 - 0.05 * p
    add(sfx, RES_1, arp_up([84, 91, 96], 0.05, 0.25, 0.3), 0.2)
    add(sfx, RES_1, explosion(), 0.5)
    add(sfx, RES_2, explosion(), 0.45)

    # Scene 6
    add(sfx, STAMP, thump(), 0.8)
    add(sfx, STAMP, explosion(), 0.3)
    add(sfx, COMENTA, arp_up([76, 81], 0.04, 0.25, 0.06), 0.15)
    add(sfx, TRADE, arp_up([84, 91], 0.07, 0.5, 0.4), 0.22)  # coin-ish
    add(sfx, MANDO, arp_up([79, 84], 0.04, 0.25, 0.06), 0.15)
    return sfx


# ---------------------------------------------------------------- voice
def load_mp3(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def build_vo():
    vo = np.zeros(N)
    cache = {}
    for path, a, b, dst in VO:
        if path not in cache:
            cache[path] = load_mp3(path)
        seg = cache[path][int(a * SR) : int(b * SR)].copy()
        fi, fo = int(0.008 * SR), int(0.04 * SR)
        seg[:fi] *= np.linspace(0, 1, fi)
        seg[-fo:] *= np.linspace(1, 0, fo)
        add(vo, dst, seg)
    vo = hp(vo) * 0.15 + vo  # a little presence
    return vo / np.abs(vo).max() * 0.92


def smooth_env(x, att=0.02, rel=0.3):
    a = np.abs(x)
    # block-wise peak then attack/release smoothing
    blk = 441
    pk = a[: len(a) // blk * blk].reshape(-1, blk).max(1)
    out = np.empty_like(pk)
    acc = 0.0
    ka, kr = 1 - np.exp(-blk / SR / att), 1 - np.exp(-blk / SR / rel)
    for i, v in enumerate(pk):
        acc += (ka if v > acc else kr) * (v - acc)
        out[i] = acc
    e = np.repeat(out, blk)
    return np.pad(e, (0, len(x) - len(e)), mode="edge")


def main():
    mus = build_music()
    mus[int(FINAL_HIT * SR):] = 0  # groove stops dead on the final hit
    tail = np.zeros(N)
    for m in (47, 59, 66, 71, 74, 78):
        s = pulse(midi(m), DURATION - FINAL_HIT, 0.25 if m > 60 else 0.5)
        add(tail, FINAL_HIT, s * env(len(s), decay=0.5, release=0.05) * 0.12)
    s = tri(midi(35), DURATION - FINAL_HIT)
    add(tail, FINAL_HIT, s * env(len(s), decay=0.6, release=0.05) * 0.6)
    add(tail, FINAL_HIT, crash(), 0.8)
    add(tail, FINAL_HIT, kick(), 1.0)
    mus += tail
    mus = lp_fast(mus, 9000)
    mus /= np.abs(mus).max()

    sfx = build_sfx()
    vo = build_vo()

    duck = 1 - 0.55 * np.clip(smooth_env(vo) / 0.35, 0, 1)
    mix_m = mus * 0.42 * duck + sfx * 0.55 + vo
    # stereo: slight width on music/sfx via tiny delay
    d = int(0.011 * SR)
    left = mix_m
    right = mus * 0.42 * duck
    right = np.concatenate([np.zeros(d), right[:-d]]) + sfx * 0.55 + vo
    st = np.stack([left, right], 1)
    st = np.tanh(st * 1.1) / np.tanh(1.1)
    st /= np.abs(st).max() / 0.95
    with wave.open("mix_raw.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", "mix_raw.wav", "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", str(SR), "mix.wav"],
        check=True,
    )
    print("audio ok")


if __name__ == "__main__":
    main()
