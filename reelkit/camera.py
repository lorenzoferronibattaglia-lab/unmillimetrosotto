"""
Regia di camera automatica: rende ogni scena dinamica senza toccare le scene.
- stacco: a inizio scena parte ingrandita del 10% e si assesta in 0,35 s
- deriva: zoom lento del 3,5%, alternato (dentro/fuori) scena per scena
- eventi: quando compare un'etichetta/numero/timbro la camera si avvicina a quel punto (+12%) e poi torna
Gli zoom sono lenti e fluidi: nessun lampeggiamento.
"""
import engine as E

FOCUS0 = (540, 900)


def events(spec, ctx, par):
    ev = []

    def add(at, x, y):
        try:
            ev.append((ctx.at(par, at), x, y))
        except KeyError:
            pass
    for lab in spec.get("labels", []) or []:
        x, y = lab.get("pos", [540, 1250])
        if lab.get("arrow_to"):
            x, y = (x + lab["arrow_to"][0]) / 2, (y + lab["arrow_to"][1]) / 2
        add(lab.get("at", 0.3), x, y)
    if spec.get("stamp") and isinstance(spec["stamp"], dict) and spec["stamp"].get("at"):
        add(spec["stamp"]["at"], 540, 640)
    if spec.get("big"):
        add(spec["big"].get("at"), 540, 900)
    for i, it in enumerate(spec.get("items", []) or []):
        add(it.get("at", 0.2 + i), 540, 520 + i * 200)
    return ev


def apply(cr, t, s0, s1, idx, spec, ctx, par):
    span = max(0.5, s1 - s0)
    drift = E.ease(E.prog(t, s0, s1))
    base = 1.0 + 0.035 * (drift if idx % 2 == 0 else 1 - drift)
    punch = 0.10 * (1 - E.ease(E.prog(t, s0, s0 + 0.35))) if idx > 0 else 0.0
    kmax, fx, fy = 0.0, FOCUS0[0], FOCUS0[1]
    for te, x, y in events(spec, ctx, par):
        k = E.ease(E.prog(t, te - 0.05, te + 0.4)) * (1 - E.ease(E.prog(t, te + 1.6, te + 2.3)))
        if k > kmax:
            kmax, fx, fy = k, x, y
    z = base + punch + 0.12 * kmax
    cx = E.lerp(FOCUS0[0], fx, 0.6 * kmax)
    cy = E.lerp(FOCUS0[1], fy, 0.6 * kmax)
    cr.translate(cx, cy)
    cr.scale(z, z)
    cr.translate(-cx, -cy)
