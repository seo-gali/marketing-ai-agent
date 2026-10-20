import { createRoot } from 'react-dom/client'
import { useEffect, useState } from 'react'
import './style.css'

function App() {
  const [status, setStatus] = useState('연결 확인 중')
  useEffect(() => { fetch('/api/health').then(r => r.json()).then(h => setStatus(`Ollama: ${h.ollama} · YouTube: ${h.youtube}`)).catch(() => setStatus('백엔드 연결 실패')) }, [])
  return <main><h1>Marketing AI</h1><p role="status">{status}</p><p>로컬 실행 환경 · 영상 기능 구현 중</p></main>
}

createRoot(document.getElementById('root')!).render(<App />)
