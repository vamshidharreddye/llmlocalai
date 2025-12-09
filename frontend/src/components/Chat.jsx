import React, { useState, useRef, useEffect } from 'react'

export default function Chat({ apiBase, selectedModel, addMessage, replaceLastAssistant, setSourceList, messages }) {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [editingIndex, setEditingIndex] = useState(null)    // <--- index of msg being edited
  const [editingText, setEditingText] = useState('')        // <--- text for inline edit
  const sendBtnRef = useRef(null)
  const messagesRef = useRef(null)
  const abortRef = useRef([])

  useEffect(() => {
    try {
      if (messagesRef.current) {
        messagesRef.current.scrollTop = messagesRef.current.scrollHeight
      }
    } catch (e) {}
  }, [messages])

  async function sendQuery(q) {
    if (!q || sending) return
    setSending(true)
    const controller = new AbortController()
    abortRef.current.push(controller)

    addMessage('user', `<div>${escapeHtml(q)}</div>`)
    addMessage('assistant', `<div class="loading inline"><span class="spinner"></span>Thinking...</div>`)

    try {
      const resp = await fetch(`${apiBase}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, model: selectedModel }),
        signal: controller.signal,
      })
      const data = await resp.json()

      if (data.answer) {
        replaceLastAssistant(`<div>${escapeHtml(data.answer)}</div>`)
      }

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
      const idx = abortRef.current.indexOf(controller)
      if (idx >= 0) abortRef.current.splice(idx, 1)
      // when a send finishes, leave edit mode
      setEditingIndex(null)
      setEditingText('')
    }
  }

  function escapeHtml(text) {
    if (!text) return ''
    return text.replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    }[c]))
  }

  function stripHtml(html) {
    if (!html) return ''
    return html.replace(/<[^>]*>/g, '')
  }

  function copyToClipboard(text) {
    try {
      navigator.clipboard.writeText(text)
    } catch (e) {
      // ignore
    }
  }

  function cancelRequest() {
    try {
      abortRef.current.forEach(c => {
        try { c.abort() } catch (e) {}
      })
    } finally {
      abortRef.current = []
      setSending(false)
    }
  }

  async function handleEditSave() {
    const trimmed = editingText.trim()
    if (!trimmed) return
    // send the edited text as a new query in the same session
    await sendQuery(trimmed)
    // sendQuery's finally will reset editingIndex/editingText
  }

  function handleEditClick(i, m) {
    setEditingIndex(i)
    setEditingText(stripHtml(m.content))
  }

  function handleEditCancel() {
    setEditingIndex(null)
    setEditingText('')
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="messages" id="messages" ref={messagesRef} style={{ flex: 1 }}>
        {(() => {
          const lastUserIndex = (() => {
            for (let j = messages.length - 1; j >= 0; j--) {
              if (messages[j] && messages[j].role === 'user') return j
            }
            return -1
          })()

          return messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              {/* INLINE EDITING FOR LAST USER MESSAGE */}
              {editingIndex === i && m.role === 'user' ? (
                <>
                  <div className="message-content edit-mode-box">
                    <div className="small muted" style={{ marginBottom: 4 }}>
                      ✏️ Edit mode – update your last question and click “Save &amp; Send”.
                    </div>
                    <textarea
                      value={editingText}
                      onChange={e => setEditingText(e.target.value)}
                      style={{
                        width: '100%',
                        minHeight: '80px',
                        borderRadius: '6px',
                        padding: '8px',
                        resize: 'vertical',
                      }}
                    />
                  </div>
                  <div className="message-toolbar" style={{ marginTop: 4, display: 'flex', gap: 8 }}>
                    <button className="mini" onClick={handleEditSave} disabled={sending}>
                      {sending ? 'Sending…' : 'Save & Send'}
                    </button>
                    <button className="mini" onClick={handleEditCancel} disabled={sending}>
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {/* Normal message bubble */}
                  <div
                    className="message-content"
                    dangerouslySetInnerHTML={{ __html: m.content }}
                  />
                  <div className="message-meta small muted">{m.time || ''}</div>

                  {/* Toolbar only on LAST user message, under the bubble */}
                  {i === lastUserIndex && m.role === 'user' ? (
                    <div className="message-toolbar" style={{ marginTop: 4, display: 'flex', gap: 8 }}>
                      <button
                        className="mini"
                        onClick={() => copyToClipboard(stripHtml(m.content))}
                        title="Copy"
                      >
                        📋
                      </button>
                      <button
                        className="mini"
                        onClick={() => handleEditClick(i, m)}
                        title="Edit this message in place"
                      >
                        ✏️
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </div>
          ))
        })()}
      </div>

      {/* Bottom input stays as a fresh prompt box – not used for edit-in-place */}
      <div className="input-area">
        <div className="input-group">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendQuery(input)
              }
            }}
            placeholder="Ask me anything about your files..."
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              ref={sendBtnRef}
              className="btn-primary"
              onClick={() => sendQuery(input)}
              disabled={sending}
            >
              {sending ? (
                <span className="loading inline">
                  <span className="spinner"></span> Sending
                </span>
              ) : (
                'Send'
              )}
            </button>
            {abortRef.current && abortRef.current.length > 0 ? (
              <button className="btn" onClick={cancelRequest}>
                Cancel
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
