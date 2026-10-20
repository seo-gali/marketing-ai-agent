import { createRoot } from 'react-dom/client'
import { useEffect, useState } from 'react'
import './style.css'
import { api, type Video, type Health } from './api'

function App() {
  const [health, setHealth] = useState<Health>()
  const [videos, setVideos] = useState<Video[]>([])
  const [selected, setSelected] = useState<Video>()
  const [search, setSearch] = useState('')
  const [channel, setChannel] = useState('')
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [warnings, setWarnings] = useState<string[]>([])
  useEffect(() => { api<Health>('/health').then(setHealth).catch(e => setError(e.message)) }, [])
  async function load() {
    setBusy(true); setError(''); setWarnings([])
    try { const data = await api<{videos: Video[]; warnings: string[]}>('/videos'); setVideos(data.videos); setWarnings(data.warnings) }
    catch(e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  async function resolve() {
    setBusy(true); setError('')
    try { const video = await api<Video>('/videos/resolve', 'POST', {url}); setVideos(v => [video, ...v.filter(x => x.id !== video.id)]); setSelected(video) }
    catch(e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const visible = videos.filter(v => (!channel || v.channel_id === channel) && `${v.title} ${v.channel}`.toLowerCase().includes(search.toLowerCase()))
  return <div className="shell">
    <aside className="sidebar"><a className="logo" href="#videos">◈ Marketing AI</a><nav><a href="#videos">대시보드</a><a href="#videos">영상 목록</a><a href="#analysis">AI 분석</a><a href="#composer">댓글 검토</a><a href="#activity">작업 이력</a></nav><div className="sidebar-status">Ollama · {health?.ollama ?? '연결 확인 중'}<p>{health?.model}</p><p>YouTube · {health?.youtube}</p></div></aside>
    <main className="main" id="videos"><input aria-label="영상 검색" className="input" type="search" placeholder="영상 제목이나 채널을 검색하세요..." value={search} onChange={e => setSearch(e.target.value)}/><div className="page-heading"><h1>Video Library</h1><p>실제 영상 데이터를 확인하고 광고 댓글을 검토하세요.</p></div>
      <div className="filter"><button className="chip" aria-pressed={!channel} onClick={() => setChannel('')}>전체</button>{Object.entries(health?.channels ?? {}).map(([id,name]) => <button className="chip" key={id} aria-pressed={channel === id} onClick={() => setChannel(id)}>{name}</button>)}</div>
      <div className="toolbar"><button className="btn primary" disabled={busy} onClick={load}>{busy ? '불러오는 중…' : '① 영상 불러오기'}</button><span>{videos.length}개 영상 · 5개 채널</span></div>
      <form className="tools" onSubmit={e => {e.preventDefault(); void resolve()}}><input aria-label="YouTube 영상 링크" className="input" value={url} onChange={e => setUrl(e.target.value)} placeholder="YouTube 영상 URL"/><button className="btn" disabled={busy || !url}>링크 확인</button></form>
      {error && <p role="alert" className="callout">{error}</p>}{warnings.map(w => <p className="callout" key={w}>{w}</p>)}
      <div role="status" className="count">{busy ? 'YouTube API 조회 중' : `${visible.length}개 표시`}</div><div className="video-list">{visible.map(video => <button key={video.id} className="video-card" aria-pressed={selected?.id === video.id} onClick={() => setSelected(video)}><img className="thumb" src={video.thumbnail} alt=""/><span className="video-meta"><h3>{video.title}</h3><p>{video.channel} · {new Date(video.published_at).toLocaleDateString('ko-KR')}</p><span className="badge">{video.allowed ? '게시 허용 범위' : '분석만 가능'}</span></span></button>)}{!busy && !visible.length && <div className="blank">{videos.length ? '검색 결과가 없습니다.' : '아직 불러온 영상이 없습니다.'}</div>}</div>
    </main><aside className="detail" id="analysis"><div className="detail-top"><span className="badge">AI Content Review</span><h2>② 영상 선택 · 분석</h2><p>{selected?.title ?? '왼쪽에서 영상을 선택하세요.'}</p></div>{selected && <div className="detail-scroll"><p>{selected.channel} · {new Date(selected.published_at).toLocaleDateString('ko-KR')}</p><a className="btn" href={`https://www.youtube.com/watch?v=${selected.id}`} target="_blank" rel="noreferrer">영상 보기 ↗</a><p className="description">{selected.description}</p></div>}</aside>
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
