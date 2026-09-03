# Speech Coordinator Agent

A REST API service that coordinates speech recognition and synthesis using Azure Cognitive Services. The application listens for user speech input and synthesizes spoken responses.

## Prerequisites

- Python 3.7+
- Azure Cognitive Services account (Speech service)
- Microphone access

## Setup

1. **Clone or navigate to the repository:**
   ```bash
   cd speech-coordinator-agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the project root with your Azure credentials:
   ```env
   AZURE_SPEECH_KEY=your_speech_key_here
   AZURE_SPEECH_REGION=your_region_here
   ```
   
   Replace `your_speech_key_here` and `your_region_here` with your Azure Cognitive Services credentials.

## Running the Application

Start the REST API server:
```bash
.venv/bin/python run.py
```

The server will start on `http://localhost:8000`

## API Endpoint

### POST /run

Starts the speech coordinator. The endpoint:
1. Speaks the provided message
2. Listens for user speech input
3. Continues listening until the user says "submit"
4. Synthesizes and speaks back the collected text
5. Returns the submitted text as JSON

**Request:**
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"message":"Please speak your text. When you are finished, say submit."}'
```

**Request body:**
```json
{
  "message": "Please speak your text. When you are finished, say submit."
}
```

**Response (200 OK):**
```json
{
  "text": "This is the text the user spoke."
}
```

**Error responses:**

- **400 Bad Request** - Missing or invalid `message` parameter:
  ```json
  {
    "error": "message must be a non-empty string"
  }
  ```

- **404 Not Found** - Invalid endpoint path

### POST /synthesize

Converts text from a file to speech and saves the audio output.

**Request:**
```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"filename":"/path/to/text_file.txt"}'
```

**Request body:**
```json
{
  "filename": "/path/to/text_file.txt"
}
```

**Response (200 OK):**
```json
{
  "audio_file": "/path/to/text_file.wav"
}
```

The endpoint:
1. Reads text from the specified file
2. Uses Azure Text-to-Speech to synthesize the audio
3. Saves the audio as a WAV file at the same path with `.wav` extension
4. Returns the path to the generated audio file

**Error responses:**

- **400 Bad Request** - Missing or invalid `filename` parameter, or file is empty:
  ```json
  {
    "error": "filename must be a non-empty string"
  }
  ```

- **404 Not Found** - File does not exist:
  ```json
  {
    "error": "file not found: /path/to/file.txt"
  }
  ```

- **500 Internal Server Error** - Synthesis failed:
  ```json
  {
    "error": "synthesis failed: ..."
  }
  ```

## Usage Examples

### Python Requests
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/run",
    json={"message": "Please tell me about your day."},
    timeout=300  # 5 minute timeout for long conversations
)

data = response.json()
print("Submitted text:", data["text"])
```

### JavaScript/Node.js
```javascript
const message = "Please speak your text. Say submit when done.";

const response = await fetch("http://localhost:8000/run", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ message })
});

const data = await response.json();
console.log("Submitted text:", data.text);
```

### Text-to-Speech File Synthesis

**Python:**
```python
import requests

# Create a text file
with open("my_text.txt", "w") as f:
    f.write("This is the text to convert to speech.")

response = requests.post(
    "http://localhost:8000/synthesize",
    json={"filename": "my_text.txt"}
)

data = response.json()
print("Audio saved to:", data["audio_file"])  # my_text.wav
```

**curl:**
```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"filename":"/path/to/document.txt"}'

# Response:
# {"audio_file": "/path/to/document.wav"}
```

**JavaScript/Node.js:**
```javascript
const filename = "my_text.txt";

const response = await fetch("http://localhost:8000/synthesize", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ filename })
});

const data = await response.json();
console.log("Audio file:", data.audio_file);  // my_text.wav
```

## How It Works

### POST /run
1. The client sends a POST request with an initial message
2. The server speaks the message using Azure Text-to-Speech
3. The server listens for user input using Azure Speech-to-Text
4. User input is collected until the user says "submit"
5. The collected text is spoken back and returned to the client

### POST /synthesize
1. The client sends a filename path in the request
2. The server reads text from the file
3. Azure Text-to-Speech synthesizes the text to audio
4. The audio is saved as a WAV file at the same path with `.wav` extension
5. The path to the audio file is returned to the client

## Notes

- The `/run` endpoint is blocking and will remain open for the duration of the speech session
- Ensure your microphone is enabled and properly configured
- The application requires active internet connection for Azure Cognitive Services
- Network timeouts should be set to at least 5 minutes (300 seconds)
