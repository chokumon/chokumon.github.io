"""音読の見本音声づくり（Kokoro）と、楽譜と合っているかの機械チェック"""
import os, re, subprocess, numpy as np, soundfile as sf, parselmouth
MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.expanduser("~/kokoro"))
URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
VOICES = ["af_heart", "af_bella", "am_michael", "am_puck"]
FUNC = set("""a an the and or but so nor for yet of to in on at by with from into onto over under about after before during until since than as if that which who whom whose what when where why how this these those it its they them their he him his she her we us our you your i me my is are was were be been being am do does did have has had will would shall should can could may might must not no there here very also just all any each every some such own same other another more most much many both either neither only too up out off""".split())
_K = None

def kokoro():
    global _K
    if _K is None:
        from kokoro_onnx import Kokoro
        os.makedirs(MODEL_DIR, exist_ok=True)
        for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            p = os.path.join(MODEL_DIR, f)
            if not os.path.exists(p): subprocess.run(["curl", "-sSL", "-o", p, URL + f], check=True)
        _K = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    return _K

def last_content(ch):
    ws = re.findall(r"[A-Za-z][A-Za-z'\-]*", ch)
    for w in reversed(ws):
        if w.lower() not in FUNC and len(w) > 2: return w
    return ws[-1] if ws else ""

def pauses(path, min_len=0.12, drop=28):
    s = parselmouth.Sound(path); I = s.to_intensity(time_step=0.01); v, t = I.values[0], I.xs()
    sil = v < v.max() - drop; on = np.where(~sil)[0]; first, last = on[0], on[-1]; out = []; i = first
    while i <= last:
        if sil[i]:
            j = i
            while j <= last and sil[j]: j += 1
            if t[j - 1] - t[i] >= min_len: out.append((float(t[i]), float(t[j - 1] - t[i])))
            i = j
        else: i += 1
    return out, (float(t[first]), float(t[last]))

def final_pitch(path, span=0.45):
    p = parselmouth.Sound(path).to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=500)
    f = p.selected_array["frequency"]; t = p.xs(); voiced = np.where(f > 0)[0]
    if len(voiced) < 10: return None
    end = t[voiced[-1]]; seg = [(tt, ff) for tt, ff in zip(t, f) if ff > 0 and end - span <= tt <= end]
    tt, ff = np.array(seg).T; st = 12 * np.log2(ff / np.median(f[voiced])); k = max(3, len(st) // 4)
    return round(float(st[-k:].mean() - st[:k].mean()), 1)

def final_ok(arrow, d):
    if d is None: return False
    return d >= 1.0 if arrow == "↗" else d <= -1.5

def synth(text, voice, speed, path):
    a, sr = kokoro().create(text, voice=voice, speed=speed, lang="en-us"); sf.write(path, a, sr)

def make_model_audio(x, wav):
    """自然な速さの見本を作る。文末の上げ下げ・かたまりの途中で止まらないかを確かめ、だめなら声と速さを変える"""
    best = None
    for v in VOICES:
        for sp in (0.9, 0.95, 0.85):
            synth(x["say"], v, sp, wav)
            d = final_pitch(wav); ps, (a, b) = pauses(wav)
            lens = []
            for c in x["say_chunks"]:
                synth(c, v, sp, wav + ".c.wav"); lens.append(pauses(wav + ".c.wav")[1][1] - pauses(wav + ".c.wav")[1][0])
            cum = np.cumsum(lens)[:-1] / sum(lens) * (b - a) + a
            bad = [p for p, L in ps if len(cum) == 0 or min(abs(p + L / 2 - c) for c in cum) > 0.4]
            ok = final_ok(x["final"], d) and not bad
            rep = dict(voice=v, speed=sp, final=d, mid_pause=len(bad), ok=ok)
            if ok:
                os.remove(wav + ".c.wav"); return rep
            best = best or rep
    synth(x["say"], best["voice"], best["speed"], wav)
    if os.path.exists(wav + ".c.wav"): os.remove(wav + ".c.wav")
    best["ok"] = False; return best

def to_m4a(wav, m4a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1", "-c:a", "aac", "-b:a", "96k", m4a], check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", m4a], capture_output=True, text=True).stdout)
    return int(d * 1000)
