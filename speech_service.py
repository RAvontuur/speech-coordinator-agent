import os
import subprocess
import threading
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import azure.cognitiveservices.speech as speechsdk


class SpeechService:

    def __init__(self):

        print("Initializing Speech Service...")
        key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")  
        
        self.speech_config = speechsdk.SpeechConfig(
            subscription=key,
            region=region
        )

    def listen(self):

        audio = speechsdk.audio.AudioConfig(
            use_default_microphone=True
        )

        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio
        )

        print("Listening...")

        result = recognizer.recognize_once()

        return result.text

    def speak(self, text):
        synth = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config
        )
        synth.speak_text_async(text).get()

    def text_to_speech_file(self, text, output_path):
        """Synthesize text to speech and save to audio file."""
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
        )
        synth = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        result = synth.speak_text(text)
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_path
        else:
            raise Exception(f"Speech synthesis failed: {result.reason}")

    def speech_to_text_file(self, input_path):
        """Transcribe an audio file with Azure Speech-to-Text."""
        input_path = Path(input_path).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="audio-plan-stt-") as temporary_dir:
            wav_path = Path(temporary_dir) / "input.wav"
            self._convert_to_pcm_wav(input_path, wav_path)
            return self._recognize_wav_file(wav_path)

    @staticmethod
    def _convert_to_pcm_wav(input_path, output_path):
        """Convert phone recordings to the PCM WAV format accepted by Azure STT."""
        try:
            subprocess.run(
                [
                    os.getenv("FFMPEG_PATH", "ffmpeg"),
                    "-nostdin",
                    "-y",
                    "-i",
                    str(input_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(output_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                "ffmpeg is required to transcribe M4A annotations; "
                "install ffmpeg or set FFMPEG_PATH"
            ) from error
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip().splitlines()[-1] if error.stderr else "unknown ffmpeg error"
            raise RuntimeError(f"Unable to decode annotation audio: {detail}") from error

    def _recognize_wav_file(self, input_path):
        audio = speechsdk.audio.AudioConfig(filename=str(input_path))
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio,
        )
        recognized_parts = []
        finished = threading.Event()
        failure = []

        def on_recognized(event):
            result = event.result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text:
                recognized_parts.append(result.text.strip())

        def on_canceled(event):
            details = event.reason
            if details == speechsdk.CancellationReason.Error:
                failure.append(f"Speech recognition failed: {event.error_details}")
            finished.set()

        def on_session_stopped(_event):
            finished.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)
        recognizer.session_stopped.connect(on_session_stopped)
        recognizer.start_continuous_recognition_async().get()
        finished.wait()
        recognizer.stop_continuous_recognition_async().get()

        if failure:
            raise RuntimeError(failure[0])
        return " ".join(recognized_parts)

    def process_annotation_file(self, audio_path):
        """Create STT text and TTS WAV files for one annotation recording."""
        audio_path = Path(audio_path).expanduser().resolve()
        text_path = audio_path.with_name(f"{audio_path.stem}.stt.txt")
        wav_path = audio_path.with_name(f"{audio_path.stem}.stt.wav")

        if not text_path.exists():
            text = self.speech_to_text_file(audio_path)
            text_path.write_text(text + "\n", encoding="utf-8")

        if not wav_path.exists():
            self.text_to_speech_file(text_path.read_text(encoding="utf-8"), str(wav_path))

        return text_path, wav_path

    def start_audio_plan_task(self, stop_event=None):
        """Poll the active plan's audio directory for unprocessed M4A files."""
        plan_path = Path(
            os.getenv(
                "ACTIVE_AUDIO_PLAN",
                "/Users/ravontuur/Library/Mobile Documents/com~apple~CloudDocs/audio/example-audio-plan",
            )
        ).expanduser()
        interval = float(os.getenv("AUDIO_PLAN_INTERVAL_SECONDS", "10"))
        if interval <= 0:
            raise ValueError("AUDIO_PLAN_INTERVAL_SECONDS must be greater than zero")
        stop_event = stop_event or threading.Event()

        def worker():
            print(f"Watching {plan_path / 'audio'} every {interval:g} seconds")
            while not stop_event.is_set():
                try:
                    audio_dir = plan_path / "audio"
                    if audio_dir.is_dir():
                        for audio_path in sorted(audio_dir.glob("*.m4a")):
                            text_path = audio_path.with_name(f"{audio_path.stem}.stt.txt")
                            wav_path = audio_path.with_name(f"{audio_path.stem}.stt.wav")
                            if text_path.exists() and wav_path.exists():
                                continue
                            try:
                                self.process_annotation_file(audio_path)
                                print(f"Processed annotation: {audio_path.name}")
                            except Exception as error:
                                print(f"Unable to process {audio_path.name}: {error}")
                except Exception as error:
                    print(f"Audio-plan task failed: {error}")
                stop_event.wait(interval)

        thread = threading.Thread(target=worker, name="audio-plan-task", daemon=True)
        thread.start()
        return thread, stop_event