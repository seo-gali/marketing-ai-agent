import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { api, labels, type Video, type Health, type Analysis, type Activities, type BrowserStatus, type Job } from './api'
import Icon from './Icon'

const routes: Record<string,string> = {'/':'영상 탐색','/activities':'작업 이력','/settings':'환경 상태'}
const terminal = ['success','failed','uncertain']
const date = (value:string) => new Date(value).toLocaleString('ko-KR')
function readFilters() {
  try {
    const value=JSON.parse(localStorage.getItem('marketing-ai:filters')??'{}')
    return {search:typeof value.search==='string'?value.search.slice(0,100):'',channel:typeof value.channel==='string'?value.channel:'',active:value.active===true}
  } catch {return {search:'',channel:'',active:false}}
}
function validate(text:string,min=40,max=120) {
  text=text.normalize('NFC').trim()
  if([...text].length<min||[...text].length>max) return `댓글을 ${min}~${max}자로 작성하세요.`
  if(!text.startsWith('[광고]')||!text.includes('운명원')) return '[광고]로 시작하고 운명원을 포함하세요.'
  if(/https?:|www\.|(?:[\p{L}\p{N}_-]+\.)+[\p{L}]{2,63}|(?:\d{1,3}\.){3}\d{1,3}|#|[\p{Cc}\p{Cf}]/iu.test(text.normalize('NFKC'))) return '링크·해시태그·보이지 않는 제어 문자를 제거하세요.'
  return ''
}

export default function App() {
  const [path,setPath]=useState(location.pathname)
  const [menuOpen,setMenuOpen]=useState(false)
  const [health,setHealth]=useState<Health>()
  const [videos,setVideos]=useState<Video[]>([])
  const [selected,setSelected]=useState<Video>()
  const [filters]=useState(readFilters)
  const [search,setSearch]=useState(filters.search)
  const [channel,setChannel]=useState(filters.channel)
  const [searchActive,setSearchActive]=useState(filters.active)
  const [url,setUrl]=useState('')
  const [loading,setLoading]=useState(false)
  const [analyzing,setAnalyzing]=useState(false)
  const [saving,setSaving]=useState(false)
  const [analysis,setAnalysis]=useState<Analysis>()
  const [draft,setDraft]=useState('')
  const [draftError,setDraftError]=useState('')
  const [edited,setEdited]=useState(false)
  const [localState,setLocalState]=useState('')
  const [approved,setApproved]=useState(false)
  const [activities,setActivities]=useState<Activities>()
  const [history,setHistory]=useState<Activities>()
  const [historyPage,setHistoryPage]=useState(0)
  const [historyError,setHistoryError]=useState('')
  const [browser,setBrowser]=useState<BrowserStatus>()
  const [browserBusy,setBrowserBusy]=useState(false)
  const [posting,setPosting]=useState(false)
  const [storedJob,setStoredJob]=useState<Job|null>(null)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [undo,setUndo]=useState<ReturnType<typeof readFilters>|null>(null)
  const selectedId=useRef('')
  const historyCache=useRef(new Map<number,Activities>())
  const job=activities?.jobs.find(item=>item.video_id===selected?.id)??storedJob
  const pending=activities?.jobs.some(item=>!terminal.includes(item.status))??false
  const blocked=!!job&&job.status!=='failed'
  const invalid=validate(draft,health?.min_chars,health?.max_chars)
  const visible=videos.filter(video=>(!channel||video.channel_id===channel)&&(!searchActive||(!!search.trim()&&`${video.title} ${video.channel}`.toLowerCase().includes(search.trim().toLowerCase()))))
  const canPost=!!selected?.allowed&&!!analysis&&approved&&!invalid&&!analyzing&&!posting&&!pending&&!blocked&&!!activities&&activities.quota.used<activities.quota.max
  const historyPageCount=history?.total_pages??1
  const firstHistoryPage=Math.max(0,Math.min(historyPage-2,historyPageCount-5))
  const historyPages=Array.from({length:Math.min(5,historyPageCount)},(_,index)=>firstHistoryPage+index)

  function navigate(destination:string) {
    window.history.pushState({},'',destination);setPath(destination);setMenuOpen(false)
    requestAnimationFrame(()=>document.getElementById('main-content')?.focus())
  }
  function follow(event:MouseEvent<HTMLAnchorElement>,destination:string) {
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey) return
    event.preventDefault();navigate(destination)
  }
  function fail(problem:unknown,target='global-message') {
    setError(problem instanceof Error?problem.message:String(problem));setNotice('')
    requestAnimationFrame(()=>{const element=document.getElementById(target);element?.focus();element?.scrollIntoView({block:'nearest'})})
  }
  function success(message:string) {setNotice(message);setError('');setUndo(null)}
  async function refreshHealth() {try {setHealth(await api<Health>('/health'))} catch(problem) {fail(problem)}}
  useEffect(()=>{
    const back=()=>{setPath(location.pathname);setMenuOpen(false)}
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'&&menuOpen){setMenuOpen(false);document.getElementById('menu-toggle')?.focus()}}
    window.addEventListener('popstate',back);window.addEventListener('keydown',escape)
    return ()=>{window.removeEventListener('popstate',back);window.removeEventListener('keydown',escape)}
  },[menuOpen])
  useEffect(()=>{document.title=`${routes[path]??'페이지를 찾을 수 없습니다'} · Marketing AI`},[path])
  useEffect(()=>{void refreshHealth()},[])
  useEffect(()=>{
    try {
      for(let index=localStorage.length-1;index>=0;index--) {
        const key=localStorage.key(index)
        if(!key?.startsWith('marketing-ai:draft:')) continue
        try {const saved=JSON.parse(localStorage.getItem(key)??'null');if(!saved||saved.expiresAt<=Date.now()) localStorage.removeItem(key)} catch {localStorage.removeItem(key)}
      }
    } catch { /* 브라우저 저장 제한 */ }
  },[])
  useEffect(()=>{
    const refresh=()=>{api<Activities>('/activities').then(data=>{setActivities(data);setHistoryError('')}).catch(()=>setHistoryError('이력을 불러오지 못했습니다. 서버 연결을 확인하세요.'))}
    refresh();const timer=setInterval(refresh,3000);return ()=>clearInterval(timer)
  },[])
  useEffect(()=>{
    if(path!=='/activities') return
    let active=true
    const cached=historyCache.current.get(historyPage)
    if(cached) setHistory(cached)
    api<Activities>(`/activities?offset=${historyPage*30}&limit=30`).then(data=>{
      if(active) setHistory(data)
      if(data.has_more) api<Activities>(`/activities?offset=${(historyPage+1)*30}&limit=30`).then(next=>{historyCache.current.clear();historyCache.current.set(historyPage+1,next)}).catch(()=>{})
    }).catch(fail)
    return ()=>{active=false}
  },[path,historyPage,activities?.logs[0]?.id])
  useEffect(()=>{try {localStorage.setItem('marketing-ai:filters',JSON.stringify({search,channel,active:searchActive}))} catch { /* 브라우저 저장 제한 */ }},[search,channel,searchActive])
  useEffect(()=>{
    if(!selected||!edited) return
    try {localStorage.setItem(`marketing-ai:draft:${selected.id}`,JSON.stringify({text:draft,expiresAt:Date.now()+7*86400000}));setLocalState('이 브라우저에 임시 저장됨 · 7일 보관')}
    catch {setLocalState('임시 저장이 제한됐습니다. 초안 저장 버튼을 사용하세요.')}
  },[selected?.id,draft,edited])
  useEffect(()=>{
    if(!selected) return
    const heading=document.getElementById('analysis-title');heading?.focus({preventScroll:true})
    if(window.matchMedia('(max-width:1150px)').matches) heading?.scrollIntoView({block:'start'})
  },[selected?.id])

  function resetFilters() {const previous={search,channel,active:searchActive};setSearch('');setChannel('');setSearchActive(false);success('검색과 필터를 초기화했습니다.');setUndo(previous)}
  async function load() {
    setLoading(true);setError('')
    try {const data=await api<{videos:Video[];warnings:string[]}>('/videos');setVideos(data.videos);success(data.warnings.length?data.warnings.join(' / '):`${data.videos.length}개 영상을 불러왔습니다.`)}
    catch(problem) {fail(problem)} finally {setLoading(false)}
  }
  async function select(video:Video) {
    selectedId.current=video.id;setSelected(video);setAnalysis(undefined);setDraft('');setEdited(false);setDraftError('');setLocalState('');setApproved(false);setStoredJob(null);setAnalyzing(true);setError('')
    try {
      const detail=await api<Video&{analysis:Analysis|null;posting_job:Job|null}>(`/videos/${video.id}`)
      if(selectedId.current===video.id) setStoredJob(detail.posting_job)
      const data=detail.analysis??await api<Analysis>(`/videos/${video.id}/analyze`,'POST')
      if(selectedId.current!==video.id) return
      let text=data.comment
      try {
        const cached=JSON.parse(localStorage.getItem(`marketing-ai:draft:${video.id}`)??'null')
        if(cached&&cached.expiresAt>Date.now()&&typeof cached.text==='string'&&cached.text.length<=2000) {text=cached.text;setLocalState('이 브라우저의 임시 초안을 불러왔습니다.')}
        else if(cached) localStorage.removeItem(`marketing-ai:draft:${video.id}`)
      } catch { /* 손상된 임시 초안 무시 */ }
      setAnalysis(data);setDraft(text)
    } catch(problem) {if(selectedId.current===video.id) fail(problem)} finally {if(selectedId.current===video.id) setAnalyzing(false)}
  }
  async function resolve() {
    if(!url.trim()) {fail(new Error('영상 URL을 입력하세요.'),'video-url');return}
    setLoading(true);setError('')
    try {const video=await api<Video>('/videos/resolve','POST',{url:url.trim()});setVideos(items=>[video,...items.filter(item=>item.id!==video.id)]);setChannel('');setSearchActive(false);setUrl('');success('영상 링크를 확인했습니다.');void select(video)}
    catch(problem) {fail(problem,'video-url')} finally {setLoading(false)}
  }
  async function regenerate() {
    if(!selected) return
    const id=selected.id;setAnalyzing(true);setApproved(false);setError('')
    try {const data=await api<Analysis>(`/videos/${id}/analyze`,'POST');if(selectedId.current===id) {setAnalysis(data);setDraft(data.comment);setEdited(true);setDraftError('');success('새 초안을 생성했습니다.')}}
    catch(problem) {fail(problem)} finally {if(selectedId.current===id) setAnalyzing(false)}
  }
  async function save() {
    if(!selected) return
    if(invalid) {setDraftError(invalid);fail(new Error(invalid),'draft');return}
    setSaving(true)
    try {const data=await api<{comment:string}>(`/drafts/${selected.id}`,'PUT',{text:draft});setDraft(data.comment);setApproved(false);setDraftError('');success('초안을 저장했습니다.')}
    catch(problem) {fail(problem,'draft')} finally {setSaving(false)}
  }
  async function openBrowser() {
    setBrowserBusy(true);setError('')
    try {setBrowser(await api<BrowserStatus>('/browser/open','POST',{video_id:selected?.id}));success('지정 프로필을 열었습니다.')}
    catch(problem) {fail(problem)} finally {setBrowserBusy(false)}
  }
  async function checkBrowser() {try {setBrowser(await api<BrowserStatus>('/browser/status'))} catch(problem) {fail(problem)}}
  async function post() {
    if(!selected||!canPost) return
    setPosting(true);setError('')
    try {setStoredJob(await api<Job>('/posting-jobs','POST',{video_id:selected.id,text:draft,approved,profile:'유튜브1'}));setActivities(await api<Activities>('/activities'));setApproved(false);success('게시 작업을 시작했습니다. 완료 여부는 서버 상태에서 확인하세요.')}
    catch(problem) {fail(problem)} finally {setPosting(false)}
  }
  function clearLocal() {
    try {for(let index=localStorage.length-1;index>=0;index--) {const key=localStorage.key(index);if(key?.startsWith('marketing-ai:')) localStorage.removeItem(key)}setLocalState('임시 저장을 삭제했습니다.');success('이 브라우저의 초안과 검색 상태를 삭제했습니다.')}
    catch {fail(new Error('브라우저 저장 공간을 삭제하지 못했습니다.'))}
  }

  return <div className={`app-shell ${menuOpen?'mobile-open':''}`}>
    <a className="skip-link" href="#main-content">본문으로 이동</a>
    <aside className="sidebar"><div className="mobile-heading"><a className="brand" href="/" onClick={event=>follow(event,'/')} aria-label="Marketing AI 홈"><span className="brand-mark"><Icon name="sparkle" size={20}/></span><span><span className="brand-name">Marketing <span>AI</span></span><span className="brand-sub">LOCAL WORKSPACE</span></span></a><button id="menu-toggle" className="mobile-toggle" aria-expanded={menuOpen} aria-controls="main-navigation" aria-label={menuOpen?'메뉴 닫기':'메뉴 열기'} onClick={()=>setMenuOpen(!menuOpen)}><Icon name="grid"/></button></div><div className="nav-label">WORKSPACE</div><nav id="main-navigation" aria-label="주 메뉴">{[['/','grid','영상 탐색'],['/activities','clock','작업 이력'],['/settings','settings','환경 상태']].map(([destination,icon,label])=><a className={`nav-item ${path===destination?'active':''}`} href={destination} key={destination} onClick={event=>follow(event,destination)} aria-current={path===destination?'page':undefined}><Icon name={icon}/>{label}</a>)}</nav><div className="sidebar-bottom"><div className="connection-box"><div className="connection-head"><span className={`status-dot ${health?.ollama==='ready'?'on':''}`}/>Ollama {health?.ollama==='ready'?'연결됨':'확인 필요'}</div><p>{health?.model??'연결 확인 중'}</p><div className="connection-head"><span className={`status-dot ${health?.youtube==='configured'?'on':''}`}/>YouTube API {health?.youtube==='configured'?'키 설정됨':'확인 필요'}</div></div><div className="user-chip"><span className="avatar"><Icon name="user"/></span><span><strong>Local Operator</strong><span>광고 콘텐츠 · 승인 후 게시</span></span></div></div></aside>
    {path==='/'&&<><main id="main-content" className="main-panel" tabIndex={-1} aria-labelledby="page-title"><header className="heading"><div className="eyebrow">CONTENT DISCOVERY</div><h1 id="page-title">영상 탐색 <span key={videos.length} className="soft-count">{videos.length}</span></h1><p>영상을 불러오고, 분석할 대상을 선택하세요.</p></header><form className="search-form" onSubmit={event=>{event.preventDefault();setSearchActive(true);if(!search.trim()) fail(new Error('검색어를 입력하세요.'),'video-search')}}><label className="field-label" htmlFor="video-search">영상 검색</label><div className="top-search"><Icon name="search"/><input id="video-search" type="search" maxLength={100} value={search} onChange={event=>{setSearch(event.target.value);setSearchActive(true)}}/><button className="search-submit" aria-label="검색 실행"><Icon name="chevron"/></button></div></form>{searchActive&&!search.trim()&&<p className="field-error">검색어를 입력하세요. 빈 검색어로 전체 목록을 조회하지 않습니다.</p>}
      <section className="section-spacing" aria-label="영상 수집"><div className="section-title"><strong>01 · 영상 불러오기</strong><span>지정 채널 5개</span></div><button className="btn primary full-load" disabled={loading} onClick={load}><Icon name="refresh" size={16}/>{loading?'불러오는 중…':'① 영상 불러오기'}</button><details className="more-tools"><summary>더보기 · 영상 URL로 선택</summary><form onSubmit={event=>{event.preventDefault();void resolve()}}><label className="field-label" htmlFor="video-url">YouTube 영상 링크</label><div className="url-control"><input id="video-url" type="url" inputMode="url" maxLength={2048} value={url} onChange={event=>setUrl(event.target.value)} aria-describedby="url-help"/><button aria-label="링크 확인" title="링크 확인" disabled={loading||analyzing}><Icon name="link"/></button></div><p id="url-help" className="help-text">YouTube 영상 주소를 입력하세요. 실제 채널을 확인합니다.</p></form></details></section>
      <div className="section-title videos-heading"><strong>채널별 영상 목록</strong><span role="status">{loading?'조회 중':`${visible.length}개 표시`}</span></div><div className="channel-chips" role="group" aria-label="채널 필터"><button aria-pressed={!channel} className={!channel?'selected':''} onClick={()=>setChannel('')}>전체 채널</button>{Object.entries(health?.channels??{}).map(([id,name])=><button key={id} aria-pressed={channel===id} className={channel===id?'selected':''} onClick={()=>setChannel(id)}>{name}</button>)}</div>{(searchActive||channel)&&<div className="filter-actions"><button className="btn light" onClick={resetFilters}>전체 목록 보기</button><span className="help-text">검색·필터 상태가 이 브라우저에 저장됩니다.</span></div>}<div className="video-list" id="video-list" aria-busy={loading}>{visible.map(video=><button className={`video-item ${selected?.id===video.id?'selected':''}`} key={video.id} aria-pressed={selected?.id===video.id} disabled={analyzing} onClick={()=>void select(video)}><span className="thumbnail"><img src={video.thumbnail} alt="" loading="lazy" decoding="async" width="120" height="90"/></span><span className="video-info"><strong>{video.title}</strong><span>{video.channel} · {new Date(video.published_at).toLocaleDateString('ko-KR')}</span><small>{video.allowed?'게시 허용 범위':'분석만 가능'}</small></span><span className="video-arrow"><Icon name={selected?.id===video.id?'check':'chevron'}/></span></button>)}{!loading&&!visible.length&&<div className="empty-state"><span className="empty-icon"><Icon name="video" size={23}/></span><strong>{videos.length?'조건에 맞는 영상이 없습니다.':'아직 불러온 영상이 없습니다.'}</strong><p>{videos.length?'검색어를 입력하거나 전체 목록 보기를 선택하세요.':'영상 불러오기를 눌러 목록을 확인하세요.'}</p>{!videos.length&&<button className="btn secondary" onClick={load}>영상 불러오기</button>}</div>}</div><p className="bottom-footnote">수집한 자막과 화면의 출처를 확인하세요. 근거를 얻지 못한 영상은 메타데이터 분석으로 표시합니다.</p></main>
      <aside className="detail-panel" aria-label="AI 분석 및 댓글 상세"><div className="detail-header"><div className="detail-header-left"><span className="detail-icon"><Icon name="sparkle"/></span><div><strong>AI 콘텐츠 분석</strong><span>OLLAMA LOCAL AGENT</span></div></div><span className="badge neutral">로컬 실행</span></div><div className="detail-scroll">{!selected?<div className="selection-empty"><div className="empty-orb"><Icon name="video" size={30}/></div><h2>분석할 영상을 선택하세요</h2><p>영상 목록에서 하나를 선택하면 고민 요약과 댓글 초안이 표시됩니다.</p></div>:<>
        <section className="detail-section"><div className="section-title"><strong>02 · 영상 선택 및 AI 분석</strong><span className="badge neutral">{selected.channel}</span></div><h2 id="analysis-title" className="selected-title" tabIndex={-1}>{selected.title}</h2><div className="mini-meta"><Icon name="clock" size={13}/>{date(selected.published_at)}</div><a className="source-link" href={`https://www.youtube.com/watch?v=${selected.id}`} target="_blank" rel="noreferrer">YouTube에서 영상 보기 <Icon name="external" size={13}/></a><button className="btn secondary full" disabled={analyzing||pending} onClick={regenerate}><Icon name="sparkle" size={15}/>{analyzing?'Ollama 분석 중…':analysis?'초안 다시 생성':'영상 분석'}</button>{analyzing&&<p role="status" className="help-text">실제 자료를 수집하고 있습니다. 완료까지 잠시 기다려 주세요.</p>}</section>
        {analysis&&<section className="detail-section"><div className="section-title"><h3>영상의 핵심 고민</h3><span className="badge blue">{analysis.scene_verified?(analysis.source_basis==='frame_ocr'?'화면 근거 확인':'자막 근거 확인'):'메타데이터 분석'}</span></div><p className="concern-box">{analysis.concern}</p><div className="evidence-box"><div className="evidence-title"><Icon name="shield" size={14}/>분석 근거</div>{analysis.evidence.map((item,index)=><div key={index}><a href={item.url} target="_blank" rel="noreferrer">{item.label} ↗</a><p>{item.quote}</p>{item.capture&&<a href={`/api/screenshots/${encodeURIComponent(item.capture)}`} target="_blank" rel="noreferrer">영상 화면 캡처 ↗</a>}</div>)}{analysis.warnings.map(warning=><p className="limitation" key={warning}><Icon name="alert" size={13}/>{warning}</p>)}</div><details><summary>더보기 · 영상 설명과 분석 정보</summary><p className="video-description">{selected.description}</p><p className="help-text">{analysis.model} · {date(analysis.created_at)}</p></details></section>}
        <section className="detail-section"><div className="section-title"><h3>03 · 댓글 검토 및 게시</h3><span className={`badge ${invalid?'warn':'success'}`}>{invalid?'검토 필요':'형식 충족'}</span></div><label className="field-label" htmlFor="draft">댓글 초안 · 40~120자</label><textarea id="draft" value={draft} rows={5} maxLength={120} onChange={event=>{setDraft(event.target.value);setApproved(false);setEdited(true);setDraftError('')}} onBlur={()=>setDraftError(validate(draft,health?.min_chars,health?.max_chars))} aria-invalid={!!draftError} aria-describedby="draft-help draft-error" disabled={analyzing||pending||blocked}/><div className="editor-foot"><span id="draft-help">[광고]와 운명원 필수</span><strong>{[...draft.normalize('NFC').trim()].length}/120</strong></div><p id="draft-error" className="field-error">{draftError}</p><p className="help-text">{localState}</p><button className="btn light" disabled={!draft||saving||pending||blocked} onClick={save}><Icon name="check" size={14}/>{saving?'저장 중…':'수정 저장'}</button></section>
        <section className="detail-section"><label className="field-label" htmlFor="profile">Chrome 프로필</label><div className="profile-line"><select id="profile" disabled><option>유튜브1</option></select><button className="btn light" disabled={browserBusy||pending} onClick={openBrowser}><Icon name="external" size={14}/>{browserBusy?'여는 중…':'전용 Chrome 열기'}</button></div><details><summary>더보기 · 로그인 상태 확인</summary><button className="btn light" disabled={browserBusy||pending} onClick={checkBrowser}>로그인 상태 확인</button>{browser&&<p role="status" className="help-text">{browser.signed_in?'로그인 확인됨':browser.needs_action}</p>}</details><p className="help-text">최초 로그인은 README 절차로 진행하세요. CAPTCHA·인증·접근 제한을 우회하지 않습니다.</p><label className="approval"><input type="checkbox" checked={approved} onChange={event=>setApproved(event.target.checked)} disabled={pending||blocked}/><span>현재 본문을 확인했으며 광고 댓글 게시를 승인합니다.</span></label>{!selected.allowed&&<p className="field-error">허용 채널 또는 등록된 테스트 영상에만 게시할 수 있습니다.</p>}{blocked&&<p className="field-error">진행·게시·확인 불가 이력이 있어 재게시를 차단합니다.</p>}<button className="btn primary full post" disabled={!canPost} onClick={post}><Icon name="play" size={15}/>{posting?'작업 요청 중…':'③ 댓글 달기'}</button><p className="help-text">실제 YouTube 공개 댓글을 작성합니다. 확인 불가 상태는 재게시하지 않습니다.</p></section>{job&&<section className="detail-section job-section" aria-label="게시 진행 상태"><strong role="status">{labels[job.status]??job.status}</strong>{job.error&&<p className="error-inline">{job.error}</p>}<div className="job-actions">{job.screenshot&&<a className="btn light" href={`/api/screenshots/${job.screenshot}`} target="_blank" rel="noreferrer">화면 캡처</a>}{job.comment_url&&<a className="btn light" href={job.comment_url} target="_blank" rel="noreferrer">댓글 보기 ↗</a>}</div></section>}
      </>}</div><div className="detail-footer"><span className={`status-dot ${health?.ollama==='ready'?'on':''}`}/>오늘 예약·게시 {activities?.quota.used??'–'} / {health?.daily_max??10}</div></aside></>}
    {path==='/activities'&&<main id="main-content" tabIndex={-1} className="wide-panel" aria-labelledby="page-title"><header className="heading"><div className="eyebrow">POSTING ACTIVITY</div><h1 id="page-title">작업 이력</h1><p>게시 상태와 오류를 시간순으로 확인합니다.</p></header>{historyError&&<p role="alert" className="field-error">{historyError}</p>}<div className="history-list">{history?.jobs.map(item=><article className="history-row" key={item.id}><span className="badge neutral">{labels[item.status]??item.status}</span><div><strong>{item.title??item.video_id}</strong><p>{item.profile} · {item.text}</p>{item.error&&<p className="error-inline">{item.error}</p>}{item.screenshot&&<a href={`/api/screenshots/${item.screenshot}`} target="_blank" rel="noreferrer">화면 캡처 ↗</a>}{item.comment_url&&<a href={item.comment_url} target="_blank" rel="noreferrer">댓글 보기 ↗</a>}</div><span className="history-date">{date(item.created_at)}</span></article>)}{!history?.jobs.length&&<div className="empty-state"><strong>아직 게시 작업이 없습니다.</strong><a className="btn secondary" href="/" onClick={event=>follow(event,'/')}>영상 탐색으로 이동</a></div>}</div><details><summary>더보기 · 단계별 활동 기록</summary>{history?.logs.map(log=><div className="history-row" key={log.id}><span className="badge neutral">{labels[log.stage]??log.stage}</span><div><strong>{log.video_id}</strong><p>{log.detail}</p></div><span className="history-date">{date(log.created_at)}</span></div>)}</details><nav className="pagination" aria-label="작업 이력 페이지">{historyPages.map(index=><button className="btn light" key={index} aria-label={`${index+1}페이지`} aria-current={index===historyPage?'page':undefined} onClick={()=>setHistoryPage(index)}>{index+1}</button>)}</nav></main>}
    {path==='/settings'&&<main id="main-content" tabIndex={-1} className="wide-panel" aria-labelledby="page-title"><header className="heading"><div className="eyebrow">LOCAL ENVIRONMENT</div><h1 id="page-title">환경 상태</h1><p>연결 여부만 표시합니다. 키 값은 노출하지 않습니다.</p></header><button className="btn secondary" onClick={()=>void refreshHealth()}>연결 상태 새로고침</button><div className="settings-grid"><section className="setting-card"><Icon name="video"/><h2>YouTube Data API</h2><p>{health?.youtube==='configured'?'키가 설정됐습니다. 실제 조회는 영상 불러오기로 확인하세요.':'YOUTUBE_API_KEY를 설정한 뒤 서버를 다시 실행하세요.'}</p></section><section className="setting-card"><Icon name="sparkle"/><h2>Ollama</h2><p>{health?.model} · {health?.ollama==='ready'?'모델 연결 확인됨':'Ollama 실행과 모델 설치 상태를 확인하세요.'}</p></section><section className="setting-card"><Icon name="user"/><h2>Chrome · 유튜브1</h2><p>지정된 전용 프로필을 사용합니다. 최초 로그인은 README의 일반 Chrome 절차로 진행하세요.</p><button className="btn light" disabled={browserBusy||pending} onClick={openBrowser}>전용 Chrome 열기</button></section><section className="setting-card"><Icon name="shield"/><h2>이 브라우저의 임시 저장</h2><p>댓글은 7일간 보관합니다. API 키·쿠키·인증 토큰은 저장하지 않습니다.</p><button className="btn light" onClick={clearLocal}>임시 저장 삭제</button></section></div></main>}
    {!routes[path]&&<main id="main-content" tabIndex={-1} className="wide-panel not-found" aria-labelledby="page-title"><span className="error-code">404</span><h1 id="page-title">페이지를 찾을 수 없습니다</h1><p>주소를 확인하거나 영상 탐색으로 돌아가세요.</p><a className="btn primary" href="/" onClick={event=>follow(event,'/')}>영상 탐색으로 이동</a></main>}
    <footer className="app-footer"><a href="https://github.com/seo-gali/marketing-ai-agent" target="_blank" rel="noreferrer">© {new Date().getFullYear()} seo-gali/marketing-ai-agent</a><nav aria-label="푸터 링크"><a href="/api/health" target="_blank" rel="noreferrer">API 상태</a><a href="https://developers.google.com/youtube/v3" target="_blank" rel="noreferrer">YouTube API 문서</a></nav></footer>
    {(error||notice)&&<div id="global-message" tabIndex={-1} role={error?'alert':'status'} className={`toast ${error?'toast-error':''}`}><span>{error||notice}</span>{!error&&undo&&<button className="undo-button" onClick={()=>{setSearch(undo.search);setChannel(undo.channel);setSearchActive(undo.active);setUndo(null);success('이전 검색·필터로 돌아갔습니다.')}}>실행 취소</button>}<button aria-label="알림 닫기" onClick={()=>{setError('');setNotice('');setUndo(null)}}>×</button></div>}
  </div>
}
