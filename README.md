# AI Voice Assistant Bots

A real-time voice chatbot web application that combines browser speech recognition, streaming AI responses via Groq LLM, and text-to-speech synthesis. The entire application is contained in a single Python file for simplicity.

## Features

🎤 **Real-time Voice Recognition** - Uses browser's built-in speech recognition  
🤖 **AI-Powered Responses** - Powered by Groq LLM with streaming responses  
🔊 **Text-to-Speech** - Speaks responses back with natural voice synthesis  
💬 **Live Chat Interface** - Real-time conversation display with visual feedback  
📱 **Responsive Design** - Works on desktop and mobile browsers  
🛡️ **Graceful Fallback** - Works offline without AI when API unavailable  

## Architecture

- **Backend**: Flask server with embedded HTML/CSS/JS template
- **AI Integration**: Groq API for chat completions with graceful fallback mode
- **Frontend**: Single-page application with real-time voice interface
- **Streaming**: Server-Sent Events (SSE) for token-by-token response delivery

## Requirements

- Python 3.8+
- Chrome/Edge browser (recommended for speech recognition)
- Microphone access

# AI Voice Assistant Bots

A real-time voice chatbot web application that combines browser speech recognition, streaming AI responses via Groq LLM, and text-to-speech synthesis. The entire application is contained in a single Python file for simplicity.

---

## 🚀 Features
- Real-time voice recognition (browser-based)
- AI-powered responses via Groq LLM (streaming)
- Text-to-speech for spoken responses
- Live chat interface with visual feedback
- Responsive design for desktop and mobile
- Graceful fallback (works offline if API unavailable)

---

## 🛠️ Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Muhammad-Muzammil-Shah/AI_Voice_Assistant_Bots.git
   cd AI_Voice_Assistant_Bots
   ```
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # Or
   source .venv/bin/activate  # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Configure environment:
   ```bash
   echo "GROQ_API_KEY=your_groq_api_key_here" > .env
   echo "GROQ_MODEL=llama-3.1-8b-instant" >> .env
   ```

---

## 💡 Usage
1. Start the application:
   ```bash
   python web_voice_chatbot.py
   ```
2. Open your browser at `http://127.0.0.1:5000`
3. Allow microphone access and start chatting

---

## 📦 API Endpoints
- `/` - Main chat interface
- `/chat` - POST endpoint for text-based conversations
- `/chat_stream` - GET endpoint for streaming responses
- `/health_groq` - Health check for Groq API status

---

## ⚙️ Environment Variables
| Variable         | Description                                 | Default                  |
|------------------|---------------------------------------------|--------------------------|
| GROQ_API_KEY     | Your Groq API key (get from Groq Console)   | None                     |
| GROQ_MODEL       | Groq model to use                           | llama-3.1-8b-instant     |
| DEBUG            | Enable detailed error logging               | False                    |

---

## 🌐 Browser Compatibility
- Recommended: Chrome, Edge (full speech recognition)
- Supported: Firefox, Safari (limited speech recognition)
- Requirements: HTTPS or localhost for microphone access

---

## 📝 Troubleshooting
- **Port 5000 in use**: Stop other services or change port
- **Microphone issues**: Check browser permissions, use Chrome/Edge
- **No voice output**: Check browser TTS support and system volume
- **API key issues**: Verify format (should start with `gsk_`), check validity

---

## 🤝 Contributing
Fork the repo, create a feature branch, test, and submit a pull request.

---

## 📃 License
Open source. Feel free to use, modify, and distribute.

---

## 🙏 Acknowledgments
- [Groq](https://groq.com) for fast LLM inference
- [Flask](https://flask.palletsprojects.com/) for web framework
- Browser APIs for speech recognition and synthesis

---

**Built with ❤️ for seamless voice interactions**