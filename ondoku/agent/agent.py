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
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav], capture_output=True, text=True, timeout=30).stdout or 0)
        if dur > 30:
            return "長すぎるので、1文だけ（30秒以内）で送ってね。（今回は回数に数えません）", {"dur": dur, "retry": True}
        from azure_pa import assess
        az = assess(wav, x["say"])
        if not az["ok"]:
            return "うまく聞き取れませんでした。静かな場所で、スマホを口から20cmくらいにして、もう一度送ってね。（今回は回数に数えません）", {"azure": az.get("reason"), "retry": True}
        R = measure(wav, x, az["words"])
        text = advise(x, R, az)
        return text, {"R": R, "scores": az["scores"], "dur": dur}
    # 録音は一時フォルダごと消える

def cleanup():
    for f in os.listdir(LOG):
        q = os.path.join(LOG, f)
        if f.endswith(".jsonl") and time.time() - os.path.getmtime(q) > KEEP_DAYS * 86400:
            os.remove(q)

def heartbeat(state):
    if time.time() - state["hb"] > 60:
        try:
            requests.post(W + "/agent/heartbeat", headers=H, timeout=15); state["hb"] = time.time()
        except Exception as e:  # noqa: BLE001
            print(datetime.now(), "heartbeat error", repr(e), flush=True)

def finish(job, status, how, text=None):
    """結果を Worker に知らせる。失敗しても次の仕事へ進む（10分たてば Worker がもう一度出す）"""
    body = {"id": job["id"], "status": status, "note": how}
    if text and status == "done": body["text"] = text
    for _ in range(3):
        try:
            requests.post(W + "/agent/done", headers=H, json=body, timeout=15); return
        except Exception as e:  # noqa: BLE001
            print(datetime.now(), "done error", repr(e), flush=True); time.sleep(3)

def run(job):
    t0 = time.time(); text = None
    try:
        text, info = work(job)
        status = "retry" if info.get("retry") else "done"
    except Exception as e:  # noqa: BLE001
        info = {"error": repr(e), "tb": traceback.format_exc()[-800:]}; status = "error"
        text = "チェック中にエラーが起きました。少ししてからもう一度送ってね。（今回は回数に数えません）"
    try:
        how = send(job, text)
    except Exception as e:  # noqa: BLE001
        how = f"send-error:{e!r}"[:120]
    if not how.startswith("reply") and how != "push:200":
        status = "error"   # 届けられなかった → その回は数えない
    finish(job, status, how, text)
    log({"t": datetime.now().isoformat(timespec="seconds"), "user": job["user_id"][-6:], "sid": job["sid"], "how": how, "status": status,
         "sec": round(time.time() - t0, 1), **info})

def main():
    state = {"hb": 0}; last_clean = 0
    while True:
        try:
            if time.time() - last_clean > 86400:
                cleanup(); last_clean = time.time()
            heartbeat(state)
            jobs = requests.get(W + "/agent/jobs", headers=H, timeout=15).json()
            for job in jobs:
                heartbeat(state)   # 仕事が続いても「動いている」と知らせる
                run(job)
        except Exception as e:  # noqa: BLE001  ネットが一時的に切れても止まらない
            print(datetime.now(), "loop error", repr(e), flush=True); time.sleep(10)
        time.sleep(5)   # 受付を見に来る間隔（Cloudflare の無料枠の回数を使いすぎないように）

if __name__ == "__main__":
    main()
