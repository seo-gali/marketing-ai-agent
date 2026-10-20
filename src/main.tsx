import { createRoot } from 'react-dom/client'
import { useEffect, useState, useRef } from 'react'
import './style.css'
import { api, labels, type Video, type Health, type Analysis, type Activities, type BrowserStatus, type Job } from './api'

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
  const [browser, setBrowser] = useState<BrowserStatus>()
  const [approved, setApproved] = useState(false)
  const [posting, setPosting] = useState(false)
  const [browserBusy, setBrowserBusy] = useState(false)
  async function openBrowser() {
    setBrowserBusy(true); setError('')
    try {setBrowser(await api<BrowserStatus>('/browser/open', 'POST', {video_id:selected?.id}))}
    catch(e) {setError((e as Error).message)} finally {setBrowserBusy(false)}
  }
  async function checkBrowser() {
    try {setBrowser(await api<BrowserStatus>('/browser/status'))} catch(e) {setError((e as Error).message)}
  }
  async function post() {
    if(!selected) return
    setPosting(true); setError('')
    try {await api<Job>('/posting-jobs', 'POST', {video_id:selected.id, text:draft, approved, profile:'유튜브1'}); setActivities(await api<Activities>('/activities')); setApproved(false)}
    catch(e) {setError((e as Error).message)} finally {setPosting(false)}
  }
  useEffect(() => {
    const refresh = () => { api<Activities>('/activities').then(data => {setActivities(data); setHistoryError('')}).catch(e => setHistoryError(e.message)) }
    refresh(); const timer = setInterval(refresh, 2000); return () => clearInterval(timer)
  }, [])
  const selectedId = useRef('')
  useEffect(() => {
    if(selected && window.matchMedia('(max-width:1100px)').matches) document.getElementById('analysis')?.scrollIntoView({block:'start'})
  }, [selected?.id])
  async function select(video: Video) {
    selectedId.current = video.id; setSelected(video); setAnalysis(undefined); setDraft(''); setApproved(false); setError(''); setAnalyzing(true)
    try {
      const detail = await api<Video & {analysis: Analysis | null}>(`/videos/${video.id}`)
      const data = detail.analysis ?? await api<Analysis>(`/videos/${video.id}/analyze`, 'POST')
      if(selectedId.current === video.id) {setAnalysis(data); setDraft(data.comment)}
    } catch(e) { if(selectedId.current === video.id) setError((e as Error).message) }
    finally { if(selectedId.current === video.id) setAnalyzing(false) }
  }
  async function regenerate() {
    if(!selected) return
    const id = selected.id; setAnalyzing(true); setApproved(false); setError('')
    try { const data = await api<Analysis>(`/videos/${id}/analyze`, 'POST'); if(selectedId.current === id) {setAnalysis(data); setDraft(data.comment)} }
    catch(e) {setError((e as Error).message)} finally { if(selectedId.current === id) setAnalyzing(false) }
  }
  async function save() {
    if(!selected) return
    try { const data = await api<{comment:string}>(`/drafts/${selected.id}`, 'PUT', {text:draft}); setDraft(data.comment); setApproved(false); setError('') }
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
  const job = activities?.jobs.find(job => job.video_id === selected?.id)
  const pending = activities?.jobs.some(job => !['success','failed','uncertain'].includes(job.status))
  const count = [...draft.normalize('NFC').trim()].length
  const canPost = !!selected?.allowed && approved && count >= (health?.min_chars ?? 40) && count <= (health?.max_chars ?? 120) && draft.startsWith('[광고]') && draft.includes('운명원') && !/[#＃]|https?:|www\./i.test(draft) && !analyzing && !posting && !pending && !activities?.blocked_video_ids.includes(selected.id) && !!activities && activities.quota.used < activities.quota.max
  return <div className="shell">
    <aside className="sidebar"><a className="logo" href="#videos"><span className="logo-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="5"/><path d="m7 14 3-4 3 3 4-5"/></svg></span><span><span className="logo-name">Marketing AI</span><span className="logo-sub">AGENT WORKSPACE</span></span></a><div className="nav-section">WORKSPACE</div><nav className="nav" aria-label="주 메뉴"><a className="nav-item active" href="#videos"><span aria-hidden="true">▦</span>대시보드</a><a className="nav-item" href="#videos"><span aria-hidden="true">▷</span>영상 목록<span className="nav-count">{videos.length}</span></a><a className="nav-item" href="#analysis"><span aria-hidden="true">✧</span>AI 분석</a><a className="nav-item" href="#composer"><span aria-hidden="true">▤</span>댓글 검토</a><a className="nav-item" href="#activity"><span aria-hidden="true">◷</span>작업 이력</a></nav><div className="sidebar-spacer"/><div className="sidebar-status"><div className="sidebar-status-label"><span className={health?.ollama === 'ready' ? 'green-dot' : 'dot'}/>Ollama · {health?.ollama === 'ready' ? '연결됨' : health?.ollama ?? '연결 확인 중'}</div><p>{health?.model}</p><p>YouTube · {health?.youtube === 'configured' ? '키 설정됨' : health?.youtube ?? '확인 중'}</p></div><div className="profile"><div className="avatar">MA</div><div><div className="profile-name">Local Workspace</div><div className="profile-role">광고 콘텐츠 · 승인 후 게시</div></div></div></aside>
    <main className="main" id="videos"><div className="search-wrap"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="10.7" cy="10.7" r="6.6"/><path d="m16 16 4.3 4.3"/></svg><input aria-label="영상 검색" type="search" placeholder="영상 제목이나 채널을 검색하세요..." value={search} onChange={e => setSearch(e.target.value)}/></div><div className="page-heading"><h1>Video Library</h1><p>① 불러오기 · ② 영상 선택과 분석 · ③ 승인한 광고 댓글 게시</p></div><div className="topline"><span className="kicker">콘텐츠 관리</span><span className="stat">오늘 예약·게시 <strong>{activities?.quota.used ?? '–'}</strong> / {health?.daily_max ?? 10}</span></div>
      <div className="filter"><button className="chip" aria-pressed={!channel} onClick={() => setChannel('')}>전체</button>{Object.entries(health?.channels ?? {}).map(([id,name]) => <button className="chip" key={id} aria-pressed={channel === id} onClick={() => setChannel(id)}>{name}</button>)}</div>
      <div className="toolbar"><button className="btn primary" disabled={busy} onClick={load}>{busy ? '불러오는 중…' : '① 영상 불러오기'}</button><span className="badge neutral">5개 채널 · 실제 API</span></div>
      <form className="tools" onSubmit={e => {e.preventDefault(); void resolve()}}><input aria-label="YouTube 영상 링크" className="input" value={url} onChange={e => setUrl(e.target.value)} placeholder="YouTube 영상 URL"/><button className="btn" disabled={busy || analyzing || !url}>링크 확인</button></form>
      {error && !selected && <p role="alert" className="callout">{error}</p>}{warnings.map(w => <p className="callout" key={w}>{w}</p>)}
      <div className="list-label"><span className="kicker">Video List</span><span role="status" className="count">{busy ? 'YouTube API 조회 중' : `${visible.length}개 표시`}</span></div><div className="video-list">{visible.map(video => <button key={video.id} className="video-card" aria-pressed={selected?.id === video.id} disabled={analyzing} onClick={() => void select(video)}><img className="thumb" src={video.thumbnail} alt=""/><span className="video-meta"><h3>{video.title}</h3><p>{video.channel} · {new Date(video.published_at).toLocaleDateString('ko-KR')}</p><span className="badge inline">{video.allowed ? '게시 허용 범위' : '분석만 가능'}</span></span>{selected?.id === video.id && <span className="round-check" aria-label="선택됨">✓</span>}</button>)}{!busy && !visible.length && <div className="blank">{videos.length ? '검색 결과가 없습니다.' : '아직 불러온 영상이 없습니다.'}</div>}</div>
      <section className="activity" id="activity"><div className="activity-head"><h2>작업 이력</h2><span className="badge neutral">SQLite · {activities?.quota.day}</span></div>{historyError && <p role="alert">{historyError}</p>}{!activities?.jobs.length && <p className="blank">아직 게시 작업이 없습니다.</p>}{activities?.jobs.map(job => <article className="evidence-row" key={job.id}><strong>{job.title ?? job.video_id}</strong><p>{new Date(job.created_at).toLocaleString('ko-KR')} · {job.profile} · {labels[job.status] ?? job.status}</p><p>{job.text}</p>{job.error && <p className="callout">{job.error}</p>}{job.comment_url && <a href={job.comment_url} target="_blank" rel="noreferrer">댓글 보기 ↗</a>}</article>)}<details><summary>단계별 활동 기록 ({activities?.logs.length ?? 0})</summary>{activities?.logs.map(log => <p key={log.id}>{new Date(log.created_at).toLocaleTimeString('ko-KR')} · {log.video_id} · {labels[log.stage] ?? log.stage} · {log.detail}</p>)}</details></section>
    </main><aside className="detail" id="analysis" aria-label="AI 분석 및 댓글 상세"><div className="detail-top"><div className="detail-toprow"><span className="detail-symbol">✧</span><span className="detail-label">AI Content Review</span><span className="detail-id">#LOCAL</span></div><h2 className="detail-title">② 영상 선택 · 분석</h2><p className="detail-description">{selected?.title ?? '왼쪽에서 영상을 선택하세요.'}</p></div>{!selected && <div className="blank"><strong>영상 선택을 기다리고 있습니다.</strong>실제 제목과 출처를 바탕으로 광고 초안을 만듭니다.</div>}{selected && <div className="detail-scroll">{error && <p role="alert" className="callout">{error}</p>}<div className="selected-header"><div><div className="name">{selected.title}</div><p>{selected.channel} · {new Date(selected.published_at).toLocaleDateString('ko-KR')}</p></div></div><a className="btn small source-link" href={`https://www.youtube.com/watch?v=${selected.id}`} target="_blank" rel="noreferrer">영상 보기 ↗</a><details><summary>영상 설명</summary><p className="description">{selected.description}</p></details>
      {analyzing && <p role="status">Ollama 분석 중… 실제 자료를 읽고 있습니다.</p>}
      {analysis && <><div className="insight"><p className="lead">AI INSIGHT</p><p className="statement">{analysis.concern}</p></div><h3>분석 근거 · 출처</h3>{analysis.evidence.map((e,i) => <div className="evidence-row" key={i}><a href={e.url} target="_blank" rel="noreferrer">{e.label} ↗</a><p>{e.quote}</p></div>)}{analysis.warnings.map(w => <p className="callout" key={w}>{w}</p>)}<p className="fineprint">{analysis.model} · {new Date(analysis.created_at).toLocaleString('ko-KR')}</p></>}
      <button className="btn" disabled={analyzing} onClick={regenerate}>{analysis ? '초안 다시 생성' : '영상 분석'}</button>
      <div className="divider"/><section id="composer"><div className="panel-no">STEP 03 / COMMENT</div><h3 className="panel-title">③ 광고 댓글 검토</h3><label className="editor-label" htmlFor="draft">댓글 초안 · 40~120자</label><textarea id="draft" value={draft} onChange={e => {setDraft(e.target.value);setApproved(false)}} disabled={analyzing || pending} rows={5}/><p className="fineprint">{count}자 · [광고]와 운명원 필수 · 링크·해시태그·허위 이용 후기 금지</p><button className="btn small" disabled={analyzing || !draft || pending} onClick={save}>수정 저장</button>
        <div className="divider"/><h3>Chrome · 유튜브1</h3><div className="actions"><button className="btn" disabled={browserBusy || pending} onClick={openBrowser}>{browserBusy ? 'Chrome 여는 중…' : '전용 Chrome 열기 · 로그인'}</button><button className="btn" disabled={browserBusy || pending} onClick={checkBrowser}>로그인 상태 확인</button></div>{browser && <p role="status" className={browser.signed_in ? 'insight' : 'callout'}>{browser.signed_in ? '전용 프로필 로그인 확인됨' : browser.needs_action}</p>}
        <label className="approval"><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} disabled={pending}/>현재 본문을 확인했으며 광고 댓글 게시를 승인합니다.</label><p className="fineprint">전용 Chrome에서 한 글자씩 입력 후 실제로 게시합니다. 로그인·인증은 직접 진행하세요.</p>
        {!selected.allowed && <p className="callout">허용 채널·등록 테스트 영상이 아니므로 게시할 수 없습니다.</p>}{activities?.blocked_video_ids.includes(selected.id) && <p className="callout">게시 이력 또는 확인 불가 작업이 있어 재게시를 차단합니다.</p>}
        <button className="btn primary full" disabled={!canPost} onClick={post}>③ 댓글 달기</button>{job && <div role="status" className="posting-demo"><strong>{labels[job.status]}</strong>{job.error && <p className="callout">{job.error}</p>}{job.screenshot && <a href={`/api/screenshots/${job.screenshot}`} target="_blank" rel="noreferrer">화면 캡처 ↗</a>}{job.comment_url && <a href={job.comment_url} target="_blank" rel="noreferrer">댓글 보기 ↗</a>}</div>}
      </section>
    </div>}</aside>
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
