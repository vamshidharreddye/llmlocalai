import React, { useState, useEffect } from 'react'
import Chat from './components/Chat'
import Sources from './components/Sources'

const API_BASE = 'http://127.0.0.1:8000'

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `<div class="greeting-block"><strong style="font-size:18px;display:block;margin-bottom:10px">Hello — I'm your Local AI Assistant.</strong><div style="font-size:13px;color:#0b1220;line-height:1.5">I can search your files, summarize PDFs and text files, preview documents, and open files on your computer. Ask me anything about your files or just chat with me about general topics.</div></div>`
    }
  ])
  const [sources, setSources] = useState([])
  const [status, setStatus] = useState('')
  const [model, setModel] = useState('')

  useEffect(() => {
    // health check
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/health`)
        if (r.ok) setStatus('Connected')
        else setStatus('Backend unreachable')
      } catch (e) {
        setStatus('Backend unreachable')
      }
    })()
  }, [])

  useEffect(() => {
    // fetch config to learn default model
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/config`)
        const d = await r.json()
        setModel(d.ollama_model || '')
      } catch (e) {}
    })()
  }, [])

  function addMessage(role, content) {
    setMessages(m => [...m, { role, content, time: new Date().toLocaleTimeString() }])
  }

  function replaceLastAssistant(newContent) {
    setMessages(m => {
      const copy = [...m]
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === 'assistant' && (copy[i].content.includes('Thinking') || copy[i].content.includes('spinner') || copy[i].content.includes('Thinking...'))) {
          copy[i] = { ...copy[i], content: newContent, time: new Date().toLocaleTimeString() }
          return copy
        }
      }
      // fallback: append
      return [...copy, { role: 'assistant', content: newContent, time: new Date().toLocaleTimeString() }]
    })
  }

  function setSourceList(list) {
    setSources(list)
  }

  return (
    <div className="app-root">
      <div className="container">
        <div className="chat-panel">
          <div className="header">
            <div className="title-wrap">
              <div style={{width:44,height:44,display:'flex',alignItems:'center',justifyContent:'center',borderRadius:10,background:'linear-gradient(135deg,#8b5cf6,#06b6d4)'}}>
                <span style={{fontSize:20}}>🤖</span>
              </div>
              <div>
                <h1>Local AI Assistant</h1>
                <div className="desc">Search your files, summarize PDFs, preview and open results locally.</div>
              </div>
            </div>
            <div className="header-buttons">
                <div style={{display:'flex',alignItems:'center',gap:12}}>
                  <select value={model} onChange={e => setModel(e.target.value)} style={{padding:8,borderRadius:8,border:'1px solid rgba(0,0,0,0.06)'}}>
                    <option value="">(default)</option>
                    <option value="mistral">mistral</option>
                    <option value="tinyllama">tinyllama</option>
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                  </select>
                  <button className="btn-primary" onClick={async () => {
                try {
                  const r = await fetch(`${API_BASE}/reindex`, { method: 'POST' })
                  const data = await r.json()
                  addMessage('assistant', `<div class='success'>✅ Reindexed ${data.files_indexed} files</div>`)
                } catch (e) {
                  addMessage('assistant', `<div class='error'>Reindex failed: ${e.message}</div>`)
                }
                  }}>Reindex Files</button>
                </div>
            </div>
          </div>

            <Chat apiBase={API_BASE} selectedModel={model} addMessage={addMessage} replaceLastAssistant={replaceLastAssistant} setSourceList={setSourceList} messages={messages} />
        </div>

        <Sources apiBase={API_BASE} selectedModel={model || 'tinyllama'} sources={sources} addMessage={addMessage} />
      </div>
    </div>
  )
}
