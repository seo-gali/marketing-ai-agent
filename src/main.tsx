import { createRoot } from 'react-dom/client'
import { useEffect, useState, useRef } from 'react'
import './style.css'
import { api, labels, type Video, type Health, type Analysis, type Activities } from './api'

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
  const [analysis, setAnalysis] = useState<Analysis>()
  const [draft, setDraft] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [activities, setActivities] = useState<Activities>()
  const [historyError, setHistoryError] = useState('')
  useEffect(() => {
    const refresh = () => { api<Activities>('/activities').then(data => {setActivities(data); setHistoryError('')}).catch(e => setHistoryError(e.message)) }
    refresh(); const timer = setInterval(refresh, 2000); return () => clearInterval(timer)
  }, [])
  const selectedId = useRef('')
  async function select(video: Video) {
    selectedId.current = video.id; setSelected(video); setAnalysis(undefined); setDraft(''); setError(''); setAnalyzing(true)
    try {
      const detail = await api<Video & {analysis: Analysis | null}>(`/videos/${video.id}`)
      const data = detail.analysis ?? await api<Analysis>(`/videos/${video.id}/analyze`, 'POST')
      if(selectedId.current === video.id) {setAnalysis(data); setDraft(data.comment)}
    } catch(e) { if(selectedId.current === video.id) setError((e as Error).message) }
    finally { if(selectedId.current === video.id) setAnalyzing(false) }
  }
  async function regenerate() {
    if(!selected) return
    const id = selected.id; setAnalyzing(true); setError('')
    try { const data = await api<Analysis>(`/videos/${id}/analyze`, 'POST'); if(selectedId.current === id) {setAnalysis(data); setDraft(data.comment)} }
    catch(e) {setError((e as Error).message)} finally { if(selectedId.current === id) setAnalyzing(false) }
  }
  async function save() {
    if(!selected) return
    try { const data = await api<{comment:string}>(`/drafts/${selected.id}`, 'PUT', {text:draft}); setDraft(data.comment); setError('') }
    catch(e) {setError((e as Error).message)}
  }
  useEffect(() => { api<Health>('/health').then(setHealth).catch(e => setError(e.message)) }, [])
  async function load() {
    setBusy(true); setError(''); setWarnings([])
    try { const data = await api<{videos: Video[]; warnings: string[]}>('/videos'); setVideos(data.videos); setWarnings(data.warnings) }
    catch(e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  async function resolve() {
    setBusy(true); setError('')
    try { const video = await api<Video>('/videos/resolve', 'POST', {url}); setVideos(v => [video, ...v.filter(x => x.id !== video.id)]); void select(video) }
    catch(e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const visible = videos.filter(v => (!channel || v.channel_id === channel) && `${v.title} ${v.channel}`.toLowerCase().includes(search.toLowerCase()))
  return <div className="shell">
    <aside className="sidebar"><a className="logo" href="#videos">◈ Marketing AI</a><nav><a href="#videos">대시보드</a><a href="#videos">영상 목록</a><a href="#analysis">AI 분석</a><a href="#composer">댓글 검토</a><a href="#activity">작업 이력</a></nav><div className="sidebar-status">Ollama · {health?.ollama ?? '연결 확인 중'}<p>{health?.model}</p><p>YouTube · {health?.youtube}</p></div></aside>
    <main className="main" id="videos"><input aria-label="영상 검색" className="input" type="search" placeholder="영상 제목이나 채널을 검색하세요..." value={search} onChange={e => setSearch(e.target.value)}/><div className="page-heading"><h1>Video Library</h1><p>실제 영상 데이터를 확인하고 광고 댓글을 검토하세요.</p></div>
      <div className="filter"><button className="chip" aria-pressed={!channel} onClick={() => setChannel('')}>전체</button>{Object.entries(health?.channels ?? {}).map(([id,name]) => <button className="chip" key={id} aria-pressed={channel === id} onClick={() => setChannel(id)}>{name}</button>)}</div>
      <div className="toolbar"><button className="btn primary" disabled={busy} onClick={load}>{busy ? '불러오는 중…' : '① 영상 불러오기'}</button><span>{videos.length}개 영상 · 오늘 {activities?.quota.used ?? '–'}/{health?.daily_max ?? 10}건 예약·게시</span></div>
      <form className="tools" onSubmit={e => {e.preventDefault(); void resolve()}}><input aria-label="YouTube 영상 링크" className="input" value={url} onChange={e => setUrl(e.target.value)} placeholder="YouTube 영상 URL"/><button className="btn" disabled={busy || !url}>링크 확인</button></form>
      {error && <p role="alert" className="callout">{error}</p>}{warnings.map(w => <p className="callout" key={w}>{w}</p>)}
      <div role="status" className="count">{busy ? 'YouTube API 조회 중' : `${visible.length}개 표시`}</div><div className="video-list">{visible.map(video => <button key={video.id} className="video-card" aria-pressed={selected?.id === video.id} disabled={analyzing} onClick={() => void select(video)}><img className="thumb" src={video.thumbnail} alt=""/><span className="video-meta"><h3>{video.title}</h3><p>{video.channel} · {new Date(video.published_at).toLocaleDateString('ko-KR')}</p><span className="badge">{video.allowed ? '게시 허용 범위' : '분석만 가능'}</span></span></button>)}{!busy && !visible.length && <div className="blank">{videos.length ? '검색 결과가 없습니다.' : '아직 불러온 영상이 없습니다.'}</div>}</div>
      <section className="activity" id="activity"><div className="activity-head"><h2>작업 이력</h2><span className="badge neutral">SQLite · {activities?.quota.day}</span></div>{historyError && <p role="alert">{historyError}</p>}{!activities?.jobs.length && <p className="blank">아직 게시 작업이 없습니다.</p>}{activities?.jobs.map(job => <article className="evidence-row" key={job.id}><strong>{job.title ?? job.video_id}</strong><p>{new Date(job.created_at).toLocaleString('ko-KR')} · {job.profile} · {labels[job.status] ?? job.status}</p><p>{job.text}</p>{job.error && <p className="callout">{job.error}</p>}{job.comment_url && <a href={job.comment_url} target="_blank" rel="noreferrer">댓글 보기 ↗</a>}</article>)}<details><summary>단계별 활동 기록 ({activities?.logs.length ?? 0})</summary>{activities?.logs.map(log => <p key={log.id}>{new Date(log.created_at).toLocaleTimeString('ko-KR')} · {log.video_id} · {labels[log.stage] ?? log.stage} · {log.detail}</p>)}</details></section>
    </main><aside className="detail" id="analysis"><div className="detail-top"><span className="badge">AI Content Review</span><h2>② 영상 선택 · 분석</h2><p>{selected?.title ?? '왼쪽에서 영상을 선택하세요.'}</p></div>{selected && <div className="detail-scroll"><p>{selected.channel} · {new Date(selected.published_at).toLocaleDateString('ko-KR')}</p><a className="btn" href={`https://www.youtube.com/watch?v=${selected.id}`} target="_blank" rel="noreferrer">영상 보기 ↗</a><details><summary>영상 설명</summary><p className="description">{selected.description}</p></details>
      {analyzing && <p role="status">Ollama 분석 중… 실제 자료를 읽고 있습니다.</p>}
      {analysis && <><div className="insight"><p className="lead">AI INSIGHT</p><p className="statement">{analysis.concern}</p></div><h3>분석 근거 · 출처</h3>{analysis.evidence.map((e,i) => <div className="evidence-row" key={i}><a href={e.url} target="_blank" rel="noreferrer">{e.label} ↗</a><p>{e.quote}</p></div>)}{analysis.warnings.map(w => <p className="callout" key={w}>{w}</p>)}<p className="fineprint">{analysis.model} · {new Date(analysis.created_at).toLocaleString('ko-KR')}</p></>}
      <button className="btn" disabled={analyzing} onClick={regenerate}>{analysis ? '초안 다시 생성' : '영상 분석'}</button>
      <div className="divider"/><section id="composer"><h3>③ 광고 댓글 검토</h3><label htmlFor="draft">댓글 초안 · 40~120자</label><textarea id="draft" value={draft} onChange={e => setDraft(e.target.value)} disabled={analyzing} rows={5}/><p>{[...draft].length}자 · [광고]와 운명원 필수</p><button className="btn" disabled={analyzing || !draft} onClick={save}>수정 저장</button></section>
    </div>}</aside>
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
