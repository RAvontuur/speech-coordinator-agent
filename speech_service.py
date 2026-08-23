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

    def speak(self,text):

        synth = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config
        )

        synth.speak_text_async(text).get()