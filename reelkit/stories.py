"""Stories 1080x1920 nello stile della pagina: titolo, illustrazione, zona vuota per lo sticker, firma."""
import sys, json, cairo
sys.path.insert(0, ".")
import engine as E, props as P

def story(out, lines, prop=None, sub=None, sticker_hint=True, t=2.0):
    s, cr = E.new_surface()
    g = cairo.LinearGradient(0, 0, 0, 1920); g.add_color_stop_rgb(0, *E.BG_TOP); g.add_color_stop_rgb(1, *E.BG_BOT); cr.set_source(g); cr.paint()
    E.title(cr, lines, t=5, t0=0, y=330, size=96)
    if prop:
        cr.save(); cr.translate(540, 1100); cr.scale(0.85, 0.85); cr.translate(-540, -1380); prop(cr, t); cr.restore()
    if sticker_hint:
        E.rounded_rect(cr, 140, 1260, 800, 240, 40)
        cr.set_source_rgba(1, 1, 1, 0.10); cr.fill()
        cr.set_dash([18, 14]); E.rounded_rect(cr, 140, 1260, 800, 240, 40)
        cr.set_source_rgba(1, 1, 1, 0.35); cr.set_line_width(4); cr.stroke(); cr.set_dash([])
    if sub:
        E.outlined_text(cr, sub, 540, 1640, 50, fill=E.YELLOW, lw=8)
    E.outlined_text(cr, "@unmillimetrosotto", 540, 1820, 40, fill=E.WHITE, lw=6)
    s.write_to_png(out)

if __name__ == "__main__":
    import os
    d = sys.argv[1]; os.makedirs(d, exist_ok=True)
    story(f"{d}/1_ciabatta.png", ["HAI UNA CIABATTA", "SU UN'ALTRA CIABATTA?"],
          prop=lambda cr, t: P.power_strips(cr, 540, 1380, t=t, heat=1.0), sub="ALLE 11 TI DICO PERCHÉ È UN PROBLEMA")
    story(f"{d}/2_pane.png", ["LA CROSTA PIÙ SCURA", "È LA PIÙ BUONA?"],
          prop=lambda cr, t: P.toast_slices(cr, 540, 1380, t=t, burnt=1.0), sub="ALLE 13:15 LA RISPOSTA")
    story(f"{d}/3_buio.png", ["LEGGERE AL BUIO", "ROVINA LA VISTA?"],
          prop=lambda cr, t: P.book_dark(cr, 540, 1380, t=t), sub="ALLE 17:45 LA RISPOSTA")
    story(f"{d}/4_acqua.png", ["TU BEVI L'ACQUA", "DEL RUBINETTO?"],
          prop=lambda cr, t: P.tap_vs_bottle(cr, 540, 1380, t=t), sub="ALLE 20:00 TI SORPRENDO")
