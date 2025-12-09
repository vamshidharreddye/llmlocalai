import React, { useState } from 'react'

export default function Sources({ apiBase, selectedModel, sources, addMessage }) {
  const [previewUrl, setPreviewUrl] = useState('')
  const [confirmPath, setConfirmPath] = useState('')
  const [filter, setFilter] = useState('')

  function escapeHtml(text) {
    if (!text) return ''
    return text.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;"}[c]))
  }

  async function doOpen(path) {
    try {
      const r = await fetch(`${apiBase}/open_file`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path }) })
      // not checking response deeply; provide feedback
      addMessage('assistant', `<div class='success'>Opened: ${escapeHtml(path)}</div>`)
    } catch (e) {
      addMessage('assistant', `<div class='error'>Open failed: ${escapeHtml(e.message)}</div>`)
    }
    setConfirmPath('')
  }

  async function analyze(path) {
    try {
      addMessage('assistant', `<div class='muted'>Analyzing ${escapeHtml(path)}…</div>`)
      const r = await fetch(`${apiBase}/analyze_file`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, model: selectedModel }) })
      const d = await r.json()
      if (d.summary) addMessage('assistant', `<div>${escapeHtml(d.summary)}</div>`)
      else addMessage('assistant', `<div class='error'>Analysis failed</div>`)
    } catch (e) {
      addMessage('assistant', `<div class='error'>Analysis error: ${escapeHtml(e.message)}</div>`)
    }
  }

  return (
    <div className="sources-panel">
      <div className="sources-header">📄 Sources</div>
      <div style={{padding:'8px 12px'}}>
        <input placeholder="Filter sources..." value={filter} onChange={e => setFilter(e.target.value)} style={{width:'100%',padding:8,borderRadius:8,border:'1px solid rgba(255,255,255,0.04)',background:'transparent',color:'#e5e7eb'}} />
      </div>
      <div className="sources-list">
        {(!sources || sources.length === 0) && <div className="status">No results yet</div>}

        {sources && sources.filter(s => {
          if (!filter) return true
          const q = filter.toLowerCase()
          return (s.name||'').toLowerCase().includes(q) || (s.path||'').toLowerCase().includes(q) || (s.reason_detail||'').toLowerCase().includes(q)
        }).map((s, idx) => (
          <div key={idx} className="source-item">
            <div className="source-path">{idx+1}. {s.name || (s.path||'').split(/[\\\/]/).pop()}</div>
            <div className="source-preview" title={s.path}>{s.path}</div>
            <div className="source-meta">
              <div>Size: <strong>{((s.size_bytes||0)/1024).toFixed(1)} KB</strong></div>
              <div>Matched: <strong>{s.reason_detail || s.reason || ''}</strong></div>
            </div>
            {s.reason_detail && <div className="source-snippet"><small>{s.reason_detail}</small></div>}

            <div className="source-actions">
              <button className="btn" onClick={() => analyze(s.path || s.file_path)}>Analyze</button>
              <button className="btn" onClick={() => setPreviewUrl(`${apiBase}/file_stream?path=${encodeURIComponent(s.path || s.file_path)}`)}>Preview</button>
              <button className="btn danger" onClick={() => setConfirmPath(s.path || s.file_path)}>Open</button>
            </div>
          </div>
        ))}
      </div>

      {previewUrl ? (
        <div className="modal-backdrop" style={{display:'flex'}}>
          <div className="modal" style={{maxWidth:'900px',width:'96%'}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <div style={{fontWeight:700}}>Preview</div>
              <div><button className="btn" onClick={() => setPreviewUrl('')}>Close</button></div>
            </div>
            <div style={{marginTop:12,height:'70vh'}}>
              <iframe src={previewUrl} style={{width:'100%', height:'100%',border:'none'}} title="preview" />
            </div>
          </div>
        </div>
      ) : null}

      {confirmPath ? (
        <div className="confirm">
          <div>Open file in OS?</div>
          <div className="small muted">{confirmPath}</div>
          <div style={{marginTop:8}}>
            <button className="btn" onClick={() => setConfirmPath('')}>Cancel</button>
            <button className="btn-primary" onClick={() => doOpen(confirmPath)}>Open</button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
