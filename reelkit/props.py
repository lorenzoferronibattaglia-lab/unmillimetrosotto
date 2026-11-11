"""
Oggetti di scena riutilizzabili (pentola, fornello, spargisale, bottiglia d'olio,
mestolo, spaghetti, bolle, molecole, ioni, gocce d'olio, granuli d'amido).
Tutti i colori vengono letti dal modulo engine a runtime, così il tema è intercambiabile.
"""
import math
import random

import cairo

import engine as E

OIL = (0.98, 0.80, 0.25)
OIL_DARK = (0.85, 0.62, 0.10)
PASTA = (0.98, 0.84, 0.42)
PASTA_DARK = (0.80, 0.62, 0.22)
STARCH = (0.97, 0.97, 0.92)


def stove(cr, cx, y, w):
    E.rounded_rect(cr, cx - w / 2, y, w, 70, 14)
    cr.set_source_rgb(0.20, 0.22, 0.26)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()


def flames(cr, cx, y, w, t, intensity=1.0):
    n = 7
    for i in range(n):
        fx = cx - w / 2 + (i + 0.5) * w / n
        hgt = (55 + 18 * math.sin(t * 13 + i * 1.7)) * intensity
        for col, k in ((E.RED, 1.0), (E.YELLOW, 0.55)):
            cr.move_to(fx - 22 * k, y)
            cr.curve_to(fx - 20 * k, y - hgt * 0.5 * k, fx, y - hgt * k * 0.9, fx, y - hgt * k)
            cr.curve_to(fx, y - hgt * k * 0.9, fx + 20 * k, y - hgt * 0.5 * k, fx + 22 * k, y)
            cr.close_path()
            cr.set_source_rgb(*col)
            cr.fill()


def pot(cr, cx, top, w, h, water_level=0.72, t=0.0, wave=1.0, liquid=None):
    """Pentola in sezione. Ritorna (ix0, ix1, superficie_y, fondo_y) dell'interno."""
    x0, x1 = cx - w / 2, cx + w / 2
    bottom = top + h
    for sx in (-1, 1):
        hx = cx + sx * (w / 2 + 10) - (50 if sx < 0 else 0)
        E.rounded_rect(cr, hx, top + 40, 60, 34, 14)
        cr.set_source_rgb(*E.STEEL_DARK)
        cr.fill_preserve()
        cr.set_source_rgb(*E.INK)
        cr.set_line_width(5)
        cr.stroke()
    E.rounded_rect(cr, x0, top, w, h, 30)
    cr.set_source_rgb(*E.STEEL)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    ix0, ix1, itop, ibot = x0 + 22, x1 - 22, top + 10, bottom - 22
    E.rounded_rect(cr, ix0, itop, ix1 - ix0, ibot - itop, 18)
    cr.set_source_rgb(0.86, 0.89, 0.92)
    cr.fill()
    surf_y = ibot - (ibot - itop) * water_level
    cr.save()
    E.rounded_rect(cr, ix0, itop, ix1 - ix0, ibot - itop, 18)
    cr.clip()
    cr.move_to(ix0, ibot)
    for i in range(31):
        xx = E.lerp(ix0, ix1, i / 30)
        cr.line_to(xx, surf_y + wave * 7 * math.sin(xx * 0.03 + t * 4))
    cr.line_to(ix1, ibot)
    cr.close_path()
    g = cairo.LinearGradient(0, surf_y, 0, ibot)
    c0, c1 = (E.WATER, E.WATER_DEEP) if liquid is None else liquid
    g.add_color_stop_rgb(0, *c0)
    g.add_color_stop_rgb(1, *c1)
    cr.set_source(g)
    cr.fill()
    cr.restore()
    return ix0, ix1, surf_y, ibot


def pot_rim(cr, cx, top, w):
    """Bordo della pentola: va disegnato DOPO il contenuto che sporge."""
    E.rounded_rect(cr, cx - w / 2 - 14, top - 8, w + 28, 26, 12)
    cr.set_source_rgb(*E.STEEL_DARK)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()


def kitchen_pot(cr, t, cx=540, top=840, w=560, h=380, water_level=0.72, liquid=None, fire=1.0):
    """Fornello + fiamme + pentola: la composizione standard. fire in [0,1] = intensita' della fiamma (0 = spenta)."""
    stove(cr, cx, top + h + 35, w + 60)
    if fire > 0.02:
        flames(cr, cx, top + h + 35, w * 0.68, t, intensity=fire)
    inner = pot(cr, cx, top, w, h, water_level, t, liquid=liquid)
    return inner


def shaker(cr, x, y, angle, label="SALE"):
    """Spargisale. Il tappo forato è in alto a riposo (asse -y).
    ATTENZIONE FISICA: per versare verso sinistra usare angle NEGATIVO."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    E.rounded_rect(cr, -55, -80, 110, 150, 30)
    cr.set_source_rgb(0.95, 0.96, 0.98)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    E.rounded_rect(cr, -58, -120, 116, 52, 16)
    cr.set_source_rgb(*E.STEEL)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.stroke()
    for hx in (-25, 0, 25):
        E.circle(cr, hx, -120, 6, E.INK, lw=0)
    lsz = 36
    while lsz > 18 and E.text_extents(cr, label, lsz).x_advance > 100:
        lsz -= 2
    E.outlined_text(cr, label, 0, 12, lsz, fill=E.INK, lw=0)
    cr.restore()


def oil_bottle(cr, x, y, angle):
    """Bottiglia d'olio. Il collo è in alto a riposo (asse -y).
    Per versare verso sinistra usare angle NEGATIVO."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    # corpo
    E.rounded_rect(cr, -55, -60, 110, 190, 26)
    cr.set_source_rgba(0.75, 0.88, 0.70, 0.95)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    # olio dentro
    E.rounded_rect(cr, -45, -10, 90, 130, 20)
    cr.set_source_rgb(*OIL)
    cr.fill()
    # collo
    cr.move_to(-55, -40)
    cr.curve_to(-55, -90, -22, -100, -22, -130)
    cr.line_to(22, -130)
    cr.curve_to(22, -100, 55, -90, 55, -40)
    cr.close_path()
    cr.set_source_rgba(0.75, 0.88, 0.70, 0.95)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.stroke()
    E.rounded_rect(cr, -26, -158, 52, 32, 8)
    cr.set_source_rgb(*E.RED)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.stroke()
    # etichetta
    E.rounded_rect(cr, -46, 30, 92, 54, 10)
    cr.set_source_rgb(1, 1, 1)
    cr.fill()
    E.outlined_text(cr, "OLIO", 0, 68, 30, fill=E.INK, lw=0)
    cr.restore()


def mouth_point(x, y, angle, dist):
    """Posizione dell'apertura di un contenitore ruotato di `angle`,
    con l'apertura a distanza `dist` lungo l'asse -y a riposo."""
    return x + dist * math.sin(angle), y - dist * math.cos(angle)


def falling_grains(cr, t, t0, origin, until_y, n=26, spread=18, drift=-40, size=16, gap=0.09, seed=3):
    rnd = random.Random(seed)
    ox, oy = origin
    for i in range(n):
        k = t - (t0 + i * gap)
        if k < 0:
            continue
        gx = ox + rnd.uniform(-spread, spread) + k * drift
        gy = oy + 900 * k * k
        if gy < until_y:
            E_salt(cr, gx, gy, size, k * 4)


def E_salt(cr, x, y, s, angle=0.0, alpha=1.0):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    E.rounded_rect(cr, -s / 2, -s / 2, s, s, s * 0.15)
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.fill_preserve()
    cr.set_source_rgba(0.55, 0.6, 0.68, alpha)
    cr.set_line_width(max(2, s * 0.08))
    cr.stroke()
    cr.restore()


def oil_stream(cr, t, t0, t1, origin, surf_y):
    """Filo d'olio che scende dall'apertura fino alla superficie."""
    p = E.prog(t, t0, t0 + 0.3)
    q = E.prog(t, t1, t1 + 0.3)
    if p <= 0 or q >= 1:
        return
    ox, oy = origin
    top = E.lerp(oy, surf_y, q)
    bot = E.lerp(oy, surf_y, p)
    cr.move_to(ox, top)
    cr.line_to(ox - 6, bot)
    cr.set_source_rgb(*OIL)
    cr.set_line_width(12)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.stroke()
    cr.set_line_cap(cairo.LINE_CAP_BUTT)


def oil_slick(cr, ix0, ix1, surf_y, t, amount, thickness=18):
    """Strato d'olio che galleggia sulla superficie (amount 0..1)."""
    if amount <= 0:
        return
    cx = (ix0 + ix1) / 2
    half = (ix1 - ix0) / 2 * amount
    cr.move_to(cx - half, surf_y)
    for i in range(21):
        xx = E.lerp(cx - half, cx + half, i / 20)
        cr.line_to(xx, surf_y - 4 + 4 * math.sin(xx * 0.03 + t * 4))
    for i in range(20, -1, -1):
        xx = E.lerp(cx - half, cx + half, i / 20)
        cr.line_to(xx, surf_y + thickness * amount + 3 * math.sin(xx * 0.05 + t * 3))
    cr.close_path()
    cr.set_source_rgba(*OIL, 0.95)
    cr.fill_preserve()
    cr.set_source_rgb(*OIL_DARK)
    cr.set_line_width(3)
    cr.stroke()


def spaghetti(cr, ix0, ix1, bot, t, n=14, clump=0.0, separate=0.0, height=300, seed=8):
    """Spaghetti in pentola. clump 0..1 li stringe in un mazzo, separate 0..1 li apre e li muove."""
    rnd = random.Random(seed)
    cr.set_line_width(9)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cx = (ix0 + ix1) / 2
    for i in range(n):
        x0 = rnd.uniform(ix0 + 30, ix1 - 30)
        a = rnd.uniform(-0.5, 0.5)
        x0 = E.lerp(x0, cx + (x0 - cx) * 0.15, clump)
        a = E.lerp(a, a * 0.1, clump)
        if separate > 0:
            a += separate * 0.35 * math.sin(t * 2.5 + i)
        x1 = x0 + height * math.sin(a)
        y1 = bot - 15 - height * math.cos(a)
        cr.move_to(x0, bot - 15)
        cr.line_to(x1, y1)
        cr.set_source_rgb(*PASTA)
        cr.stroke()
    cr.set_line_cap(cairo.LINE_CAP_BUTT)


def spoon(cr, x, y, angle):
    """Mestolo di legno, impugnatura in alto."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    E.rounded_rect(cr, -12, -420, 24, 380, 12)
    cr.set_source_rgb(0.72, 0.50, 0.28)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()
    cr.save()
    cr.scale(1, 1.4)
    cr.arc(0, -10, 40, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgb(0.72, 0.50, 0.28)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.stroke()
    cr.restore()


def bubble(cr, x, y, r, alpha=1.0):
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.set_source_rgba(0.85, 0.95, 1.0, 0.55 * alpha)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.set_line_width(3)
    cr.stroke()


def water_molecule(cr, x, y, scale=1.0, angle=0.0, alpha=1.0):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    for s in (-1, 1):
        a = math.pi / 2 + s * math.radians(52)
        E.circle(cr, 30 * math.cos(a), 30 * math.sin(a), 15, E.WHITE, lw=3.5, alpha=alpha)
    E.circle(cr, 0, 0, 25, E.O_RED, lw=3.5, alpha=alpha)
    cr.restore()


def oil_molecule(cr, x, y, scale=1.0, angle=0.0, alpha=1.0, length=6):
    """Molecola grassa stilizzata: testa + lunga catena a zig-zag."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    cr.move_to(-length * 14 / 2, 0)
    for i in range(length + 1):
        cr.line_to(-length * 14 / 2 + i * 14, -8 if i % 2 else 8)
    cr.set_source_rgba(*OIL_DARK, alpha)
    cr.set_line_width(7)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.stroke()
    for i in range(length + 1):
        E.circle(cr, -length * 14 / 2 + i * 14, -8 if i % 2 else 8, 9, OIL, lw=2.5, alpha=alpha)
    cr.restore()


def starch_grain(cr, x, y, r, alpha=1.0):
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.set_source_rgba(*STARCH, alpha)
    cr.fill_preserve()
    cr.set_source_rgba(0.7, 0.68, 0.55, alpha)
    cr.set_line_width(3)
    cr.stroke()


def check_card(cr, x, y, text, ok, t, t0, w=880):
    p = E.ease_out_back(E.prog(t, t0, t0 + 0.4))
    if p <= 0:
        return
    cr.save()
    cr.translate(x, y)
    cr.scale(p, p)
    E.rounded_rect(cr, -w / 2, -85, w, 170, 40)
    cr.set_source_rgb(*E.WHITE)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(7)
    cr.stroke()
    # il testo si restringe per non toccare l'icona
    size = 80
    while size > 34 and E.text_extents(cr, text, size).x_advance > w - 60 - 190:
        size -= 4
    E.outlined_text(cr, text, -w / 2 + 60, size * 0.37, size, fill=E.INK, lw=0, anchor="left")
    col = (0.2, 0.75, 0.35) if ok else E.RED
    E.circle(cr, w / 2 - 110, 0, 58, col, lw=6)
    cr.set_source_rgb(*E.WHITE)
    cr.set_line_width(16)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    bx = w / 2 - 110
    if ok:
        cr.move_to(bx - 30, 2)
        cr.line_to(bx - 8, 26)
        cr.line_to(bx + 32, -22)
    else:
        cr.move_to(bx - 24, -24)
        cr.line_to(bx + 24, 24)
        cr.move_to(bx + 24, -24)
        cr.line_to(bx - 24, 24)
    cr.stroke()
    cr.set_line_cap(cairo.LINE_CAP_BUTT)
    cr.restore()


def pointer(cr, x0, y0, x1, y1, t, t0, color=None):
    """Freccia curva che compare (stile 'cerchio + freccia')."""
    p = E.ease(E.prog(t, t0, t0 + 0.35))
    if p <= 0:
        return
    color = color or E.RED
    xe, ye = E.lerp(x0, x1, p), E.lerp(y0, y1, p)
    mx, my = (x0 + xe) / 2 + 60, (y0 + ye) / 2
    cr.move_to(x0, y0)
    cr.curve_to(mx, my, mx, my, xe, ye)
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(20)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.stroke_preserve()
    cr.set_source_rgb(*color)
    cr.set_line_width(11)
    cr.stroke()
    if p >= 1:
        ang = math.atan2(ye - my, xe - mx)
        cr.move_to(xe + 10 * math.cos(ang), ye + 10 * math.sin(ang))
        cr.line_to(xe - 34 * math.cos(ang - 0.5), ye - 34 * math.sin(ang - 0.5))
        cr.line_to(xe - 34 * math.cos(ang + 0.5), ye - 34 * math.sin(ang + 0.5))
        cr.close_path()
        cr.set_source_rgb(*color)
        cr.fill_preserve()
        cr.set_source_rgb(*E.INK)
        cr.set_line_width(4)
        cr.stroke()
    cr.set_line_cap(cairo.LINE_CAP_BUTT)


def microwave(cr, cx, cy, w, h, t, on=0.0, food="lasagna", heat=0.0):
    """Forno a microonde frontale. on 0..1 accende la luce interna, heat 0..1 colora il cibo."""
    x0, y0 = cx - w / 2, cy - h / 2
    E.rounded_rect(cr, x0, y0, w, h, 34)
    cr.set_source_rgb(0.86, 0.88, 0.91)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(7)
    cr.stroke()
    # finestra
    wx0, wy0, ww, wh = x0 + 34, y0 + 34, w * 0.66, h - 68
    E.rounded_rect(cr, wx0, wy0, ww, wh, 22)
    light = 0.18 + 0.55 * on
    cr.set_source_rgb(0.12 + light * 0.9, 0.12 + light * 0.8, 0.10 + light * 0.35)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    # piatto girevole + cibo
    pcx, pcy = wx0 + ww / 2, wy0 + wh - 70
    cr.save()
    cr.translate(pcx, pcy)
    cr.scale(1, 0.28)
    cr.arc(0, 0, ww * 0.38, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgb(0.92, 0.94, 0.96)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(4)
    cr.stroke()
    fw, fh = ww * 0.46, 90
    fx, fy = pcx - fw / 2, pcy - fh - 6
    col = (E.lerp(0.95, 0.93, heat), E.lerp(0.80, 0.45, heat), E.lerp(0.55, 0.20, heat))
    E.rounded_rect(cr, fx, fy, fw, fh, 14)
    cr.set_source_rgb(*col)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()
    for k in (1, 2):
        cr.move_to(fx + 10, fy + k * fh / 3)
        cr.line_to(fx + fw - 10, fy + k * fh / 3)
        cr.set_source_rgba(0.75, 0.25, 0.15, 0.8)
        cr.set_line_width(6)
        cr.stroke()
    # onde se acceso
    if on > 0.05:
        for i in range(3):
            ph = (t * 1.6 + i / 3) % 1.0
            cr.arc(pcx, fy + fh / 2, 40 + ph * 160, math.pi * 1.1, math.pi * 1.9)
            cr.set_source_rgba(1, 1, 1, 0.5 * (1 - ph) * on)
            cr.set_line_width(5)
            cr.stroke()
    # pannello comandi
    px = wx0 + ww + 30
    E.rounded_rect(cr, px, wy0, x0 + w - 34 - px, 70, 12)
    cr.set_source_rgb(0.15, 0.17, 0.2)
    cr.fill()
    secs = max(0, 90 - int(t * 6) % 90)
    E.outlined_text(cr, f"{secs // 60}:{secs % 60:02d}", px + (x0 + w - 34 - px) / 2, wy0 + 50, 38,
                    fill=(0.4, 1.0, 0.5), lw=0)
    for j in range(2):
        E.circle(cr, px + (x0 + w - 34 - px) / 2, wy0 + 150 + j * 110, 34, E.STEEL, lw=5)
    E.rounded_rect(cr, x0 + w - 40, y0 + 60, 14, h - 120, 7)
    cr.set_source_rgb(*E.STEEL_DARK)
    cr.fill()


def field_plates(cr, cx, cy, r, level, alpha=1.0):
    """Piastre sopra e sotto la lente. level in [-1, 1] varia in modo continuo:
    i colori sfumano (mai scatti rosso/blu) per non creare lampeggiamenti."""
    pos, neg = (0.85, 0.42, 0.40), (0.40, 0.55, 0.85)  # toni smorzati, non saturi
    for k, yy in ((1, cy - r - 70), (-1, cy + r + 70)):
        v = k * level  # +1 = piastra positiva
        mix = (1 - v) / 2
        col = tuple(E.lerp(p0, n0, mix) for p0, n0 in zip(pos, neg))
        E.rounded_rect(cr, cx - 230, yy - 26, 460, 52, 26)
        cr.set_source_rgba(*col, alpha)
        cr.fill_preserve()
        cr.set_source_rgba(*E.INK, alpha)
        cr.set_line_width(5)
        cr.stroke()
        if abs(v) > 0.35:
            E.outlined_text(cr, "+ + + +" if v > 0 else "− − − −", cx, yy + 16, 44, fill=E.WHITE, lw=0,
                            alpha=alpha * min(1.0, (abs(v) - 0.35) / 0.4))


GREEN_OK = (0.20, 0.72, 0.38)
ICE = (0.84, 0.94, 1.0)


def ice_cube(cr, x, y, s, angle=0.0, alpha=0.9):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    E.rounded_rect(cr, -s / 2, -s / 2, s, s, s * 0.22)
    cr.set_source_rgba(*ICE, alpha)
    cr.fill_preserve()
    cr.set_source_rgba(0.45, 0.65, 0.85, alpha)
    cr.set_line_width(4)
    cr.stroke()
    cr.move_to(-s * 0.25, -s * 0.2)
    cr.line_to(s * 0.05, -s * 0.3)
    cr.set_source_rgba(1, 1, 1, alpha)
    cr.set_line_width(5)
    cr.stroke()
    cr.restore()


def wine_bottle(cr, x, y, scale=1.0, angle=0.0, label="VINO", cork=True):
    """Bottiglia di vino, fondo in (x, y) a riposo; collo verso l'alto."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    cr.move_to(-60, 0)
    cr.line_to(-60, -330)
    cr.curve_to(-60, -400, -24, -410, -22, -470)
    cr.line_to(-22, -560)
    cr.line_to(22, -560)
    cr.line_to(22, -470)
    cr.curve_to(24, -410, 60, -400, 60, -330)
    cr.line_to(60, 0)
    cr.close_path()
    cr.set_source_rgb(0.16, 0.32, 0.20)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    E.rounded_rect(cr, -48, -260, 96, 120, 10)
    cr.set_source_rgb(0.96, 0.93, 0.85)
    cr.fill()
    lsz = 30
    while lsz > 16 and E.text_extents(cr, label, lsz).x_advance > 86:
        lsz -= 2
    E.outlined_text(cr, label, 0, -190, lsz, fill=E.INK, lw=0)
    if cork:
        E.rounded_rect(cr, -24, -585, 48, 40, 6)
        cr.set_source_rgb(0.55, 0.12, 0.18)
        cr.fill()
    cr.move_to(-40, -320)
    cr.line_to(-40, -40)
    cr.set_source_rgba(1, 1, 1, 0.25)
    cr.set_line_width(10)
    cr.stroke()
    cr.restore()


def ice_bucket(cr, cx, top, w, h, t, frost=0.0, salt_t=None, water_level=0.62):
    """Secchiello in sezione con acqua, cubetti e bottiglia. Ritorna (ix0, ix1, superficie, fondo)."""
    x0, x1 = cx - w / 2, cx + w / 2
    bot = top + h
    inset = 40
    # bottiglia dietro (sporge dal secchiello)
    wine_bottle(cr, cx + 30, bot - 30, scale=0.95, angle=0.08)
    # acqua dentro il secchiello (trapezio)
    surf = bot - (h - 20) * water_level
    def side(y):
        k = (y - top) / h
        return E.lerp(x0, x0 + inset, k), E.lerp(x1, x1 - inset, k)
    l0, r0 = side(surf)
    l1, r1 = side(bot - 12)
    cr.move_to(l0, surf)
    for i in range(21):
        xx = E.lerp(l0, r0, i / 20)
        cr.line_to(xx, surf + 5 * math.sin(xx * 0.03 + t * 3))
    cr.line_to(r1, bot - 12)
    cr.line_to(l1, bot - 12)
    cr.close_path()
    cr.set_source_rgba(0.55, 0.78, 0.95, 0.75)
    cr.fill()
    # cubetti galleggianti
    rnd = random.Random(12)
    for i in range(9):
        xx = rnd.uniform(l0 + 40, r0 - 40)
        yy = surf + rnd.uniform(-10, 60) + 4 * math.sin(t * 2 + i)
        ice_cube(cr, xx, yy, rnd.uniform(50, 70), angle=rnd.uniform(-0.5, 0.5) + 0.05 * math.sin(t + i))
    # secchiello in metallo (pareti), davanti
    cr.move_to(x0, top)
    cr.line_to(x1, top)
    cr.line_to(x1 - inset, bot)
    cr.line_to(x0 + inset, bot)
    cr.close_path()
    cr.set_source_rgba(0.75, 0.79, 0.84, 0.28)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(7)
    cr.stroke()
    E.rounded_rect(cr, x0 - 14, top - 14, w + 28, 28, 14)
    cr.set_source_rgb(*E.STEEL)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()
    # brina sulle pareti
    if frost > 0:
        rnd = random.Random(3)
        for i in range(60):
            fy = rnd.uniform(top + 20, bot - 20)
            fl, fr = side(fy)
            fx = fl + 8 if i % 2 else fr - 8
            E.circle(cr, fx + rnd.uniform(-6, 6), fy, rnd.uniform(3, 7), (1, 1, 1), lw=0, alpha=0.8 * frost)
    return l0, r0, surf, bot


def lid(cr, cx, y, w, lift=0.0, angle=0.0):
    """Coperchio appoggiato sul bordo della pentola (y = bordo). lift lo solleva."""
    cr.save()
    cr.translate(cx, y - lift)
    cr.rotate(angle)
    cr.move_to(-w / 2 - 16, 0)
    cr.curve_to(-w / 2, -70, w / 2, -70, w / 2 + 16, 0)
    cr.close_path()
    cr.set_source_rgb(*E.STEEL)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    E.rounded_rect(cr, -40, -82, 80, 26, 12)
    cr.set_source_rgb(*E.STEEL_DARK)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.stroke()
    cr.restore()


def steam(cr, x, y, t, n=4, alpha=0.7, spread=120):
    for i in range(n):
        ph = (t * 0.5 + i / n) % 1.0
        xx = x + math.sin(ph * 6 + i) * 25 + (i - n / 2) * spread / n
        yy = y - ph * 220
        cr.arc(xx, yy, 18 + ph * 22, 0, 2 * math.pi)
        cr.set_source_rgba(1, 1, 1, alpha * (1 - ph) * 0.6)
        cr.fill()


WINE = (0.50, 0.06, 0.14)


def wine_glass(cr, cx, base_y, scale=1.0, fill=0.45, t=0.0):
    """Calice da rosso: base in base_y."""
    cr.save()
    cr.translate(cx, base_y)
    cr.scale(scale, scale)
    # coppa
    def bowl_path():
        cr.move_to(-150, -560)
        cr.curve_to(-170, -380, -120, -260, 0, -250)
        cr.curve_to(120, -260, 170, -380, 150, -560)
    # vino (parte bassa della coppa)
    cr.save()
    bowl_path()
    cr.close_path()
    cr.clip()
    top = -250 - 310 * fill
    cr.move_to(-200, top + 6 * math.sin(t * 2))
    cr.curve_to(-60, top - 8, 60, top + 8, 200, top + 6 * math.sin(t * 2 + 1))
    cr.line_to(200, 0)
    cr.line_to(-200, 0)
    cr.close_path()
    cr.set_source_rgb(*WINE)
    cr.fill()
    cr.restore()
    bowl_path()
    cr.set_source_rgba(1, 1, 1, 0.9)
    cr.set_line_width(8)
    cr.stroke()
    # gambo e piede
    cr.move_to(0, -250)
    cr.line_to(0, -20)
    cr.set_line_width(12)
    cr.stroke()
    cr.save()
    cr.scale(1, 0.22)
    cr.arc(0, -20 / 0.22, 110, 0, 2 * math.pi)
    cr.restore()
    cr.set_line_width(8)
    cr.stroke()
    # riflesso
    cr.move_to(-110, -520)
    cr.curve_to(-125, -420, -100, -350, -70, -320)
    cr.set_source_rgba(1, 1, 1, 0.35)
    cr.set_line_width(10)
    cr.stroke()
    cr.restore()
    return cx, base_y - (250 + 310 * fill) * scale


def ethanol(cr, x, y, scale=1.0, angle=0.0, alpha=1.0):
    """Etanolo stilizzato: due carboni scuri, ossigeno rosso, idrogeni bianchi."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    for hx, hy in ((-62, -18), (-58, 22), (-30, -34), (10, 34), (66, 22)):
        E.circle(cr, hx, hy, 12, E.WHITE, lw=3, alpha=alpha)
    E.circle(cr, -36, 0, 22, (0.25, 0.27, 0.30), lw=3.5, alpha=alpha)
    E.circle(cr, 6, 0, 22, (0.25, 0.27, 0.30), lw=3.5, alpha=alpha)
    E.circle(cr, 46, 6, 22, E.O_RED, lw=3.5, alpha=alpha)
    cr.restore()


def co2(cr, x, y, scale=1.0, angle=0.0, alpha=1.0):
    """CO2: carbonio scuro al centro, due ossigeni rossi ai lati."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    for sx in (-1, 1):
        E.circle(cr, sx * 30, 0, 19, E.O_RED, lw=3.5, alpha=alpha)
    E.circle(cr, 0, 0, 20, (0.25, 0.27, 0.30), lw=3.5, alpha=alpha)
    cr.restore()


VIT = (1.0, 0.62, 0.12)


def vitamin(cr, x, y, r=22, alpha=1.0, label="C"):
    """Vitamina stilizzata: esagono arancione con lettera."""
    cr.save()
    cr.translate(x, y)
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3
        (cr.move_to if i == 0 else cr.line_to)(r * math.cos(a), r * math.sin(a))
    cr.close_path()
    cr.set_source_rgba(*VIT, alpha)
    cr.fill_preserve()
    cr.set_source_rgba(*E.INK, alpha)
    cr.set_line_width(3.5)
    cr.stroke()
    E.outlined_text(cr, label, 0, r * 0.45, r * 1.2, fill=E.WHITE, lw=0, alpha=alpha)
    cr.restore()


def glass_of(cr, cx, base_y, liquid=(0.62, 0.82, 0.97), fill=0.6, t=0.0, ice=0, scale=1.0, bubbles=False):
    """Bicchiere dritto con liquido; ice = numero di cubetti che GALLEGGIANO in superficie."""
    cr.save()
    cr.translate(cx, base_y)
    cr.scale(scale, scale)
    w_top, w_bot, h = 300, 230, 480
    top = -h
    lvl = -h * fill
    cr.move_to(-w_bot / 2, 0)
    cr.line_to(w_bot / 2, 0)
    cr.line_to(w_top / 2 - (w_top - w_bot) / 2 * (1 - fill), lvl)
    cr.line_to(-w_top / 2 + (w_top - w_bot) / 2 * (1 - fill), lvl)
    cr.close_path()
    cr.set_source_rgba(*liquid, 0.85)
    cr.fill()
    if bubbles:
        for i in range(10):
            ph = (t * 0.5 + i * 0.1) % 1.0
            bx = -80 + (i * 37) % 160
            E.circle(cr, bx + 6 * math.sin(t * 3 + i), -10 - ph * (-lvl - 20), 5 + 3 * ph, (1, 1, 1), lw=0, alpha=0.8 * (1 - ph * 0.5))
    rnd = random.Random(5)
    for i in range(ice):
        ice_cube(cr, -90 + i * 75 + rnd.uniform(-8, 8), lvl + 8 + 5 * math.sin(t * 2 + i), 66, angle=rnd.uniform(-0.4, 0.4))
    cr.move_to(-w_top / 2, top)
    cr.line_to(-w_bot / 2, 0)
    cr.line_to(w_bot / 2, 0)
    cr.line_to(w_top / 2, top)
    cr.set_source_rgba(1, 1, 1, 0.95)
    cr.set_line_width(8)
    cr.stroke()
    cr.restore()


def teaspoon(cr, x, y, scale=1.0):
    """Cucchiaino d'acciaio verticale: manico verso il basso da (x, y), conca in alto."""
    cr.save()
    cr.translate(x, y)
    cr.scale(scale, scale)
    steel = (0.80, 0.83, 0.87)
    E.rounded_rect(cr, -9, -10, 18, 200, 9)
    cr.set_source_rgb(*steel)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()
    cr.save()
    cr.translate(0, -50)
    cr.scale(1, 1.45)
    cr.arc(0, 0, 34, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgb(*steel)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.stroke()
    cr.save()
    cr.translate(-10, -62)
    cr.scale(1, 1.8)
    cr.arc(0, 0, 8, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgba(1, 1, 1, 0.7)
    cr.fill()
    cr.restore()


SUGAR = (1.0, 0.98, 0.92)
H_ION = (0.60, 0.34, 0.95)
EGG_SHELL = (0.96, 0.89, 0.76)
EGG_WHITE = (0.98, 0.97, 0.90)
EGG_YOLK = (1.0, 0.76, 0.18)
AIR = (0.80, 0.90, 0.98)


def sugar_ring(cr, x, y, r=26, angle=0.0, alpha=1.0):
    """Zucchero stilizzato: anello esagonale ambra (glucosio/fruttosio)."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3
        (cr.move_to if i == 0 else cr.line_to)(r * math.cos(a), r * math.sin(a))
    cr.close_path()
    cr.set_source_rgba(*SUGAR, alpha)
    cr.fill_preserve()
    cr.set_source_rgba(*E.INK, alpha)
    cr.set_line_width(5)
    cr.stroke()
    cr.arc(0, 0, r * 0.32, 0, 2 * math.pi)
    cr.set_source_rgba(1, 1, 1, 0.55 * alpha)
    cr.fill()
    cr.restore()


def microbe(cr, x, y, scale=1.0, shrink=0.0, t=0.0, angle=0.25):
    """Batterio a bastoncello. shrink in [0,1]: perde acqua, si rimpicciolisce e si raggrinzisce."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    k = scale * (1 - 0.38 * shrink)
    L, R = 120 * k, 44 * k * (1 - 0.15 * shrink)
    n = 48
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        wob = 1 + 0.10 * shrink * math.sin(7 * a + 1.3)
        px = (L / 2 * (1 if math.cos(a) > 0 else -1) + R * math.cos(a)) if abs(math.cos(a)) > 0 else R * math.cos(a)
        px = (L / 2) * math.copysign(1, math.cos(a)) + R * math.cos(a) * wob
        py = R * math.sin(a) * wob
        (cr.move_to if i == 0 else cr.line_to)(px, py)
    cr.close_path()
    g = (E.lerp(0.45, 0.62, shrink), E.lerp(0.80, 0.66, shrink), E.lerp(0.36, 0.40, shrink))
    cr.set_source_rgb(*g)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(6)
    cr.stroke()
    # flagello
    cr.move_to(-(L / 2 + R), 0)
    for i in range(1, 9):
        cr.line_to(-(L / 2 + R) - i * 10 * k, 10 * k * math.sin(i * 1.2 + t * 6))
    cr.set_line_width(4)
    cr.stroke()
    cr.restore()


def h_ion(cr, x, y, alpha=1.0, scale=1.0):
    """Ione idrogeno (acidita'): pallina rossa con H+."""
    E.circle(cr, x, y, 32 * scale, H_ION, lw=5, alpha=alpha)
    E.outlined_text(cr, "H+", x, y + 13 * scale, 34 * scale, fill=E.WHITE, lw=0, alpha=alpha)


def _egg_path(cr, rx, ry):
    n = 64
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        x = rx * math.sin(th) * (1 + 0.12 * math.cos(th))
        y = -ry * math.cos(th)
        (cr.move_to if i == 0 else cr.line_to)(x, y)
    cr.close_path()


def egg_whole(cr, x, y, scale=1.0, angle=0.0, rx=50, ry=66):
    """Uovo intero, parte larga in alto a riposo (angle in radianti)."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(scale, scale)
    _egg_path(cr, rx, ry)
    cr.set_source_rgb(*EGG_SHELL)
    cr.fill_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5 / scale)
    cr.stroke()
    cr.save()
    cr.translate(-rx * 0.35, -ry * 0.35)
    cr.scale(1, 1.7)
    cr.arc(0, 0, rx * 0.16, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgba(1, 1, 1, 0.6)
    cr.fill()
    cr.restore()


def egg_section(cr, cx, cy, air=0.08, rx=230, ry=300):
    """Uovo in sezione, parte larga in alto: guscio, albume, tuorlo, camera d'aria (air = frazione dell'altezza)."""
    cr.save()
    cr.translate(cx, cy)
    _egg_path(cr, rx, ry)
    cr.set_source_rgb(*EGG_WHITE)
    cr.fill()
    cr.save()
    _egg_path(cr, rx - 4, ry - 4)
    cr.clip()
    yl = -ry + air * 2 * ry
    cr.move_to(-rx - 20, -ry - 20)
    cr.line_to(rx + 20, -ry - 20)
    cr.line_to(rx + 20, yl - 18)
    cr.curve_to(rx * 0.4, yl + 22, -rx * 0.4, yl + 22, -rx - 20, yl - 18)
    cr.close_path()
    cr.set_source_rgb(*AIR)
    cr.fill_preserve()
    cr.set_source_rgba(*E.INK, 0.6)
    cr.set_line_width(4)
    cr.stroke()
    cr.restore()
    E.circle(cr, 0, ry * 0.18, rx * 0.46, EGG_YOLK, lw=5)
    _egg_path(cr, rx, ry)
    cr.set_source_rgb(*EGG_SHELL)
    cr.set_line_width(22)
    cr.stroke_preserve()
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(5)
    cr.stroke()
    # pori
    for i in range(22):
        th = 2 * math.pi * (i + 0.5) / 22
        x = rx * math.sin(th) * (1 + 0.12 * math.cos(th))
        y = -ry * math.cos(th)
        cr.arc(x, y, 3.5, 0, 2 * math.pi)
        cr.set_source_rgb(*E.INK)
        cr.fill()
    cr.restore()


def egg_point(th, rx=230, ry=300):
    """Punto del guscio all'angolo th (0 = cima) e normale uscente."""
    x = rx * math.sin(th) * (1 + 0.12 * math.cos(th))
    y = -ry * math.cos(th)
    d = math.hypot(x, y) or 1
    return x, y, x / d, y / d
