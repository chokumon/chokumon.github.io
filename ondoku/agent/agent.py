"""Mac mini で動く分析係。Worker に録音を取りに行き、分析して LINE に返信する。
launchd が常に動かし、落ちたら自動で起こす（com.chokumon.ondoku.plist）"""
import json, os, subprocess, sys, tempfile, time, traceback
from datetime import datetime
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from analyze import measure
from feedback import advise

def env_file():
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for line in open(p):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v)
env_file()
W = os.environ["WORKER_URL"].rstrip("/")
H = {"Authorization": "Bearer " + os.environ["AGENT_TOKEN"]}
LT = os.environ["LINE_CHANNEL_TOKEN"]
LOG = os.path.join(HERE, "logs"); os.makedirs(LOG, exist_ok=True)
KEEP_DAYS = int(os.environ.get("KEEP_DAYS", "30"))   # 結果の記録を残す日数（録音そのものは残さない）

def log(rec):
    with open(os.path.join(LOG, datetime.now().strftime("%Y-%m") + ".jsonl"), "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def send(job, text):
    msg = [{"type": "text", "text": text}]
    age = time.time() - job["received_at"] / 1000
    if job.get("reply_token") and age < 50:
        r = requests.post("https://api.line.me/v2/bot/message/reply", timeout=15,
                          headers={"Authorization": "Bearer " + LT}, json={"replyToken": job["reply_token"], "messages": msg})
        if r.status_code == 200: return "reply"
    r = requests.post("https://api.line.me/v2/bot/message/push", timeout=15,
                      headers={"Authorization": "Bearer " + LT}, json={"to": job["user_id"], "messages": msg})
    return f"push:{r.status_code}"

def work(job):
    x = job["sentence"]
    with tempfile.TemporaryDirectory() as td:
        src, wav = os.path.join(td, "in.m4a"), os.path.join(td, "in.wav")
        r = requests.get(f"https://api-data.line.me/v2/bot/message/{job['message_id']}/content", headers={"Authorization": "Bearer " + LT}, timeout=30)
        r.raise_for_status(); open(src, "wb").write(r.content)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True, timeout=60)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav], capture_output=True, text=True).stdout or 0)
        if dur > 30:
            return "長すぎるので、1文だけ（30秒以内）で送ってね。", {"dur": dur}
        from azure_pa import assess
        az = assess(wav, x["say"])
        if not az["ok"]:
            return "うまく聞き取れませんでした。静かな場所で、スマホを口から20cmくらいにして、もう一度送ってね。", {"azure": az.get("reason")}
        R = measure(wav, x, az["words"])
        text = advise(x, R, az)
        return text, {"R": R, "scores": az["scores"], "dur": dur}
    # 録音は一時フォルダごと消える

def cleanup():
    for f in os.listdir(LOG):
        q = os.path.join(LOG, f)
        if f.endswith(".jsonl") and time.time() - os.path.getmtime(q) > KEEP_DAYS * 86400:
            os.remove(q)

def main():
    last_hb = 0
    cleanup()
    while True:
        try:
            if time.time() - last_hb > 60:
                requests.post(W + "/agent/heartbeat", headers=H, timeout=15); last_hb = time.time()
            jobs = requests.get(W + "/agent/jobs", headers=H, timeout=15).json()
            for job in jobs:
                t0 = time.time()
                try:
                    text, info = work(job); how = send(job, text); status = "done"
                except Exception as e:  # noqa: BLE001
                    info = {"error": repr(e), "tb": traceback.format_exc()[-800:]}; how = send(job, "チェック中にエラーが起きました。少ししてからもう一度送ってね。"); status = "error"
                requests.post(W + "/agent/done", headers=H, json={"id": job["id"], "status": status, "note": how}, timeout=15)
                log({"t": datetime.now().isoformat(timespec="seconds"), "user": job["user_id"][-6:], "sid": job["sid"], "how": how,
                     "sec": round(time.time() - t0, 1), **info})
        except Exception as e:  # noqa: BLE001  ネットが一時的に切れても止まらない
            print(datetime.now(), "loop error", repr(e), flush=True); time.sleep(10)
        time.sleep(2)

if __name__ == "__main__":
    main()
