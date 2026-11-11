"""
Motore di disegno per reel 2D verticali (1080x1920, 30 fps).
Primitive riutilizzabili: sfondo, titoli, sottotitoli parola-per-parola,
pentola in sezione, molecole d'acqua, ioni, timbro "FALSO MITO".
"""
import math
import random
import cairo

W, H, FPS = 1080, 1920, 30

# ---------- palette del brand ----------
BG_TOP = (0.078, 0.129, 0.239)      # #14213D
BG_BOT = (0.122, 0.231, 0.361)      # #1F3B5C
YELLOW = (1.0, 0.788, 0.235)        # #FFC93C
RED = (0.902, 0.224, 0.275)         # #E63946
WHITE = (1, 1, 1)
INK = (0.06, 0.07, 0.10)
WATER = (0.31, 0.64, 0.88)
WATER_DEEP = (0.18, 0.47, 0.75)
STEEL = (0.62, 0.67, 0.72)
STEEL_DARK = (0.38, 0.42, 0.47)
O_RED = (0.91, 0.30, 0.31)
NA_COL = (0.58, 0.40, 0.92)
CL_COL = (0.30, 0.80, 0.45)
FONT = "Poppins"


def set_theme(theme):
    """Sostituisce la palette globale con quella del tema (valori esadecimali)."""
    g = globals()
    for k, v in theme.get("colors", {}).items():
        v = v.lstrip("#")
        g[k] = tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
    if "font" in theme:
        g["FONT"] = theme["font"]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, b):
    """Progresso lineare 0..1 di t nell'intervallo [a, b]."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x, s=1.7):
    x = clamp(x)
    x -= 1
    return 1 + x * x * ((s + 1) * x + s)


def lerp(a, b, x):
    return a + (b - a) * x


# ---------- primitive ----------
def new_surface():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    return surf, cairo.Context(surf)


def background(cr):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *globals()['BG_TOP'])
    g.add_color_stop_rgb(1, *globals()['BG_BOT'])
    cr.set_source(g)
    cr.paint()
    # piano di lavoro (bancone) sotto la scena
    cr.rectangle(0, 1385, W, H - 1385)
    cr.set_source_rgba(0, 0, 0, 0.18)
    cr.fill()
    cr.rectangle(0, 1385, W, 10)
    cr.set_source_rgba(1, 1, 1, 0.08)
    cr.fill()
    # puntini decorativi leggeri
    rnd = random.Random(7)
    cr.set_source_rgba(1, 1, 1, 0.04)
    for _ in range(60):
        cr.arc(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(3, 9), 0, 2 * math.pi)
        cr.fill()


def rounded_rect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def circle(cr, x, y, r, fill, stroke=INK, lw=4, alpha=1.0):
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.set_source_rgba(*fill, alpha)
    if stroke is not None and lw > 0:
        cr.fill_preserve()
        cr.set_source_rgba(*stroke, alpha)
        cr.set_line_width(lw)
        cr.stroke()
    else:
        cr.fill()


def text_extents(cr, s, size, weight=cairo.FONT_WEIGHT_BOLD):
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, weight)
    cr.set_font_size(size)
    return cr.text_extents(s)


def outlined_text(cr, s, x, y, size, fill=WHITE, stroke=INK, lw=12, anchor="center", alpha=1.0):
    """Testo con contorno spesso. y = linea di base."""
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    ext = cr.text_extents(s)
    if anchor == "center":
        x0 = x - (ext.x_advance) / 2
    elif anchor == "right":
        x0 = x - ext.x_advance
    else:
        x0 = x
    cr.move_to(x0, y)
    cr.text_path(s)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if lw > 0:
        cr.set_source_rgba(*stroke, alpha)
        cr.set_line_width(lw)
        cr.stroke_preserve()
    cr.set_source_rgba(*fill, alpha)
    cr.fill()
    cr.new_path()
    return ext.x_advance


def title(cr, lines, t, t0=0.0, y=210, size=96, highlight_last=True):
    """Titolo in alto: righe bianche, ultima gialla. Entrata a scatto."""
    for i, line in enumerate(lines):
        p = ease_out_back(prog(t, t0 + i * 0.08, t0 + i * 0.08 + 0.35))
        if p <= 0:
            continue
        cr.save()
        yy = y + i * size * 1.08
        cr.translate(W / 2, yy)
        cr.scale(p, p)
        col = YELLOW if (highlight_last and i == len(lines) - 1 and len(lines) > 1) else WHITE
        outlined_text(cr, line, 0, 0, size, fill=col, lw=14)
        cr.restore()


def stamp(cr, text, x, y, t, t0, size=110, angle=-0.18, color=None):
    """Timbro rosso che 'sbatte' sullo schermo."""
    p = prog(t, t0, t0 + 0.28)
    if p <= 0:
        return
    sc = lerp(2.4, 1.0, ease(p))
    a = clamp(p * 1.6)
    ext = text_extents(cr, text, size)
    w, h = ext.x_advance + 70, size * 1.35
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(sc, sc)
    rounded_rect(cr, -w / 2, -h / 2, w, h, 26)
    cr.set_source_rgba(*(color or globals()['RED']), 0.95 * a)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, a)
    cr.set_line_width(10)
    cr.stroke()
    outlined_text(cr, text, 0, size * 0.36, size, fill=WHITE, lw=0, alpha=a)
    cr.restore()


def label(cr, text, x, y, t, t0, size=64, bg=RED, fg=WHITE):
    """Etichetta a pillola che compare con rimbalzo."""
    p = ease_out_back(prog(t, t0, t0 + 0.35))
    if p <= 0:
        return
    ext = text_extents(cr, text, size)
    w, h = ext.x_advance + 60, size * 1.45
    cr.save()
    cr.translate(x, y)
    cr.scale(p, p)
    rounded_rect(cr, -w / 2, -h / 2, w, h, h / 2)
    cr.set_source_rgb(*bg)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(6)
    cr.stroke()
    outlined_text(cr, text, 0, size * 0.36, size, fill=fg, lw=0)
    cr.restore()


# ---------- sottotitoli ----------
def caption(cr, chunk, words_t, t, y=1400, size=80):
    """
    chunk: lista di (parola, t_inizio, t_fine) del gruppo corrente.
    La parola pronunciata in quel momento è gialla.
    """
    if not chunk:
        return
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    space = cr.text_extents(" ").x_advance
    widths = [cr.text_extents(w.upper()).x_advance for w, _, _ in chunk]
    total = sum(widths) + space * (len(chunk) - 1)
    x = W / 2 - total / 2
    start = chunk[0][1]
    pop = ease_out_back(prog(t, start - 0.02, start + 0.15), 2.2)
    cr.save()
    cr.translate(W / 2, y)
    cr.scale(lerp(0.85, 1.0, pop), lerp(0.85, 1.0, pop))
    cr.translate(-W / 2, -y)
    for (w, a, b), ww in zip(chunk, widths):
        active = a <= t < b
        col = YELLOW if active else WHITE
        outlined_text(cr, w.upper(), x, y, size, fill=col, lw=14, anchor="left")
        x += ww + space
    cr.restore()


# ---------- oggetti ----------
def flames(cr, cx, y, w, t, intensity=1.0):
    n = 7
    for i in range(n):
        fx = cx - w / 2 + (i + 0.5) * w / n
        hgt = (55 + 18 * math.sin(t * 13 + i * 1.7)) * intensity
        for col, k in ((RED, 1.0), (YELLOW, 0.55)):
            cr.move_to(fx - 22 * k, y)
            cr.curve_to(fx - 20 * k, y - hgt * 0.5 * k, fx, y - hgt * k * 0.9, fx, y - hgt * k)
            cr.curve_to(fx, y - hgt * k * 0.9, fx + 20 * k, y - hgt * 0.5 * k, fx + 22 * k, y)
            cr.close_path()
            cr.set_source_rgb(*col)
            cr.fill()


def stove(cr, cx, y, w):
    rounded_rect(cr, cx - w / 2, y, w, 70, 14)
    cr.set_source_rgb(0.20, 0.22, 0.26)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(5)
    cr.stroke()


def pot(cr, cx, top, w, h, water_level=0.75, t=0.0, wave=1.0, draw_water=True):
    """Pentola in sezione. Ritorna (x0, x1, superficie_y, fondo_y) dell'interno."""
    x0, x1 = cx - w / 2, cx + w / 2
    bottom = top + h
    # manici
    for sx in (-1, 1):
        rounded_rect(cr, cx + sx * (w / 2 + 10) - (50 if sx < 0 else 0) - (0 if sx < 0 else 0),
                     top + 40, 60, 34, 14)
        cr.set_source_rgb(*STEEL_DARK)
        cr.fill_preserve()
        cr.set_source_rgb(*INK)
        cr.set_line_width(5)
        cr.stroke()
    # corpo esterno
    rounded_rect(cr, x0, top, w, h, 30)
    cr.set_source_rgb(*STEEL)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(6)
    cr.stroke()
    # interno (taglio)
    ix0, ix1, itop, ibot = x0 + 22, x1 - 22, top + 10, bottom - 22
    rounded_rect(cr, ix0, itop, ix1 - ix0, ibot - itop, 18)
    cr.set_source_rgb(0.86, 0.89, 0.92)
    cr.fill()
    surf_y = ibot - (ibot - itop) * water_level
    if draw_water:
        cr.save()
        rounded_rect(cr, ix0, itop, ix1 - ix0, ibot - itop, 18)
        cr.clip()
        cr.move_to(ix0, ibot)
        steps = 30
        for i in range(steps + 1):
            xx = lerp(ix0, ix1, i / steps)
            yy = surf_y + wave * 7 * math.sin(xx * 0.03 + t * 4)
            cr.line_to(xx, yy)
        cr.line_to(ix1, ibot)
        cr.close_path()
        g = cairo.LinearGradient(0, surf_y, 0, ibot)
        g.add_color_stop_rgb(0, *WATER)
        g.add_color_stop_rgb(1, *WATER_DEEP)
        cr.set_source(g)
        cr.fill()
        cr.restore()
    # bordo superiore
    rounded_rect(cr, x0 - 14, top - 8, w + 28, 26, 12)
    cr.set_source_rgb(*STEEL_DARK)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(5)
    cr.stroke()
    return ix0, ix1, surf_y, ibot


def water_molecule(cr, x, y, scale=1.0, angle=0.0, alpha=1.0):
    """H2O: ossigeno rosso, due idrogeni bianchi a 104,5° circa."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    for s in (-1, 1):
        a = math.pi / 2 + s * math.radians(52)
        circle(cr, 30 * math.cos(a), 30 * math.sin(a), 15, WHITE, lw=3.5, alpha=alpha)
    circle(cr, 0, 0, 25, O_RED, lw=3.5, alpha=alpha)
    cr.restore()


def ion(cr, x, y, kind, scale=1.0, alpha=1.0):
    r, col, sign = (24, NA_COL, "+") if kind == "na" else (34, CL_COL, "−")
    cr.save()
    cr.translate(x, y)
    cr.scale(scale, scale)
    circle(cr, 0, 0, r, col, lw=4, alpha=alpha)
    outlined_text(cr, sign, 0, 12 if kind == "na" else 13, 38, fill=WHITE, lw=0, alpha=alpha)
    cr.restore()


def salt_grain(cr, x, y, s, angle=0.0, alpha=1.0):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    rounded_rect(cr, -s / 2, -s / 2, s, s, s * 0.15)
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.fill_preserve()
    cr.set_source_rgba(0.55, 0.6, 0.68, alpha)
    cr.set_line_width(max(2, s * 0.08))
    cr.stroke()
    cr.restore()


def lens_frame(cr, cx, cy, r):
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.set_source_rgb(*INK)
    cr.set_line_width(22)
    cr.stroke()
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.set_source_rgb(*STEEL)
    cr.set_line_width(12)
    cr.stroke()


def thermo_pill(cr, x, y, value_text, t, t0, hot=0.0):
    """Pillola temperatura con icona termometro."""
    p = ease_out_back(prog(t, t0, t0 + 0.35))
    if p <= 0:
        return
    size = 66
    ext = text_extents(cr, value_text, size)
    w, h = ext.x_advance + 150, 120
    cr.save()
    cr.translate(x, y)
    cr.scale(p, p)
    rounded_rect(cr, -w / 2, -h / 2, w, h, h / 2)
    cr.set_source_rgb(*WHITE)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(6)
    cr.stroke()
    # termometro
    tx = -w / 2 + 62
    rounded_rect(cr, tx - 12, -40, 24, 62, 12)
    cr.set_source_rgb(0.9, 0.9, 0.9)
    cr.fill_preserve()
    cr.set_source_rgb(*INK)
    cr.set_line_width(4)
    cr.stroke()
    fill_h = lerp(12, 54, clamp(hot))
    rounded_rect(cr, tx - 6, 22 - fill_h, 12, fill_h, 6)
    cr.set_source_rgb(*RED)
    cr.fill()
    circle(cr, tx, 30, 18, RED, lw=4)
    outlined_text(cr, value_text, tx + 40, 24, size, fill=INK, lw=0, anchor="left")
    cr.restore()
