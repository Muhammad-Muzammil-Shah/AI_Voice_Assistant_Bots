# AI Voice Assistant Bot - Development Guide

## Project Overview
This is a real-time voice chatbot web application that combines browser speech recognition, streaming AI responses via Groq LLM, and text-to-speech synthesis. The entire application is contained in a single Python file for simplicity.

## Architecture
- **Backend**: Flask server (`web_voice_chatbot.py`) with embedded HTML/CSS/JS template
- **AI Integration**: Groq API for chat completions with graceful fallback mode
- **Frontend**: Single-page application with real-time voice interface
- **Streaming**: Server-Sent Events (SSE) for token-by-token response delivery

## Key Components

### Core Functions
- `_call_groq()`: Handles LLM API calls with error handling and validation
- `_manage_conversation_memory()`: Maintains conversation context within token limits
- `fallback_reply()`: Provides responses when Groq API is unavailable

### Routes
- `/` - Serves the embedded HTML interface
- `/chat` - POST endpoint for text-based conversations
- `/chat_stream` - GET endpoint for streaming responses via SSE
- `/health_groq` - Health check for Groq API status

### Memory Management
- Conversation history limited to `MAX_TURNS * 2` messages
- Automatic cleanup of invalid entries and consecutive same-role messages
- Token-efficient system prompts for voice interaction

## Environment Configuration
```bash
GROQ_API_KEY=gsk_...    # Required for AI features
GROQ_MODEL=llama-3.1-8b-instant  # Optional, defaults shown
DEBUG=1                 # Optional, enables detailed error logging
```

## Development Workflow

### Running the Application
```bash
python web_voice_chatbot.py
# Opens on http://127.0.0.1:5000
```

### Testing Components
- Use `/health_groq` endpoint to verify Groq API connectivity
- Test fallback mode by removing `GROQ_API_KEY`
- Browser console shows WebRTC and speech synthesis status

## Code Patterns

### Error Handling
- All external API calls return empty strings on failure for graceful degradation
- Import errors are caught to allow running without optional dependencies
- Comprehensive input validation for API parameters

### Frontend Integration
- Embedded HTML template in `TEMPLATE` constant for single-file deployment
- State management via visual circle indicator (idle/listening/thinking/speaking)
- Automatic voice synthesis with soft female voice preference

## Dependencies
- `Flask`: Web framework
- `groq`: LLM API client (optional, graceful fallback)
- `python-dotenv`: Environment variable loading

## Browser Requirements
- Chrome/Edge recommended for speech recognition (`webkitSpeechRecognition`)
- Requires HTTPS or localhost for microphone access
- Speech synthesis supported in all modern browsers

## Performance Considerations
- Chunked streaming responses (24 chars) for smooth voice synthesis
- Sentence-boundary TTS triggering for natural speech flow
- Memory cleanup prevents context window overflow

## Common Issues
- Port 5000 conflicts: Application detects and warns about port usage
- API key format validation: Warns if key doesn't match expected pattern
- Microphone permissions: Frontend gracefully handles denied access