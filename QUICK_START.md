# Archived Quick Start

This quick-start guide has been archived and moved to `archive/removed_docs/QUICK_START.md`.

If you need the original quick start instructions, open the archived copy.

-- Cleaned by maintenance script
# 🚀 Quick Start Guide - Local AI Chatbot

## ✅ Everything is Ready!

Your local AI chatbot is now fully set up and running. Here's what's active:

- **✅ Ollama** - Running at `http://localhost:11434`
- **✅ Backend** - Running at `http://127.0.0.1:8000`
- **✅ Frontend** - Running at `http://localhost:3000`

## 🎯 What to Do Now

### 1. **Download an Ollama Model** (If you haven't already)

Open a PowerShell terminal and run:

```powershell
ollama pull mistral
```

Or try a smaller/faster model:
```powershell
ollama pull neural-chat
```

Check available models:
```powershell
ollama list
```

### 2. **Use the Chatbot**

1. Go to **http://localhost:3000** in your browser
2. Type a question and press Enter
3. Ollama will generate an answer (first time takes longer as it loads the model)

### 3. **Example Questions to Try**

- "What is machine learning?"
- "Explain blockchain in simple terms"
- "Write a Python hello world script"
- "What are the steps to make pizza?"
- "Summarize the importance of Python"

## 📁 Project Structure

```
llmlocalai/
├── 🌐 http://localhost:3000          ← Open this in browser
├── 🔌 http://127.0.0.1:8000          ← Backend API
├── 🤖 http://localhost:11434         ← Ollama (local LLM)
├── 📄 index.html                      ← UI
├── 📄 server.py                       ← UI Server
├── backend/
│   ├── app_simple.py                 ← Simplified backend (currently running)
│   └── ...
├── data/                             ← Your files go here (for future indexing)
└── .env                              ← Configuration
```

## ⌛ How It Works

1. **You type**: A question in the chat
2. **Backend**: Receives your question
3. **Ollama**: Generates an intelligent answer locally on your computer
4. **Response**: You get the answer instantly

## 🛠️ Stopping Services

To stop a service, go to its terminal window and press **Ctrl+C**:

```powershell
# Stop Ollama (first terminal)
Ctrl+C

# Stop Backend (second terminal)
Ctrl+C

# Stop UI Server (third terminal)
Ctrl+C
```

## 🔄 Restarting Services

### Restart everything:

```powershell
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
cd C:\Users\VAMSHI\llmlocalai\backend
python -m uvicorn app_simple:app --reload --host 127.0.0.1 --port 8000

# Terminal 3: UI
cd C:\Users\VAMSHI\llmlocalai
python server.py
```

Or use the automated launcher:

```powershell
.\LAUNCH.ps1
```

## 📚 Available Commands

**Test the backend:**
```powershell
# Check if backend is running
curl http://127.0.0.1:8000/health

# Ask a question via API
$body = @{query="Hello, how are you?"} | ConvertTo-Json
curl -X POST http://127.0.0.1:8000/ask `
  -H "Content-Type: application/json" `
  -d $body
```

**Check Ollama:**
```powershell
# List available models
curl http://localhost:11434/api/tags

# Check Ollama is running
ollama list
```

## 🎨 Features

✅ **Real-time Chat** - Get instant responses  
✅ **Multiple Models** - Switch models with `ollama pull MODEL_NAME`  
✅ **Fully Local** - Nothing leaves your computer  
✅ **Private** - No cloud, no tracking  
✅ **Fast** - Runs on your hardware  
✅ **No Setup** - Just click and chat  

## 💡 Tips & Tricks

1. **Try different models:**
   ```powershell
   ollama pull mistral        # Fast, accurate
   ollama pull neural-chat    # Optimized for chat
   ollama pull llama2         # Larger, more powerful
   ```

2. **Set default model in `.env`:**
   ```ini
   OLLAMA_MODEL=mistral
   ```

3. **Be specific with questions** for better answers:
   - ❌ "Tell me about programming"
   - ✅ "Explain Python decorators with examples"

4. **Check system resources:**
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like "*ollama*" -or $_.Name -like "*python*"} | Format-Table
   ```

## 🐛 Troubleshooting

**Q: Ollama not responding?**
```powershell
# Check if it's running
Test-NetConnection -ComputerName localhost -Port 11434

# Or check process
Get-Process -Name ollama -ErrorAction SilentlyContinue
```

**Q: Backend not starting?**
```powershell
cd C:\Users\VAMSHI\llmlocalai\backend
python -m uvicorn app_simple:app --host 127.0.0.1 --port 8000
```

**Q: No response from chatbot?**
1. Make sure Ollama has a model: `ollama list`
2. Download one: `ollama pull mistral`
3. Refresh the page
4. Try asking again

**Q: Want to use the full featured version with file indexing?**

The current version (app_simple.py) uses direct LLM queries. The full version (app.py) with file indexing is available but requires fixing dependency issues. You can upgrade later if needed.

## 🚀 Next Steps

1. ✅ Chat with Ollama (you're here!)
2. 📁 [Optional] Add file indexing for local document search
3. 🎨 [Optional] Customize the UI
4. 🚀 [Optional] Deploy to a web server

## 📞 Quick Reference

| What | Where |
|------|-------|
| Chat UI | http://localhost:3000 |
| API | http://127.0.0.1:8000 |
| Ollama | http://localhost:11434 |
| Config | `.env` file |
| Backend logs | Terminal window |
| Ollama logs | Terminal window |

---

**You're all set! 🎉 Start asking questions at http://localhost:3000**

Enjoy your private, local AI assistant!
