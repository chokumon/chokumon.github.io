#!/bin/bash
# 直問！ 音読チェックの分析係を Mac mini に入れる（何回やり直しても大丈夫）
#   curl -fsSL https://chokumon.com/ondoku/agent/install.sh -o /tmp/ondoku_install.sh && bash /tmp/ondoku_install.sh
set -e
DIR="$HOME/aep/ondoku"
BASE="https://chokumon.com/ondoku/agent"
mkdir -p "$DIR/logs" && cd "$DIR"
echo "== 1/5 プログラムをダウンロード"
for f in agent.py analyze.py feedback.py azure_pa.py com.chokumon.ondoku.plist; do curl -fsSL "$BASE/$f" -o "$f"; done
echo "== 2/5 ffmpeg と Python の準備"
BREW="$(command -v brew || echo /usr/local/bin/brew)"
command -v ffmpeg >/dev/null || "$BREW" install ffmpeg
PY="$("$BREW" --prefix)/bin/python3.12"; [ -x "$PY" ] || PY="$(command -v python3)"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q requests numpy praat-parselmouth azure-cognitiveservices-speech
echo "== 3/5 鍵を入れる（入力した文字は画面に出ません。貼り付けたら Enter）"
if [ -f .env ] && [ "$1" != "--reset" ]; then
  echo "   .env はもうあるので、そのまま使います（入れ直すときは bash /tmp/ondoku_install.sh --reset）"
else
  read -rsp "   AGENT_TOKEN（Claude が伝えた合言葉）: " AT; echo
  read -rsp "   LINE_CHANNEL_TOKEN（直問！のチャネルアクセストークン）: " LT; echo
  read -rsp "   AZURE_SPEECH_KEY（Azure の キー1）: " AK; echo
  umask 077
  cat > .env <<ENV
WORKER_URL=https://chokumon-ondoku.hinashibaxta.workers.dev
AGENT_TOKEN=$AT
LINE_CHANNEL_TOKEN=$LT
AZURE_SPEECH_KEY=$AK
AZURE_SPEECH_REGION=japaneast
KEEP_DAYS=30
ENV
  chmod 600 .env
fi
echo "== 4/5 Azure に1回だけつないで、鍵が正しいか確かめる"
.venv/bin/python - <<'PYCHK'
import os, azure.cognitiveservices.speech as sdk
for l in open(".env"):
    if "=" in l: k, v = l.strip().split("=", 1); os.environ[k] = v
cfg = sdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"], region=os.environ["AZURE_SPEECH_REGION"])
s = sdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
r = s.speak_text_async("ok").get()
print("   Azure:", "OK" if r.reason == sdk.ResultReason.SynthesizingAudioCompleted else f"NG {r.reason} {getattr(r, 'cancellation_details', '')}")
PYCHK
echo "== 5/5 常に動かす設定（Mac のパスワードを聞かれたら入力）"
sed -e "s#__PY__#$DIR/.venv/bin/python#" -e "s#__DIR__#$DIR#g" com.chokumon.ondoku.plist > /tmp/com.chokumon.ondoku.plist
sudo /usr/libexec/PlistBuddy -c "Add :UserName string $(whoami)" /tmp/com.chokumon.ondoku.plist 2>/dev/null || true
sudo cp /tmp/com.chokumon.ondoku.plist /Library/LaunchDaemons/com.chokumon.ondoku.plist
sudo chown root:wheel /Library/LaunchDaemons/com.chokumon.ondoku.plist
sudo launchctl bootout system/com.chokumon.ondoku 2>/dev/null || true
sudo launchctl bootstrap system /Library/LaunchDaemons/com.chokumon.ondoku.plist
sudo pmset -a sleep 0 disksleep 0 autorestart 1 >/dev/null
sleep 5
if sudo launchctl print system/com.chokumon.ondoku | grep -q "state = running"; then echo "完了：分析係が動いています"; else echo "注意：分析係が動いていません。 tail -20 $DIR/logs/agent.err を Claude に送ってください"; fi
