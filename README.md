# 🤖 Local AI File Chatbot

A powerful, privacy-first desktop AI agent that searches your local files and answers questions using Ollama (local LLM). No data leaves your computer.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Features

- 🔍 **Full-Text & Vector Search** - Find files using semantic search
- 🤖 **Local AI** - Uses Ollama for completely private question answering
- 📄 **Multiple Formats** - Support for PDF, DOCX, TXT, MD files
- 🚀 **Fast** - Instant search and responses
- 🔒 **Private** - Everything stays on your machine
- 💻 **Beautiful UI** - Clean, modern chat interface
- ⚡ **Zero Setup** - One-click launch

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.ai) installed and running
- Windows, macOS, or Linux

### Installation (Windows)

1. **Clone/Download** this repository

2. **Install Python dependencies**:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

3. **Start Ollama** (if not already running):
   ```powershell
   ollama serve
   ```

4. **Run the launcher**:
   ```powershell
   # Double-click START.bat  
   # OR
   .\START.ps1
   ```

That's it! Your browser will open to `http://localhost:3000`

## 📖 Usage

### Basic Workflow

1. **Add Your Files**
   - Copy PDFs, Word docs, text files to the `data/` folder
   
2. **Index Files**
   - Click "Reindex Files" button in the chat
   
3. **Ask Questions**
   - Type your question and press Enter
   - Chatbot searches your files and answers

4. **View Sources**
   - See which files were used in the right panel
   - Click filenames to copy their paths

### Example Queries

```
"Summarize the main points from my documents"
"Find all references to machine learning"
"What does the technical specification say about authentication?"
"Which file mentions the API endpoints?"
"Explain the deployment process"
```

## 📁 Project Structure

```
llmlocalai/
├── 📄 START.bat                    # Windows launcher (batch)
├── 📄 START.ps1                    # Windows launcher (PowerShell)
├── 🌐 index.html                   # Web UI
├── 📄 server.py                    # UI HTTP server
├── 📋 SETUP_GUIDE.md              # Detailed setup guide
├── 📋 README.md                    # This file
├── 📋 .env                         # Configuration
│
├── 📂 backend/
│   ├── 🐍 app.py                  # FastAPI main application
│   ├── 🔍 indexer.py              # File indexing & embedding
│   ├── 🔎 search.py               # Vector search
│   ├── 🤖 llm_client.py           # Ollama integration
│   ├── 📄 file_extractor.py       # PDF/DOCX/TXT parsing
│   └── 📋 requirements.txt         # Python dependencies
│
├── 📂 data/                        # Your files go here ⭐
│   ├── test_docs/
│   └── README.md
│
└── 📂 vector_store/               # Embeddings database (auto-created)
```

## ⚙️ Configuration

Edit `.env` file to customize behavior:

```ini
# LLM Provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral  # Can use: mistral, llama2, neural-chat, etc.

# Search Settings
VECTOR_DB_PATH=./vector_store
CHUNK_SIZE=2000
TOP_K_RESULTS=5

# Directories to Index (comma-separated)
INDEX_DIRECTORIES=./data,./data/test_docs
```

## 🔌 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check if API is alive |
| `/reindex` | POST | Scan and index directories |
| `/ask` | POST | Ask a question |
| `/llm-config` | GET | View configuration |

**Example: Ask a question**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is in my files?"}'
```

## 🗂️ File Format Support

| Format | Extension | Support |
|--------|-----------|---------|
| PDF | `.pdf` | ✅ Full |
| Word | `.docx` | ✅ Full |
| Text | `.txt` | ✅ Full |
| Markdown | `.md` | ✅ Full |
| Images | `.jpg, .png` | ⏳ Metadata only |

## 🔒 Privacy & Security

✅ **Completely Private**
- All files indexed locally
- No cloud API calls
- Ollama runs on your machine
- Data never leaves your computer

✅ **Secure**
- Backend listens only on localhost
- Single machine architecture
- No external dependencies

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Check Python installation
python --version

# Reinstall dependencies
pip install -r backend/requirements.txt

# Start manually
cd backend
python -m uvicorn app:app --reload
```

### Ollama connection error
```powershell
# Make sure Ollama is running
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Files not indexed
1. Ensure files are in `data/` folder
2. Supported formats only (.txt, .pdf, .docx, .md)
3. Click "Reindex Files" button
4. Check browser console for errors

### UI not loading
```powershell
# Restart UI server
python server.py
# Then open http://localhost:3000
```

### No search results
- Try simpler, more specific keywords
- Make sure files are indexed (click Reindex)
- Use descriptive words from your documents

## 📊 How It Works

### Indexing Pipeline
```
Your Files (PDFs, DOCX, TXT)
    ↓
Extract Text Content
    ↓
Split into Chunks
    ↓
Create Vector Embeddings (sentence-transformers)
    ↓
Store in ChromaDB
    ↓
Ready for Search!
```

### Query Pipeline
```
Your Question
    ↓
Embed Question
    ↓
Vector Search (find similar docs)
    ↓
Retrieve Top N Results
    ↓
Format with Ollama Prompt
    ↓
Generate Answer Locally (Ollama)
    ↓
Return Answer + Source Files
```

## 🎯 Performance Tips

1. **Fewer, Larger Files** - One 100-page doc is faster than 100 small files
2. **Specific Keywords** - "kubernetes pod security policy" beats "kubernetes"
3. **Organize Folders** - Group related documents in subfolders
4. **Use Reindex Wisely** - Only reindex when you add new files
5. **Pick Right Model** - Mistral is faster, Llama2 is more accurate

## 🧪 Testing

**Test the API directly:**
```powershell
# Health check
curl http://127.0.0.1:8000/health

# Reindex
curl -X POST http://127.0.0.1:8000/reindex

# Ask question
curl -X POST http://127.0.0.1:8000/ask `
  -H "Content-Type: application/json" `
  -d '{"query": "test query"}'
```

## 🚀 Advanced Usage

### Using Different Ollama Models

```bash
# List available models
ollama list

# Download new model
ollama pull llama2
ollama pull neural-chat

# Use in .env
OLLAMA_MODEL=llama2
```

### Indexing Large Document Collections

```powershell
# Reindex with more results
# Edit .env: TOP_K_RESULTS=10

# Increase chunk size for faster but less granular search
# Edit .env: CHUNK_SIZE=4000
```

### Custom Directory Structure

```ini
# .env
INDEX_DIRECTORIES=C:/Users/You/Documents,C:/Data/Projects,D:/Archive
```

## 📝 Examples

### Question: "Summarize the architecture"
**Answer from bot:** "Based on your documents, the architecture consists of..."
**Sources:** 
- `C:/Users/VAMSHI/llmlocalai/data/architecture.md`
- `C:/Users/VAMSHI/llmlocalai/data/design-doc.pdf`

### Question: "What are the API endpoints?"
**Answer from bot:** "According to your documentation, the main endpoints are..."
**Sources:**
- `C:/Users/VAMSHI/llmlocalai/data/api-reference.docx`

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests!

## 📄 License

MIT License - feel free to use for personal or commercial projects

## 💡 Ideas & Improvements

- [ ] Add image OCR support
- [ ] Database search
- [ ] Multi-language support  
- [ ] Custom system prompts
- [ ] Export chat history
- [ ] Plugin system
- [ ] Mobile app
- [ ] Collaborative features

## 📞 Support

1. Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup
2. Review terminal output for error messages
3. Ensure Ollama is running
4. Try reindexing your files

## 🎉 You're All Set!

Your local AI chatbot is ready to use:
- 🌐 **UI**: http://localhost:3000
- 🔌 **API**: http://127.0.0.1:8000
- 📁 **Data**: Add files to `data/` folder
- 🚀 **Launch**: Double-click `START.bat` or run `START.ps1`

**Happy searching and enjoy your private AI assistant! 🚀**

---

Built with ❤️ using FastAPI, ChromaDB, Ollama, and Python
