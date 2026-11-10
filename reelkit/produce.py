"""
Pipeline: storyboard JSON -> voce ElevenLabs (con tempi per carattere) -> video 1080x1920.

Uso:
  python3 produce.py storyboards/02_olio.json [--preview]
  --preview  genera solo copertina e foglio di controllo (nessun video completo)

Uscite in out/<id>/: <id>.mp4, copertina.png, controllo.png, meta.json
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E  # noqa: E402
import scenes as S  # noqa: E402

VOICE_CFG = {
    "voice_id": "8BRNClOqAj0d70eCur4i",  # SimoneF
    "model_id": "eleven_multilingual_v2",
    "language_code": "it",
    "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.3, "speed": 1.08},
}
KEY_PATH = os.path.expanduser("~/.secrets/elevenlabs_key")


# ------------------------------------------------------------------ voce
def tts_with_timestamps(text, out_dir):
    """Genera la voce una sola volta per testo+voce (cache su hash)."""
    import base64
    h = hashlib.sha1((text + json.dumps(VOICE_CFG, sort_keys=True)).encode()).hexdigest()[:16]
    cache = os.path.join(HERE, "cache", h)
    mp3, al = cache + ".mp3", cache + ".align.json"
    if not (os.path.exists(mp3) and os.path.exists(al)):
        key = open(KEY_PATH).read().strip()
        body = json.dumps({"text": text, "model_id": VOICE_CFG["model_id"],
                           "language_code": VOICE_CFG["language_code"],
                           "voice_settings": VOICE_CFG["voice_settings"]}).encode()
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_CFG['voice_id']}/with-timestamps"
            "?output_format=mp3_44100_192",
            data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read())
        open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
        json.dump(d["alignment"], open(al, "w"))
        print(f"voce generata: {len(text)} caratteri (~{len(text)} crediti)", flush=True)
    else:
        print("voce dalla cache (0 crediti)", flush=True)
    wav = os.path.join(out_dir, "voce.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mp3,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", wav], check=True)
    return wav, json.load(open(al))


def words_from_alignment(paragraphs, al):
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    text = "".join(chars)
    expected = "\n\n".join(paragraphs)
    if text != expected:
        raise ValueError("il testo restituito da ElevenLabs non coincide con lo storyboard")
    bounds, pos = [], 0
    for k, par in enumerate(paragraphs):
        bounds.append((pos, pos + len(par), k))
        pos += len(par) + 2
    words = []
    for m in re.finditer(r"\S+", text):
        a, b = m.start(), m.end() - 1
        par = next(k for x, y, k in bounds if x <= a < y)
        words.append((m.group(), st[a], en[b], par))
    return words


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


# ------------------------------------------------------------------ sottotitoli
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


# ------------------------------------------------------------------ render
def build(sb_path, preview=False):
    sb = json.load(open(sb_path))
    theme = json.load(open(os.path.join(HERE, "themes", sb.get("theme", "cucina_notte") + ".json")))
    E.set_theme(theme)
    out = os.path.join(HERE, "out", sb["id"])
    os.makedirs(out, exist_ok=True)
    paragraphs = [p["text"] for p in sb["paragraphs"]]
    wav, al = tts_with_timestamps("\n\n".join(paragraphs), out)
    words = words_from_alignment(paragraphs, al)
    ctx = S.Ctx(words, duration(wav))
    chunks = make_chunks(words)
    fr = lambda x: round(x * E.FPS) / E.FPS
    starts = [0.0] + [ctx.par_start[i] - 0.15 for i in range(1, len(paragraphs))]
    ends = starts[1:] + [ctx.dur + 0.8]
    bounds = [(fr(a), fr(b)) for a, b in zip(starts, ends)]

    def frame(i, t, captions=True):
        surf, cr = E.new_surface()
        cr.save()
        cr.translate(0, 60)
        spec = sb["paragraphs"][i]["scene"]
        S.TYPES[spec["type"]](cr, t, ctx, i, spec)
        cr.restore()
        if captions:
            for ch in chunks:
                a, b = ch[0][1], ch[-1][2]
                if a - 0.05 <= t < b + 0.15:
                    E.caption(cr, [(clean(w), wa, wb) for w, wa, wb, _ in ch], None, t, y=1540)
                    break
        return surf

    # copertina: gancio subito dopo il timbro, senza sottotitoli
    hook_spec = sb["paragraphs"][0]["scene"]
    t_cover = ctx.at(0, hook_spec.get("stamp", {}).get("at"), 1.0) + 0.6
    frame(0, min(t_cover, bounds[0][1] - 0.05), captions=False).write_to_png(os.path.join(out, "copertina.png"))

    # foglio di controllo: per ogni scena, inizio+0.6s, ogni ancora +0.6s, fine-0.1s
    from PIL import Image
    shots = []
    for i, (a, b) in enumerate(bounds):
        ts = {a + 0.6, b - 0.1}
        for v in re.findall(r'"at":\s*"([^"]+)"', json.dumps(sb["paragraphs"][i]["scene"])):
            try:
                ts.add(ctx.at(i, v) + 0.6)
            except KeyError as e:
                raise SystemExit(f"ERRORE storyboard: {e}")
        for tt in sorted(x for x in ts if a <= x < b):
            shots.append((i, tt))
    thumbs = []
    for i, tt in shots:
        p = os.path.join(out, "_tmp.png")
        frame(i, tt).write_to_png(p)
        thumbs.append(Image.open(p).convert("RGB").resize((270, 480)))
    cols = 8
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (270 * cols, 480 * rows), "white")
    for k, im in enumerate(thumbs):
        sheet.paste(im, (270 * (k % cols), 480 * (k // cols)))
    sheet.save(os.path.join(out, "controllo.png"))
    os.remove(os.path.join(out, "_tmp.png"))

    meta = {"id": sb["id"], "titolo": sb.get("topic"), "durata_s": round(ctx.dur, 1),
            "caratteri_voce": len("\n\n".join(paragraphs)), "didascalia": sb.get("caption"),
            "fonti": sb.get("sources", []), "verifiche": sb.get("fact_check", [])}
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), ensure_ascii=False, indent=1)
    if preview:
        print("anteprima pronta:", out)
        return out

    parts = []
    for i, (a, b) in enumerate(bounds):
        n = int(round((b - a) * E.FPS))
        tmp, fin = os.path.join(out, f"s{i:02d}.tmp.mp4"), os.path.join(out, f"s{i:02d}.mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
                              "-pix_fmt", "bgra", "-s", f"{E.W}x{E.H}", "-r", str(E.FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                              "-r", str(E.FPS), tmp], stdin=subprocess.PIPE)
        for f in range(n):
            p.stdin.write(bytes(frame(i, a + f / E.FPS).get_data()))
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError(f"scena {i} fallita")
        os.replace(tmp, fin)
        parts.append(fin)
    lst = os.path.join(out, "lista.txt")
    open(lst, "w").writelines(f"file '{x}'\n" for x in parts)
    silent = os.path.join(out, "muto.mp4")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", silent], check=True)
    final = os.path.join(out, sb["id"] + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", silent, "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", "apad", "-shortest", "-movflags", "+faststart", final], check=True)
    for x in parts + [silent, lst]:
        os.remove(x)
    print("video:", final)
    return out


if __name__ == "__main__":
    build(sys.argv[1], preview="--preview" in sys.argv)
