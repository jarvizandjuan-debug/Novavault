"""Shared timing for audio + video. Everything is locked to a 137.14 BPM grid
so that each 7-second scene is exactly four bars."""

FPS = 30
DURATION = 35.0
BEAT = 0.4375
T0 = -0.0625  # beat 7 lands exactly on 3.0 s


def tb(b):
    """Time (s) of beat index b."""
    return T0 + BEAT * b


# Scene boundaries (s)
S1, S2, S3, S4, S5, S6, END = 0.0, 3.0, 10.0, 17.0, 24.0, 31.0, 35.0

# Sub-cuts inside scenes
CUT_2B = tb(13)    # 5.625  trader room -> Claude Code scan grid
CUT_2C = tb(17)    # 7.375  dense mega-grid
CUT_3B = tb(27)    # 11.75  big chart
POPUP = tb(28)     # 12.1875 news popup
JUMP = tb(31)      # 13.5   news candle
POPUP_OUT = tb(33) # 14.375
STOP_FILL = 17.79  # synced to VO "stop"
TGT_FILL = 18.32   # synced to VO "target"
RR_BADGE = tb(44)  # 19.1875
COUNT = [tb(45), tb(47), tb(49)]  # 3, 2, 1
GO = tb(51)        # 22.25 entry
CUT_5B = tb(59)    # 25.75  vortex over the chart
RES_1 = tb(65)     # 28.375 counter lands + TARGET %
RES_2 = tb(66)     # 28.8125 STOP %
STAMP = S6
COMENTA = 32.46
TRADE = 32.90
MANDO = 33.46
FINAL_HIT = tb(79) # 34.5

# Voice-over segments: (file, src_start, src_end, dst_start)
VO = [
    ("vo/vo_main.mp3", 0.04, 2.48, 0.14),    # Claude Code acaba de destruir el day trading.
    ("vo/vo_main.mp3", 3.12, 7.22, 3.06),    # Once skills convierten a Claude ... escanea gráficas,
    ("vo/vo_main.mp3", 7.36, 8.56, 11.66),   # sigue las noticias,
    ("vo/vo_main.mp3", 8.69, 10.78, 17.39),  # pone tu stop y tu target antes de entrar,
    ("vo/vo_main.mp3", 10.95, 14.07, 24.39), # y simula el día diez mil veces ...
    ("vo/vo_cta.mp3", 0.04, 1.21, 31.00),    # Todo en paper trading.
    ("vo/vo_cta.mp3", 1.88, 3.93, 32.40),    # Comenta TRADE, y te mando el link.
]

# Scene 1 typing schedule
CMD = "> claude --skills day-trading"
HEAD = ["CLAUDE CODE", "DESTRUYÓ EL", "DAY TRADING"]
GOLD_LINES = ["11 SKILLS"]
CMD_T = (0.00, 0.30)
HEAD_T = (0.32, 1.58)
GOLD_T = (1.70, 2.00)


def typed_chars(t, span, n):
    a, b = span
    if t <= a:
        return 0
    return min(n, int((t - a) / (b - a) * n) + 1)


def char_times(span, n):
    a, b = span
    return [a + (b - a) * i / n for i in range(n)]
