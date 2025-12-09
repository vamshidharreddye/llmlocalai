# Local AI Chatbot Guide

## Overview
This is a local AI-powered file search and chat application that helps you search across your documents and files on your computer.

## Features
- Full-text search across PDFs, text files, Word documents
- AI-powered answers using Ollama (local LLM)
- Vector search using embeddings
- Beautiful web-based UI
- No data sent to the cloud - everything stays local

## Getting Started

### Prerequisites
- Python 3.8+
- Ollama installed and running on http://localhost:11434
- A modern web browser

### Installation
1. Install Python dependencies: `pip install -r requirements.txt`
2. Start Ollama: `ollama serve`
3. Run the backend: `python -m uvicorn app:app --reload`
4. Open `index.html` in your browser

### Usage
1. Click "Reindex Files" to scan your directories
2. Ask questions about your files
3. View results and source file paths in the right panel
4. Click on file paths to copy them to clipboard

## Architecture
- **Backend**: FastAPI with Python
- **Search**: ChromaDB for vector embeddings
- **LLM**: Local Ollama for question answering
- **Frontend**: Simple HTML/JavaScript UI

## Configuration
Edit `.env` file to configure:
- `LLM_PROVIDER`: Set to "ollama" for local mode
- `OLLAMA_BASE_URL`: URL to Ollama instance (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model name (default: mistral)
- `INDEX_DIRECTORIES`: Directories to index (comma-separated)

## Tips
- First indexing may take a few minutes depending on folder size
- Use specific keywords for better search results
- Make sure Ollama is running before asking questions
