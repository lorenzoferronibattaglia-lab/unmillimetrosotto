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
    payoff = spec.get("mode") == "payoff"
    if payoff:
        # gancio v2: movimento dal fotogramma 0 (lieve zoom continuo), titolo subito visibile
        z = 1.0 + 0.05 * E.clamp((t - s) / 6.0)
        cr.save()
        cr.translate(540, 1000)
        cr.scale(z, z)
        cr.translate(-540, -1000)
        s_title = s - 1.0
    else:
        s_title = s
    stamp_col = None
    if spec.get("stamp", {}).get("color") == "green":
        stamp_col = P.GREEN_OK
    if pr.get("appliance") in ("pot_lid", "wine_glass", "water_glass_ice", "bottle_spoon", "oil_pot", "pasta_pot", "microwave2"):
        if pr["appliance"] == "water_glass_ice":
            P.glass_of(cr, 540, 1320, fill=0.62, t=t, ice=4, scale=1.1)
        elif pr["appliance"] == "bottle_spoon":
            P.glass_of(cr, 330, 1330, liquid=(0.97, 0.90, 0.55), fill=0.55, t=t, scale=0.7, bubbles=True)
            # bottiglia aperta, cucchiaino col manico nel collo e la conca fuori
            P.teaspoon(cr, 640, 1330 - 600, scale=0.9)
            P.wine_bottle(cr, 640, 1330, scale=1.0, angle=0.0, label="SPUMANTE", cork=False)
            cr.save()
            cr.rectangle(560, 1330 - 610, 160, 52)
            cr.clip()
            P.teaspoon(cr, 640, 1330 - 600, scale=0.9)
            cr.restore()
            P.steam(cr, 640, 1330 - 700, t, n=3, alpha=0.35, spread=30)
        elif pr["appliance"] in ("oil_pot", "pasta_pot"):
            liq = (P.OIL, P.OIL_DARK) if pr["appliance"] == "oil_pot" else None
            fire = 1.0
            if pr.get("fire_off_at") is not None:
                fire = 1 - E.ease(E.prog(t, ctx.at(par, pr["fire_off_at"]), ctx.at(par, pr["fire_off_at"]) + 0.6))
            ix0, ix1, surf, bot = P.kitchen_pot(cr, t, top=860, w=560, h=380, liquid=liq, fire=fire)
            if pr["appliance"] == "pasta_pot":
                cr.save()
                E.rounded_rect(cr, ix0, surf - 200, ix1 - ix0, bot - surf + 200, 18)
                cr.clip()
                P.spaghetti(cr, ix0, ix1, bot, t, height=bot - surf - 45)
                cr.restore()
                if pr.get("lid_at") is not None:
                    tl = ctx.at(par, pr["lid_at"])
                    kl = E.ease(E.prog(t, tl, tl + 0.5))
                    if kl > 0:
                        P.pot_rim(cr, 540, 860, 560)
                        P.lid(cr, 540, 852, 560, lift=E.lerp(260, 4, kl))
            else:
                rnd = random.Random(2)
                for j in range(14):
                    ph = (t * 0.9 + j * 0.07) % 1.0
                    P.bubble(cr, rnd.uniform(ix0 + 30, ix1 - 30), E.lerp(bot - 20, surf + 8, ph), 5 + 6 * ph, 1 - ph * 0.4)
            P.pot_rim(cr, 540, 860, 560)
        elif pr["appliance"] == "microwave2":
            on = E.ease(E.prog(t, s - 1, s - 0.5))
            P.microwave(cr, 540, 1000, 860, 560, t, on=on, heat=0.3)
        elif pr["appliance"] == "pot_lid":
            ix0, ix1, surf, bot = P.kitchen_pot(cr, t, top=860, w=560, h=380)
            P.pot_rim(cr, 540, 860, 560)
            P.steam(cr, 540 - 300, 820, t, n=3, alpha=0.5, spread=60)
            P.lid(cr, 540, 852, 560, lift=6 + 4 * math.sin(t * 9))
        else:
            P.wine_glass(cr, 540, 1330, scale=1.05, fill=0.4, t=t)
        th = pr.get("thermo")
        if payoff:
            cr.restore()
        if th:
            a0, a1 = ctx.at(par, th.get("start", 0)), ctx.at(par, th.get("end", 3))
            k = E.ease(E.prog(t, a0, a1))
            v = E.lerp(th.get("from", 20), th.get("to", 100), k)
            E.thermo_pill(cr, th.get("x", 300), th.get("y", 770), f"{v:.0f} °C", t, s - 1, hot=th.get("hot", 0.6))
        E.title(cr, spec["title"], t, s_title, y=250, size=spec.get("title_size", 92))
        st = spec.get("stamp")
        if st:
            E.stamp(cr, st.get("text", "FALSO MITO"), 540, 610, t, ctx.at(par, st.get("at")), size=104, color=stamp_col)
        return
    if pr.get("appliance") == "ice_bucket":
        frost = E.ease(E.prog(t, ctx.at(par, pr.get("frost_at", 0.5)), ctx.at(par, pr.get("frost_at", 0.5)) + 2.0))
        l0, r0, surf, bot = P.ice_bucket(cr, 540, 860, 640, 470, t, frost=frost)
        # spargisale gia' inclinato e che versa dal primo fotogramma (tappo verso la pentola: angolo negativo)
        ang = -2.3
        mx, my = P.mouth_point(800, 620, ang, 120)
        P.falling_grains(cr, t, s - 1.5, (mx, my), surf, n=60, gap=0.07)
        P.shaker(cr, 800, 620, ang)
        th = pr.get("thermo")
        if payoff:
            cr.restore()
        if th:
            a0, a1 = ctx.at(par, th.get("start", 0)), ctx.at(par, th.get("end", 3))
            k = E.ease(E.prog(t, a0, a1))
            v = E.lerp(th.get("from", 0), th.get("to", -10), k)
            E.thermo_pill(cr, 300, 770, f"{v:.0f} °C".replace("-", "−"), t, s - 1, hot=0.1)
        E.title(cr, spec["title"], t, s_title, y=250, size=spec.get("title_size", 92))
        st = spec.get("stamp")
        if st:
            E.stamp(cr, st.get("text", "FALSO MITO"), 540, 610, t, ctx.at(par, st.get("at")), size=104, color=stamp_col)
        return
    if pr.get("appliance") == "microwave":
        on = E.ease(E.prog(t, s + 0.3, s + 0.8))
        P.microwave(cr, 540, 1000, 860, 560, t, on=on, heat=0.55 * E.ease(E.prog(t, s + 0.5, s + 4)))
        E.title(cr, spec["title"], t, s, y=250, size=spec.get("title_size", 92))
        st = spec.get("stamp")
        if st:
            E.stamp(cr, st.get("text", "FALSO MITO"), 540, 610, t, ctx.at(par, st.get("at")), size=104)
        return
    liq = None
    if pr.get("liquid") == "sugo":
        liq = ((0.82, 0.20, 0.13), (0.62, 0.12, 0.08))
    ix0, ix1, surf, bot = P.kitchen_pot(cr, t, top=840, liquid=liq)
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
            P.shaker(cr, 760, 660, ang, label=pr.get("label", "SALE"))
    else:
        P.pot_rim(cr, 540, 840, 560)
    E.title(cr, spec["title"], t, s, y=250, size=spec.get("title_size", 92))
    st = spec.get("stamp")
    if st:
        E.stamp(cr, st.get("text", "FALSO MITO"), 540, 620, t, ctx.at(par, st.get("at")), size=104, color=stamp_col)


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
    if "ice" in layers:  # il liquido sta solo sotto il reticolo del ghiaccio
        excl.append((cx - r - 100, cy - r - 100, cx + r + 100, cy - r + 70 + 4 * 86 * 0.87 - 10))
    key = (par, bool(surface), len(excl))
    if key not in _FIELDS:
        _FIELDS[key] = molecule_field(11 + par * 7, surface=surface, exclude=excl)
    field = _FIELDS[key]

    p_open = 1.0 if spec.get("no_open") else E.ease(E.prog(t, s, s + 0.45))
    rr = E.lerp(40, r, p_open)
    cr.save()
    cr.arc(cx, cy, rr, 0, 2 * math.pi)
    cr.clip()
    if spec.get("bg"):
        import cairo as _c
        h = spec["bg"].lstrip("#")
        bc = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        g = _c.LinearGradient(0, cy - r, 0, cy + r)
        g.add_color_stop_rgb(0, *[min(1, c * 1.12) for c in bc])
        g.add_color_stop_rgb(1, *[c * 0.85 for c in bc])
        cr.set_source(g)
        cr.paint()
    else:
        water_bg(cr, surface, t)
    if spec.get("tint"):
        h = spec["tint"].lstrip("#")
        tc = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        cr.set_source_rgba(*tc, spec.get("tint_alpha", 0.45))
        cr.paint()

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
    falign, fs = 0.0, 1.0
    if fld:
        tf = ctx.at(par, fld.get("at"))
        falign = E.ease(E.prog(t, tf, tf + 0.8))
        half = max(1.0, fld.get("period", 1.2))  # mai piu' di un'inversione al secondo
        # inversione FLUIDA (coseno): niente scatti, niente lampi
        fs = math.cos(math.pi * max(0.0, t - tf) / half)
    lidl = layers.get("lid")
    wpos = []
    hide_water = spec.get("water", True) is False
    for i, m in enumerate(field):
        x, y, a = jiggle(m, t, amp)
        if falign > 0:
            target = math.pi * (1 - fs) / 2  # 0 con + in alto, pi con + in basso
            da = (target - a + math.pi) % (2 * math.pi) - math.pi
            a = a + da * falign * 0.85
        if i in esc_ids:
            if lidl:
                # col coperchio: salgono, sbattono e ricadono (ciclo continuo)
                ph = ((t - tesc) * 0.6 + (i % 5) * 0.2) % 1.0 if t > tesc else 0.0
                # rimbalzano SOTTO il coperchio (cy - r + 70): mai attraverso
                hop = math.sin(ph * math.pi) * max(0.0, min(230, y - (cy - r + 70) - 35))
                y -= hop
            else:
                k = E.prog(t, tesc + (i % 5) * 0.25, tesc + (i % 5) * 0.25 + 1.4)
                y -= E.ease(k) * 420
        wpos.append((x, y))
        if not hide_water:
            P.water_molecule(cr, x, y, 0.95, a)

    # zuccheri: anelli che trattengono l'acqua (con "bind_at" compaiono i legami verso le molecole vicine)
    sug = layers.get("sugar")
    if sug:
        ts0 = ctx.at(par, sug.get("at", 0.0))
        tb = ctx.at(par, sug["bind_at"]) if sug.get("bind_at") else None
        rnd = random.Random(91)
        spots = []
        while len(spots) < sug.get("n", 11):
            px, py = rnd.uniform(cx - r + 60, cx + r - 60), rnd.uniform(cy - r + 60, cy + r - 60)
            if math.hypot(px - cx, py - cy) < r - 60 and all(math.hypot(px - a, py - b) > 120 for a, b in spots):
                if not (layers.get("microbe") and math.hypot(px - (cx + 20), py - (cy + 70)) < 170):
                    spots.append((px, py))
        for j, (px, py) in enumerate(spots):
            k = E.ease(E.prog(t, ts0 + j * 0.05, ts0 + 0.4 + j * 0.05))
            if k <= 0:
                continue
            x, y = px + 6 * math.sin(t * 2.2 + j), py + 6 * math.cos(t * 1.9 + j)
            if tb is not None:
                kb = E.ease(E.prog(t, tb + j * 0.04, tb + 0.6 + j * 0.04))
                if kb > 0 and wpos:
                    near = sorted(wpos, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)[:3]
                    cr.set_source_rgba(1, 1, 1, 0.85 * kb)
                    cr.set_line_width(4)
                    cr.set_dash([7, 6])
                    for qx, qy in near:
                        cr.move_to(x, y)
                        cr.line_to(E.lerp(x, qx, kb), E.lerp(y, qy, kb))
                    cr.stroke()
                    cr.set_dash([])
            P.sugar_ring(cr, x, y, 30 * k, angle=0.3 * math.sin(t + j))

    # batterio: compare con "at", con "dry_at" perde acqua e si raggrinzisce
    mic = layers.get("microbe")
    if mic:
        tm0 = ctx.at(par, mic.get("at", 0.0))
        k = E.ease_out_back(E.prog(t, tm0, tm0 + 0.45))
        td = ctx.at(par, mic["dry_at"]) if mic.get("dry_at") else None
        shr = E.ease(E.prog(t, td, td + 2.2)) if td is not None else 0.0
        mx, my = cx + 20, cy + 70
        if k > 0:
            if td is not None and t > td:
                for j in range(7):
                    kk = E.ease(E.prog(t, td + j * 0.18, td + 1.4 + j * 0.18))
                    ang = j * 2 * math.pi / 7 + 0.4
                    P.water_molecule(cr, mx + math.cos(ang) * E.lerp(30, 230, kk), my + math.sin(ang) * E.lerp(20, 200, kk), 0.8, ang)
            P.microbe(cr, mx, my, scale=1.5 * k, shrink=shr, t=t)

    # catene di amido: disordinate e morbide; con "align_at" si riordinano e si irrigidiscono, con "melt_at" si sciolgono
    ch = layers.get("chains")
    if ch:
        ta = ctx.at(par, ch["align_at"]) if ch.get("align_at") else None
        tmc = ctx.at(par, ch["melt_at"]) if ch.get("melt_at") else None
        ka = E.ease(E.prog(t, ta, ta + 1.6)) if ta is not None else float(ch.get("start_aligned", 0))
        km = E.ease(E.prog(t, tmc, tmc + 1.6)) if tmc is not None else 0.0
        k = ka * (1 - km)
        for j in range(6):
            pts = []
            for b in range(10):
                bx = cx - 290 + b * 64
                ph = j * 1.7
                y_dis = cy - 220 + j * 85 + 60 * math.sin(bx * 0.018 + ph) + 35 * math.sin(bx * 0.043 + ph * 2 + t * 1.5)
                y_ord = cy - 120 + j * 46 + 3 * math.sin(t * 4 + b + j)
                x = E.lerp(bx + 10 * math.sin(t * 2 + b + j), cx - 260 + b * 58, k)
                pts.append((x, E.lerp(y_dis, y_ord, k)))
            cr.set_source_rgb(*E.INK)
            cr.set_line_width(7)
            for b, (x, y) in enumerate(pts):
                (cr.move_to if b == 0 else cr.line_to)(x, y)
            cr.stroke()
            for x, y in pts:
                E.circle(cr, x, y, 15, (0.97, 0.92, 0.78), lw=4)
        if k > 0.05:
            cr.set_source_rgba(1, 1, 1, 0.5 * k)
            cr.set_line_width(3)
            cr.set_dash([6, 8])
            for j in range(5):
                yy = cy - 120 + j * 46 + 23
                cr.move_to(cx - 280, yy)
                cr.line_to(cx + 280, yy)
            cr.stroke()
            cr.set_dash([])

    # ioni H+ (acidita'): con "neutralize_at" spariscono uno dopo l'altro
    ion = layers.get("ions")
    if ion:
        tn = ctx.at(par, ion["neutralize_at"]) if ion.get("neutralize_at") else None
        ti0 = ctx.at(par, ion.get("at", 0.0))
        rnd = random.Random(101)
        for j in range(ion.get("n", 9)):
            px = cx - r + 80 + rnd.uniform(0, 2 * r - 160)
            py = cy - r + 90 + rnd.uniform(0, 2 * r - 180)
            if math.hypot(px - cx, py - cy) > r - 50:
                px, py = cx + (px - cx) * 0.6, cy + (py - cy) * 0.6
            a = E.ease(E.prog(t, ti0 + j * 0.06, ti0 + 0.4 + j * 0.06))
            if tn is not None:
                a *= 1 - E.ease(E.prog(t, tn + j * 0.15, tn + 0.5 + j * 0.15))
            if a > 0.01:
                P.h_ion(cr, px + 8 * math.sin(t * 3 + j), py + 8 * math.cos(t * 2.6 + j), alpha=a, scale=E.lerp(0.6, 1.0, a))

    # ghiaccio: reticolo ordinato nella meta' alta della lente; con "melt_at" si smonta dal basso
    ice = layers.get("ice")
    if ice:
        tm = ctx.at(par, ice["melt_at"]) if ice.get("melt_at") else None
        ions_at = ctx.at(par, ice["ions_at"]) if ice.get("ions_at") else None
        rows_n, cols_n, sp = 4, 7, 86
        for rr_ in range(rows_n):
            for cc in range(cols_n):
                bx = cx - 3 * sp + cc * sp + (sp / 2 if rr_ % 2 else 0) - (sp / 4)
                by = cy - r + 70 + rr_ * sp * 0.87
                ang = 0.0 if (rr_ + cc) % 2 == 0 else math.pi
                x, y = bx + 2 * math.sin(t * 6 + cc + rr_), by
                if tm is not None:
                    order = (rows_n - 1 - rr_) * 0.35 + (cc % 3) * 0.12
                    k = E.ease(E.prog(t, tm + order, tm + order + 1.4))
                    x += k * 40 * math.sin(cc * 1.7 + rr_)
                    y += k * (140 + 30 * cc % 3)
                    ang += k * 2.0 * math.sin(t * 3 + cc)
                P.water_molecule(cr, x, y, 0.85, ang)
        # legami del reticolo (spariscono mentre fonde)
        if tm is None or t < tm + 0.6:
            alpha = 1.0 if tm is None else 1 - E.prog(t, tm, tm + 0.6)
            cr.set_source_rgba(1, 1, 1, 0.5 * alpha)
            cr.set_line_width(3)
            cr.set_dash([8, 8])
            for rr_ in range(rows_n):
                y = cy - r + 70 + rr_ * sp * 0.87
                cr.move_to(cx - 3.5 * sp, y)
                cr.line_to(cx + 3.5 * sp, y)
            cr.stroke()
            cr.set_dash([])
        if ions_at is not None:
            rnd = random.Random(44)
            for j in range(6):
                k = E.ease(E.prog(t, ions_at + j * 0.15, ions_at + 1.0 + j * 0.15))
                if k <= 0:
                    continue
                ix = cx - 250 + j * 100
                iy = E.lerp(cy + r + 60, cy - r + 190 + (j % 2) * 60, k)
                P.E.circle  # noqa (riferimento per chiarezza)
                import props as _P  # noqa
                ion_kind = "na" if j % 2 == 0 else "cl"
                E.circle(cr, ix, iy, 24 if ion_kind == "na" else 32, P.__dict__.get("NA_COL", (0.58, 0.40, 0.92)) if ion_kind == "na" else (0.30, 0.80, 0.45), lw=4)
                E.outlined_text(cr, "+" if ion_kind == "na" else "−", ix, iy + 12, 36, fill=E.WHITE, lw=0)

    # etanolo: molecole di alcol mescolate all'acqua; con "rise_at" salgono ed escono dalla superficie
    eth = layers.get("ethanol")
    if eth:
        tr = ctx.at(par, eth["rise_at"]) if eth.get("rise_at") else None
        rnd = random.Random(61)
        for j in range(eth.get("n", 7)):
            bx = cx - 280 + j * 95 + rnd.uniform(-20, 20)
            by = cy + rnd.uniform(-40, 230)
            x, y = bx + 8 * math.sin(t * 3 + j), by + 6 * math.cos(t * 2.5 + j)
            if tr is not None and j % 2 == 0:
                k = E.ease(E.prog(t, tr + j * 0.18, tr + j * 0.18 + 1.6))
                y = E.lerp(y, (surface or cy - r) - 140 - (j % 3) * 50, k)
            P.ethanol(cr, x, y, 0.95, angle=0.3 * math.sin(t + j))
    # anidride carbonica che sale e scappa dalla superficie (bottiglia aperta)
    gas = layers.get("co2")
    if gas:
        tg0 = ctx.at(par, gas.get("at", 0.0))
        rnd = random.Random(81)
        for j in range(12):
            bx = cx - r + 60 + rnd.uniform(0, 2 * r - 120)
            if gas.get("from_zero") and t < tg0:
                continue
            ph = ((t - tg0) * 0.35 + j / 12) % 1.0 if t > tg0 else (j / 12) * 0.3
            yb = E.lerp(cy + r - 40, (surface or cy - r) - 260, ph)
            P.co2(cr, bx + 10 * math.sin(t * 2 + j), yb, 0.85, angle=0.4 * math.sin(t + j))

    # coperchio in cima alla lente
    if lidl:
        tl = ctx.at(par, lidl.get("at", 0.0))
        k = E.ease(E.prog(t, tl, tl + 0.5))
        if k > 0:
            ly = E.lerp(cy - r - 80, cy - r + 70, k)
            E.rounded_rect(cr, cx - r - 20, ly - 40, 2 * r + 40, 40, 10)
            cr.set_source_rgb(*E.STEEL)
            cr.fill_preserve()
            cr.set_source_rgb(*E.INK)
            cr.set_line_width(6)
            cr.stroke()

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
            rod_col = (0.35, 0.70, 0.30) if pasta.get("veg") else P.PASTA
            rod_dark = (0.20, 0.45, 0.18) if pasta.get("veg") else P.PASTA_DARK
            cr.set_source_rgb(*rod_col)
            cr.fill_preserve()
            cr.set_source_rgb(*rod_dark)
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
    # vitamine dentro la verdura che, con "leach_at", escono nell'acqua (amount = quanta parte esce)
    vit = layers.get("vitamins")
    if vit and layers.get("pasta"):
        tl = ctx.at(par, vit["leach_at"]) if vit.get("leach_at") else None
        amount = vit.get("amount", 0.5)
        rnd = random.Random(71)
        nv = 10
        for j in range(nv):
            vx = cx - r + 50 + j * (2 * r - 100) / (nv - 1)
            vy = pasta_y
            leaves = j < round(nv * amount)
            if tl is not None and leaves:
                k = E.ease(E.prog(t, tl + j * 0.1, tl + 1.4 + j * 0.1))
                vx += k * rnd.uniform(-60, 60)
                vy -= k * rnd.uniform(140, 260)
            P.vitamin(cr, vx, vy, 20)
    cr.restore()
    E.lens_frame(cr, cx, cy, rr)
    if fld and falign > 0:
        P.field_plates(cr, cx, cy, r, fs, alpha=falign)
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
            # main + sub centrati insieme, rimpiccioliti se non entrano nella scheda
            ms, ss = 92, 62
            while ms > 50:
                wm = E.text_extents(cr, card["main"], ms).x_advance
                ws = E.text_extents(cr, card.get("sub", ""), ss).x_advance
                if wm + ws + 24 <= 720:
                    break
                ms, ss = ms - 6, ss - 4
            x0 = -(wm + ws + 24) / 2
            E.outlined_text(cr, card["main"], x0, 30, ms, fill=E.INK, lw=0, anchor="left")
            E.outlined_text(cr, card.get("sub", ""), x0 + wm + 24, 30, ss, fill=E.STEEL_DARK, lw=0, anchor="left")
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
    st_txt = spec.get("stamp", "FALSO MITO")
    st_size = 120
    while st_size > 70 and E.text_extents(cr, st_txt, st_size).x_advance > 780:
        st_size -= 6
    E.stamp(cr, st_txt, 540, 760, t, s + 0.4, size=st_size)
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


# ---------------------------------------------------------------- REAL (ripresa reale in apertura)
import os as _os
import subprocess as _sp
import cairo as _cairo

_CLIP_CACHE = {}


def _clip_frames(path):
    """Estrae una volta i fotogrammi del clip (PNG, 30 fps) e li tiene in cache su disco."""
    if path in _CLIP_CACHE:
        return _CLIP_CACHE[path]
    d = path + ".frames"
    if not _os.path.isdir(d) or not _os.listdir(d):
        _os.makedirs(d, exist_ok=True)
        _sp.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf",
                 f"fps={E.FPS},scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
                 _os.path.join(d, "f%04d.png")], check=True)
    files = sorted(_os.path.join(d, f) for f in _os.listdir(d) if f.endswith(".png"))
    _CLIP_CACHE[path] = files
    return files


def scene_end(ctx, par):
    nxt = ctx.par_start.get(par + 1)
    return nxt - 0.15 if nxt is not None else ctx.dur + 0.8


def real(cr, t, ctx, par, spec):
    """Ripresa reale (clip) a tutto schermo con titolo e timbro; nell'ultimo tratto l'inquadratura
    si stringe in un cerchio che coincide con la lente della scena dopo: il tuffo 'un millimetro sotto'."""
    s0, s1 = scene_start(ctx, par), scene_end(ctx, par)
    here = _os.path.dirname(_os.path.abspath(__file__))
    files = _clip_frames(_os.path.join(here, spec["clip"]))
    n = len(files)
    speed = min(1.0, (n - 1) / max(1.0, (s1 - s0) * E.FPS))
    idx = int(E.clamp((t - s0) * E.FPS * speed, 0, n - 1))
    img = _cairo.ImageSurface.create_from_png(files[idx])
    dive = spec.get("dive", True)
    k = E.ease(E.prog(t, s1 - 0.7, s1)) if dive else 0.0
    cx, cy, r_end = LENS
    # coordinate della scena: il frame è traslato di +60 in y, il video copre tutto lo schermo
    r = E.lerp(1250, r_end, k)
    zoom = 1.0 + 0.6 * k
    E.background(cr)
    cr.save()
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.clip()
    cr.translate(cx, cy)
    cr.scale(zoom, zoom)
    cr.translate(-cx, -cy)
    cr.translate(0, -60)
    cr.scale(E.W / 720, E.H / 1280)
    cr.set_source_surface(img, 0, 0)
    cr.get_source().set_filter(_cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()
    if k > 0:
        E.lens_frame(cr, cx, cy, r) if r < 900 else None
    # velo scuro in alto per leggere il titolo
    g = _cairo.LinearGradient(0, -60, 0, 560)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.62 * (1 - k))
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    cr.rectangle(0, -60, E.W, 620)
    cr.set_source(g)
    cr.fill()
    E.title(cr, spec["title"], t, s0 - 1.0, y=250, size=spec.get("title_size", 92))
    st = spec.get("stamp")
    if st:
        col = P.GREEN_OK if st.get("color") == "green" else None
        E.stamp(cr, st.get("text", "FALSO MITO"), 540, 610, t, ctx.at(par, st.get("at")), size=104, color=col)


# ---------------------------------------------------------------- EGG
def egg_scene(cr, t, ctx, par, spec):
    """mode "section": uovo in sezione, camera d'aria che cresce (grow_at), acqua che esce e aria che entra (pores_at).
    mode "glasses": tre bicchieri d'acqua con uovo fresco (sdraiato), di qualche settimana (in piedi), vecchio (galleggia)."""
    s = scene_start(ctx, par)
    E.background(cr)
    E.title(cr, spec["title"], t, s)
    if spec.get("mode", "section") == "section":
        cx, cy = 540, 900
        tg = ctx.at(par, spec["grow_at"]) if spec.get("grow_at") else None
        tp = ctx.at(par, spec["pores_at"]) if spec.get("pores_at") else None
        a0, a1 = spec.get("air_from", 0.07), spec.get("air_to", 0.30)
        air = E.lerp(a0, a1, E.ease(E.prog(t, tg, tg + 2.6))) if tg is not None else a0
        pin = E.ease_out_back(E.prog(t, s, s + 0.45))
        cr.save()
        cr.translate(cx, cy)
        cr.scale(pin, pin)
        cr.translate(-cx, -cy)
        P.egg_section(cr, cx, cy, air=air)
        cr.restore()
        if tp is not None and t > tp:
            for j in range(10):
                th = 2 * math.pi * (j + 0.5) / 10 + 0.15
                x, y, nx, ny = P.egg_point(th)
                ph = ((t - tp) * 0.45 + j / 10) % 1.0
                d = E.lerp(-40, 150, ph)
                al = min(1.0, (t - tp) * 2) * (1 - ph * 0.6)
                P.water_molecule(cr, cx + x + nx * d, cy + y + ny * d, 0.8, th, alpha=al)
            for j in range(5):
                th = -0.9 + j * 0.45
                x, y, nx, ny = P.egg_point(th)
                ph = ((t - tp) * 0.4 + j / 5) % 1.0
                d = E.lerp(170, -30, ph)
                al = min(1.0, (t - tp) * 2) * (1 - abs(ph - 0.5))
                E.circle(cr, cx + x + nx * d, cy + y + ny * d, 20, P.AIR, lw=4, alpha=al)
        labels(cr, t, ctx, par, spec.get("labels"))
        return
    base_y, sc, fill = 1230, 0.95, 0.8
    lvl = base_y - 480 * sc * fill
    for j, it in enumerate(spec.get("items", [])):
        gx = 220 + j * 320
        es = 1.45
        ta = ctx.at(par, it.get("at", 0.2 + j))
        k = E.ease(E.prog(t, ta, ta + 0.5))
        P.glass_of(cr, gx, base_y, fill=fill, t=t, scale=sc)
        if k <= 0:
            continue
        st = it["state"]
        if st == "fresh":
            ex, ey, ang = gx, base_y - 8 - 50 * es, math.pi / 2
        elif st == "medium":
            ex, ey, ang = gx, base_y - 8 - 64 * es, 0.3
        else:
            ex, ey, ang = gx, lvl + 30 * es + 4 * math.sin(t * 2.4), 0.12 * math.sin(t * 1.7)
        drop = (1 - k) * (ey - (lvl - 200))
        P.egg_whole(cr, ex, ey - drop, angle=ang, scale=es)
        cr.save()
        cr.move_to(gx - 115 * sc, base_y)
        cr.line_to(gx + 115 * sc, base_y)
        cr.line_to(gx + (150 - 35 * (1 - fill)) * sc, lvl)
        cr.line_to(gx - (150 - 35 * (1 - fill)) * sc, lvl)
        cr.close_path()
        cr.set_source_rgba(0.62, 0.82, 0.97, 0.28)
        cr.fill()
        cr.restore()
        E.label(cr, it["text"], gx, base_y + 75, t, ta + 0.2, size=it.get("size", 42), bg=(0.18, 0.47, 0.75) if st != "old" else E.RED)
    labels(cr, t, ctx, par, spec.get("labels"))


TYPES = {"hook": hook, "lens": lens, "pot": pot_scene, "number": number, "checklist": checklist, "end": end, "section": section, "real": real, "egg": egg_scene}
