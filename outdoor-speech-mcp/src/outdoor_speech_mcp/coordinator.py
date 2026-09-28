from .speech_service import SpeechService


class Coordinator:
    def __init__(self, speech=None):
        self.speech = speech or SpeechService()

    def run(self, message: str):
        self.speech.speak(message)
        text = ""
        while True:
            user_text = self.speech.listen()
            if user_text.lower().startswith("submit"):
                break
            if user_text:
                text += user_text + "\n"
        self.speech.speak(text)
        self.speech.speak("The application will now quit. Goodbye.")
        return text