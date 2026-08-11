"""
voice_input.py
Transcribes browser-recorded audio (from streamlit-mic-recorder) to text
using the free Google Web Speech API via the SpeechRecognition library.
No API key required.

Usage:
    from streamlit_mic_recorder import mic_recorder
    import voice_input

    audio = mic_recorder(start_prompt="🎤 Record", stop_prompt="⏹ Stop", format="wav")
    if audio:
        text, error = voice_input.transcribe(audio, language="en-IN")
"""

import speech_recognition as sr

def transcribe_auto(audio_dict: dict):
    """
    Tries English first, then Hindi, without requiring the user to pick
    a language upfront. Returns (text, detected_language, error).
    """
    if not audio_dict or "bytes" not in audio_dict:
        return None, None, "No audio recorded."

    for lang_name, lang_code in [("English", "en-IN"), ("Hindi", "hi-IN")]:
        text, error = transcribe(audio_dict, language=lang_code)
        if text:
            return text, lang_name, None

    return None, None, "Couldn't understand the audio. Try speaking clearly and a bit louder."


def transcribe(audio_dict: dict, language: str = "en-IN"):
    """
    Transcribes an audio dict (as returned by streamlit_mic_recorder.mic_recorder)
    into text.

    Returns (text, error) — exactly one will be None.
    """
    if not audio_dict or "bytes" not in audio_dict:
        return None, "No audio recorded."

    recognizer = sr.Recognizer()
    try:
        audio_data = sr.AudioData(
            audio_dict["bytes"],
            audio_dict["sample_rate"],
            audio_dict["sample_width"],
        )
    except Exception as e:
        return None, f"Couldn't read the recorded audio: {e}"

    try:
        text = recognizer.recognize_google(audio_data, language=language)
        return text, None
    except sr.UnknownValueError:
        return None, "Couldn't understand the audio. Try speaking clearly and a bit louder."
    except sr.RequestError as e:
        # recognize_google() uses Google's free, unkeyed endpoint. It is
        # rate-limited and unofficial, so intermittent failures are expected —
        # surface that as something the user can act on, not a raw traceback.
        return None, (
            "Speech service is unavailable right now (it's a free, rate-limited "
            "endpoint). Check your internet, wait a few seconds and try again, "
            f"or type the expense instead. [{e}]"
        )
    except Exception as e:
        return None, f"Unexpected error during transcription: {e}"