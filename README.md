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
- Groq API key (optional, works in fallback mode without it)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Muhammad-Muzammil-Shah/AI_Voice_Assistant_Bots.git
   cd AI_Voice_Assistant_Bots
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (optional)**
   ```bash
   # Create .env file
   echo "GROQ_API_KEY=your_groq_api_key_here" > .env
   echo "GROQ_MODEL=llama-3.1-8b-instant" >> .env
   ```

## Usage

1. **Start the application**
   ```bash
   python web_voice_chatbot.py
   ```

2. **Open in browser**
   - Navigate to `http://127.0.0.1:5000`
   - Allow microphone access when prompted

3. **Start chatting**
   - Click the microphone button to start voice chat
   - Speak your question or message
   - Watch the response appear in real-time
   - Listen to the AI's spoken response

## API Endpoints

- `/` - Main chat interface
- `/chat` - POST endpoint for text-based conversations
- `/chat_stream` - GET endpoint for streaming responses via SSE
- `/health_groq` - Health check for Groq API status

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key (get from [Groq Console](https://console.groq.com)) | None |
| `GROQ_MODEL` | Groq model to use | `llama-3.1-8b-instant` |
| `DEBUG` | Enable detailed error logging | `False` |

## Browser Compatibility

- **Recommended**: Chrome, Edge (full speech recognition support)
- **Supported**: Firefox, Safari (limited speech recognition)
- **Requirements**: HTTPS or localhost for microphone access

## Key Features Implementation

### Voice Recognition
- Uses `webkitSpeechRecognition` for real-time speech input
- Supports continuous listening with interim results
- Automatic speech-to-text conversion

### AI Responses
- Streaming responses via Server-Sent Events
- Token-by-token delivery for real-time experience
- Configurable response length (3-8 sentences)

### Text-to-Speech
- Complete response synthesis (no interruptions)
- Smart voice selection (prefers female, natural voices)
- Visual feedback during speech playback

### Conversation Management
- Maintains conversation history
- Automatic memory cleanup to prevent context overflow
- Visual chat display with user/bot message distinction

## Troubleshooting

### Common Issues

1. **Port 5000 already in use**
   - The app will detect and warn about port conflicts
   - Stop other services using port 5000 or modify the port in code

2. **Microphone not working**
   - Ensure browser has microphone permissions
   - Use HTTPS or localhost (required for microphone access)
   - Try Chrome/Edge for best compatibility

3. **No voice output**
   - Check browser's text-to-speech support
   - Ensure system volume is on
   - Try different browsers if issues persist

4. **API key issues**
   - Verify Groq API key format (should start with `gsk_`)
   - Check API key validity at [Groq Console](https://console.groq.com)
   - App works in fallback mode without API key

## Development

### File Structure
```
AI_Voice_Assistant_Bots/
├── web_voice_chatbot.py     # Main application file
├── requirements.txt         # Python dependencies
├── .github/                 # GitHub configuration
│   └── copilot-instructions.md
├── .env                     # Environment variables (optional)
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

### Key Functions
- `_call_groq()`: Handles LLM API calls with error handling
- `_manage_conversation_memory()`: Maintains conversation context
- `fallback_reply()`: Provides responses when Groq API unavailable
- `speakComplete()`: Text-to-speech for complete responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Feel free to use, modify, and distribute.

## Acknowledgments

- [Groq](https://groq.com) for fast LLM inference
- [Flask](https://flask.palletsprojects.com/) for web framework
- Browser APIs for speech recognition and synthesis

---

**Built with ❤️ for seamless voice interactions**