"""
Tipi di scena parametrici. Ogni scena riceve lo `spec` dallo storyboard e un contesto
con i tempi delle parole: gli eventi si agganciano alle parole pronunciate ("at").

Tipi disponibili: hook, lens, pot, number, checklist, end.
"""
import math
import random

import engine as E
import props as P

LENS = (540, 860, 380)
SURF = LENS[1] - 170


# ---------------------------------------------------------------- contesto
class Ctx:
    def __init__(self, words, dur):
        self.words = words  # (parola, t0, t1, par)
        self.dur = dur
        self.par_start = {}
        for w, a, b, p in words:
            self.par_start.setdefault(p, a)

    def at(self, par, spec, default=None):
        """Risolve un'ancora: "parola", "parola#2" (n-esima), o numero (secondi da inizio paragrafo)."""
        if spec is None:
            return default
        if isinstance(spec, (int, float)):
            return self.par_start[par] + spec
        word, _, nth = str(spec).partition("#")
        nth = int(nth) if nth else 0
        k = 0
        for w, a, b, p in self.words:
            if p == par and word.lower() in w.lower():
                if k == nth:
                    return a
                k += 1
        raise KeyError(f"ancora '{spec}' non trovata nel paragrafo {par}")


def scene_start(ctx, par):
    return 0.0 if par == 0 else ctx.par_start[par] - 0.15


# ---------------------------------------------------------------- utilità comuni
def labels(cr, t, ctx, par, items):
    for it in items or []:
        x, y = it.get("pos", [540, 1250])
        col = getattr(E, it.get("color", "RED"), None) or E.RED
        if isinstance(it.get("color"), str) and it["color"].startswith("#"):
            h = it["color"].lstrip("#")
            col = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        E.label(cr, it["text"], x, y, t, ctx.at(par, it.get("at", 0.3)), size=it.get("size", 56), bg=col)
    for ar in [i for i in (items or []) if i.get("arrow_to")]:
        x, y = ar.get("pos", [540, 1250])
        tx, ty = ar["arrow_to"]
        sy = y - 50 if ty < y else y + 45
        P.pointer(cr, x, sy, tx, ty, t, ctx.at(par, ar.get("at", 0.3)) + 0.2)


def molecule_field(seed, spacing=100, surface=None, exclude=()):
    cx, cy, r = LENS
    rnd = random.Random(seed)
    pts = []
    y = cy - r - spacing
    row = 0
    while y < cy + r + spacing:
        x = cx - r - spacing + (spacing / 2 if row % 2 else 0)
        while x < cx + r + spacing:
            px, py = x + rnd.uniform(-14, 14), y + rnd.uniform(-14, 14)
            ok = surface is None or py > surface + 45
            for (ex0, ey0, ex1, ey1) in exclude:
                if ex0 <= px <= ex1 and ey0 <= py <= ey1:
                    ok = False
            if ok:
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


def water_bg(cr, surface=None, t=0.0):
    import cairo
    cx, cy, r = LENS
    g = cairo.LinearGradient(0, cy - r, 0, cy + r)
    g.add_color_stop_rgb(0, 0.55, 0.80, 0.96)
    g.add_color_stop_rgb(1, 0.33, 0.62, 0.88)
    if surface is None:
        cr.set_source(g)
        cr.paint()
        return
    cr.set_source_rgb(0.86, 0.91, 0.96)
    cr.paint()
    cr.move_to(cx - r - 20, cy + r + 20)
    for i in range(41):
        xx = E.lerp(cx - r - 20, cx + r + 20, i / 40)
        cr.line_to(xx, surface + 8 * math.sin(xx * 0.025 + t * 3))
    cr.line_to(cx + r + 20, cy + r + 20)
    cr.close_path()
    cr.set_source(g)
    cr.fill()


# ---------------------------------------------------------------- HOOK
def hook(cr, t, ctx, par, spec):
    s = scene_start(ctx, par)
    E.background(cr)
    pr = spec.get("prop", {})
    if pr.get("appliance") == "microwave":
        on = E.ease(E.prog(t, s + 0.3, s + 0.8))
        P.microwave(cr, 540, 1000, 860, 560, t, on=on, heat=0.55 * E.ease(E.prog(t, s + 0.5, s + 4)))
        E.title(cr, spec["title"], t, s, y=250, size=spec.get("title_size", 92))
        st = spec.get("stamp")
        if st:
            E.stamp(cr, st.get("text", "FALSO MITO"), 540, 610, t, ctx.at(par, st.get("at")), size=104)
        return
    ix0, ix1, surf, bot = P.kitchen_pot(cr, t, top=840)
    if pr.get("pasta"):
        cr.save()
        E.rounded_rect(cr, ix0, surf - 200, ix1 - ix0, bot - surf + 200, 18)
        cr.clip()
        P.spaghetti(cr, ix0, ix1, bot, t, height=330)
        cr.restore()
    oil_amount = 0.0
    pour = pr.get("pour")
    if pour:
        ang = E.lerp(0.0, -2.3, E.ease(E.prog(t, s + 0.3, s + 0.9)))
        if pour == "oil":
            mx, my = P.mouth_point(770, 640, ang, 158)
            P.oil_stream(cr, t, s + 0.85, s + 3.0, (mx, my), surf)
            oil_amount = E.ease(E.prog(t, s + 1.0, s + 3.2))
            P.oil_slick(cr, ix0, ix1, surf, t, oil_amount)
            P.pot_rim(cr, 540, 840, 560)
            P.oil_bottle(cr, 770, 640, ang)
        else:
            mx, my = P.mouth_point(760, 660, ang, 120)
            P.falling_grains(cr, t, s + 0.8, (mx, my), surf)
            P.pot_rim(cr, 540, 840, 560)
            P.shaker(cr, 760, 660, ang)
    else:
        P.pot_rim(cr, 540, 840, 560)
    E.title(cr, spec["title"], t, s, y=250, size=spec.get("title_size", 92))
    st = spec.get("stamp")
    if st:
        E.stamp(cr, st.get("text", "FALSO MITO"), 540, 620, t, ctx.at(par, st.get("at")), size=104)


# ---------------------------------------------------------------- LENS
_FIELDS = {}


def lens(cr, t, ctx, par, spec):
    """Lente d'ingrandimento sull'acqua. Strati opzionali: oil, pasta, starch, escape."""
    s = scene_start(ctx, par)
    E.background(cr)
    E.title(cr, spec["title"], t, s)
    cx, cy, r = LENS
    surface = SURF if spec.get("surface", True) else None
    layers = {l["kind"]: l for l in spec.get("layers", [])}
    pasta_y = cy + 170
    excl = [(cx - r - 50, pasta_y - 60, cx + r + 50, pasta_y + 60)] if "pasta" in layers else []
    key = (par, bool(surface), bool(excl))
    if key not in _FIELDS:
        _FIELDS[key] = molecule_field(11 + par * 7, surface=surface, exclude=excl)
    field = _FIELDS[key]

    p_open = E.ease(E.prog(t, s, s + 0.45))
    rr = E.lerp(40, r, p_open)
    cr.save()
    cr.arc(cx, cy, rr, 0, 2 * math.pi)
    cr.clip()
    water_bg(cr, surface, t)

    heat = spec.get("heat", 0.3)
    amp = E.lerp(6, 22, heat)
    # molecole d'acqua
    esc = layers.get("escape")
    esc_ids = set()
    if esc and surface is not None:
        top = sorted(range(len(field)), key=lambda i: field[i]["y"])[:12]
        esc_ids = set(random.Random(5).sample(top, 5))
    tesc = ctx.at(par, esc.get("at")) if esc else None
    fld = layers.get("field")
    fsign, falign = 1, 0.0
    if fld:
        tf = ctx.at(par, fld.get("at"))
        falign = E.ease(E.prog(t, tf, tf + 0.6))
        fsign = 1 if int(max(0.0, t - tf) / fld.get("period", 0.45)) % 2 == 0 else -1
    for i, m in enumerate(field):
        x, y, a = jiggle(m, t, amp)
        if falign > 0:
            target = 0.0 if fsign > 0 else math.pi  # ossigeno (-) verso la piastra +
            da = (target - a + math.pi) % (2 * math.pi) - math.pi
            a = a + da * falign * 0.85 + 0.15 * math.sin(t * 9 + m["ph"])
        if i in esc_ids:
            k = E.prog(t, tesc + (i % 5) * 0.25, tesc + (i % 5) * 0.25 + 1.4)
            y -= E.ease(k) * 420
        P.water_molecule(cr, x, y, 0.95, a)

    # olio: molecole grasse che salgono e si raccolgono sopra l'acqua
    oil = layers.get("oil")
    if oil and surface is not None:
        t0 = ctx.at(par, oil.get("at"))
        rnd = random.Random(21)
        for j in range(7):
            k = E.ease(E.prog(t, t0 + j * 0.12, t0 + 1.6 + j * 0.12))
            sx = cx - 300 + j * 100 + rnd.uniform(-20, 20)
            sy0 = cy + 250 - rnd.uniform(0, 120)
            ty = surface - 28 + 6 * math.sin(t * 3 + j)
            x = sx + 8 * math.sin(t * 2 + j)
            y = E.lerp(sy0, ty, k)
            if k > 0:
                P.oil_molecule(cr, x, y, 0.95, angle=0.15 * math.sin(t + j))
        if oil.get("repel_label_at"):
            pass

    # spaghetto in primo piano
    pasta = layers.get("pasta")
    if pasta:
        pp = E.ease(E.prog(t, ctx.at(par, pasta.get("at", 0.1)), ctx.at(par, pasta.get("at", 0.1)) + 0.5))
        if pp > 0:
            E.rounded_rect(cr, cx - r - 40, pasta_y - 45 + (1 - pp) * 300, 2 * r + 80, 90, 45)
            cr.set_source_rgb(*P.PASTA)
            cr.fill_preserve()
            cr.set_source_rgb(*P.PASTA_DARK)
            cr.set_line_width(5)
            cr.stroke()
    # amido che esce dalla pasta e si gonfia (colla)
    st = layers.get("starch")
    if st and pasta:
        t0 = ctx.at(par, st.get("at"))
        tg = ctx.at(par, st.get("glue_at", st.get("at")), t0 + 1.5)
        rnd = random.Random(31)
        for j in range(16):
            k = E.prog(t, t0 + j * 0.08, t0 + 1.2 + j * 0.08)
            if k <= 0:
                continue
            gx = cx - r + 40 + j * (2 * r - 80) / 15 + rnd.uniform(-10, 10)
            gy = pasta_y - 40 - E.ease(k) * rnd.uniform(30, 90)
            swell = E.ease(E.prog(t, tg, tg + 1.2))
            P.starch_grain(cr, gx, gy, 9 + 14 * swell)
        swell = E.ease(E.prog(t, tg, tg + 1.2))
        if swell > 0:
            E.rounded_rect(cr, cx - r - 40, pasta_y - 70, 2 * r + 80, 40, 20)
            cr.set_source_rgba(*P.STARCH, 0.55 * swell)
            cr.fill()
    cr.restore()
    E.lens_frame(cr, cx, cy, rr)
    if fld and falign > 0:
        P.field_plates(cr, cx, cy, r, fsign, alpha=falign)
    th = spec.get("thermo")
    if th:
        a0 = ctx.at(par, th.get("start", 0))
        a1 = ctx.at(par, th.get("end", 1.5))
        k = E.ease(E.prog(t, a0, a1))
        val = int(E.lerp(th.get("from", 20), th.get("to", 100), k))
        E.thermo_pill(cr, 540, 1270, f"{val} °C", t, a0, hot=k)
    labels(cr, t, ctx, par, spec.get("labels"))


# ---------------------------------------------------------------- POT
def pot_scene(cr, t, ctx, par, spec):
    """Pentola con pasta: strato d'olio, pasta che si incolla, mestolo che gira."""
    s = scene_start(ctx, par)
    E.background(cr)
    E.title(cr, spec["title"], t, s)
    top, w, h = 760, 600, 460
    ix0, ix1, surf, bot = P.kitchen_pot(cr, t, top=top, w=w, h=h, water_level=0.7)
    oil_at = spec.get("oil_at")
    oil_amount = 1.0 if oil_at == "always" else (E.ease(E.prog(t, ctx.at(par, oil_at), ctx.at(par, oil_at) + 1.0)) if oil_at else 0)
    clump = E.ease(E.prog(t, ctx.at(par, spec["clump_at"]), ctx.at(par, spec["clump_at"]) + 1.0)) if spec.get("clump_at") else 0
    sep = 0.0
    if spec.get("stir_at"):
        ts = ctx.at(par, spec["stir_at"])
        sep = E.ease(E.prog(t, ts, ts + 0.8))
        clump *= 1 - sep
    cr.save()
    E.rounded_rect(cr, ix0, surf - 260, ix1 - ix0, bot - surf + 260, 18)
    cr.clip()
    # pasta cotta: completamente sommersa (coerente con 'l'olio non la tocca')
    h_sub = (bot - surf) - 45 if spec.get("submerged", True) else 360
    P.spaghetti(cr, ix0, ix1, bot, t, n=16, clump=clump, separate=sep, height=h_sub)
    # bolle d'ebollizione
    rnd = random.Random(4)
    for j in range(10):
        ph = (t * 0.5 + j * 0.1) % 1.0
        bx = rnd.uniform(ix0 + 30, ix1 - 30)
        P.bubble(cr, bx, E.lerp(bot - 20, surf + 10, ph), 6 + 10 * ph, 1 - ph * 0.5)
    cr.restore()
    P.oil_slick(cr, ix0, ix1, surf, t, oil_amount)
    P.pot_rim(cr, 540, top, w)
    if sep > 0:
        ang = 0.25 * math.sin((t - ctx.at(par, spec["stir_at"])) * 5)
        P.spoon(cr, 540 + 120 * math.sin((t - ctx.at(par, spec["stir_at"])) * 3), bot - 60, ang)
    labels(cr, t, ctx, par, spec.get("labels"))


# ---------------------------------------------------------------- NUMBER
def number(cr, t, ctx, par, spec):
    s = scene_start(ctx, par)
    E.background(cr)
    E.title(cr, spec["title"], t, s, y=270, size=spec.get("title_size", 104))
    card = spec.get("card")
    if card:
        t0 = ctx.at(par, card.get("at", 0.2))
        p = E.ease_out_back(E.prog(t, t0, t0 + 0.4))
        if p > 0:
            cr.save()
            cr.translate(540, 560)
            cr.scale(p, p)
            E.rounded_rect(cr, -400, -110, 800, 220, 40)
            cr.set_source_rgb(*E.WHITE)
            cr.fill_preserve()
            cr.set_source_rgb(*E.INK)
            cr.set_line_width(7)
            cr.stroke()
            E.outlined_text(cr, card["main"], -20, 30, 92, fill=E.INK, lw=0, anchor="right")
            E.outlined_text(cr, card.get("sub", ""), 10, 30, 62, fill=E.STEEL_DARK, lw=0, anchor="left")
            cr.restore()
    big = spec.get("big")
    if big:
        t0 = ctx.at(par, big.get("at"))
        p2 = E.ease_out_back(E.prog(t, t0 - 0.3, t0 + 0.1))
        if p2 > 0:
            cr.save()
            cr.translate(540, 920)
            cr.scale(p2, p2)
            E.outlined_text(cr, big["text"], 0, 0, big.get("size", 180), fill=E.YELLOW, lw=18)
            cr.restore()
    labels(cr, t, ctx, par, spec.get("labels"))


# ---------------------------------------------------------------- CHECKLIST
def checklist(cr, t, ctx, par, spec):
    s = scene_start(ctx, par)
    E.background(cr)
    E.title(cr, spec["title"], t, s)
    if spec.get("prop") == "pasta_pot":
        ix0, ix1, surf, bot = P.kitchen_pot(cr, t, top=920, w=500, h=320)
        cr.save()
        E.rounded_rect(cr, ix0, surf - 300, ix1 - ix0, bot - surf + 300, 18)
        cr.clip()
        P.spaghetti(cr, ix0, ix1, bot, t, height=300)
        cr.restore()
        P.pot_rim(cr, 540, 920, 500)
    for i, it in enumerate(spec["items"]):
        P.check_card(cr, 540, 520 + i * 200, it["text"], it["ok"], t, ctx.at(par, it.get("at", 0.2 + i)))
    labels(cr, t, ctx, par, spec.get("labels"))


# ---------------------------------------------------------------- END
def end(cr, t, ctx, par, spec):
    s = scene_start(ctx, par)
    E.background(cr)
    p = E.ease_out_back(E.prog(t, s, s + 0.4))
    cr.save()
    cr.translate(540, 560)
    cr.scale(p, p)
    E.outlined_text(cr, spec.get("line", "IL PROSSIMO"), 0, 0, 100, fill=E.WHITE, lw=14)
    cr.restore()
    E.stamp(cr, spec.get("stamp", "FALSO MITO"), 540, 760, t, s + 0.4, size=120)
    tg = ctx.at(par, spec.get("follow_at", 0.2))
    handle = spec.get("handle", "@unmillimetrosotto")
    pb = E.ease_out_back(E.prog(t, tg + 0.5, tg + 0.85))
    if pb > 0:
        press = 1 - 0.08 * math.sin(E.clamp((t - tg - 1.4) / 0.25) * math.pi)
        cr.save()
        cr.translate(540, 1060)
        cr.scale(pb * press, pb * press)
        ext = E.text_extents(cr, handle, 54)
        w = ext.x_advance + 250
        E.rounded_rect(cr, -w / 2, -75, w, 150, 75)
        cr.set_source_rgb(*E.WHITE)
        cr.fill_preserve()
        cr.set_source_rgb(*E.INK)
        cr.set_line_width(7)
        cr.stroke()
        E.outlined_text(cr, handle, -w / 2 + 42, 19, 54, fill=E.INK, lw=0, anchor="left")
        bx = w / 2 - 105
        E.rounded_rect(cr, bx - 75, -48, 150, 96, 48)
        cr.set_source_rgb(0.25, 0.4, 0.98)
        cr.fill()
        E.outlined_text(cr, "SEGUI", bx, 18, 40, fill=E.WHITE, lw=0)
        cr.restore()


def section(cr, t, ctx, par, spec):
    """Sezione di un cibo: banda esterna scaldata dalle microonde, poi il calore entra per conduzione."""
    s = scene_start(ctx, par)
    E.background(cr)
    E.title(cr, spec["title"], t, s)
    x0, y0, w, h = 140, 520, 800, 560
    t_pen = ctx.at(par, spec.get("penetrate_at", 0.2))
    t_con = ctx.at(par, spec.get("conduct_at"), t_pen + 3) if spec.get("conduct_at") else None
    pen = E.ease(E.prog(t, t_pen, t_pen + 0.8))
    con = E.ease(E.prog(t, t_con, t_con + 3.0)) if t_con else 0.0
    depth = spec.get("depth_px", 110)
    cold, hot = (0.33, 0.62, 0.95), (0.95, 0.35, 0.22)
    # griglia di celle: temperatura = funzione della distanza dal bordo
    n = 24
    cw, ch = w / n, h / (n * h / w)
    rows = int(h / cw)
    for i in range(n):
        for j in range(rows):
            cxp, cyp = x0 + (i + 0.5) * cw, y0 + (j + 0.5) * cw
            dist = min(cxp - x0, x0 + w - cxp, cyp - y0, y0 + h - cyp)
            # la conduzione avanza ma NON arriva al centro: il centro resta freddo
            reach = depth * pen + (min(w, h) / 2 - depth) * con * 0.5
            k = E.clamp(1 - (dist - depth * pen * 0.6) / max(1, reach - depth * pen * 0.6 + 60)) if reach > 0 else 0
            if dist <= depth * pen:
                k = max(k, 0.85 * pen)
            col = tuple(E.lerp(c0, c1, k) for c0, c1 in zip(cold, hot))
            cr.rectangle(x0 + i * cw, y0 + j * cw, cw + 0.5, cw + 0.5)
            cr.set_source_rgb(*col)
            cr.fill()
    E.rounded_rect(cr, x0, y0, w, rows * cw, 24)
    cr.set_source_rgb(*E.INK)
    cr.set_line_width(8)
    cr.stroke()
    # quota della profondità
    if pen > 0.9 and spec.get("depth_label"):
        a = E.prog(t, t_pen + 0.8, t_pen + 1.1)
        yy = y0 - 30
        cr.move_to(x0, yy)
        cr.line_to(x0 + depth, yy)
        cr.set_source_rgba(*E.YELLOW, a)
        cr.set_line_width(6)
        cr.stroke()
        for xx in (x0, x0 + depth):
            cr.move_to(xx, yy - 14)
            cr.line_to(xx, yy + 14)
            cr.stroke()
        E.outlined_text(cr, spec["depth_label"], x0 + depth + 20, yy + 14, 44, fill=E.YELLOW, lw=8, anchor="left", alpha=a)
    # frecce di conduzione verso il centro
    if con > 0:
        mx, my = x0 + w / 2, y0 + rows * cw / 2
        for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
            ph = (t * 0.8) % 1.0
            d0 = E.lerp(min(w, h) / 2 - 40, 60, ph)
            px, py = mx + d0 * math.cos(ang), my + d0 * math.sin(ang)
            cr.arc(px, py, 12, 0, 2 * math.pi)
            cr.set_source_rgba(1, 0.9, 0.6, 0.9 * con)
            cr.fill()
    labels(cr, t, ctx, par, spec.get("labels"))


TYPES = {"hook": hook, "lens": lens, "pot": pot_scene, "number": number, "checklist": checklist, "end": end, "section": section}
