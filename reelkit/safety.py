"""
Controllo anti-lampeggio (epilessia fotosensibile), ispirato a WCAG 2.3.1 / linee guida Ofcom:
un "lampo" e' una coppia di variazioni opposte di luminanza relativa >= 10% su un'area
>= 10% dello schermo; vale anche per transizioni di rosso saturo. Piu' di 3 lampi in
un secondo qualsiasi = video BLOCCATO.
"""
import subprocess
import sys

import numpy as np

W, H = 108, 192  # analisi a 1/10 di risoluzione


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32) / 255.0


def rel_lum(rgb):
    c = np.where(rgb <= 0.03928, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def red_sat(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return np.clip((r - np.maximum(g, b)) / np.maximum(r + g + b, 1e-3), 0, 1) * (r > 0.5)


WIN = 64  # ~10 gradi di campo visivo su un telefono a 30-40 cm (circa 0,6 della larghezza)


def window_max(mask):
    """Frazione massima di pixel attivi in una finestra WIN x WIN (immagine integrale)."""
    ii = np.pad(mask.astype(np.float32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    s = ii[WIN:, WIN:] - ii[:-WIN, WIN:] - ii[WIN:, :-WIN] + ii[:-WIN, :-WIN]
    return float(s.max()) / (WIN * WIN)


def check(path, fps=30, area=0.25, max_flashes=3):
    prev_l = prev_r = None
    events = []  # (indice fotogramma, segno) per luminanza e rosso
    for i, f in enumerate(frames(path)):
        l, r = rel_lum(f), red_sat(f)
        if prev_l is not None:
            dl = l - prev_l
            dark = np.minimum(l, prev_l) < 0.8  # WCAG: il piu' scuro dei due sotto 0.80
            up = window_max((dl >= 0.1) & dark)
            down = window_max((dl <= -0.1) & dark)
            dr = r - prev_r
            rup, rdown = window_max(dr >= 0.2), window_max(dr <= -0.2)
            if up >= area or rup >= area:
                events.append((i, +1))
            if down >= area or rdown >= area:
                events.append((i, -1))
        prev_l, prev_r = l, r
    # un lampo = due transizioni opposte consecutive
    flashes = []
    for (i0, s0), (i1, s1) in zip(events, events[1:]):
        if s0 != s1:
            flashes.append(i1)
    worst, at = 0, 0
    for k, fi in enumerate(flashes):
        n = sum(1 for x in flashes[k:] if x - fi < fps)
        if n > worst:
            worst, at = n, fi / fps
    ok = worst <= max_flashes
    return ok, worst, at


if __name__ == "__main__":
    ok, worst, at = check(sys.argv[1])
    print(f"anti-lampeggio: {'OK' if ok else 'BLOCCATO'} (max {worst} lampi in 1 s, intorno a {at:.1f}s)")
    sys.exit(0 if ok else 2)
