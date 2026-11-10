"""
Reel pilota: "Il sale fa bollire prima l'acqua?" (falso mito).
Uso: python3 make_reel.py <voce.wav> <cartella_out> [--frames t1,t2,...]
"""
import math
import os
import random
import re
import subprocess
import sys

import cairo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import *  # noqa

SCRIPT = [
    "Il sale fa bollire prima l'acqua della pasta? Falso. Anzi, succede il contrario.",
    "Guarda dentro la pentola. L'acqua è fatta di miliardi di molecole che si tengono strette l'una all'altra.",
    "Quando scaldi, si agitano sempre di più. A cento gradi alcune si staccano e scappano via: è l'ebollizione.",
    "Ora butti il sale. Nell'acqua si divide in due pezzi: sodio e cloro. Questi pezzi si infilano tra le molecole d'acqua e le tengono legate a sé.",
    "Così, per farle scappare, serve un po' più di calore: il punto di ebollizione si alza.",
    "Di quanto? Con dieci grammi per litro, nemmeno due decimi di grado. In pratica, niente.",
    "E allora perché, quando butti il sale, l'acqua frizza? Perché i granelli fanno da appiglio: il vapore pronto a uscire forma le bolle tutte insieme sulla loro superficie.",
    "Morale: il sale non cambia la cottura. Serve solo a dare sapore.",
    "Segui per il prossimo falso mito in cucina.",
]


# =====================================================================
# 1. ALLINEAMENTO PAROLE ↔ AUDIO
# =====================================================================
def detect_silences(wav):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.12", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", wav], capture_output=True, text=True).stdout)
    return list(zip(starts, ends)), dur


def speech_intervals(sil, dur):
    segs, cur = [], 0.0
    for a, b in sil:
        if a > cur:
            segs.append((cur, a))
        cur = b
    if cur < dur:
        segs.append((cur, dur))
    return segs


def speech_map(segs):
    """Funzione: secondi di solo parlato -> tempo reale."""
    total = sum(b - a for a, b in segs)

    def f(s):
        acc = 0.0
        for a, b in segs:
            if s <= acc + (b - a):
                return a + (s - acc)
            acc += b - a
        return segs[-1][1]
    return f, total


def split_sentences(par):
    return [s.strip() for s in re.findall(r"[^.?:]+[.?:]?", par) if s.strip()]


def word_weight(w):
    return len(re.sub(r"[^\wàèéìòù']", "", w)) + 1.5


def align_from_timestamps(wav, al_path):
    """Tempi esatti per parola dai timestamp per carattere restituiti da ElevenLabs."""
    import json
    al = json.load(open(al_path))
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    text = "".join(chars)
    expected = "\n\n".join(SCRIPT)
    assert text == expected, "il testo dei timestamp non coincide con lo script"
    _, dur = detect_silences(wav)
    words, pi, i = [], 0, 0
    par_bounds = []
    pos = 0
    for k, par in enumerate(SCRIPT):
        par_bounds.append((pos, pos + len(par), k))
        pos += len(par) + 2
    for m in re.finditer(r"\S+", text):
        a, b = m.start(), m.end() - 1
        par = next(k for x, y, k in par_bounds if x <= a < y)
        words.append((m.group(), st[a], en[b], par))
    return words, dur


def align(wav):
    al_path = os.path.splitext(wav)[0] + ".align.json"
    if os.path.exists(al_path):
        return align_from_timestamps(wav, al_path)
    sil, dur = detect_silences(wav)
    segs = speech_intervals(sil, dur)
    to_real, total = speech_map(segs)
    long_sil = [(a, b) for a, b in sil if b - a >= 0.22]

    sentences = []  # (par_idx, [words])
    for pi, par in enumerate(SCRIPT):
        for s in split_sentences(par):
            sentences.append((pi, s.split()))
    weights = [sum(word_weight(w) for w in ws) for _, ws in sentences]
    W_tot = sum(weights)

    # Allineamento globale (programmazione dinamica): scelgo per ogni confine di frase
    # una pausa reale, in ordine, minimizzando lo scarto tra durata parlata attesa e reale.
    t0, tend = segs[0][0], segs[-1][1]
    cands = [(a, e) for a, e in sil if e - a >= 0.18 and a > t0 + 0.1 and a < tend - 0.1]
    rate = total / W_tot

    def speech_between(a, b):
        return sum(max(0.0, min(y, b) - max(x, a)) for x, y in segs)

    par_of = [pi for pi, _ in sentences]
    N, M = len(sentences), len(cands)
    INF = float("inf")
    # dp[i][j]: costo migliore con la frase i che termina nella pausa j
    dp = [[INF] * M for _ in range(N)]
    bk = [[-1] * M for _ in range(N)]

    def cost(i, a, b, j=None):
        exp = weights[i] * rate
        got = speech_between(a, b)
        c = (got - exp) ** 2 / max(exp, 0.3)
        if j is not None and i + 1 < N:
            plen = cands[j][1] - cands[j][0]
            # i confini di paragrafo preferiscono pause lunghe
            if par_of[i + 1] != par_of[i]:
                c -= 0.6 * min(plen, 1.0)
            else:
                c -= 0.2 * min(plen, 1.0)
        return c

    for j in range(M):
        dp[0][j] = cost(0, t0, cands[j][0], j)
    for i in range(1, N - 1):
        for j in range(M):
            best, arg = INF, -1
            for k in range(j):
                if dp[i - 1][k] < INF:
                    v = dp[i - 1][k] + cost(i, cands[k][1], cands[j][0], j)
                    if v < best:
                        best, arg = v, k
            dp[i][j], bk[i][j] = best, arg
    best, last = INF, -1
    for k in range(M):
        if dp[N - 2][k] < INF:
            v = dp[N - 2][k] + cost(N - 1, cands[k][1], tend)
            if v < best:
                best, last = v, k
    chosen = [0] * (N - 1)
    j = last
    for i in range(N - 2, -1, -1):
        chosen[i] = j
        j = bk[i][j]
    snapped = [t0] + [cands[j][1] for j in chosen]
    ends = [cands[j][0] for j in chosen] + [tend]

    words = []  # (parola, t0, t1, par_idx)
    for (pi, ws), s0, s1 in zip(sentences, snapped, ends):
        # parlato interno alla frase (togli i silenzi interni)
        inner = [(max(a, s0), min(b, s1)) for a, b in segs if b > s0 and a < s1]
        f, tot = speech_map(inner) if inner else ((lambda x: s0 + x), s1 - s0)
        wts = [word_weight(w) for w in ws]
        tw = sum(wts)
        c = 0.0
        for w, wt in zip(ws, wts):
            a = f(tot * c / tw)
            c += wt
            b = f(tot * c / tw)
            words.append((w, a, b, pi))
    return words, dur


def clean(w):
    return re.sub(r"[.,:;!]", "", w)


def make_chunks(words):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(clean(x[0]) for x in cur)
        if len(cur) >= 3 or len(txt) >= 15 or re.search(r"[.,?:]$", w[0]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


# =====================================================================
# 2. SCENE
# =====================================================================
LENS = (540, 860, 380)


class Ctx:
    def __init__(self, words, dur):
        self.words = words
        self.dur = dur
        self.par_start = {}
        for w, a, b, pi in words:
            self.par_start.setdefault(pi, a)

    def wt(self, needle, par=None, nth=0):
        """Tempo d'inizio della parola che contiene `needle` (nel paragrafo dato)."""
        k = 0
        for w, a, b, pi in self.words:
            if (par is None or pi == par) and needle.lower() in w.lower():
                if k == nth:
                    return a
                k += 1
        raise KeyError(needle)


def molecule_field(seed, spacing=100, surface=None):
    cx, cy, r = LENS
    rnd = random.Random(seed)
    pts = []
    y = cy - r - spacing
    row = 0
    while y < cy + r + spacing:
        x = cx - r - spacing + (spacing / 2 if row % 2 else 0)
        while x < cx + r + spacing:
            px, py = x + rnd.uniform(-14, 14), y + rnd.uniform(-14, 14)
            if surface is None or py > surface + 45:
                pts.append({"x": px, "y": py, "ph": rnd.uniform(0, 6.28),
                            "ang": rnd.uniform(-0.6, 0.6), "sp": rnd.uniform(0.8, 1.3)})
            x += spacing
        y += spacing * 0.87
        row += 1
    return pts


def jiggle(m, t, amp):
    return (m["x"] + amp * math.sin(t * 7 * m["sp"] + m["ph"]),
            m["y"] + amp * math.cos(t * 6 * m["sp"] + m["ph"] * 1.3),
            m["ang"] + amp * 0.02 * math.sin(t * 5 + m["ph"]))


def lens_begin(cr, t_in, t, grow_from=None):
    """Clip circolare della lente con apertura animata. Ritorna la scala d'apertura."""
    cx, cy, r = LENS
    p = ease(prog(t, t_in, t_in + 0.45))
    rr = lerp(40, r, p)
    if grow_from:
        gx, gy = grow_from
        cxx, cyy = lerp(gx, cx, p), lerp(gy, cy, p)
    else:
        cxx, cyy = cx, cy
    cr.save()
    cr.arc(cxx, cyy, rr, 0, 2 * math.pi)
    cr.clip()
    return cxx, cyy, rr


def lens_end(cr, cxx, cyy, rr):
    cr.restore()
    lens_frame(cr, cxx, cyy, rr)


def draw_bonds(cr, pos, alpha):
    if alpha <= 0:
        return
    cr.set_source_rgba(1, 1, 1, 0.55 * alpha)
    cr.set_line_width(4)
    cr.set_dash([10, 9])
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            dx, dy = pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]
            if dx * dx + dy * dy < 118 * 118:
                cr.move_to(pos[i][0], pos[i][1])
                cr.line_to(pos[j][0], pos[j][1])
    cr.stroke()
    cr.set_dash([])


def water_bg(cr, surface=None, t=0.0):
    cx, cy, r = LENS
    g = cairo.LinearGradient(0, cy - r, 0, cy + r)
    g.add_color_stop_rgb(0, 0.55, 0.80, 0.96)
    g.add_color_stop_rgb(1, 0.33, 0.62, 0.88)
    if surface is None:
        cr.set_source(g)
        cr.paint()
        return
    cr.set_source_rgb(0.86, 0.91, 0.96)  # aria / vapore
    cr.paint()
    cr.move_to(cx - r - 20, cy + r + 20)
    for i in range(41):
        xx = lerp(cx - r - 20, cx + r + 20, i / 40)
        cr.line_to(xx, surface + 8 * math.sin(xx * 0.025 + t * 3))
    cr.line_to(cx + r + 20, cy + r + 20)
    cr.close_path()
    cr.set_source(g)
    cr.fill()


def shaker(cr, x, y, angle):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    rounded_rect(cr, -55, -80, 110, 150, 30)
    cr.set_source_rgb(0.95, 0.96, 0.98)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(6)
    cr.stroke()
    rounded_rect(cr, -58, -120, 116, 52, 16)
    cr.set_source_rgb(*STEEL)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.stroke()
    for hx in (-25, 0, 25):
        circle(cr, hx, -120, 6, INK, lw=0)
    outlined_text(cr, "SALE", 0, 12, 36, fill=INK, lw=0)
    cr.restore()


# ---------- scena 0: gancio ----------
def scene_hook(cr, t, c):
    s = 0.0
    background(cr)
    stove(cr, 540, 1255, 620)
    flames(cr, 540, 1255, 380, t)
    ix0, ix1, surf, bot = pot(cr, 540, 840, 560, 380, 0.72, t)
    # spargisale che versa
    ang = lerp(0.0, -2.3, ease(prog(t, 0.3, 0.9)))
    shaker(cr, 760, 660, ang)
    rnd = random.Random(3)
    if t > 0.8:
        for i in range(26):
            st = 0.8 + i * 0.09
            k = t - st
            if k < 0:
                continue
            gx = 760 + (-89) + rnd.uniform(-18, 18) - k * 40
            gy = 660 + (80) + 900 * k * k
            if gy < surf:
                salt_grain(cr, gx, gy, 16, angle=k * 4)
    title(cr, ["IL SALE FA BOLLIRE", "PRIMA L'ACQUA?"], t, 0.0, y=250, size=92)
    tf = c.wt("Falso", 0)
    stamp(cr, "FALSO MITO", 540, 620, t, tf, size=104)


# ---------- scena 1: dentro la pentola ----------
FIELD1 = molecule_field(11)


def scene_inside(cr, t, c):
    s = c.par_start[1] - 0.15
    background(cr)
    title(cr, ["DENTRO", "LA PENTOLA"], t, s)
    cxx, cyy, rr = lens_begin(cr, s, t, grow_from=(540, 1100))
    water_bg(cr)
    amp = 6
    pos = [jiggle(m, t, amp) for m in FIELD1]
    draw_bonds(cr, pos, ease(prog(t, c.wt("strette", 1) - 0.2, c.wt("strette", 1) + 0.4)))
    pop = ease_out_back(prog(t, c.wt("molecole", 1) - 0.3, c.wt("molecole", 1) + 0.2))
    for x, y, a in pos:
        if pop > 0:
            water_molecule(cr, x, y, scale=0.95 * pop, angle=a)
    lens_end(cr, cxx, cyy, rr)
    label(cr, "H2O", 540, 1250, t, c.wt("molecole", 1), size=60, bg=O_RED)


# ---------- scena 2: riscaldamento ----------
SURF = LENS[1] - 170
FIELD2 = molecule_field(23, surface=SURF)


def escaping(field, n_seed, count):
    rnd = random.Random(n_seed)
    top = sorted(range(len(field)), key=lambda i: field[i]["y"])[:12]
    return rnd.sample(top, count)


ESC2 = escaping(FIELD2, 5, 5)


def scene_heat(cr, t, c):
    s = c.par_start[2] - 0.15
    background(cr)
    title(cr, ["COSA SUCCEDE", "A 100 °C"], t, s)
    cxx, cyy, rr = lens_begin(cr, s - 0.5, t)
    water_bg(cr, SURF, t)
    t100 = c.wt("cento", 2)
    tesc = c.wt("staccano", 2)
    heat = prog(t, s, t100 + 0.3)
    amp = lerp(6, 22, heat)
    for i, m in enumerate(FIELD2):
        x, y, a = jiggle(m, t, amp)
        if i in ESC2:
            k = prog(t, tesc + ESC2.index(i) * 0.25, tesc + ESC2.index(i) * 0.25 + 1.4)
            y -= ease(k) * 420
            x += math.sin(k * 6 + i) * 30 * k
            if k > 0:
                cr.set_source_rgba(1, 1, 1, 0.7 * (1 - k))
                cr.set_line_width(4)
                cr.move_to(x, y + 45)
                cr.line_to(x, y + 95)
                cr.stroke()
        water_molecule(cr, x, y, 0.95, a)
    lens_end(cr, cxx, cyy, rr)
    temp = int(lerp(20, 100, ease(heat)))
    thermo_pill(cr, 540, 1270, f"{temp} °C", t, s, hot=heat)
    label(cr, "EBOLLIZIONE", 540, 1105 - 520, t, c.wt("ebollizione", 2), size=56, bg=RED)


# ---------- scena 3/4: sale ----------
FIELD3 = molecule_field(37, surface=SURF)
NA_POS = (430, 930)
CL_POS = (660, 1000)


def free_spot(field, spots, rad=75):
    return [m for m in field if all((m["x"] - sx) ** 2 + (m["y"] - sy) ** 2 > rad * rad for sx, sy in spots)]


FIELD3 = free_spot(FIELD3, [NA_POS, CL_POS])


def shells(field):
    """Per ogni ione sceglie le molecole vicine e calcola posizione/orientamento finale."""
    plan = {}
    for (ix, iy), kind, rad, n in ((NA_POS, "na", 82, 5), (CL_POS, "cl", 96, 6)):
        near = sorted(range(len(field)), key=lambda i: (field[i]["x"] - ix) ** 2 + (field[i]["y"] - iy) ** 2)
        near = [i for i in near if i not in plan][:n]
        for k, i in enumerate(near):
            ang = math.atan2(field[i]["y"] - iy, field[i]["x"] - ix)
            ang = ang * 0.3 + (k * 2 * math.pi / n) * 0.7
            tx, ty = ix + rad * math.cos(ang), iy + rad * math.sin(ang)
            d = math.atan2(iy - ty, ix - tx)  # direzione molecola -> ione
            rot = (d + math.pi - math.pi / 2) if kind == "na" else (d - math.pi / 2)
            plan[i] = (tx, ty, rot)
    return plan


SHELL = shells(FIELD3)


def ions_and_water(cr, t, c, hyd, split, amp):
    # molecole
    for i, m in enumerate(FIELD3):
        x, y, a = jiggle(m, t, amp)
        if i in SHELL and hyd > 0:
            tx, ty, rot = SHELL[i]
            jx, jy = 4 * math.sin(t * 8 + i), 4 * math.cos(t * 7 + i)
            x, y = lerp(x, tx + jx, hyd), lerp(y, ty + jy, hyd)
            da = (rot - a + math.pi) % (2 * math.pi) - math.pi
            a = a + da * hyd
        water_molecule(cr, x, y, 0.95, a)
    return


def crystal(cr, t, c, s):
    """Cristallo NaCl che cade e poi si separa negli ioni."""
    tsplit = c.wt("divide", 3)
    fall = ease(prog(t, s + 0.2, s + 1.4))
    cx0, cy0 = 545, lerp(LENS[1] - 360, 960, fall)
    sp = ease(prog(t, tsplit, tsplit + 0.8))
    base = [((-1, -1), "na"), ((1, -1), "cl"), ((-1, 1), "cl"), ((1, 1), "na")]
    targets = {0: NA_POS, 3: (NA_POS[0] - 210, NA_POS[1] + 170), 1: CL_POS, 2: (CL_POS[0] - 60, CL_POS[1] - 290)}
    return cx0, cy0, sp, base, targets


EXTRA_NA = (NA_POS[0] - 210, NA_POS[1] + 170)
EXTRA_CL = (CL_POS[0] - 60, CL_POS[1] - 290)


def scene_salt(cr, t, c):
    s = c.par_start[3] - 0.15
    background(cr)
    title(cr, ["ENTRA", "IL SALE"], t, s)
    cxx, cyy, rr = lens_begin(cr, s - 0.5, t)
    water_bg(cr, SURF, t)
    thyd = c.wt("infilano", 3)
    hyd = ease(prog(t, thyd, thyd + 1.6))
    ions_and_water(cr, t, c, hyd, 0, 12)
    cx0, cy0, sp, base, targets = crystal(cr, t, c, s)
    for k, ((gx, gy), kind) in enumerate(base):
        x0, y0 = cx0 + gx * 30, cy0 + gy * 30
        tx, ty = targets[k] if k in (0, 1) else (EXTRA_NA if kind == "na" else EXTRA_CL)
        # per non affollare: il 2° sodio e il 2° cloro escono dalla lente
        if k in (2, 3):
            tx, ty = (LENS[0] + (380 if kind == "cl" else -380) * 1.3, LENS[1] + 300)
        x, y = lerp(x0, tx, sp), lerp(y0, ty, sp)
        ion(cr, x, y, kind, scale=1.4)
    lens_end(cr, cxx, cyy, rr)
    label(cr, "SODIO  Na+", 300, 1250, t, c.wt("sodio", 3), size=52, bg=NA_COL)
    label(cr, "CLORO  Cl-", 780, 1250, t, c.wt("cloro", 3), size=52, bg=CL_COL)


def scene_more_heat(cr, t, c):
    s = c.par_start[4] - 0.15
    background(cr)
    title(cr, ["SERVE PIÙ", "CALORE"], t, s)
    cxx, cyy, rr = lens_begin(cr, s - 1.0, t)
    water_bg(cr, SURF, t)
    ions_and_water(cr, t, c, 1.0, 0, 14)
    ion(cr, *NA_POS, "na", scale=1.4)
    ion(cr, *CL_POS, "cl", scale=1.4)
    # tentativi di fuga che falliscono: due molecole d'acqua del guscio provano a salire
    for j, i in enumerate(sorted(SHELL, key=lambda i: SHELL[i][1])[:2]):
        pass
    tesc = c.wt("scappare", 4)
    for j in range(3):
        k = prog(t, tesc + j * 0.5, tesc + j * 0.5 + 1.2)
        if 0 < k < 1:
            hop = math.sin(k * math.pi) * 110
            x = 420 + j * 120
            y = SURF + 60 - hop
            water_molecule(cr, x, y, 0.95, 0.3 * math.sin(k * 9))
    lens_end(cr, cxx, cyy, rr)
    talza = c.wt("alza", 4)
    thermo_pill(cr, 540, 1270, "100 °C", t, s, hot=0.9)
    # freccia su
    p = ease_out_back(prog(t, talza, talza + 0.35))
    if p > 0:
        cr.save()
        cr.translate(800, 1270)
        cr.scale(p, p)
        cr.move_to(0, -70)
        cr.line_to(48, -5)
        cr.line_to(18, -5)
        cr.line_to(18, 55)
        cr.line_to(-18, 55)
        cr.line_to(-18, -5)
        cr.line_to(-48, -5)
        cr.close_path()
        cr.set_source_rgb(*RED)
        cr.fill_preserve()
        cr.set_source_rgb(*INK)
        cr.set_line_width(6)
        cr.stroke()
        cr.restore()


# ---------- scena 5: numeri ----------
def scene_numbers(cr, t, c):
    s = c.par_start[5] - 0.15
    background(cr)
    title(cr, ["DI QUANTO?"], t, s, y=270, size=110)
    # card 10 g / litro
    tdieci = c.wt("dieci", 5)
    p = ease_out_back(prog(t, tdieci, tdieci + 0.4))
    if p > 0:
        cr.save()
        cr.translate(540, 560)
        cr.scale(p, p)
        rounded_rect(cr, -400, -110, 800, 220, 40)
        cr.set_source_rgb(*WHITE)
        cr.fill_preserve()
        cr.set_source_rgb(*INK)
        cr.set_line_width(7)
        cr.stroke()
        # mucchietto di sale
        rnd = random.Random(2)
        for i in range(22):
            salt_grain(cr, -280 + rnd.uniform(-60, 60), 40 - rnd.uniform(0, 60) * (1 - abs(rnd.uniform(-1, 1))),
                       18, angle=rnd.uniform(0, 1))
        outlined_text(cr, "10 g", -100, 30, 92, fill=INK, lw=0, anchor="left")
        outlined_text(cr, "/ litro", 120, 30, 62, fill=STEEL_DARK, lw=0, anchor="left")
        cr.restore()
    tdec = c.wt("decimi", 5)
    p2 = ease_out_back(prog(t, tdec - 0.4, tdec))
    if p2 > 0:
        cr.save()
        cr.translate(540, 900)
        cr.scale(p2, p2)
        outlined_text(cr, "+0,18 °C", 0, 0, 190, fill=YELLOW, lw=18)
        cr.restore()
        # barra 0-100 °C con il pezzettino in più
        bx0, bx1, by = 140, 940, 1080
        rounded_rect(cr, bx0, by, bx1 - bx0, 60, 30)
        cr.set_source_rgb(*WHITE)
        cr.fill_preserve()
        cr.set_source_rgb(*INK)
        cr.set_line_width(6)
        cr.stroke()
        fill = ease(prog(t, tdec, tdec + 1.0))
        fx = lerp(bx0 + 8, bx1 - 14, fill)
        rounded_rect(cr, bx0 + 8, by + 8, fx - bx0 - 8, 44, 22)
        cr.set_source_rgb(*WATER_DEEP)
        cr.fill()
        if fill >= 1:
            cr.rectangle(bx1 - 14, by + 6, 3, 48)
            cr.set_source_rgb(*RED)
            cr.fill()
        outlined_text(cr, "0 °C", bx0, by + 120, 44, fill=WHITE, lw=8, anchor="left")
        outlined_text(cr, "100 °C", bx1, by + 120, 44, fill=WHITE, lw=8, anchor="right")
    tn = c.wt("niente", 5)
    label(cr, "IN PRATICA: NIENTE", 540, 1290, t, tn - 0.2, size=60, bg=RED)


# ---------- scena 6: perché frizza ----------
def bubble(cr, x, y, r, alpha=1.0):
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.set_source_rgba(0.85, 0.95, 1.0, 0.55 * alpha)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.set_line_width(3)
    cr.stroke()


def scene_fizz(cr, t, c):
    s = c.par_start[6] - 0.15
    tapp = c.wt("appiglio", 6)
    background(cr)
    title(cr, ["PERCHÉ", "FRIZZA?"], t, s)
    if t < tapp - 0.3:
        stove(cr, 540, 1255, 620)
        flames(cr, 540, 1255, 380, t)
        ix0, ix1, surf, bot = pot(cr, 540, 760, 600, 460, 0.7, t)
        shaker(cr, 760, 600, -2.3)
        rnd = random.Random(9)
        tfz = c.wt("frizza", 6)
        cr.save()
        rounded_rect(cr, ix0, surf - 20, ix1 - ix0, bot - surf + 20, 18)
        cr.clip()
        for i in range(40):
            st = s + 0.2 + i * 0.06
            k = t - st
            if k < 0:
                continue
            gx = 760 + (-89) + rnd.uniform(-25, 25) - k * 30
            gy = 600 + (80) + 700 * k * k
            if gy > surf:
                gy = surf + min((gy - surf) * 0.25, bot - surf - 20)
            salt_grain(cr, gx, gy, 14, angle=k * 3)
            # bolle che nascono sul granello
            if t > tfz - 0.3 and gy > surf:
                for b in range(3):
                    bk = ((t * 1.3 + b * 0.33 + i * 0.17) % 1.0)
                    by = gy - bk * (gy - surf)
                    bubble(cr, gx + math.sin(bk * 8 + i) * 8, by, 6 + 8 * bk, 1 - bk * 0.6)
        cr.restore()
    else:
        # primo piano del granello
        cxx, cyy, rr = lens_begin(cr, tapp - 0.3, t)
        water_bg(cr)
        gx, gy = 540, 940
        cr.save()
        cr.translate(gx, gy)
        cr.rotate(0.25)
        salt_grain(cr, 0, 0, 230)
        cr.restore()
        rnd = random.Random(4)
        sites = [(rnd.uniform(-110, 110), rnd.uniform(-110, 110)) for _ in range(14)]
        for i, (sx, sy) in enumerate(sites):
            ph = (t * 0.6 + i * 0.137) % 1.0
            grow = clamp(ph / 0.45)
            if ph < 0.45:
                bubble(cr, gx + sx * 1.05, gy + sy * 1.05 - 10 * grow, 8 + 26 * grow)
            else:
                k = (ph - 0.45) / 0.55
                bubble(cr, gx + sx + math.sin(k * 7 + i) * 15, gy + sy - 10 - k * 520, 34 + 6 * k, 1 - k * 0.5)
        lens_end(cr, cxx, cyy, rr)
        label(cr, "APPIGLIO PER LE BOLLE", 540, 1270, t, tapp + 0.2, size=50, bg=RED)


# ---------- scena 7: morale ----------
def check_card(cr, x, y, text, ok, t, t0):
    p = ease_out_back(prog(t, t0, t0 + 0.4))
    if p <= 0:
        return
    cr.save()
    cr.translate(x, y)
    cr.scale(p, p)
    rounded_rect(cr, -380, -85, 760, 170, 40)
    cr.set_source_rgb(*WHITE)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(7)
    cr.stroke()
    outlined_text(cr, text, -320, 30, 84, fill=INK, lw=0, anchor="left")
    col = (0.2, 0.75, 0.35) if ok else RED
    circle(cr, 270, 0, 58, col, lw=6)
    cr.set_source_rgb(*WHITE)
    cr.set_line_width(16)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    if ok:
        cr.move_to(240, 2)
        cr.line_to(262, 26)
        cr.line_to(302, -22)
    else:
        cr.move_to(246, -24)
        cr.line_to(294, 24)
        cr.move_to(294, -24)
        cr.line_to(246, 24)
    cr.stroke()
    cr.set_line_cap(cairo.LINE_CAP_BUTT)
    cr.restore()


def scene_moral(cr, t, c):
    s = c.par_start[7] - 0.15
    background(cr)
    title(cr, ["A COSA SERVE", "DAVVERO"], t, s)
    stove(cr, 540, 1255, 560)
    flames(cr, 540, 1255, 340, t)
    ix0, ix1, surf, bot = pot(cr, 540, 900, 500, 320, 0.72, t)
    cr.save()
    rounded_rect(cr, ix0, surf, ix1 - ix0, bot - surf, 18)
    cr.clip()
    rnd = random.Random(8)
    cr.set_source_rgb(0.98, 0.84, 0.42)
    cr.set_line_width(9)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(14):
        x0 = rnd.uniform(ix0 + 20, ix1 - 20)
        a = rnd.uniform(-0.5, 0.5) + 0.05 * math.sin(t * 3 + i)
        cr.move_to(x0, bot - 15)
        cr.line_to(x0 + 300 * math.sin(a), bot - 15 - 300 * math.cos(a))
        cr.stroke()
    cr.restore()
    cr.set_line_cap(cairo.LINE_CAP_BUTT)
    # spaghetti che escono dalla pentola
    for i in range(8):
        x0 = 420 + i * 30
        cr.move_to(x0, surf + 20)
        cr.line_to(x0 + 60 + i * 8, 760 - i * 6)
    cr.set_source_rgb(0.98, 0.84, 0.42)
    cr.set_line_width(9)
    cr.stroke()
    check_card(cr, 540, 530, "COTTURA", False, t, c.wt("cottura", 7) - 0.2)
    check_card(cr, 540, 730, "SAPORE", True, t, c.wt("sapore", 7) - 0.2)


# ---------- scena 8: chiusura ----------
def scene_end(cr, t, c):
    s = c.par_start[8] - 0.15
    background(cr)
    p = ease_out_back(prog(t, s, s + 0.4))
    cr.save()
    cr.translate(540, 560)
    cr.scale(p, p)
    outlined_text(cr, "IL PROSSIMO", 0, 0, 100, fill=WHITE, lw=14)
    cr.restore()
    stamp(cr, "FALSO MITO", 540, 760, t, s + 0.4, size=120)
    tg = c.wt("Segui", 8)
    handle = "@unmillimetrosotto"
    pb = ease_out_back(prog(t, tg + 0.5, tg + 0.85))
    if pb > 0:
        press = 1 - 0.08 * math.sin(clamp((t - tg - 1.4) / 0.25) * math.pi)
        cr.save()
        cr.translate(540, 1060)
        cr.scale(pb * press, pb * press)
        ext = text_extents(cr, handle, 54)
        w = ext.x_advance + 250
        rounded_rect(cr, -w / 2, -75, w, 150, 75)
        cr.set_source_rgb(*WHITE)
        cr.fill_preserve()
        cr.set_source_rgb(*INK)
        cr.set_line_width(7)
        cr.stroke()
        outlined_text(cr, handle, -w / 2 + 42, 19, 54, fill=INK, lw=0, anchor="left")
        bx = w / 2 - 105
        rounded_rect(cr, bx - 75, -48, 150, 96, 48)
        cr.set_source_rgb(0.25, 0.4, 0.98)
        cr.fill()
        outlined_text(cr, "SEGUI", bx, 18, 40, fill=WHITE, lw=0)
        cr.restore()


SCENES = [scene_hook, scene_inside, scene_heat, scene_salt, scene_more_heat,
          scene_numbers, scene_fizz, scene_moral, scene_end]


# =====================================================================
# 3. RENDER
# =====================================================================
def scene_bounds(c):
    starts = [0.0] + [c.par_start[i] - 0.15 for i in range(1, len(SCRIPT))]
    ends = starts[1:] + [c.dur + 0.8]
    # arrotonda ai frame
    fr = lambda x: round(x * FPS) / FPS
    return [(fr(a), fr(b)) for a, b in zip(starts, ends)]


def draw_frame(idx, t, c, chunks):
    surf, cr = new_surface()
    cr.save()
    cr.translate(0, 60)
    SCENES[idx](cr, t, c)
    cr.restore()
    for ch in chunks:
        a, b = ch[0][1], ch[-1][2]
        if a - 0.05 <= t < b + 0.15:
            caption(cr, [(clean(w), wa, wb) for w, wa, wb, _ in ch], None, t, y=1540)
            break
    return surf


def render(wav, out):
    os.makedirs(out, exist_ok=True)
    words, dur = align(wav)
    c = Ctx(words, dur)
    chunks = make_chunks(words)
    bounds = scene_bounds(c)
    parts = []
    for i, (a, b) in enumerate(bounds):
        n = int(round((b - a) * FPS))
        tmp = os.path.join(out, f"scena_{i:02d}.tmp.mp4")
        fin = os.path.join(out, f"scena_{i:02d}.mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                              "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                              "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                              "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
        for f in range(n):
            t = a + f / FPS
            surf = draw_frame(i, t, c, chunks)
            p.stdin.write(bytes(surf.get_data()))
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError(f"scena {i} fallita")
        os.replace(tmp, fin)
        parts.append(fin)
        print(f"scena {i}: {a:.2f}-{b:.2f}s", flush=True)
    lst = os.path.join(out, "lista.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(x)}'\n" for x in parts)
    silent = os.path.join(out, "muto.mp4")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", silent], check=True)
    final = os.path.join(out, os.environ.get("REEL_NAME", "reel_pilota_sale") + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", silent, "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", "apad", "-shortest", "-movflags", "+faststart", final], check=True)
    return final


def stills(wav, out, times):
    os.makedirs(out, exist_ok=True)
    words, dur = align(wav)
    c = Ctx(words, dur)
    chunks = make_chunks(words)
    bounds = scene_bounds(c)
    for t in times:
        idx = max(i for i, (a, b) in enumerate(bounds) if a <= t)
        draw_frame(idx, t, c, chunks).write_to_png(os.path.join(out, f"frame_{t:05.1f}.png"))
    for w, a, b, pi in words:
        print(f"{a:6.2f} {b:6.2f} p{pi} {w}")


if __name__ == "__main__":
    wav, out = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3] == "--frames":
        stills(wav, out, [float(x) for x in sys.argv[4].split(",")])
    else:
        print(render(wav, out))
