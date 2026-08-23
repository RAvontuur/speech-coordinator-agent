import sys

print(sys.executable)

from coordinator import Coordinator

# source .venv/bin/activate
print("Starting coordinator...")
Coordinator().run("Starting the speech coordinator. Please speak your text. When you are finished, say 'submit' to submit your text.")