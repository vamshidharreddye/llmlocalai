import React, { useState, useRef, useEffect } from 'react'

export default function Chat({ apiBase, selectedModel, addMessage, replaceLastAssistant, setSourceList, messages }) {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const sendBtnRef = useRef(null)
  const messagesRef = useRef(null)
  const abortRef = useRef([]) // support multiple in-flight controllers

  useEffect(() => {
    // auto-scroll to bottom when messages change
    try { messagesRef.current && (messagesRef.current.scrollTop = messagesRef.current.scrollHeight) } catch(e){}
  }, [messages])

  async function sendQuery(q) {
    if (!q || sending) return
    setSending(true)
    // create abort controller so the request can be cancelled
    const controller = new AbortController()
    abortRef.current.push(controller)

    addMessage('user', `<div>${escapeHtml(q)}</div>`)
    addMessage('assistant', `<div class="loading inline"><span class="spinner"></span>Thinking...</div>`)
    try {
      const resp = await fetch(`${apiBase}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, model: selectedModel }),
        signal: controller.signal
      })
      const data = await resp.json()

      // replace the previous loading assistant message with the actual answer
      if (data.answer) replaceLastAssistant(`<div>${escapeHtml(data.answer)}</div>`)

      if (data.markdown) {
        const cleaned = data.markdown.replace(/```(?:text)?\\n?|```/g, '')
        addMessage('assistant', `<pre>${escapeHtml(cleaned)}</pre>`)
      }

      setSourceList(data.sources || data.results || [])

    } catch (e) {
      if (e.name === 'AbortError') {
        replaceLastAssistant(`<div class='muted'>Request canceled.</div>`)
      } else {
        replaceLastAssistant(`<div class='error'>Error: ${escapeHtml(e.message)}</div>`)
      }
    } finally {
      setSending(false)
      // remove this controller from the list
      const idx = abortRef.current.indexOf(controller)
      if (idx >= 0) abortRef.current.splice(idx, 1)
    }
  }

  function escapeHtml(text){
    if(!text) return ''
    return text.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;"}[c]))
  }

  function stripHtml(html) {
    if (!html) return ''
    return html.replace(/<[^>]*>/g, '')
  }

  function copyToClipboard(text){
    try { navigator.clipboard.writeText(text) } catch(e){ /* ignore */ }
  }

  function cancelRequest(){
    try {
      abortRef.current.forEach(c => { try { c.abort() } catch(e){} })
    } finally {
      abortRef.current = []
      setSending(false)
    }
  }

  return (
    <div style={{height:'100%',display:'flex',flexDirection:'column'}}>
      <div className="messages" id="messages" ref={messagesRef} style={{flex:1}}>
        {(() => {
          const lastUserIndex = (() => {
            for (let j = messages.length - 1; j >= 0; j--) {
              if (messages[j] && messages[j].role === 'user') return j
            }
            return -1
          })()
          return messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              <div className="message-content" dangerouslySetInnerHTML={{ __html: m.content }} />
              <div className="message-meta small muted">{m.time || ''}</div>

              {i === lastUserIndex && m.role === 'user' ? (
                <div className="message-toolbar">
                  <button className="mini" onClick={() => copyToClipboard(stripHtml(m.content))} title="Copy">📋</button>
                  <button className="mini" onClick={() => { setInput(stripHtml(m.content)); }} title="Edit">✏️</button>
                </div>
              ) : null}
            </div>
          ))
        })()}
      </div>

      <div className="input-area">
        <div className="input-group">
          <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { sendQuery(input); /* keep input so user can edit while thinking */ }
          }} placeholder="Ask me anything about your files... (you can edit while I think)" />

          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <button ref={sendBtnRef} className="btn-primary" onClick={() => { sendQuery(input); }}>
              {sending ? (<span className="loading inline"><span className="spinner"></span> Sending</span>) : 'Send'}
            </button>
            {abortRef.current && abortRef.current.length > 0 ? (<button className="btn" onClick={cancelRequest}>Cancel</button>) : null}
          </div>
        </div>

        {/* note: copy/edit icons are shown on the last sent user message only */}
      </div>
    </div>
  )
}
