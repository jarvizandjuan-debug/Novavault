"""Pixel-art renderer: draws every frame at 270x480, scales x4 to 1080x1920,
adds CRT scanlines/glow and pipes raw frames to ffmpeg."""
import math
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from timeline import *

W, H, SC = 270, 480, 4
OW, OH = W * SC, H * SC
F = {s: ImageFont.truetype("PressStart2P.ttf", s) for s in (8, 16, 24, 32, 48)}

# ---------------------------------------------------------------- palette
BG = (6, 7, 14)
INK = (0, 0, 0)
WHITE = (240, 240, 232)
GREY = (120, 128, 150)
DKGREY = (44, 48, 66)
NAVY = (16, 20, 48)
NAVY2 = (26, 32, 74)
TGREEN = (60, 255, 110)
DGREEN = (20, 110, 50)
GREEN = (40, 220, 100)
RED = (255, 60, 84)
DKRED = (110, 18, 34)
GOLD = (255, 204, 51)
GOLD_LT = (255, 244, 170)
GOLD_DK = (214, 120, 20)
ORANGE = (222, 122, 88)
CYAN = (70, 230, 255)
MAGENTA = (230, 60, 255)
PURPLE = (100, 36, 180)
SKIN = (226, 168, 124)
HAIR = (44, 28, 20)

TICKERS = ["BIT16", "CRT9", "ZAP3", "VX4", "QBT2", "BITZ", "NEO7", "KO1N", "RYU5", "MEGA",
           "HEX6", "LVL9", "PWR2", "GG4", "XP10", "TURBO", "BLOK", "JMP3", "RAM4", "ROM2"]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def draw(img):
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    return d


def tw(s, size):
    return int(F[size].getlength(s))


ACCENTS = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U"}


def _glyphs(d, x, y, s, size, fill):
    """Draw text; accented capitals get a hand-placed acute above the base letter."""
    d.text((x, y), "".join(ACCENTS.get(c, c) for c in s), font=F[size], fill=fill)
    u = max(1, size // 8)
    for i, ch in enumerate(s):
        if ch in ACCENTS:
            ax = x + i * size
            for px, py in ((3, -2), (4, -2), (4, -3), (5, -3)):
                d.rectangle((ax + px * u, y + py * u, ax + px * u + u - 1, y + py * u + u - 1), fill=fill)


def text(d, x, y, s, size, fill, outline=None, shadow=None, center=False):
    if center:
        x = x - tw(s, size) // 2
    if shadow:
        sx, sy, sc = shadow
        _glyphs(d, x + sx, y + sy, s, size, sc)
    if outline:
        o = 1 if size < 32 else 2
        for dx in range(-o, o + 1):
            for dy in range(-o, o + 1):
                if dx or dy:
                    _glyphs(d, x + dx, y + dy, s, size, outline)
    _glyphs(d, x, y, s, size, fill)
    return x


def text_sprite(s, size, top, bottom=None, outline=INK, shadow=3):
    """RGBA sprite with 2-tone vertical shading, outline and drop shadow."""
    f = F[size]
    w, h = tw(s, size), size
    o = 1 if size < 32 else 2
    pad = o
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    md.fontmode = "1"
    md.text((0, 0), s, font=f, fill=255)
    a = np.array(m) > 0
    sw, sh = w + 2 * pad + shadow, h + 2 * pad + shadow
    out = np.zeros((sh, sw, 4), np.uint8)
    # shadow
    out[pad + shadow:pad + shadow + h, pad + shadow:pad + shadow + w][a] = (0, 0, 0, 255)
    # outline
    for dx in range(-o, o + 1):
        for dy in range(-o, o + 1):
            out[pad + dy:pad + dy + h, pad + dx:pad + dx + w][a] = (*outline, 255)
    # body with lower-half shading
    body = np.zeros((h, w, 4), np.uint8)
    body[:] = (*top, 255)
    if bottom:
        body[int(h * 0.55):] = (*bottom, 255)
    region = out[pad:pad + h, pad:pad + w]
    region[a] = body[a]
    return Image.fromarray(out, "RGBA")


def paste_scaled(img, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.NEAREST)
    if alpha < 1.0:
        a = np.array(spr)
        a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
        spr = Image.fromarray(a, "RGBA")
    img.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def overlay(img, fn):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(lay))
    img.paste(Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB"))


def dim(img, box, alpha):
    overlay(img, lambda d: d.rectangle(box, fill=(0, 0, 0, int(255 * alpha))))


def pbox(d, x0, y0, x1, y1, fill=NAVY, border=WHITE, shadow=True):
    """16-bit RPG style dialog box."""
    if shadow:
        d.rectangle((x0 + 3, y0 + 3, x1 + 3, y1 + 3), fill=INK)
    d.rounded_rectangle((x0, y0, x1, y1), radius=3, fill=INK)
    d.rounded_rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), radius=2, fill=border)
    d.rectangle((x0 + 3, y0 + 3, x1 - 3, y1 - 3), fill=(90, 100, 170))
    d.rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), fill=fill)


def star(d, x, y, col, big=False):
    d.point([(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], fill=col)
    if big:
        d.point([(x - 2, y), (x + 2, y), (x, y - 2), (x, y + 2)], fill=col)


def sparkles(d, t, box, n, seed, col=WHITE):
    r = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = r.randint(x0, x1), r.randint(y0, y1)
        ph = r.random()
        v = (t * 3 + ph) % 1
        if v < 0.5:
            star(d, x, y, col, big=v < 0.2)


def particles(d, t, t0, cx, cy, n, cols, seed, speed=120, life=0.6):
    u = t - t0
    if u < 0 or u > life:
        return
    r = random.Random(seed)
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi)
        v = r.uniform(0.3, 1) * speed
        x = int(cx + math.cos(a) * v * u)
        y = int(cy + math.sin(a) * v * u + 90 * u * u)
        s = 2 if u < life * 0.5 else 1
        d.rectangle((x, y, x + s - 1, y + s - 1), fill=r.choice(cols))


# ---------------------------------------------------------------- charts
def gen_series(seed, n, start=50.0, vol=0.6, drift=0.0):
    r = random.Random(seed)
    out, p = [], start
    for _ in range(n):
        o = p
        c = o + r.gauss(drift, vol)
        h = max(o, c) + abs(r.gauss(0, vol * 0.5))
        l = min(o, c) - abs(r.gauss(0, vol * 0.5))
        out.append((o, h, l, c))
        p = c
    return out


def draw_candles(d, series, x0, y0, x1, y1, cw, gap, lo=None, hi=None):
    if not series:
        return
    if lo is None:
        lo = min(c[2] for c in series)
        hi = max(c[1] for c in series)
        pad = (hi - lo) * 0.08 + 1e-6
        lo, hi = lo - pad, hi + pad

    def py(p):
        return int(round(y1 - (p - lo) / (hi - lo) * (y1 - y0)))

    x = x0
    for o, h, l, c in series:
        if x + cw - 1 > x1:
            break
        col = GREEN if c >= o else RED
        cx = x + cw // 2
        d.line((cx, py(h), cx, py(l)), fill=col)
        top, bot = py(max(o, c)), py(min(o, c))
        d.rectangle((x, top, x + cw - 1, max(bot, top + 1)), fill=col)
        x += cw + gap


def story_series():
    """PXL16: trend -> bull flag -> news candle -> tight base -> breakout."""
    r = random.Random(42)
    s, p = [], 46.0
    for i in range(14):
        o = p
        c = o + r.uniform(0.05, 0.65) * (1 if r.random() < 0.8 else -0.6)
        s.append((o, max(o, c) + r.uniform(0.05, 0.3), min(o, c) - r.uniform(0.05, 0.3), c))
        p = c
    p = 50.95
    for i in range(8):
        o = p
        c = o - r.uniform(-0.15, 0.25)
        c = clamp(c, 50.25, 51.0)
        s.append((o, max(o, c) + r.uniform(0.05, 0.2), min(o, c) - r.uniform(0.05, 0.2), c))
        p = c
    s[-1] = (s[-1][0], max(s[-1][0], 50.25) + 0.1, 50.15, 50.25)
    s.append((50.25, 53.95, 50.2, 53.65))  # idx 22: the news candle (+6.8%)
    p = 53.65
    for i in range(8):  # idx 23-30: base under 53.80
        o = p
        c = clamp(o + r.uniform(-0.3, 0.25), 53.05, 53.7)
        s.append((o, min(max(o, c) + r.uniform(0.02, 0.1), 53.76), min(o, c) - r.uniform(0.05, 0.2), c))
        p = c
    return s


STORY = story_series()
ENTRY, STOP, TARGET = 53.80, 52.80, 56.30
TINY = [gen_series(1000 + i, 40, 50, r_vol, r_dr)
        for i, (r_vol, r_dr) in enumerate((random.Random(i).uniform(0.3, 0.9), random.Random(i + 99).uniform(-0.2, 0.25))
                                           for i in range(64))]


def live_candle(t):
    """idx 31: wiggles under the entry while the countdown runs, then breaks out."""
    o = STORY[30][3]
    if t < GO:
        c = 53.42 + 0.22 * math.sin(t * 5.3) + 0.08 * math.sin(t * 13.1)
        c = min(c, 53.74)
        return (o, 53.76, 53.05, c)
    c = 53.74 + 0.55 * ease_out((t - GO) / 0.3)
    return (o, c + 0.08, 53.05, c)


AFTER = [(54.29, 54.75, 54.10, 54.62), (54.62, 55.10, 54.40, 54.95), (54.95, 55.45, 54.85, 55.32), (55.32, 55.60, 55.0, 55.18)]


# ---------------------------------------------------------------- shared UI
def hud(d, t, stage):
    score = int(scanned(t)) + (2500 if t > 10.45 else 0) + (2500 if t > POPUP else 0) + (5000 if t > GO else 0) + int(sims(t))
    text(d, 8, 8, "1UP", 8, RED if int(t * 2) % 2 else WHITE)
    text(d, 36, 8, f"{score:06d}", 8, WHITE)
    text(d, W - 8 - tw(f"STAGE {stage}", 8), 8, f"STAGE {stage}", 8, GOLD)


def caption(d, t, t0, lines, colors=None):
    if t < t0:
        return
    n = len(lines)
    inner = n * 16 + (n - 1) * 6
    x0, x1, y0 = 12, W - 12, 304
    full_h = inner + 20
    u = clamp((t - t0) / 0.12)
    h = max(6, int(full_h * ease_out(u)))
    yc = y0 + full_h // 2
    pbox(d, x0, yc - h // 2, x1, yc - h // 2 + h)
    if u < 1:
        return
    shown = int((t - t0 - 0.12) * 110)
    y = y0 + 10
    for i, s in enumerate(lines):
        part = s[: max(0, shown)]
        shown -= len(s)
        col = colors[i] if colors else WHITE
        x = (W - tw(s, 16)) // 2
        text(d, x, y, part, 16, col, shadow=(2, 2, INK))
        y += 22


def claude_window(d, x0, y0, x1, y1, title="CLAUDE CODE"):
    d.rectangle((x0 + 3, y0 + 3, x1 + 3, y1 + 3), fill=INK)
    d.rectangle((x0, y0, x1, y1), fill=ORANGE)
    d.rectangle((x0 + 1, y0 + 15, x1 - 1, y1 - 1), fill=(8, 8, 12))
    # sparkle glyph + title
    cx, cy = x0 + 9, y0 + 7
    for dx, dy in ((0, -3), (0, -2), (0, 2), (0, 3), (-3, 0), (-2, 0), (2, 0), (3, 0), (-2, -2), (2, 2), (-2, 2), (2, -2), (0, 0)):
        d.point((cx + dx, cy + dy), fill=(40, 20, 14))
    text(d, x0 + 17, y0 + 4, title, 8, (40, 20, 14))
    for k in range(3):
        bx = x1 - 10 - k * 9
        d.rectangle((bx, y0 + 4, bx + 5, y0 + 9), fill=(40, 20, 14))
        d.rectangle((bx + 1, y0 + 5, bx + 4, y0 + 8), fill=(250, 190, 160) if k else ORANGE)


def cursor(d, x, y, t, col=TGREEN, h=14):
    if int(t * 4) % 2 == 0:
        d.rectangle((x, y, x + 7, y + h), fill=col)


# ---------------------------------------------------------------- scene 1
def scene1(img, d, t):
    # faint terminal frame
    d.rectangle((4, 4, W - 5, H - 5), outline=(14, 40, 22))
    n = typed_chars(t, CMD_T, len(CMD))
    text(d, (W - tw(CMD, 8)) // 2, 108, CMD[:n], 8, (40, 170, 80))
    head = "".join(HEAD)
    k = typed_chars(t, HEAD_T, len(head))
    x0 = (W - tw(HEAD[0], 16)) // 2
    y = 136
    last = (x0, y)
    for line in HEAD:
        part = line[: max(0, k)]
        k -= len(line)
        if part:
            text(d, x0, y, part, 16, TGREEN, shadow=(0, 2, DGREEN))
            last = (x0 + tw(part, 16) + 2, y)
        y += 26
    g = typed_chars(t, GOLD_T, len("".join(GOLD_LINES)))
    shimmer = t > GOLD_T[1] and int(t * 10) % 3 == 0
    ys = (232,)
    for i, line in enumerate(GOLD_LINES):
        part = line[: max(0, g)]
        g -= len(line)
        if part:
            x = (W - tw(line, 24)) // 2
            text(d, x, ys[i], part, 24, GOLD_LT if shimmer else GOLD, shadow=(0, 3, GOLD_DK))
            last = (x + tw(part, 24) + 2, ys[i] + 2)
    if t > GOLD_T[1]:
        sparkles(d, t, (20, 222, 250, 262), 10, 5, GOLD_LT)
    cursor(d, last[0], last[1], t, GOLD if t > GOLD_T[0] else TGREEN, 16 if t > GOLD_T[0] else 14)


# ---------------------------------------------------------------- scene 2
def crt(d, x, y, w, h, series_seed, t, kind="chart"):
    d.rectangle((x + 2, y + 2, x + w + 1, y + h + 1), fill=INK)
    d.rounded_rectangle((x, y, x + w - 1, y + h - 1), radius=3, fill=(178, 172, 156), outline=(60, 56, 50))
    d.line((x + 3, y + 1, x + w - 4, y + 1), fill=(222, 216, 200))
    sx0, sy0, sx1, sy1 = x + 5, y + 5, x + w - 6, y + h - 10
    d.rounded_rectangle((sx0, sy0, sx1, sy1), radius=3, fill=(6, 16, 12))
    d.point((x + w - 9, y + h - 6), fill=GREEN if int(t * 3 + x) % 2 else DGREEN)
    d.line((x + 6, y + h - 6, x + 20, y + h - 6), fill=(140, 136, 122))
    if kind == "chart":
        ser = TINY[series_seed % len(TINY)] + TINY[(series_seed + 7) % len(TINY)]
        cw = 2 if w < 100 else 3
        off = int(t * 7 + series_seed * 3) % 40
        n = (sx1 - sx0 - 4) // (cw + 1)
        draw_candles(d, ser[off:off + n], sx0 + 2, sy0 + 4, sx1 - 2, sy1 - 3, cw, 1)
        for gy in range(sy0 + 6, sy1, 8):
            d.point([(gx, gy) for gx in range(sx0 + 2, sx1 - 1, 4)], fill=(20, 44, 32))
    else:  # mini Claude Code window
        d.rectangle((sx0 + 1, sy0 + 1, sx1 - 1, sy0 + 7), fill=ORANGE)
        rows = ["> /scan", "BIT16 ok", "CRT9  ok", "ZAP3  --", "VX4   ok", "QBT2  ok", "BITZ  --", "NEO7  ok"]
        off = int(t * 9)
        for i in range(5):
            s = rows[(off + i) % len(rows)] if i else rows[0]
            text(d, sx0 + 3, sy0 + 10 + i * 10, s, 8, TGREEN if i else WHITE)


def trader(d, t):
    bob = 1 if int((t - S2) / BEAT) % 2 else 0
    # chair back (in front of the trader's back)
    hx = 135
    # hoodie
    d.polygon([(92, 300), (100, 228), (116, 214), (154, 214), (170, 228), (178, 300)], fill=(56, 64, 150))
    d.polygon([(100, 236), (116, 216), (120, 226)], fill=(74, 84, 180))
    d.ellipse((114, 204, 156, 230), fill=(40, 46, 110))  # hood
    d.rectangle((128, 200 + bob, 142, 212 + bob), fill=(196, 140, 104))  # neck
    # head (hair from behind)
    d.ellipse((hx - 19, 164 + bob, hx + 19, 206 + bob), fill=HAIR)
    d.ellipse((hx - 16, 168 + bob, hx + 12, 196 + bob), fill=(62, 40, 28))
    # rim light from the monitors
    for yy in range(172, 202, 2):
        d.point((hx + 18, yy + bob), fill=TGREEN if (yy // 2 + int(t * 6)) % 3 else CYAN)
        d.point((hx - 19, yy + bob), fill=(80, 120, 220))
    # ears
    d.rectangle((hx - 22, 184 + bob, hx - 19, 194 + bob), fill=SKIN)
    d.rectangle((hx + 19, 184 + bob, hx + 22, 194 + bob), fill=SKIN)
    # headset
    d.arc((hx - 23, 160 + bob, hx + 23, 206 + bob), 195, 345, fill=(90, 90, 104), width=3)
    d.rectangle((hx - 27, 180 + bob, hx - 20, 198 + bob), fill=(26, 26, 32))
    d.rectangle((hx + 20, 180 + bob, hx + 27, 198 + bob), fill=(26, 26, 32))
    d.point((hx + 25, 184 + bob), fill=RED)
    # chair
    d.rounded_rectangle((102, 246, 168, 318), radius=6, fill=(30, 30, 40), outline=(64, 64, 80))
    d.rectangle((108, 252, 162, 256), fill=(46, 46, 60))
    d.rectangle((131, 318, 139, 340), fill=(40, 40, 52))
    d.rectangle((104, 340, 166, 344), fill=(40, 40, 52))


def scene2a(img, d, t):
    # wall with soft vertical dither
    d.rectangle((0, 0, W, 240), fill=(18, 20, 46))
    for x in range(0, W, 6):
        d.line((x, 40, x, 240), fill=(22, 24, 54))
    # LED ticker
    d.rectangle((0, 22, W, 35), fill=INK)
    d.line((0, 22, W, 22), fill=(60, 60, 80))
    d.line((0, 35, W, 35), fill=(60, 60, 80))
    items = [("PXL16 +2.4%", GREEN), ("BIT16 -0.8%", RED), ("CRT9 +5.1%", GREEN), ("ZAP3 -1.2%", RED),
             ("VX4 +0.6%", GREEN), ("MEGA +3.3%", GREEN), ("ROM2 -2.0%", RED)]
    x = 8 - int((t - S2) * 70)
    for s, c in items * 2:
        text(d, x, 25, s, 8, c)
        x += tw(s, 8) + 16
    # monitors
    crt(d, 6, 42, 82, 64, 3, t)
    crt(d, 94, 42, 82, 64, 11, t)
    crt(d, 182, 42, 82, 64, 19, t)
    crt(d, 6, 110, 124, 96, 27, t)
    crt(d, 140, 110, 124, 96, 0, t, kind="claude")
    # desk
    d.rectangle((0, 206, W, 216), fill=(78, 58, 44))
    d.line((0, 206, W, 206), fill=(110, 84, 62))
    d.rectangle((0, 217, W, 246), fill=(46, 34, 28))
    d.rectangle((0, 246, W, H), fill=(12, 12, 24))
    for y in range(250, H, 10):
        d.line((0, y, W, y), fill=(16, 16, 32))
    d.rectangle((96, 207, 176, 212), fill=(150, 146, 136))
    for kx in range(98, 174, 4):
        d.point((kx, 209), fill=(90, 88, 80))
    d.rectangle((206, 196, 214, 206), fill=WHITE)  # mug
    d.rectangle((215, 198, 217, 203), outline=WHITE)
    trader(d, t)


def scanned(t):
    if t < CUT_2B:
        return 0
    return 5000 * clamp((t - CUT_2B) / (9.6 - CUT_2B)) ** 1.6


def grid(d, area, cols, cw, ch, gap, scroll, t, labels=True, beam_speed=420, scanned_upto=None, dimmed=False):
    x0, y0, x1, y1 = area
    row_h = ch + gap
    first = int(scroll // row_h)
    oy = -(scroll % row_h)
    rows = (y1 - y0) // row_h + 2
    beam = y0 + (t * beam_speed) % (y1 - y0)
    for r in range(rows):
        ry = y0 + oy + r * row_h
        for c in range(cols):
            cx = x0 + c * (cw + gap)
            idx = (first + r) * cols + c
            y_a, y_b = int(ry), int(ry + ch - 1)
            if y_b < y0 or y_a > y1:
                continue
            hit = abs((y_a + y_b) / 2 - beam) < ch * 0.6
            d.rectangle((cx, y_a, cx + cw - 1, y_b), fill=(10, 12, 20), outline=CYAN if hit else (40, 44, 62))
            ser = TINY[idx % len(TINY)]
            if labels:
                text(d, cx + 3, y_a + 3, TICKERS[idx % len(TICKERS)], 8, WHITE if not hit else CYAN)
                d.point((cx + cw - 5, y_a + 4), fill=GREEN if idx % 5 else RED)
                draw_candles(d, ser[idx % 9: idx % 9 + 18], cx + 3, y_a + 13, cx + cw - 4, y_b - 3, 2, 1)
            else:
                draw_candles(d, ser[idx % 9: idx % 9 + 13], cx + 2, y_a + 2, cx + cw - 3, y_b - 2, 1, 1)
    # scan beam with trail
    for k in range(10):
        yy = int(beam) - k * 2
        if y0 <= yy <= y1:
            col = tuple(int(v * (1 - k / 10)) for v in CYAN)
            d.line((x0, yy, x1, yy), fill=col if k else WHITE)


def clip_area(img, area, painter):
    x0, y0, x1, y1 = area
    sub = Image.new("RGB", (x1 - x0 + 1, y1 - y0 + 1), (8, 8, 12))
    sd = draw(sub)
    painter(sub, sd, (0, 0, x1 - x0, y1 - y0))
    img.paste(sub, (x0, y0))


def integrate(fn, a, b, steps=120):
    if b <= a:
        return 0.0
    h = (b - a) / steps
    return sum(fn(a + (i + 0.5) * h) for i in range(steps)) * h


def speed_2b(t):
    return 60 + 220 * ((t - CUT_2B) / (CUT_2C - CUT_2B)) ** 1.5


def speed_2c(t):
    u = t - CUT_2C
    v = 260 + 380 * min(u, 1.6)
    if t > 9.3:
        v *= clamp(1 - (t - 9.3) / 0.6)
    return v


def status_line(d, t, y=268):
    n = int(scanned(t))
    done = n >= 5000
    s = f"ESCANEADAS {n:,}" + ("" if done else "/5,000")
    text(d, 14, y + 2, s, 8, GOLD if done and int(t * 6) % 2 else WHITE)
    if done:
        text(d, W - 14 - tw("LISTO", 8), y + 2, "LISTO", 8, TGREEN)
    d.rectangle((14, y + 14, W - 15, y + 20), outline=(60, 64, 90))
    fw = int((W - 31) * min(1, n / 5000))
    for x in range(16, 16 + fw, 4):
        d.rectangle((x, y + 16, x + 2, y + 18), fill=TGREEN)


def scene2b(img, d, t):
    d.rectangle((0, 0, W, H), fill=(10, 10, 22))
    claude_window(d, 8, 40, W - 9, 296)
    text(d, 14, 60, "> /scan-charts --todo", 8, TGREEN)
    cursor(d, 14 + tw("> /scan-charts --todo", 8) + 2, 59, t, h=8)
    area = (14, 74, W - 15, 262)
    scroll = integrate(speed_2b, CUT_2B, t)
    clip_area(img, area, lambda s, sd, a: grid(sd, a, 4, 58, 44, 3, scroll, t))
    status_line(d, t)


def scene2c(img, d, t):
    d.rectangle((0, 0, W, H), fill=(10, 10, 22))
    claude_window(d, 8, 40, W - 9, 296)
    text(d, 14, 60, "> modo turbo: x5,000", 8, GOLD)
    area = (14, 74, W - 15, 262)
    scroll = integrate(speed_2c, CUT_2C, t)
    clip_area(img, area, lambda s, sd, a: grid(sd, a, 8, 28, 22, 2, scroll, t, labels=False, beam_speed=900))
    status_line(d, t)


# ---------------------------------------------------------------- scene 3
CELL = (136, 121, 136 + 57, 121 + 43)


def scene3a(img, d, t):
    d.rectangle((0, 0, W, H), fill=(10, 10, 22))
    claude_window(d, 8, 40, W - 9, 296)
    line = "> setup detectado: PXL16" if t > 10.45 else "> analizando patrones..."
    text(d, 14, 60, line, 8, GOLD if t > 10.45 else TGREEN)
    area = (14, 74, W - 15, 262)
    clip_area(img, area, lambda s, sd, a: grid(sd, a, 4, 58, 44, 3, 0, 0, beam_speed=0))
    dim(img, (14, 74, W - 15, 262), 0.55 * ease_out((t - S3) / 0.3))
    d = draw(img)
    # selected cell: the PXL16 flag
    x0, y0, x1, y1 = CELL
    flash = 10.45 <= t < 10.52
    d.rectangle(CELL, fill=WHITE if flash else (12, 16, 26), outline=GOLD)
    if not flash:
        text(d, x0 + 3, y0 + 3, "PXL16", 8, GOLD)
        draw_candles(d, STORY[6:22], x0 + 3, y0 + 13, x1 - 3, y1 - 3, 2, 1)
    # selection brackets fly in from the grid bounds
    u = ease_back((t - S3) / 0.45)
    gx0, gy0, gx1, gy1 = 14, 74, W - 15, 262
    bx0 = gx0 + (x0 - 4 - gx0) * u
    by0 = gy0 + (y0 - 4 - gy0) * u
    bx1 = gx1 + (x1 + 4 - gx1) * u
    by1 = gy1 + (y1 + 4 - gy1) * u
    if t < 10.45 or int(t * 8) % 4 != 3:
        L = 7
        for (cx, cy, sx, sy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            cx, cy = int(cx), int(cy)
            d.rectangle((min(cx, cx + sx * L), min(cy, cy + sy * 2), max(cx, cx + sx * L), max(cy, cy + sy * 2)), fill=GOLD)
            d.rectangle((min(cx, cx + sx * 2), min(cy, cy + sy * L), max(cx, cx + sx * 2), max(cy, cy + sy * L)), fill=GOLD)
    if t > 10.55:
        s = ease_back((t - 10.55) / 0.2)
        lbl = "SETUP DETECTADO!"
        w = tw(lbl, 8) + 10
        cx = (x0 + x1) // 2 - 20
        yy = y1 + 10
        hw = int(w / 2 * s)
        d.rectangle((cx - hw + 2, yy + 2, cx + hw + 2, yy + 14), fill=INK)
        d.rectangle((cx - hw, yy, cx + hw, yy + 12), fill=GOLD)
        if s > 0.95:
            text(d, cx - w // 2 + 5, yy + 3, lbl, 8, (40, 20, 0))
        sparkles(d, t, (x0 - 14, y0 - 14, x1 + 14, y1 + 14), 8, 11, GOLD_LT)
        particles(d, t, 10.45, (x0 + x1) // 2, (y0 + y1) // 2, 26, [GOLD, WHITE, GOLD_LT], 3, speed=110, life=0.5)
    status_line(d, 9.9)


def chart_panel(d, title, header_price, header_chg, up=True):
    d.rectangle((0, 0, W, H), fill=(10, 10, 22))
    claude_window(d, 6, 40, W - 7, 298, title)
    text(d, 12, 59, "PXL16", 8, WHITE)
    text(d, 60, 59, header_price, 8, WHITE)
    text(d, W - 12 - tw(header_chg, 8), 59, header_chg, 8, GREEN if up else RED)


def price_grid(d, lo, hi, x0, y0, x1, y1, step, labels=True):
    def py(p):
        return int(round(y1 - (p - lo) / (hi - lo) * (y1 - y0)))
    p = math.ceil(lo / step) * step
    while p <= hi:
        y = py(p)
        d.point([(x, y) for x in range(x0, x1, 3)], fill=(34, 38, 62))
        if labels:
            text(d, x1 + 4, y - 3, f"{int(p)}", 8, GREY)
        p += step
    return py


def scene3b(img, d, t):
    jumped = t >= JUMP
    chart_panel(d, "PXL16 · 5 MIN", "$53.65" if jumped else "$50.25", "+6.8%" if jumped else "+0.4%")
    lo, hi = 45.5, 57.0
    x0, y0, x1, y1 = 12, 76, 236, 262
    py = price_grid(d, lo, hi, x0, y0, x1, y1, 2)
    n_extra = 0 if t < 14.0 else min(6, int((t - 14.0) / 0.5) + 1)
    ser = STORY[:22]
    if jumped:
        u = ease_out((t - JUMP) / 0.3)
        o, h, l, c = STORY[22]
        ser = ser + [(o, o + (h - o) * u, l, o + (c - o) * u)]
        ser = ser + STORY[23:23 + n_extra]
    draw_candles(d, ser, x0, y0, x1, y1, 5, 2, lo, hi)
    # bull-flag box
    if t > 11.85 and (t > 12.3 or int(t * 10) % 2):
        bx0, bx1 = x0 + 14 * 7 - 2, x0 + 22 * 7 - 1
        by0, by1 = py(51.45), py(49.95)
        for x in range(bx0, bx1, 4):
            d.line((x, by0, x + 1, by0), fill=GOLD)
            d.line((x, by1, x + 1, by1), fill=GOLD)
        for y in range(by0, by1, 4):
            d.line((bx0, y, bx0, y + 1), fill=GOLD)
            d.line((bx1, y, bx1, y + 1), fill=GOLD)
        text(d, bx0, by1 + 4, "BANDERA", 8, GOLD, outline=INK)
    if jumped:
        cx = x0 + 22 * 7 + 2
        u = (t - JUMP)
        if u < 1.4:
            yy = py(54.2) - int(u * 18)
            text(d, cx - 30, yy, "+6.8%", 8, GREEN if int(t * 12) % 2 else WHITE, outline=INK)
        particles(d, t, JUMP, cx, py(53.9), 20, [GREEN, WHITE, TGREEN], 8, speed=90, life=0.5)
    # status
    msg = "> leyendo noticias..." if t < POPUP else ("> noticia: IMPACTO ALTO" if t < JUMP else "> setup + noticia: LISTO")
    text(d, 14, 272, msg, 8, TGREEN if t < JUMP else GOLD)
    # popup
    if POPUP <= t:
        if t < POPUP_OUT:
            u = ease_back((t - POPUP) / 0.16)
        else:
            u = 1 - ease_out((t - POPUP_OUT) / 0.12)
        if u > 0.02:
            pw, ph = int(112 * u), int(40 * u)
            cx, cy = 135, 140
            bx0, by0, bx1, by1 = cx - pw, cy - ph, cx + pw, cy + ph
            d.rectangle((bx0 + 3, by0 + 3, bx1 + 3, by1 + 3), fill=INK)
            d.rectangle((bx0, by0, bx1, by1), fill=WHITE)
            d.rectangle((bx0 + 2, by0 + 2, bx1 - 2, by1 - 2), fill=(14, 14, 34))
            if u > 0.97:
                d.rectangle((bx0 + 2, by0 + 2, bx1 - 2, by0 + 15), fill=(206, 34, 60))
                text(d, bx0 + 8, by0 + 6, "! ÚLTIMA HORA", 8, WHITE if int(t * 6) % 2 else GOLD_LT)
                text(d, bx0 + 10, by0 + 24, "PXL16 FIRMA CONTRATO", 8, WHITE)
                text(d, bx0 + 10, by0 + 38, "RÉCORD DE $2,000M", 8, WHITE)
                text(d, bx0 + 10, by0 + 56, "IMPACTO: ALTO ▲", 8, GOLD)
    if t >= POPUP_OUT + 0.12:
        d.rectangle((14, 78, 14 + tw("CATALIZADOR ▲", 8) + 6, 90), fill=(206, 34, 60))
        text(d, 17, 81, "CATALIZADOR ▲", 8, WHITE)


# ---------------------------------------------------------------- scene 4
LO4, HI4 = 49.5, 57.5
C4 = (12, 116, 236, 290)


def hp_bar(d, y, fill_u, col, dark, frame):
    x0, x1 = C4[0], C4[2]
    d.rectangle((x0, y - 5, x1, y + 5), fill=INK)
    d.rectangle((x0 + 1, y - 4, x1 - 1, y + 4), fill=frame)
    d.rectangle((x0 + 2, y - 3, x1 - 2, y + 3), fill=dark)
    segs = (x1 - x0 - 4) // 6
    for i in range(int(segs * clamp(fill_u))):
        sx = x0 + 3 + i * 6
        d.rectangle((sx, y - 2, sx + 4, y + 2), fill=col)
        d.line((sx, y - 2, sx + 4, y - 2), fill=tuple(min(255, v + 70) for v in col))


def level_label(d, x, y, s, col, bg=INK):
    d.rectangle((x - 2, y - 2, x + tw(s, 8) + 1, y + 8), fill=bg)
    text(d, x, y, s, 8, col)


def scene4(img, d, t):
    live = live_candle(t)
    price = live[3] if t < GO + 0.4 else AFTER[min(3, int((t - GO - 0.4) / BEAT))][3]
    chg = (price / 50.25 - 1) * 100
    chart_panel(d, "PXL16 · 5 MIN", f"${price:.2f}", f"+{chg:.1f}%")
    x0, y0, x1, y1 = C4
    py = price_grid(d, LO4, HI4, x0, y0, x1, y1, 2)
    after = [] if t < GO + 0.44 else AFTER[: min(4, int((t - GO - 0.44) / BEAT) + 1)]
    ser = STORY[14:31] + [live] + after
    draw_candles(d, ser, x0, y0, x1, y1, 7, 3, LO4, HI4)
    # entry line
    ye = py(ENTRY)
    in_pos = t >= GO
    for x in range(x0, x1, 4 if not in_pos else 1):
        d.line((x, ye, x + (1 if not in_pos else 0), ye), fill=GOLD if in_pos else WHITE)
    lbl = "EN POSICIÓN" if in_pos else "ENTRADA 53.80"
    level_label(d, x1 - tw(lbl, 8) - 2, ye - 12, lbl, INK if in_pos else WHITE, GOLD if in_pos else INK)
    if in_pos:
        ex = x0 + 17 * 10
        d.polygon([(ex - 8, ye - 4), (ex - 2, ye), (ex - 8, ye + 4)], fill=GOLD)
        particles(d, t, GO, ex, ye, 30, [GOLD, WHITE, GOLD_LT], 21, speed=130, life=0.55)
    # health bars
    if t >= STOP_FILL:
        ys = py(STOP)
        hp_bar(d, ys, (t - STOP_FILL) / 0.45, RED, DKRED, (200, 60, 70))
        level_label(d, x0 + 2, ys + 9, "♥ STOP 52.80", RED)
    if t >= TGT_FILL:
        yt = py(TARGET)
        hp_bar(d, yt, (t - TGT_FILL) / 0.45, GREEN, (10, 50, 24), (60, 200, 110))
        level_label(d, x0 + 2, yt - 16, "★ TARGET 56.30", GREEN)
    # R:R badge
    if t >= RR_BADGE:
        s = ease_back((t - RR_BADGE) / 0.18)
        w = int((tw("R:R 1:2.5", 8) + 8) * s)
        d.rectangle((14, 82, 14 + w, 96), fill=GOLD)
        if s > 0.95:
            text(d, 18, 86, "R:R 1:2.5", 8, (40, 20, 0))
    # countdown box
    bx0, by0, bx1, by1 = 146, 72, W - 12, 112
    d.rectangle((bx0, by0, bx1, by1), fill=INK, outline=GOLD)
    text(d, (bx0 + bx1) // 2, by0 + 5, "ENTRADA EN", 8, GOLD, center=True)
    cx, cy = (bx0 + bx1) // 2, by0 + 16
    if t < COUNT[0]:
        dots = "." * (1 + int(t * 4) % 3)
        text(d, cx - tw("...", 16) // 2, cy + 2, dots, 16, WHITE)
    elif t < GO:
        k = sum(1 for c in COUNT if t >= c)
        num = str(4 - k)
        age = t - COUNT[k - 1]
        col = RED if age < 0.1 else WHITE
        text(d, cx, cy, num, 24 if age > 0.07 else 16, col, center=True, shadow=(2, 2, DKRED))
    else:
        col = GOLD if int(t * 8) % 2 else GOLD_LT
        text(d, cx, cy, "¡YA!", 24, col, center=True, shadow=(2, 2, GOLD_DK))


# ---------------------------------------------------------------- scene 5
def vortex(d, cx, cy, R, t, arms=3, density=110, size=2):
    cols = [MAGENTA, CYAN, WHITE, PURPLE, (120, 80, 255)]
    for a in range(arms):
        for k in range(density):
            rad = R * (k / density)
            ang = a * 2 * math.pi / arms + k * 0.11 - t * 5.5
            x = int(cx + math.cos(ang) * rad)
            y = int(cy + math.sin(ang) * rad * 0.92)
            ci = int(k / 6 + t * 14) % len(cols)
            s = size if k > density * 0.35 else 1
            d.rectangle((x, y, x + s - 1, y + s - 1), fill=cols[ci])
    # rings rushing inward
    for j in range(4):
        r = (R * 1.05) * (1 - ((t * 0.9 + j / 4) % 1))
        for k in range(0, 360, 8):
            if (k // 8 + j) % 2:
                continue
            ang = math.radians(k + t * 90)
            d.point((cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.92), fill=(150, 90, 255))
    d.rectangle((cx - 2, cy - 2, cx + 2, cy + 2), fill=WHITE)


def scene5a(img, d, t):
    d.rectangle((0, 0, W, H), fill=(4, 2, 12))
    u = clamp((t - (CUT_5B - 0.35)) / 0.35)
    R = 92 + 260 * u ** 2
    vortex(d, 135, 228, R, t, density=130)
    jit = random.Random(int(t * 10)).randint(-2, 2) if int(t * 10) % 4 == 0 else 0
    for s, y in (("TIME", 74), ("MACHINE", 112)):
        x = (W - tw(s, 32)) // 2 + jit
        text(d, x - 2, y, s, 32, MAGENTA)
        text(d, x + 2, y, s, 32, CYAN)
        text(d, x, y, s, 32, WHITE)
    if int(t * 6) % 2 or t > S5 + 0.6:
        text(d, 135, 156, "SIMULADOR x10,000", 8, GOLD, center=True, outline=INK)
    if u > 0:
        overlay(img, lambda o: o.rectangle((0, 0, W, H), fill=(255, 255, 255, int(200 * u ** 2))))


NP = 260
SIM_X0, SIM_X1 = 86, 236


def build_paths():
    r = np.random.default_rng(3)
    steps = SIM_X1 - SIM_X0
    paths = []
    for i in range(NP):
        p = ENTRY
        pts = [p]
        res = 0
        drift = 0.012
        for s in range(steps):
            p += r.normal(drift, 0.13)
            pts.append(p)
            if p >= TARGET:
                res = 1
                break
            if p <= STOP:
                res = -1
                break
        paths.append((np.array(pts), res))
    return paths


PATHS = build_paths()
py5 = None


def sims(t):
    if t < CUT_5B:
        return 0
    return 10000 * clamp((t - CUT_5B) / (RES_1 - CUT_5B)) ** 1.8


def scene5b(img, d, t):
    global py5
    chart_panel(d, "PXL16 · TIME MACHINE", "$53.80", "SIM")
    x0, y0, x1, y1 = C4
    py = price_grid(d, LO4, HI4, x0, y0, x1, y1, 2)
    draw_candles(d, STORY[14:31] + [live_candle(GO - 0.01)], x0, y0, SIM_X0 - 2, y1, 3, 1, LO4, HI4)
    yt, ys, ye = py(TARGET), py(STOP), py(ENTRY)
    for x in range(SIM_X0, x1, 3):
        d.point([(x, yt), (x, ys)], fill=None)
        d.point((x, yt), fill=GREEN)
        d.point((x, ys), fill=RED)
        d.point((x, ye), fill=(110, 110, 120))
    text(d, x1 - tw("TARGET", 8), yt - 11, "TARGET", 8, GREEN, outline=INK)
    text(d, x1 - tw("STOP", 8), ys + 4, "STOP", 8, RED, outline=INK)
    # accumulate simulated paths
    p = clamp((t - CUT_5B) / (RES_1 - CUT_5B))
    shown = p ** 1.8 * NP
    done = int(shown)
    frac = shown - done
    acc = {1: np.zeros((H, W)), -1: np.zeros((H, W)), 0: np.zeros((H, W))}
    for i in range(min(done, NP)):
        pts, res = PATHS[i]
        xs = SIM_X0 + np.arange(len(pts))
        ys_ = np.clip(np.round(y1 - (pts - LO4) / (HI4 - LO4) * (y1 - y0)).astype(int), y0, y1)
        np.add.at(acc[res], (ys_, xs), 1)
    a = np.asarray(img).astype(np.float32)
    for res, col in ((0, (150, 150, 170)), (-1, RED), (1, GREEN)):
        k = np.clip(acc[res] * 0.35, 0, 0.85)[..., None]
        a = a * (1 - k) + np.array(col, np.float32) * k
    img.paste(Image.fromarray(a.astype(np.uint8)))
    d = draw(img)
    # head path + vortex
    if done < NP and t < RES_1:
        pts, res = PATHS[done]
        m = max(2, int(len(pts) * frac))
        coords = [(SIM_X0 + j, py(v)) for j, v in enumerate(pts[:m])]
        d.line(coords, fill=WHITE)
        hx, hy = coords[-1]
        vortex(d, hx, hy, 13, t, arms=2, density=26, size=1)
    # counter + tallies
    n = int(sims(t))
    hit_t = int(n * 0.64)
    text(d, 14, 74, "SIMULACIONES", 8, GREY)
    landed = t >= RES_1
    text(d, 12, 86, f"{n:,}".rjust(6, " "), 24, GOLD_LT if landed and int(t * 10) % 2 else GOLD, shadow=(2, 2, GOLD_DK))
    for k, (lbl, v, col) in enumerate((("TARGET", hit_t, GREEN), ("STOP", n - hit_t, RED))):
        s = f"{lbl} {v:,}"
        text(d, W - 12 - tw(s, 8), 78 + 14 * k, s, 8, col)


SPR = {}


def scene5c(img, d, t):
    scene5b(img, d, t)
    dim(img, (6, 114, W - 7, 296), 0.88 * ease_out((t - RES_1) / 0.15))
    d = draw(img)
    for t0, lbl, num, col, dark, y in ((RES_1, "LLEGA AL TARGET", "64%", GREEN, (10, 110, 50), 120),
                                       (RES_2, "TOCA EL STOP", "36%", RED, DKRED, 200)):
        if t < t0:
            continue
        key = num
        if key not in SPR:
            SPR[key] = text_sprite(num, 48, col, dark, outline=INK, shadow=3)
        age = t - t0
        sc = 2.2 if age < 1 / FPS else (1.5 if age < 2 / FPS else 1.0)
        text(d, 135, y, lbl, 8, col, center=True, outline=INK)
        paste_scaled(img, SPR[key], 135, y + 40, sc)
        d = draw(img)
        particles(d, t, t0, 135, y + 40, 40, [col, WHITE, GOLD], int(t0 * 100), speed=170, life=0.6)


# ---------------------------------------------------------------- scene 6
def stamp_sprite():
    w, h = 240, 62
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = draw(im)
    ink = (236, 48, 62, 255)
    d.rectangle((0, 0, w - 1, h - 1), outline=ink, width=3)
    d.rectangle((6, 6, w - 7, h - 7), outline=ink, width=1)
    d.text(((w - tw("PAPER TRADING", 16)) // 2, 15), "PAPER TRADING", font=F[16], fill=ink)
    s = "— SIN DINERO REAL —"
    d.text(((w - tw(s, 8)) // 2, 40), s, font=F[8], fill=ink)
    a = np.array(im)
    r = np.random.default_rng(9)
    holes = r.random(a.shape[:2]) < 0.09
    a[holes, 3] = 0
    im = Image.fromarray(a, "RGBA").rotate(6, resample=Image.NEAREST, expand=True)
    return im


STAMP_SPR = stamp_sprite()
TRADE_SPR = text_sprite("TRADE", 48, GOLD, GOLD_DK, outline=(70, 30, 0), shadow=4)
STARS = [(random.Random(i).randint(0, W), random.Random(i * 7).randint(0, H), 1 + i % 3) for i in range(70)]


def scene6(img, d, t):
    d.rectangle((0, 0, W, H), fill=(8, 10, 28))
    u = t - S6
    for x, y, layer in STARS:
        yy = (y + u * 20 * layer) % H
        d.point((x, yy), fill=(60 + 50 * layer, 60 + 50 * layer, 90 + 50 * layer))
    # faint chart in the background
    ser = STORY[:31]
    draw_candles(d, ser, 10, 120, 260, 300, 5, 3, 45.5, 57.0)
    dim(img, (0, 0, W, H), 0.72)
    d = draw(img)
    # stamp slam
    age = t - STAMP
    sc = 2.4 if age < 1 / FPS else (1.7 if age < 2 / FPS else (1.25 if age < 3 / FPS else 1.0))
    for k, (px, py_) in enumerate(((18, 72), (252, 72), (18, 128), (252, 128))):
        particles(d, t, STAMP + 3 / FPS, px, py_, 12, [(236, 48, 62), WHITE, (120, 120, 140)], 77 + k, speed=150, life=0.5)
    paste_scaled(img, STAMP_SPR, 135, 100, sc, alpha=0.6 if age < 2 / FPS else 1.0)
    d = draw(img)
    if t >= COMENTA:
        s = ease_back((t - COMENTA) / 0.15)
        y = 172 + int((1 - s) * 12)
        text(d, 135, y, "COMENTA", 24, WHITE, center=True, shadow=(0, 3, (50, 50, 90)))
    if t >= TRADE:
        age = t - TRADE
        sc = 1.9 if age < 1 / FPS else (1.4 if age < 2 / FPS else 1.0)
        bounce = int(3 * math.sin((t - TRADE) * 8)) if age > 0.2 else 0
        spr = TRADE_SPR
        # shimmer band sweeping across the letters
        ph = ((t - TRADE) * 140) % 400 - 60
        a = np.array(spr)
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        band = (np.abs(xx + yy * 0.6 - ph) < 7) & (a[..., 0] > 200) & (a[..., 3] > 0)
        a[band, :3] = (255, 252, 230)
        paste_scaled(img, Image.fromarray(a, "RGBA"), 135, 228 + bounce, sc)
        d = draw(img)
        sparkles(d, t, (8, 200, 262, 260), 12, 31, GOLD_LT)
        particles(d, t, TRADE, 135, 228, 36, [GOLD, GOLD_LT, WHITE], 55, speed=160, life=0.6)
    if t >= MANDO:
        s = ease_back((t - MANDO) / 0.15)
        y = 262 + int((1 - s) * 10)
        text(d, 135, y, "Y TE LO MANDO", 16, WHITE, center=True, shadow=(0, 2, (50, 50, 90)))
    if t >= MANDO + 0.3 and int(t * 4) % 2 == 0:
        text(d, 135, 292, "▼ ▼ ▼", 16, GOLD, center=True)


# ---------------------------------------------------------------- post / main
CUTS = [S2, CUT_2B, CUT_2C, S3, CUT_3B, S4, S5, CUT_5B, RES_1, S6]
GLITCH = [S2, S3, S4, S5, S6]
SHAKES = [(GOLD_T[1], 0.18, 2), (10.45, 0.15, 2), (JUMP, 0.3, 4), (GO, 0.3, 4), (RES_1, 0.3, 5),
          (RES_2, 0.25, 4), (STAMP + 3 / FPS, 0.35, 6), (TRADE, 0.25, 3), (FINAL_HIT, 0.3, 3)]


def make_mask():
    y = np.arange(OH)
    scan = np.where(y % SC == SC - 1, 0.62, np.where(y % SC == 0, 0.9, 1.0))
    yy, xx = np.mgrid[0:OH, 0:OW]
    nx = (xx / OW - 0.5) * 2
    ny = (yy / OH - 0.5) * 2
    vig = 1 - 0.32 * (np.abs(nx) ** 3.5 + np.abs(ny) ** 3.5)
    m = scan[:, None] * vig
    return (np.clip(m, 0, 1) * 256).astype(np.uint16)[..., None]


MASK = None


def post(img, t, i):
    # shake
    dx = dy = 0
    for t0, dur, amp in SHAKES:
        if 0 <= t - t0 < dur:
            k = amp * (1 - (t - t0) / dur)
            r = random.Random(i)
            dx += int(round(r.uniform(-k, k)))
            dy += int(round(r.uniform(-k, k)))
    if dx or dy:
        sh = Image.new("RGB", (W, H), INK)
        sh.paste(img, (dx, dy))
        img = sh
    a = np.asarray(img).copy()
    # glitch slices before big scene cuts
    for c in GLITCH:
        if 0 < c - t <= 3.5 / FPS:
            r = random.Random(i * 13)
            for _ in range(7):
                y0 = r.randint(0, H - 20)
                hgt = r.randint(3, 22)
                a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], r.randint(-30, 30), axis=1)
            a[..., 0] = np.roll(a[..., 0], 3, axis=1)
            a[..., 2] = np.roll(a[..., 2], -3, axis=1)
    # flash on cuts
    for c in CUTS:
        if 0 <= t - c < 2 / FPS:
            k = 0.6 if t - c < 1 / FPS else 0.25
            a = (a * (1 - k) + 255 * k).astype(np.uint8)
    base = Image.fromarray(a)
    big = a.repeat(SC, 0).repeat(SC, 1).astype(np.uint16)
    glow = np.asarray(base.filter(ImageFilter.GaussianBlur(2.2)).resize((OW, OH), Image.BILINEAR)).astype(np.uint16)
    out = (big * MASK >> 8) + (glow * 72 >> 8)
    # rolling CRT bar
    yb = int((t * 520) % (OH + 400)) - 200
    out[max(0, yb):max(0, yb + 140)] += 7
    return np.clip(out, 0, 255).astype(np.uint8)


def render(t):
    img = Image.new("RGB", (W, H), BG)
    d = draw(img)
    if t < S2:
        scene1(img, d, t)
    elif t < CUT_2B:
        scene2a(img, d, t)
    elif t < CUT_2C:
        scene2b(img, d, t)
    elif t < S3:
        scene2c(img, d, t)
    elif t < CUT_3B:
        scene3a(img, d, t)
    elif t < S4:
        scene3b(img, d, t)
    elif t < S5:
        scene4(img, d, t)
    elif t < CUT_5B:
        scene5a(img, d, t)
    elif t < RES_1:
        scene5b(img, d, t)
    elif t < S6:
        scene5c(img, d, t)
    else:
        scene6(img, d, t)
    d = draw(img)
    if S2 <= t < S6:
        hud(d, t, 1 + int((t - S2) // 7))
    if S2 <= t < S3:
        caption(d, t, S2 + 0.25, ["ESCANEA MILES", "DE GRÁFICAS"], [WHITE, TGREEN])
    elif S3 <= t < S4:
        caption(d, t, S3 + 0.15, ["DETECTA EL", "SETUP +", "LA NOTICIA"], [WHITE, GOLD, GOLD])
    elif S4 <= t < S5:
        caption(d, t, S4 + 0.15, ["STOP Y TARGET", "ANTES DE", "ENTRAR"], [WHITE, WHITE, TGREEN])
    elif S5 <= t < S6:
        caption(d, t, S5 + 0.15, ["SIMULA EL DÍA", "10,000 VECES"], [WHITE, GOLD])
    return img


def main():
    global MASK
    MASK = make_mask()
    mode = sys.argv[1] if len(sys.argv) > 1 else "video"
    if mode == "stills":
        times = [float(x) for x in sys.argv[2:]]
        for t in times:
            img = render(t)
            out = post(img, t, int(t * FPS))
            Image.fromarray(out).save(f"stills/f_{t:05.2f}.png")
        return
    nframes = int(DURATION * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
         "-i", "-", "-i", "mix.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", "out.mp4"],
        stdin=subprocess.PIPE,
    )
    for i in range(nframes):
        t = i / FPS
        ff.stdin.write(post(render(t), t, i).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("video ok")


if __name__ == "__main__":
    main()
