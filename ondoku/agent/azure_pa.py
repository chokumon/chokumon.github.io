"""Azure の発音評価（台本あり）。Mac mini で動かす。キーは環境変数 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION"""
import json, os
import azure.cognitiveservices.speech as speechsdk

def assess(wav, reference):
    cfg = speechsdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"], region=os.environ["AZURE_SPEECH_REGION"])
    cfg.speech_recognition_language = "en-US"
    audio = speechsdk.audio.AudioConfig(filename=wav)
    pa = speechsdk.PronunciationAssessmentConfig(reference_text=reference,
                                                 grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                                                 granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme, enable_miscue=True)
    pa.enable_prosody_assessment()
    rec = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio)
    pa.apply_to(rec)
    r = rec.recognize_once()
    if r.reason != speechsdk.ResultReason.RecognizedSpeech:
        return {"ok": False, "reason": str(r.reason), "detail": getattr(r, "cancellation_details", None) and r.cancellation_details.error_details}
    j = json.loads(r.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult))
    return parse(j)

def parse(j):
    nb = j["NBest"][0]
    pa = nb.get("PronunciationAssessment", {})
    words, mono = [], False
    for w in nb.get("Words", []):
        a = w.get("PronunciationAssessment", {})
        st = w.get("Offset", 0) / 1e7
        words.append({"word": w["Word"], "start": st, "end": st + w.get("Duration", 0) / 1e7,
                      "acc": a.get("AccuracyScore"), "err": a.get("ErrorType", "None")})
        intn = a.get("Feedback", {}).get("Prosody", {}).get("Intonation", {})
        if "Monotone" in intn.get("ErrorTypes", []): mono = True
    return {"ok": True, "words": words, "monotone": mono, "raw": j,
            "scores": {"acc": pa.get("AccuracyScore"), "flu": pa.get("FluencyScore"), "pro": pa.get("ProsodyScore"),
                       "comp": pa.get("CompletenessScore"), "total": pa.get("PronScore")}}
