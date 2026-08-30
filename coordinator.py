from speech_service import SpeechService

speech = SpeechService()


class Coordinator:

    def run(self, message: str):
        speech.speak(message)
        text = ""
        while True:
            user_text = speech.listen()
            if (user_text.lower().startswith("submit")):
                break
            print(f"User: {user_text}")
            if (user_text != ""): 
                text += user_text + "\n"

        print(f"Submitted text:\n{text}")
        speech.speak(text)
        speech.speak("The application will now quit. Goodbye.")
        print("Quitting.")
        return text