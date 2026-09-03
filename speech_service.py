import os
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
        synth = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        result = synth.speak_text(text)
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_path
        else:
            raise Exception(f"Speech synthesis failed: {result.reason}")