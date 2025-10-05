"""Web-based real-time voice chatbot with Groq-backed responses.

This module serves a single-page application that records speech in the browser,
streams responses over Server-Sent Events, and speaks them back with a gentle
voice profile. It degrades gracefully when Groq isn't configured.
"""
from __future__ import annotations

import json
import os
import traceback
from typing import Any, Dict, Generator, Iterable, List, Union, Tuple

from flask import Flask, Response, jsonify, render_template_string, request
from dotenv import load_dotenv

try:
    from groq import Groq  # type: ignore
    GROQ_AVAILABLE = True
except ImportError:  # pragma: no cover - allows running without Groq installed
    Groq = None  # type: ignore[misc]
    GROQ_AVAILABLE = False
except Exception as e:  # pragma: no cover - catch other import errors
    print(f"Warning: Failed to import Groq: {e}")
    Groq = None  # type: ignore[misc]
    GROQ_AVAILABLE = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv(override=False)

APP = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip()

# Validate environment variables
if GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_"):
    print("Warning: GROQ_API_KEY format may be invalid (should start with 'gsk_')")

CLIENT = None
if GROQ_API_KEY and GROQ_AVAILABLE and Groq:
    try:
        CLIENT = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Groq client: {e}")
        CLIENT = None

MAX_TURNS = 10  # memory length (user+assistant pairs)


def _call_groq(messages: Iterable[Dict[str, str]], *, max_tokens: int, temperature: float) -> str:
  """Call Groq chat completions and return the assistant text.

  Any exception yields an empty string so callers can gracefully fallback.
  """

  if not CLIENT:
    return ""

  try:
    # Validate input parameters
    if not messages:
        return ""
    if max_tokens <= 0 or temperature < 0 or temperature > 2:
        print(f"Warning: Invalid parameters - max_tokens={max_tokens}, temperature={temperature}")
        return ""
    
    payload = [
      {"role": msg["role"], "content": msg["content"]}
      for msg in messages
      if msg.get("role") and msg.get("content")
    ]
    
    if not payload:
        return ""
    
    response = CLIENT.chat.completions.create(  # type: ignore[attr-defined]
      model=GROQ_MODEL,
      messages=payload,  # type: ignore[arg-type]
      max_tokens=max_tokens,
      temperature=temperature,
    )
    
    if not response.choices or not response.choices[0].message:
        return ""
        
    return (response.choices[0].message.content or "").strip()
  except Exception as exc:  # pragma: no cover - network errors vary
    print(f"[Groq API Error] {type(exc).__name__}: {exc}")
    if os.environ.get("DEBUG"):
        traceback.print_exc()
    return ""


CONVERSATION_MEMORY: List[Dict[str, str]] = []

def _manage_conversation_memory() -> None:
    """Ensure conversation memory doesn't exceed limits and contains valid entries."""
    global CONVERSATION_MEMORY
    
    # Remove invalid entries
    CONVERSATION_MEMORY = [
        msg for msg in CONVERSATION_MEMORY 
        if isinstance(msg, dict) and msg.get("role") and msg.get("content")
    ]
    
    # Trim to max turns (keep pairs of user/assistant messages)
    if len(CONVERSATION_MEMORY) > MAX_TURNS * 2:
        CONVERSATION_MEMORY = CONVERSATION_MEMORY[-(MAX_TURNS * 2):]
    
    # Ensure we don't have too many consecutive messages from same role
    cleaned = []
    last_role = None
    for msg in CONVERSATION_MEMORY:
        if msg["role"] != last_role or len(cleaned) == 0:
            cleaned.append(msg)
            last_role = msg["role"]
        else:
            # Merge consecutive messages from same role
            cleaned[-1]["content"] += " " + msg["content"]
    
    CONVERSATION_MEMORY = cleaned


# ---------------------------------------------------------------------------
# Frontend template (inline to keep repo lightweight)
# ---------------------------------------------------------------------------
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Voice Chatbot (Real-Time Streaming)</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f6f8fa; margin:0; }
    .container { min-height:100vh; display:flex; flex-direction:column; }
    .topbar { display:flex; justify-content:flex-end; padding:12px 16px; }
    .settings-btn { width:36px; height:36px; border:none; background:transparent;
      cursor:pointer; border-radius:50%; display:flex; align-items:center;
      justify-content:center; color:#6b7280; }
    .settings-btn:hover { background:#f3f4f6; }
    .stage { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px; }
    .conversation { max-width:600px; width:100%; max-height:300px; overflow-y:auto; 
      background:white; border-radius:12px; padding:16px; margin-bottom:20px; 
      box-shadow:0 4px 12px rgba(0,0,0,0.1); }
    .msg { margin:8px 0; padding:8px 12px; border-radius:8px; }
    .msg.user { background:#e3f2fd; text-align:right; }
    .msg.bot { background:#f5f5f5; }
    .msg.speaking { background:#e8f5e8; border-left:3px solid #4caf50; }
    .bottombar { display:flex; justify-content:center; gap:28px; padding:24px 0 40px; }
    .fab { width:72px; height:72px; border-radius:50%; border:none; background:#f4f4f5;
      box-shadow:0 8px 24px rgba(0,0,0,.08); display:flex; align-items:center;
      justify-content:center; cursor:pointer; transition:box-shadow .2s ease; }
    .fab:hover { box-shadow:0 10px 28px rgba(0,0,0,.12); }
    .fab svg { width:28px; height:28px; }
    .status, .conversation, .input-row { display:none !important; }
    .circle { position:relative; width:88px; height:88px; border-radius:50%; display:inline-block; }
    .circle.idle { background: radial-gradient(circle at 30% 30%, #93c5fd, #3b82f6);
      box-shadow:0 0 0 0 rgba(59,130,246,.6); animation: idlePulse 3s ease-in-out infinite; }
    .circle.listening { background: radial-gradient(circle at 30% 30%, #a5b4fc, #6366f1);
      box-shadow:0 0 0 0 rgba(99,102,241,.6); animation: listenPulse 1.2s ease-in-out infinite; }
    .circle.thinking { background: transparent; border:4px solid #e5e7eb;
      border-top-color:#3b82f6; animation: spin 1s linear infinite; box-sizing:border-box; }
    .circle.speaking { background: radial-gradient(circle at 30% 30%, #86efac, #16a34a);
      box-shadow:0 0 0 0 rgba(22,163,74,.55); animation: speakPulse .9s ease-in-out infinite; }
    .circle.listening::after { content:""; position:absolute; inset:-6px;
      border:3px solid rgba(99,102,241,.35); border-radius:50%; animation: ripple 1.6s ease-out infinite; }
    @keyframes idlePulse { 0%{transform:scale(1);} 50%{transform:scale(1.04);} 100%{transform:scale(1);} }
    @keyframes listenPulse { 0%{transform:scale(1);} 50%{transform:scale(1.08);} 100%{transform:scale(1);} }
    @keyframes speakPulse { 0%{transform:scale(1);} 50%{transform:scale(1.06);} 100%{transform:scale(1);} }
    @keyframes ripple { 0%{opacity:.8; transform:scale(1);} 100%{opacity:0; transform:scale(1.35);} }
    @keyframes spin { 0%{transform:rotate(0);} 100%{transform:rotate(360deg);} }
  </style>
</head>
<body>
  <div class="container">
    <div class="topbar">
      <button id="settingsBtn" class="settings-btn" aria-label="Settings" title="Settings">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <line x1="4" y1="6" x2="14" y2="6"></line>
          <circle cx="18" cy="6" r="2"></circle>
          <line x1="20" y1="12" x2="10" y2="12"></line>
          <circle cx="6" cy="12" r="2"></circle>
          <line x1="4" y1="18" x2="14" y2="18"></line>
          <circle cx="18" cy="18" r="2"></circle>
        </svg>
      </button>
    </div>

    <div class="stage">
      <div id="conv" class="conversation" style="display:none;"></div>
      <div id="stateCircle" class="circle idle" title="Idle"></div>
    </div>

    <div class="bottombar">
      <button id="micBtn" class="fab mic" aria-label="Start" title="Start">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 14a3 3 0 0 0 3-3V7a3 3 0 0 0-6 0v4a3 3 0 0 0 3 3z"></path>
          <path d="M19 11a7 7 0 0 1-14 0"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
          <line x1="8" y1="23" x2="16" y2="23"></line>
        </svg>
      </button>
      <button id="cancelBtn" class="fab cancel" aria-label="End" title="End">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div style="display:none">
      <div id="status" class="status">Ready</div>
      <div class="input-row">
        <input id="textInput" type="text" placeholder="Type your message..." />
        <button id="sendBtn" class="send">Send</button>
      </div>
      <button id="startBtn" class="start">Start</button>
      <button id="stopBtn" class="stop" disabled>End</button>
    </div>
  </div>

  <script>
    const statusEl = document.getElementById('status');
    const convEl = document.getElementById('conv');
    const startBtn = document.getElementById('startBtn');
    const stopBtn  = document.getElementById('stopBtn');
    const textInput= document.getElementById('textInput');
    const sendBtn  = document.getElementById('sendBtn');
    const circleEl = document.getElementById('stateCircle');
    const micBtn = document.getElementById('micBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const canSTT = !!SpeechRecognition;
    const canTTS = !!window.speechSynthesis;

  let recognition;
  let currentStream = null;
  let isStreaming = false;
  let currentBotDiv = null;
  let ttsBuffer = '';
  let recognitionActive = false;
  let resumeAfterSpeech = false;
    const sentenceEnd = /[.!?]/;

    if (canSTT) {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        recognitionActive = true;
        setStatus('Listening…');
        setMode('listening');
        try { speechSynthesis.cancel(); } catch {}
      };
      recognition.onerror = (e) => setStatus('Mic error: ' + e.error);
      recognition.onend = () => {
        recognitionActive = false;
        if (resumeAfterSpeech) {
          return;
        }
        stopBtn.disabled = true;
        startBtn.disabled = false;
        if (statusEl.textContent.startsWith('Listening')) setStatus('Ready');
        setMode('idle');
      };
      recognition.onresult = async (event) => {
        let finalText = '';
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i];
          if (res.isFinal) finalText += res[0].transcript;
          else interim += res[0].transcript;
        }
        if (interim) setStatus('Listening… ' + interim);
        if (finalText) {
          setStatus('Thinking…');
          setMode('thinking');
          addMsg(finalText, true);
          await streamFromServer(finalText);
        }
      };
    }

    startBtn.onclick = () => {
      if (!canSTT) return setStatus('Speech recognition not supported in this browser.');
      resumeAfterSpeech = false;
      startBtn.disabled = true;
      startBtn.style.display = 'none';
      stopBtn.disabled = false;
      stopBtn.style.display = 'inline-block';
      setMode('listening');
      recognition.start();
    };
    micBtn.onclick = () => startBtn.onclick();
    stopBtn.onclick = () => {
      resumeAfterSpeech = false;
      recognitionActive = false;
      isCurrentlySpeaking = false;
      try { recognition.stop(); } catch {}
      try { speechSynthesis.cancel(); } catch {}
      if (currentStream) { try { currentStream.close(); } catch {} currentStream = null; }
      isStreaming = false;
      ttsBuffer = '';
      fullResponseText = '';
      ttsQueue = [];
      currentBotDiv = null;
      stopBtn.disabled = true;
      stopBtn.style.display = 'none';
      startBtn.disabled = false;
      startBtn.style.display = 'inline-block';
      setStatus('Ready');
      setMode('idle');
    };
    cancelBtn.onclick = () => stopBtn.onclick();

    sendBtn.onclick = async () => {
      const text = textInput.value.trim();
      if (!text) return;
      addMsg(text, true);
      textInput.value = '';
      setMode('thinking');
      await streamFromServer(text);
    };

    function addMsg(text, isUser) {
      if (convEl.style.display === 'none') {
        convEl.style.display = 'block';
      }
      const div = document.createElement('div');
      div.className = 'msg ' + (isUser ? 'user' : 'bot');
      div.textContent = text;
      convEl.appendChild(div);
      convEl.scrollTop = convEl.scrollHeight;
      return div;
    }

    function setStatus(s) { statusEl.textContent = s; }
    function setMode(mode) {
      if (!circleEl) return;
      circleEl.className = 'circle ' + mode;
      circleEl.title = mode.charAt(0).toUpperCase() + mode.slice(1);
    }

    async function streamFromServer(text) {
      currentBotDiv = addMsg('', false);
      if (currentStream) { try { currentStream.close(); } catch {} }
      isStreaming = true;
      ttsBuffer = '';
      fullResponseText = '';  // Reset full response
      
      // Clear any pending speech
      try { speechSynthesis.cancel(); } catch {}
      ttsQueue = [];
      isCurrentlySpeaking = false;

      try {
        const url = '/chat_stream?q=' + encodeURIComponent(text);
        const es = new EventSource(url);
        currentStream = es;

        es.onmessage = (ev) => {
          if (ev.data === '[DONE]') {
            isStreaming = false;
            setStatus('Ready');
            
            // Speak the complete response at the end
            if (fullResponseText.trim()) {
              console.log('Speaking complete response:', fullResponseText);
              speakComplete(fullResponseText.trim());
            }
            
            es.close();
            currentStream = null;
            return;
          }
          try {
            const payload = JSON.parse(ev.data);
            const token = payload.token || '';
            currentBotDiv.textContent += token;
            convEl.scrollTop = convEl.scrollHeight;
            
            // Collect the full response
            fullResponseText += token;
            
            // Still show visual feedback but don't speak chunks
            if (isStreaming) setMode('thinking');
            
          } catch { /* ignore parse errors */ }
        };
        es.onerror = () => {
          setStatus('Stream error');
          try { es.close(); } catch {}
          currentStream = null;
          isStreaming = false;
          // Speak whatever we have if there was an error
          if (fullResponseText.trim()) {
            speakComplete(fullResponseText.trim());
          }
        };
      } catch (e) {
        console.error('EventSource failed, falling back to POST.', e);
        setStatus('Streaming not supported, falling back.');
        await sendToServer(text);
      }
    }

    async function sendToServer(text) {
      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        const botResponse = data.bot_response || 'No response';
        addMsg(botResponse, false);
        setStatus('Ready');
        // Use complete speech function for non-streaming responses too
        if (botResponse) {
          speakComplete(botResponse);
        }
      } catch (e) {
        console.error('POST /chat failed', e);
        setStatus('Error talking to server');
      }
    }

    function selectSoftVoice() {
      const voices = speechSynthesis.getVoices() || [];
      if (!voices.length) return null;
      let best = null;
      let bestScore = -1;
      for (const voice of voices) {
        let score = 0;
        const name = (voice.name || '').toLowerCase();
        const vlang = (voice.lang || '').toLowerCase();
        if (vlang.startsWith('en-gb')) score += 4;
        else if (vlang.startsWith('en')) score += 3;
        if (name.includes('female')) score += 2;
        if (name.includes('natural') || name.includes('neural')) score += 2;
        if (name.includes('aria') || name.includes('jenny') || name.includes('sonia') || name.includes('emma') || name.includes('olivia') || name.includes('zira')) score += 1;
        if (name.includes('google') || name.includes('microsoft')) score += 1;
        if (score > bestScore) {
          bestScore = score;
          best = voice;
        }
      }
      return best;
    }

    // Function to speak complete response text
    function speakComplete(text) {
      if (!canTTS || !text || isCurrentlySpeaking) return;
      
      console.log('speakComplete called with:', text);
      isCurrentlySpeaking = true;
      
      // Show speaking caption
      if (currentBotDiv) {
        currentBotDiv.classList.add('speaking');
      }
      
      // Cancel any existing speech
      try { speechSynthesis.cancel(); } catch {}
      
      const utterance = new SpeechSynthesisUtterance(text);
      const shouldPauseRecognition = canSTT && recognition && recognitionActive;
      
      if (shouldPauseRecognition) {
        resumeAfterSpeech = true;
        recognitionActive = false;
        try { recognition.stop(); } catch {}
      }
      
      const voice = selectSoftVoice();
      if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang || 'en-GB';
      } else {
        utterance.lang = 'en-GB';
      }
      
      utterance.rate = 0.85;  // Slightly slower for better comprehension
      utterance.pitch = 1.0;
      utterance.volume = 1.0;  // Full volume
      
      setMode('speaking');
      
      utterance.onstart = () => {
        console.log('Speech started');
        isCurrentlySpeaking = true;
        if (currentBotDiv) {
          currentBotDiv.classList.add('speaking');
        }
      };
      
      utterance.onend = () => {
        console.log('Speech ended');
        isCurrentlySpeaking = false;
        if (currentBotDiv) {
          currentBotDiv.classList.remove('speaking');
        }
        if (resumeAfterSpeech && shouldPauseRecognition && canSTT && recognition) {
          resumeAfterSpeech = false;
          try {
            recognition.start();
          } catch {}
        } else {
          resumeAfterSpeech = false;
        }
        setMode('idle');
      };
      
      utterance.onerror = (e) => {
        console.error('Speech error:', e);
        isCurrentlySpeaking = false;
        if (currentBotDiv) {
          currentBotDiv.classList.remove('speaking');
        }
        setMode('idle');
      };
      
      // Wait a moment for any pending operations to complete
      setTimeout(() => {
        speechSynthesis.speak(utterance);
      }, 100);
    }

    function speak(text) {
      if (!canTTS || !text) return;
      
      // Show speaking caption
      if (currentBotDiv) {
        currentBotDiv.classList.add('speaking');
      }
      
      const utterance = new SpeechSynthesisUtterance(text);
      const shouldPauseRecognition = canSTT && recognition && recognitionActive;
      if (shouldPauseRecognition) {
        resumeAfterSpeech = true;
        recognitionActive = false;
        try { recognition.stop(); } catch {}
      }
      const voice = selectSoftVoice();
      if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang || 'en-GB';
      } else {
        utterance.lang = 'en-GB';
      }
      utterance.rate = 0.85;  // Slightly slower for better comprehension
      utterance.pitch = 1.0;
      utterance.volume = 0.9;
      setMode('speaking');
      
      utterance.onstart = () => {
        if (currentBotDiv) {
          currentBotDiv.classList.add('speaking');
        }
      };
      
      utterance.onend = () => {
        if (currentBotDiv) {
          currentBotDiv.classList.remove('speaking');
        }
        if (resumeAfterSpeech && shouldPauseRecognition && canSTT && recognition) {
          resumeAfterSpeech = false;
          try {
            recognition.start();
          } catch {}
        } else {
          resumeAfterSpeech = false;
        }
        if (!isStreaming) setMode('idle');
      };
      
      speechSynthesis.speak(utterance);
    }
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------
@APP.route("/")
def index() -> Response:
    response = Response(render_template_string(TEMPLATE))
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@APP.route("/chat", methods=["POST"])
def chat():
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        payload = request.get_json(silent=True) or {}
        user_text = (payload.get("text") or "").strip()
        
        if not user_text:
            return jsonify({"bot_response": "Please say or type something."})
        
        # Validate input length
        if len(user_text) > 1000:
            return jsonify({"bot_response": "Your message is too long. Please keep it under 1000 characters."})

        CONVERSATION_MEMORY.append({"role": "user", "content": user_text})
        _manage_conversation_memory()

        if CLIENT:
            try:
                print("[chat] user:", user_text[:200])
            except Exception:
                pass
            system_prompt = (
                "You are a helpful, detailed voice assistant. "
                "Provide comprehensive and informative responses in 3-8 sentences. "
                "Be conversational and engaging while being accurate and helpful. "
                "Use simple English without markdown formatting."
            )
            messages = [{"role": "system", "content": system_prompt}] + CONVERSATION_MEMORY
            bot_text = _call_groq(messages, max_tokens=800, temperature=0.4) or fallback_reply(user_text)
        else:
            bot_text = fallback_reply(user_text)

        if not bot_text:
            bot_text = fallback_reply(user_text)

        try:
            print("[chat] bot_len:", len(bot_text))
        except Exception:
            pass

        CONVERSATION_MEMORY.append({"role": "assistant", "content": bot_text})
        return jsonify({"bot_response": bot_text})
        
    except Exception as e:
        print(f"[chat] Error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@APP.route("/chat_stream", methods=["GET"])
def chat_stream() -> Response:
    try:
        user_text = (request.args.get("q") or "").strip()
        
        if not user_text:
            def empty_gen() -> Generator[str, None, None]:
                yield 'data: {"token": "Please say or type something."}\n\n'
                yield "data: [DONE]\n\n"
            return Response(empty_gen(), mimetype="text/event-stream", headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            })
        
        # Validate input length
        if len(user_text) > 1000:
            def error_gen() -> Generator[str, None, None]:
                yield 'data: {"token": "Your message is too long. Please keep it under 1000 characters."}\n\n'
                yield "data: [DONE]\n\n"
            return Response(error_gen(), mimetype="text/event-stream", headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            })

        CONVERSATION_MEMORY.append({"role": "user", "content": user_text})
        _manage_conversation_memory()

        if CLIENT:
            try:
                print("[chat_stream] user:", user_text[:200])
            except Exception:
                pass
            system_prompt = (
                "You are a helpful, detailed voice assistant. "
                "Provide comprehensive and informative responses in 3-8 sentences. "
                "Be conversational and engaging while being accurate and helpful. "
                "Use simple English without markdown formatting."
            )
            messages = [{"role": "system", "content": system_prompt}] + CONVERSATION_MEMORY
            full_text = _call_groq(messages, max_tokens=600, temperature=0.4) or fallback_reply(user_text)
        else:
            full_text = fallback_reply(user_text)

        if not full_text:
            full_text = fallback_reply(user_text)

        def generate() -> Generator[str, None, None]:
            try:
                sent = ""
                chunk_size = min(24, max(1, len(full_text) // 20))  # Adaptive chunk size
                for idx in range(0, len(full_text), chunk_size):
                    token = full_text[idx: idx + chunk_size]
                    if token:  # Only yield non-empty tokens
                        sent += token
                        yield f"data: {json.dumps({'token': token})}\n\n"
                CONVERSATION_MEMORY.append({"role": "assistant", "content": sent})
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"[chat_stream] Generator error: {e}")
                yield f"data: {json.dumps({'token': 'Sorry, there was an error generating the response.'})}\n\n"
                yield "data: [DONE]\n\n"

        return Response(generate(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        })
        
    except Exception as e:
        print(f"[chat_stream] Error: {e}")
        def error_gen() -> Generator[str, None, None]:
            yield 'data: {"token": "Sorry, there was a server error."}\n\n'
            yield "data: [DONE]\n\n"
        return Response(error_gen(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })


def fallback_reply(text: str) -> str:
    """Generate a fallback response when Groq is unavailable."""
    if not text or not isinstance(text, str):
        return "I didn't understand that. Please try again."
        
    try:
        lowered = text.lower().strip()
        
        if any(greeting in lowered for greeting in ("hello", "hi", "hey", "good morning", "good afternoon", "good evening")):
            return "Hello there! I'm your voice assistant, and I'm excited to help you today. Feel free to ask me questions, have a conversation, or just chat about anything that interests you. What would you like to talk about?"
            
        if any(word in lowered for word in ("time", "clock")):
            try:
                from datetime import datetime
                current_time = datetime.now()
                return f"The current time is {current_time.strftime('%I:%M %p')} on {current_time.strftime('%A, %B %d, %Y')}. Is there anything specific you'd like to do or discuss at this time?"
            except Exception:
                return "I can't tell you the time right now, but I'm still here to chat with you about other topics."
                
        if any(word in lowered for word in ("date", "today", "day")):
            try:
                from datetime import date
                today = date.today()
                return f"Today is {today.strftime('%A, %B %d, %Y')}. It's a great day to learn something new or have an interesting conversation. What would you like to explore today?"
            except Exception:
                return "I can't tell you the date right now, but I'm still here to have a good conversation with you."
                
        if "joke" in lowered or "funny" in lowered:
            try:
                import random
                jokes = [
                    "Why don't scientists trust atoms? Because they make up everything! But seriously, atoms are fascinating - they're the building blocks of everything around us.",
                    "I told my computer I needed a break, and it said 'No problem — I'll go to sleep.' Technology can be quite helpful when it comes to taking breaks, don't you think?",
                    "Why was the math book sad? Because it had too many problems. But unlike math books, I'm here to help solve problems, not create them!",
                    "Why did the programmer quit his job? He didn't get arrays! Programming humor aside, I'd love to help you with any questions you might have.",
                    "How do you comfort a JavaScript bug? You console it! Speaking of coding, are you interested in programming or technology topics?"
                ]
                return random.choice(jokes)
            except Exception:
                return "Here's a joke: Why did the computer go to the doctor? Because it had a virus!"
                
        if any(word in lowered for word in ("weather", "temperature")):
            return "I don't have access to weather information, but you can check your local weather app!"
            
        if any(word in lowered for word in ("help", "what can you do")):
            return "I can chat with you about various topics, tell you the current time and date, share some jokes to brighten your day, and engage in interesting conversations. While I'm currently running in offline mode, I'm still here to be your friendly companion. What would you like to talk about today?"
            
        return "That's an interesting topic! I'd love to help you explore that further. While I'm currently running in offline mode, I can still chat with you about various topics. Feel free to ask me about the time, date, or request a joke to lighten the mood. What else would you like to discuss?"
        
    except Exception as e:
        print(f"[fallback_reply] Error: {e}")
        return "I'm having trouble understanding. Please try again."


@APP.route("/health_groq")
def health_groq():
    """Health check endpoint for Groq integration status."""
    try:
        status = {
            "groq_available": GROQ_AVAILABLE,
            "groq_installed": bool(Groq),
            "api_key_present": bool(GROQ_API_KEY),
            "api_key_format_valid": bool(GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_")),
            "model": GROQ_MODEL,
            "client_initialized": bool(CLIENT),
            "using_fallback": not bool(CLIENT),
            "conversation_memory_size": len(CONVERSATION_MEMORY),
        }
        
        if CLIENT:
            try:
                probe = _call_groq([
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Reply with OK."},
                ], max_tokens=5, temperature=0.0)
                status["probe_ok"] = bool(probe and ("ok" in probe.lower() or len(probe) > 0))
                status["probe_sample"] = probe[:50] if probe else None
            except Exception as e:
                status["probe_ok"] = False
                status["probe_error"] = str(e)
                
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            "error": "Health check failed",
            "details": str(e)
        }), 500


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting Web Speech Voice Chatbot…")
    
    # Status reporting
    if not GROQ_AVAILABLE:
        print("Note: Groq package not available. Running in fallback mode.")
    elif not GROQ_API_KEY:
        print("Note: GROQ_API_KEY not set. Running in fallback mode.")
    elif not CLIENT:
        print("Note: Groq client initialization failed. Running in fallback mode.")
    else:
        print(f"✓ Groq enabled. Model: {GROQ_MODEL}")
        print(f"✓ API key format: {'valid' if GROQ_API_KEY.startswith('gsk_') else 'may be invalid'}")
    
    print("\n📝 Instructions:")
    print("1. Open http://127.0.0.1:5000 in Chrome/Edge")
    print("2. Allow microphone access when prompted")
    print("3. Click the microphone button to start voice chat")
    print("\n🔧 Endpoints:")
    print("   • / - Main chat interface")
    print("   • /chat - Text-based chat API")
    print("   • /chat_stream - Streaming chat API")
    print("   • /health_groq - Health check")
    
    try:
        # Validate port availability
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        if result == 0:
            print("\n⚠️  Warning: Port 5000 may already be in use")
        
        APP.run(debug=True, port=5000, host='127.0.0.1')
    except KeyboardInterrupt:
        print("\n👋 Chatbot stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        print("Try using a different port or check if another application is using port 5000")