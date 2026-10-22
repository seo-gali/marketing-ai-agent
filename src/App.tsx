import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { api, labels, type Video, type Health, type Analysis, type Activities, type BrowserStatus, type Job } from './api'
import Icon from './Icon'

const routes: Record<string,string> = {'/':'영상 탐색','/activities':'작업 이력','/settings':'환경 설정'}
const terminal = ['success','failed','uncertain']
const date = (value:string) => new Date(value).toLocaleString('ko-KR')
function readFilters() {
  try {
    const value=JSON.parse(localStorage.getItem('marketing-ai:filters')??'{}')
    return {search:typeof value.search==='string'?value.search.slice(0,100):'',channel:typeof value.channel==='string'?value.channel:'',active:value.active===true}
  } catch {return {search:'',channel:'',active:false}}
}
function readTheme(): 'light'|'dark' {
  try {return localStorage.getItem('marketing-ai:theme')==='dark'?'dark':'light'} catch {return 'light'}
}
function readProfile() {
  try {const name=localStorage.getItem('marketing-ai:profile');return name&&['유튜브1','유튜브2','유튜브3'].includes(name)?name:'유튜브1'} catch {return '유튜브1'}
}
function validate(text:string,min=40,max=120) {
  text=text.normalize('NFC').trim()
  if([...text].length<min||[...text].length>max) return `댓글을 ${min}~${max}자로 작성하세요.`
  if(!text.includes('운명원')) return '운명원 연애 사주에 대한 관심이 드러나는 댓글을 작성하세요.'
  if(/https?:|www\.|(?:[\p{L}\p{N}_-]+\.)+[\p{L}]{2,63}|(?:\d{1,3}\.){3}\d{1,3}|#|[\p{Cc}\p{Cf}]/iu.test(text.normalize('NFKC'))) return '링크·해시태그·보이지 않는 제어 문자를 제거하세요.'
  return ''
}

export default function App() {
  const [path,setPath]=useState(location.pathname)
  const [menuOpen,setMenuOpen]=useState(false)
  const [health,setHealth]=useState<Health>()
  const [healthLoading,setHealthLoading]=useState(false)
  const [apiConnected,setApiConnected]=useState<boolean|null>(null)
  const [apiChecking,setApiChecking]=useState(false)
  const [theme,setTheme]=useState(readTheme)
  const [profiles,setProfiles]=useState<string[]>(['유튜브1'])
  const [profile,setProfile]=useState(readProfile)
  const [addingProfile,setAddingProfile]=useState('')
  const [videos,setVideos]=useState<Video[]>([])
  const [linkedVideos,setLinkedVideos]=useState<Video[]>([])
  const [channelAddOpen,setChannelAddOpen]=useState(false)
  const [selected,setSelected]=useState<Video>()
  const [filters]=useState(readFilters)
  const [search,setSearch]=useState(filters.search)
  const [channel,setChannel]=useState(filters.channel)
  const [searchActive,setSearchActive]=useState(filters.active)
  const [url,setUrl]=useState('')
  const [loading,setLoading]=useState(false)
  const [loadedChannels,setLoadedChannels]=useState<string[]>([])
  const [analyzing,setAnalyzing]=useState(false)
  const [cancelling,setCancelling]=useState(false)
  const [analysisStarted,setAnalysisStarted]=useState(0)
  const [analysisElapsed,setAnalysisElapsed]=useState(0)
  const [saving,setSaving]=useState(false)
  const [analysis,setAnalysis]=useState<Analysis>()
  const [analysisError,setAnalysisError]=useState('')
  const [draft,setDraft]=useState('')
  const [draftError,setDraftError]=useState('')
  const [edited,setEdited]=useState(false)
  const [localState,setLocalState]=useState('')
  const [approved,setApproved]=useState(false)
  const [activities,setActivities]=useState<Activities>()
  const [history,setHistory]=useState<Activities>()
  const [historyPage,setHistoryPage]=useState(0)
  const [historyKind,setHistoryKind]=useState<'jobs'|'logs'>('jobs')
  const [historyLoading,setHistoryLoading]=useState(false)
  const [historyRevision,setHistoryRevision]=useState(0)
  const [deletingHistory,setDeletingHistory]=useState(false)
  const [historyUndo,setHistoryUndo]=useState<string|null>(null)
  const [historyError,setHistoryError]=useState('')
  const [browser,setBrowser]=useState<BrowserStatus>()
  const [browserBusy,setBrowserBusy]=useState(false)
  const [posting,setPosting]=useState(false)
  const [storedJob,setStoredJob]=useState<Job|null>(null)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [toastFading,setToastFading]=useState(false)
  const [toastRevision,setToastRevision]=useState(0)
  const [undo,setUndo]=useState<ReturnType<typeof readFilters>|null>(null)
  const selectedId=useRef('')
  const historyCache=useRef(new Map<string,Activities>())
  const lastActivityId=useRef<number|null>(null)
  const analysisDialog=useRef<HTMLDialogElement>(null)
  const cancelRequested=useRef(false)
  const analysisProgress=activities?.logs.find(item=>item.video_id===selected?.id&&item.stage==='analysis_progress'&&Date.parse(item.created_at)>=analysisStarted)?.detail
  const job=activities?.jobs.find(item=>item.video_id===selected?.id)??storedJob
  const pending=activities?.jobs.some(item=>!terminal.includes(item.status))??false
  const blocked=(!!selected&&!!activities?.blocked_video_ids.includes(selected.id))||(!!job&&job.status!=='failed')
  const invalid=validate(draft,health?.min_chars,health?.max_chars)
  const visible=channelAddOpen?linkedVideos:videos.filter(video=>(!channel||video.channel_id===channel)&&(!searchActive||(!!search.trim()&&`${video.title} ${video.channel}`.toLowerCase().includes(search.trim().toLowerCase()))))
  const needsVideoLoad=!channelAddOpen&&(channel?!loadedChannels.includes(channel):!loadedChannels.length)
  const canPost=!!selected?.allowed&&!!analysis&&(analysis.scene_verified||!!health?.test_video_ids.includes(selected.id))&&approved&&!invalid&&!analyzing&&!posting&&!pending&&!blocked&&!!activities&&activities.quota.used<activities.quota.max
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
    setError(problem instanceof Error?problem.message:String(problem));setNotice('');setToastFading(false);setToastRevision(value=>value+1)
    requestAnimationFrame(()=>{const element=document.getElementById(target);element?.focus();element?.scrollIntoView({block:'nearest'})})
  }
  function success(message:string) {setNotice(message);setError('');setUndo(null);setHistoryUndo(null);setToastFading(false);setToastRevision(value=>value+1)}
  function closeToast() {
    if(document.getElementById('global-message')?.contains(document.activeElement)) document.getElementById('main-content')?.focus({preventScroll:true})
    setError('');setNotice('');setUndo(null);setHistoryUndo(null);setToastFading(false)
  }
  useEffect(()=>{
    if(!error&&!notice) return
    const fade=setTimeout(()=>setToastFading(true),10000)
    const close=setTimeout(closeToast,10300)
    return ()=>{clearTimeout(fade);clearTimeout(close)}
  },[error,notice,toastRevision])
  useEffect(()=>{
    if(!analyzing) return
    const started=Date.now();setAnalysisStarted(started);setAnalysisElapsed(0)
    const timer=setInterval(()=>setAnalysisElapsed(Math.floor((Date.now()-started)/1000)),1000)
    return ()=>clearInterval(timer)
  },[analyzing])
  useEffect(()=>{
    const dialog=analysisDialog.current
    if(analyzing&&!dialog?.open) dialog?.showModal()
    else if(!analyzing&&dialog?.open) {
      dialog.close()
      document.getElementById(error?'global-message':'analysis-title')?.focus({preventScroll:true})
    }
  },[analyzing])
  async function refreshHealth() {
    setHealthLoading(true);setError('')
    try {
      const response=await fetch('/api/health')
      if(response.status!==200) throw new Error(`API 연결 확인 실패 (HTTP ${response.status}). 다시 확인하세요.`)
      const data:Health=await response.json().catch(()=>{throw new Error('API 응답을 읽을 수 없습니다.')})
      setHealth(data);setApiConnected(true)
    } catch(problem) {setHealth(undefined);setApiConnected(false);fail(problem)} finally {setHealthLoading(false)}
  }
  async function checkApi() {
    setApiChecking(true);setError('')
    try {
      const response=await fetch('/api/health')
      if(response.status!==200) throw new Error(`API 연결 확인 실패 (HTTP ${response.status}). 다시 확인하세요.`)
      setApiConnected(true)
    } catch(problem) {setApiConnected(false);fail(problem)} finally {setApiChecking(false)}
  }
  useEffect(()=>{
    document.documentElement.dataset.theme=theme
    try {localStorage.setItem('marketing-ai:theme',theme)} catch { /* 브라우저 저장 제한 */ }
  },[theme])
  useEffect(()=>{
    const back=()=>{setPath(location.pathname);setMenuOpen(false)}
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'&&menuOpen){setMenuOpen(false);document.getElementById('menu-toggle')?.focus()}}
    window.addEventListener('popstate',back);window.addEventListener('keydown',escape)
    return ()=>{window.removeEventListener('popstate',back);window.removeEventListener('keydown',escape)}
  },[menuOpen])
  useEffect(()=>{document.title=`${routes[path]??'페이지를 찾을 수 없습니다'} · Marketing AI`},[path])
  useEffect(()=>{void refreshHealth()},[])
  useEffect(()=>{api<string[]>('/profiles').then(names=>{setProfiles(names);setProfile(value=>names.includes(value)?value:'유튜브1')}).catch(fail)},[])
  useEffect(()=>{try {localStorage.setItem('marketing-ai:profile',profile)} catch { /* 브라우저 저장 제한 */ }},[profile])
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
    const refresh=()=>{api<Activities>('/activities').then(setActivities).catch(()=>setHistoryError('이력을 불러오지 못했습니다. 서버 연결을 확인하세요.'))}
    refresh();const timer=setInterval(refresh,3000);return ()=>clearInterval(timer)
  },[])
  useEffect(()=>{
    if(!activities) return
    const id=activities.logs[0]?.id??0
    if(lastActivityId.current!==null&&lastActivityId.current!==id&&!historyError) setHistoryRevision(value=>value+1)
    lastActivityId.current=id
  },[activities?.logs[0]?.id])
  useEffect(()=>{
    if(path!=='/activities') return
    let active=true
    const key=`${historyKind}:${historyPage}`
    const cached=historyCache.current.get(key)
    setHistory(cached);setHistoryLoading(true);setHistoryError('')
    api<Activities>(`/activities?kind=${historyKind}&offset=${historyPage*30}&limit=30`).then(data=>{
      if(!active) return
      if(historyPage>=data.total_pages) {setHistoryPage(Math.max(0,data.total_pages-1));return}
      setHistory(data)
      if(data.has_more) api<Activities>(`/activities?kind=${historyKind}&offset=${(historyPage+1)*30}&limit=30`).then(next=>{if(active){historyCache.current.clear();historyCache.current.set(`${historyKind}:${historyPage+1}`,next)}}).catch(()=>{})
    }).catch(problem=>{if(active) setHistoryError(problem instanceof Error?problem.message:'이력을 불러오지 못했습니다.')}).finally(()=>{if(active) setHistoryLoading(false)})
    return ()=>{active=false}
  },[path,historyPage,historyKind,historyRevision])
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
    setLoading(true);setError('');setChannelAddOpen(false)
    const target=channel
    try {
      const data=await api<{videos:Video[];warnings:string[];loaded_channels?:string[]}>(`/videos${target?`?channel=${encodeURIComponent(target)}`:''}`)
      const loaded=data.loaded_channels??[...new Set(data.videos.map(video=>video.channel_id))]
      setVideos(previous=>target?[...previous.filter(video=>video.channel_id!==target),...data.videos]:data.videos)
      setLoadedChannels(previous=>target?[...new Set([...previous.filter(id=>id!==target),...loaded])]:loaded)
      success(data.warnings.length?data.warnings.join(' / '):`${data.videos.length}개 영상을 불러왔습니다.`)
    }
    catch(problem) {fail(problem)} finally {setLoading(false)}
  }
  async function select(video:Video) {
    cancelRequested.current=false
    setAnalysisError('')
    selectedId.current=video.id;setSelected(video);setAnalysis(undefined);setDraft('');setEdited(false);setDraftError('');setLocalState('');setApproved(false);setStoredJob(null);setAnalyzing(true);setError('')
    try {
      const detail=await api<Video&{analysis:Analysis|null;posting_job:Job|null}>(`/videos/${video.id}`)
      if(selectedId.current===video.id) setStoredJob(detail.posting_job)
      const usable=detail.analysis&&(detail.analysis.draft_version===5||!!detail.posting_job)&&(detail.analysis.scene_verified||health?.test_video_ids.includes(video.id))
      const data=usable?detail.analysis!:await api<Analysis>(`/videos/${video.id}/analyze`,'POST')
      if(selectedId.current!==video.id) return
      let text=data.comment
      try {
        const cached=JSON.parse(localStorage.getItem(`marketing-ai:draft:${video.id}`)??'null')
        if(cached&&cached.expiresAt>Date.now()&&typeof cached.text==='string'&&cached.text.length<=2000) {text=cached.text;setLocalState('이 브라우저의 임시 초안을 불러왔습니다.')}
        else if(cached) localStorage.removeItem(`marketing-ai:draft:${video.id}`)
      } catch { /* 손상된 임시 초안 무시 */ }
      setAnalysis(data);setDraft(text)
    } catch(problem) {if(selectedId.current===video.id) {if(cancelRequested.current) success('분석을 취소했습니다.');else {setAnalysisError(problem instanceof Error?problem.message:String(problem));requestAnimationFrame(()=>document.getElementById('analysis-error')?.focus())}}} finally {if(selectedId.current===video.id) setAnalyzing(false)}
  }
  async function resolve() {
    if(!url.trim()) {fail(new Error('영상 URL을 입력하세요.'),'video-url');return}
    setLoading(true);setError('')
    try {const video=await api<Video>('/videos/resolve','POST',{url:url.trim()});setLinkedVideos(items=>[video,...items.filter(item=>item.id!==video.id)]);setUrl('');success('영상 링크를 확인했습니다.');void select(video)}
    catch(problem) {fail(problem,'video-url')} finally {setLoading(false)}
  }
  async function regenerate() {
    if(!selected) return
    cancelRequested.current=false
    setAnalysisError('')
    const id=selected.id;setAnalyzing(true);setApproved(false);setError('')
    try {const data=await api<Analysis>(`/videos/${id}/analyze`,'POST');if(selectedId.current===id) {setAnalysis(data);setDraft(data.comment);setEdited(true);setDraftError('');success('새 초안을 생성했습니다.')}}
    catch(problem) {if(cancelRequested.current) success('분석을 취소했습니다.');else {setAnalysisError(problem instanceof Error?problem.message:String(problem));requestAnimationFrame(()=>document.getElementById('analysis-error')?.focus())}} finally {if(selectedId.current===id) setAnalyzing(false)}
  }
  async function cancelAnalysis() {
    if(!selected||cancelling) return
    setCancelling(true);cancelRequested.current=true
    try {const result=await api<{status:string}>(`/videos/${selected.id}/analyze/cancel`,'POST');if(result.status!=='cancelled') cancelRequested.current=false}
    catch(problem) {cancelRequested.current=false;fail(problem)} finally {setCancelling(false)}
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
    try {setBrowser(await api<BrowserStatus>('/browser/open','POST',{video_id:selected?.id,profile}));success(`${profile} 프로필을 열었습니다.`)}
    catch(problem) {fail(problem)} finally {setBrowserBusy(false)}
  }
  async function checkBrowser() {try {setBrowser(await api<BrowserStatus>('/browser/status'))} catch(problem) {fail(problem)}}
  async function post() {
    if(!selected||!canPost) return
    setPosting(true);setError('')
    try {setStoredJob(await api<Job>('/posting-jobs','POST',{video_id:selected.id,text:draft,approved,profile}));setActivities(await api<Activities>('/activities'));setApproved(false);success('게시 작업을 시작했습니다. 완료 여부는 서버 상태에서 확인하세요.')}
    catch(problem) {fail(problem)} finally {setPosting(false)}
  }
  function clearLocal() {
    try {for(let index=localStorage.length-1;index>=0;index--) {const key=localStorage.key(index);if(key?.startsWith('marketing-ai:draft:')) localStorage.removeItem(key)}setEdited(false);setLocalState('임시 초안을 삭제했습니다.');success('이 브라우저에 임시 저장한 초안을 삭제했습니다.')}
    catch {fail(new Error('브라우저 저장 공간을 삭제하지 못했습니다.'))}
  }
  function changeProfile(value:string) {setProfile(value);setApproved(false);setBrowser(undefined)}
  async function addProfile(name:string) {
    setAddingProfile(name)
    try {setProfiles(await api<string[]>('/profiles','POST',{name}));success(`${name} 프로필을 추가했습니다.`)}
    catch(problem) {fail(problem)} finally {setAddingProfile('')}
  }
  async function loginProfile(name:string) {
    setBrowserBusy(true)
    try {const result=await api<{message:string}>('/profiles/login','POST',{name});setBrowser(undefined);success(result.message)}
    catch(problem) {fail(problem)} finally {setBrowserBusy(false)}
  }
  async function deleteHistory(id?:string) {
    setDeletingHistory(true)
    try {
      const result=await api<{token:string;count:number}>('/activities','DELETE',{kind:historyKind,id})
      historyCache.current.clear();setHistoryRevision(value=>value+1)
      success(`${result.count}건을 이력에서 삭제했습니다. YouTube 댓글은 유지됩니다.`)
      if(result.count) setHistoryUndo(result.token)
      requestAnimationFrame(()=>document.getElementById('global-message')?.focus({preventScroll:true}))
    } catch(problem) {fail(problem)} finally {setDeletingHistory(false)}
  }
  async function restoreHistory() {
    if(!historyUndo) return
    try {await api('/activities/restore','POST',{token:historyUndo});historyCache.current.clear();setHistoryRevision(value=>value+1);success('삭제한 이력을 복원했습니다.');requestAnimationFrame(()=>document.getElementById('global-message')?.focus({preventScroll:true}))}
    catch(problem) {fail(problem)}
  }

  return <div className={`app-shell ${menuOpen?'mobile-open':''}`}>
    <a className="skip-link" href="#main-content">본문으로 이동</a>
    <aside className="sidebar">
      <div className="mobile-heading"><a className="brand" href="/" onClick={event=>follow(event,'/')} aria-label="Marketing AI 홈"><span className="brand-mark"><Icon name="sparkle" size={20}/></span><span><span className="brand-name">Marketing <span>AI</span></span></span></a><button id="menu-toggle" className="mobile-toggle" aria-expanded={menuOpen} aria-controls="main-navigation" aria-label={menuOpen?'메뉴 닫기':'메뉴 열기'} onClick={()=>setMenuOpen(!menuOpen)}><Icon name="grid"/></button></div>
      <nav id="main-navigation" aria-label="주 메뉴">{[['/','grid','영상 탐색'],['/activities','clock','작업 이력'],['/settings','settings','환경 설정']].map(([destination,icon,label])=><a className={`nav-item ${path===destination?'active':''}`} href={destination} key={destination} onClick={event=>follow(event,destination)} aria-current={path===destination?'page':undefined}><Icon name={icon}/>{label}</a>)}</nav>
      <div className="sidebar-bottom">
        <section className="connection-box" aria-label="연결 상태" aria-busy={healthLoading}>
          <div className="connection-toolbar"><strong>연결 상태</strong><button className="icon-button" aria-label="연결 상태 새로고침" title="연결 상태 새로고침" disabled={healthLoading||apiChecking} onClick={()=>void refreshHealth()}><Icon name="refresh" size={15}/></button></div>
          <div className="connection-head"><span className={`status-dot ${health?.ollama==='ready'?'on':''}`}/>Ollama {healthLoading?'확인 중':health?.ollama==='ready'?'연결됨':'확인 필요'}</div><p>{health?.model??'연결 확인 중'}</p>
          <div className="connection-head"><span className={`status-dot ${health?.youtube==='configured'?'on':''}`}/>YouTube API {healthLoading?'확인 중':health?.youtube==='configured'?'키 설정됨':'확인 필요'}</div>
          <div className="connection-head api-connection" aria-busy={healthLoading||apiChecking}><span className={`status-dot ${healthLoading||apiChecking?'':apiConnected===true?'on':apiConnected===false?'off':''}`}/><span role="status">API {healthLoading||apiChecking?'확인 중':apiConnected===true?'연결됨':apiConnected===false?'연결 실패':'미확인'}</span><button className="connection-check" aria-label="API 상태 확인" disabled={healthLoading||apiChecking} onClick={()=>void checkApi()}>확인</button></div>
        </section>
      </div>
    </aside>
    {path==='/'&&<><main id="main-content" className="main-panel" tabIndex={-1} aria-labelledby="page-title"><header className="heading"><h1 id="page-title">영상 탐색</h1></header>{!channelAddOpen&&<form className="search-form" onSubmit={event=>{event.preventDefault();setSearchActive(true);if(!search.trim()) fail(new Error('검색어를 입력하세요.'),'video-search')}}><label className="field-label" htmlFor="video-search">영상 검색</label><div className="top-search"><Icon name="search"/><input id="video-search" type="search" maxLength={100} value={search} onChange={event=>{setSearch(event.target.value);setSearchActive(true)}}/><button className="search-submit" aria-label="검색 실행"><Icon name="chevron"/></button></div></form>}{!channelAddOpen&&searchActive&&!search.trim()&&<p className="field-error">검색어를 입력하세요. 빈 검색어로 전체 목록을 조회하지 않습니다.</p>}
      <div className="section-title videos-heading"><strong>채널별 영상 목록</strong><div className="video-list-actions"><span role="status">{loading?'조회 중':`${visible.length}개 표시`}</span>{!!loadedChannels.length&&!channelAddOpen&&<button className="icon-button" aria-label="영상 새로고침" title="영상 새로고침" disabled={loading} onClick={load}><Icon name="refresh" size={15}/></button>}</div></div>
      <div className="channel-chips" role="group" aria-label="채널 필터">
        <button aria-pressed={!channelAddOpen&&!channel} className={!channelAddOpen&&!channel?'selected':''} onClick={()=>{setChannelAddOpen(false);if(searchActive||channel) resetFilters()}}>전체 채널</button>
        {Object.entries(health?.channels??{}).map(([id,name])=><button key={id} aria-pressed={!channelAddOpen&&channel===id} className={!channelAddOpen&&channel===id?'selected':''} onClick={()=>{setChannelAddOpen(false);setChannel(id);setSearch('');setSearchActive(false)}}>{name}</button>)}
        <button className={`add-channel-tab ${channelAddOpen?'selected':''}`} aria-pressed={channelAddOpen} aria-controls="channel-content" onClick={()=>setChannelAddOpen(true)}><Icon name="plus" size={13}/>채널 추가</button>
      </div>
      <div id="channel-content">
        {channelAddOpen?<section className="add-channel-panel" aria-labelledby="add-channel-title">
          <h2 id="add-channel-title">채널 추가</h2>
          <form onSubmit={event=>{event.preventDefault();void resolve()}}><label className="field-label" htmlFor="video-url">YouTube 영상 링크</label><div className="url-control"><input id="video-url" type="url" inputMode="url" maxLength={2048} value={url} onChange={event=>setUrl(event.target.value)}/><button aria-label="링크 확인" title="링크 확인" disabled={loading||analyzing}><Icon name="link"/></button></div></form>
        </section>:null}
        <div className="video-list" id="video-list" role="region" aria-label="영상 목록" tabIndex={0} aria-busy={loading}>
          {visible.map(video=><button className={`video-item ${selected?.id===video.id?'selected':''}`} key={video.id} aria-pressed={selected?.id===video.id} disabled={analyzing} onClick={()=>void select(video)}><span className="thumbnail"><img src={video.thumbnail} alt="" loading="lazy" decoding="async" width="120" height="90"/></span><span className="video-info"><strong>{video.title}</strong><span>{video.channel} · {new Date(video.published_at).toLocaleDateString('ko-KR')}</span></span><span className="video-arrow"><Icon name={selected?.id===video.id?'check':'chevron'}/></span></button>)}
          {!visible.length&&<div className="empty-state"><span className="empty-icon"><Icon name="video" size={23}/></span>{needsVideoLoad&&<button className="btn primary" disabled={loading} onClick={load}>{loading?'불러오는 중…':'영상 불러오기'}</button>}<strong>{loading?'영상을 불러오고 있습니다.':channelAddOpen?'조회한 영상이 없습니다.':needsVideoLoad?'아직 불러온 영상이 없습니다.':searchActive?'조건에 맞는 영상이 없습니다.':'채널에 공개된 영상이 없습니다.'}</strong></div>}
        </div>
      </div>
    </main>
      <aside className="detail-panel" aria-label="AI 분석 및 댓글 상세"><div className="detail-header"><div className="detail-header-left"><span className="detail-icon"><Icon name="sparkle"/></span><div><strong>AI 콘텐츠 분석</strong></div></div></div><div className="detail-scroll">{!selected?<div className="selection-empty"><div className="empty-orb"><Icon name="video" size={30}/></div><h2>분석할 영상을 선택하세요</h2></div>:<>
        <section className="detail-section"><div className="section-title"><strong>영상 분석</strong><span className="badge neutral">{selected.channel}</span></div><h2 id="analysis-title" className="selected-title" tabIndex={-1}>{selected.title}</h2><div className="mini-meta"><Icon name="clock" size={13}/>{date(selected.published_at)}</div><a className="source-link" href={`https://www.youtube.com/watch?v=${selected.id}`} target="_blank" rel="noreferrer">YouTube에서 영상 보기 <Icon name="external" size={13}/></a><button className="btn secondary full" disabled={analyzing||pending} onClick={regenerate}><Icon name="sparkle" size={15}/>{analyzing?'Ollama 분석 중…':analysis?'초안 다시 생성':'영상 분석'}</button>{analysisError&&<p id="analysis-error" tabIndex={-1} role="alert" className="field-error">{analysisError}</p>}</section>
        {analysis&&<section className="detail-section">
          <div className="section-title"><h3>영상의 핵심 고민</h3><span className="badge blue">{analysis.scene_verified?(analysis.source_basis==='frame_ocr'?'화면 자막 발췌':'공개 자막 근거'):'제목·설명 분석'}</span></div>
          <p className="concern-box">{analysis.concern}</p>
          <div className="evidence-box"><div className="evidence-title"><Icon name="shield" size={14}/>분석 근거</div>
            {analysis.source_summary&&<p className="source-summary">제목·설명 · 인기 댓글 {analysis.source_summary.comments}개 · 자막 {analysis.source_summary.timed_passages}구간{analysis.source_summary.span&&` (${analysis.source_summary.span})`}</p>}
            {analysis.evidence.map((item,index)=><figure className="evidence-item" key={index}>
              <a className="evidence-source" href={item.url} target="_blank" rel="noreferrer">{item.label} <Icon name="external" size={12}/></a>
              <blockquote>{item.quote}</blockquote>
              {item.capture&&<img className="evidence-capture" src={`/api/screenshots/${encodeURIComponent(item.capture)}`} alt={`분석 근거 영상 화면: ${item.quote}`} width="1280" height="720" loading="lazy" decoding="async"/>}
            </figure>)}
            {!!analysis.warnings.length&&<details className="source-notes"><summary>수집 범위와 확인할 점</summary>{analysis.warnings.map(warning=><p key={warning}>{warning}</p>)}</details>}
          </div>

          <details className="analysis-metadata"><summary>더보기 · 영상 설명과 분석 정보</summary><div className="analysis-metadata-scroll" role="region" aria-label="영상 설명과 분석 정보" tabIndex={0}><p className="video-description">{selected.description}</p><p className="help-text">{analysis.model} · {date(analysis.created_at)}</p></div></details>
        </section>}
        <section className="detail-section"><div className="section-title"><h3>댓글 검토</h3></div><label className="field-label" htmlFor="draft">댓글</label><textarea id="draft" value={draft} rows={5} maxLength={120} onChange={event=>{setDraft(event.target.value);setApproved(false);setEdited(true);setDraftError('')}} onBlur={()=>setDraftError(validate(draft,health?.min_chars,health?.max_chars))} aria-invalid={!!draftError} aria-describedby="draft-error" disabled={analyzing||pending||blocked}/><div className="editor-foot"><strong>{[...draft.normalize('NFC').trim()].length}/120</strong></div><p id="draft-error" className="field-error">{draftError}</p>{localState.includes('제한')&&<p className="field-error">{localState}</p>}<button className="btn light" disabled={!draft||saving||pending||blocked} onClick={save}><Icon name="check" size={14}/>{saving?'저장 중…':'수정 저장'}</button></section>
        <section className="detail-section"><label className="field-label" htmlFor="profile">Chrome 프로필</label><div className="profile-line"><select id="profile" value={profile} onChange={event=>changeProfile(event.target.value)} disabled={pending||browserBusy}>{profiles.map(name=><option key={name}>{name}</option>)}</select><button className="btn light" disabled={browserBusy||pending} onClick={openBrowser}><Icon name="external" size={14}/>{browserBusy?'여는 중…':'전용 Chrome 열기'}</button></div><details><summary>더보기 · 로그인 상태 확인</summary><button className="btn light" disabled={browserBusy||pending} onClick={checkBrowser}>로그인 상태 확인</button>{browser&&<p role="status" className="help-text">{browser.profile!==profile?`${profile} Chrome을 먼저 열어 주세요.`:browser.signed_in?'로그인 확인됨':browser.needs_action}</p>}</details><label className="approval"><input type="checkbox" checked={approved} onChange={event=>setApproved(event.target.checked)} disabled={pending||blocked}/><span>이 댓글의 게시를 승인합니다.</span></label>{!selected.allowed&&<p className="field-error">허용 채널 또는 등록된 테스트 영상에만 게시할 수 있습니다.</p>}{blocked&&<p className="field-error">진행·게시·확인 불가 이력이 있어 재게시를 차단합니다.</p>}<button className="btn primary full post" disabled={!canPost} onClick={post}><Icon name="play" size={15}/>{posting?'작업 요청 중…':'댓글 달기'}</button></section>{job&&<section className="detail-section job-section" aria-label="게시 진행 상태"><strong role="status">{labels[job.status]??job.status}</strong>{job.error&&<p className="error-inline">{job.error}</p>}<div className="job-actions">{job.screenshot&&<a className="btn light" href={`/api/screenshots/${job.screenshot}`} target="_blank" rel="noreferrer">화면 캡처</a>}{job.comment_url&&<a className="btn light" href={job.comment_url} target="_blank" rel="noreferrer">댓글 보기 ↗</a>}</div></section>}
      </>}</div><div className="detail-footer"><span className={`status-dot ${health?.ollama==='ready'?'on':''}`}/>오늘 예약·게시 {activities?.quota.used??'–'} / {health?.daily_max??10}</div></aside></>}
    {path==='/activities'&&<main id="main-content" tabIndex={-1} className="wide-panel" aria-labelledby="page-title">
      <header className="heading"><h1 id="page-title">작업 이력</h1></header>
      <div className="history-toolbar">
        <div className="segmented" role="group" aria-label="이력 종류">{[['jobs','게시 작업'],['logs','활동 기록']].map(([kind,label])=><button key={kind} aria-pressed={historyKind===kind} onClick={()=>{setHistoryKind(kind as 'jobs'|'logs');setHistoryPage(0)}}>{label}</button>)}</div>
        <button className="btn danger" disabled={deletingHistory||historyLoading||!history?.total} onClick={()=>void deleteHistory()}><Icon name="trash" size={14}/>{historyKind==='jobs'?'게시 이력 비우기':'활동 기록 비우기'}</button>
      </div>

      {historyError?<div className="history-error"><p role="alert" className="field-error">{historyError}</p><button className="btn secondary" onClick={()=>setHistoryRevision(value=>value+1)}>다시 불러오기</button></div>:<>
        {historyLoading&&!history?<p role="status" className="help-text">이력을 불러오는 중…</p>:<div className="history-list" aria-busy={historyLoading}>
          {historyKind==='jobs'?history?.jobs.map(item=><article className="history-row" key={item.id}>
            <span className={`badge ${item.status==='success'?'success':item.status==='failed'||item.status==='uncertain'?'warn':'neutral'}`}>{labels[item.status]??item.status}</span>
            <div><strong>{item.title??item.video_id}</strong><p>{item.profile} · {item.text}</p>{item.error&&<p className="error-inline">{item.error}</p>}<div className="history-links">{item.screenshot&&<a href={`/api/screenshots/${item.screenshot}`} target="_blank" rel="noreferrer">화면 캡처 <Icon name="external" size={12}/></a>}{item.comment_url&&<a href={item.comment_url} target="_blank" rel="noreferrer">댓글 보기 <Icon name="external" size={12}/></a>}</div></div>
            <div className="history-meta"><time className="history-date" dateTime={item.created_at}>{date(item.created_at)}</time><button className="icon-button danger" aria-label={`${item.title??item.video_id} 게시 이력 삭제`} title="게시 이력 삭제" disabled={deletingHistory||!terminal.includes(item.status)} onClick={()=>void deleteHistory(item.id)}><Icon name="trash" size={16}/></button></div>
          </article>):history?.logs.map(log=><article className="history-row" key={log.id}>
            <span className="badge neutral">{labels[log.stage]??log.stage}</span><div><strong>{log.title??log.video_id??'일반 작업'}</strong><p>{labels[log.detail]??log.detail}</p></div>
            <div className="history-meta"><time className="history-date" dateTime={log.created_at}>{date(log.created_at)}</time><button className="icon-button danger" aria-label={`${log.id}번 활동 기록 삭제`} title="활동 기록 삭제" disabled={deletingHistory} onClick={()=>void deleteHistory(String(log.id))}><Icon name="trash" size={16}/></button></div>
          </article>)}
          {history&&history.total===0&&<div className="empty-state"><strong>{historyKind==='jobs'?'표시할 게시 작업이 없습니다.':'표시할 활동 기록이 없습니다.'}</strong><a className="btn secondary" href="/" onClick={event=>follow(event,'/')}>영상 탐색으로 이동</a></div>}
        </div>}
        {historyPageCount>1&&<nav className="pagination" aria-label="작업 이력 페이지">{historyPages.map(index=><button className="btn light" key={index} disabled={historyLoading} aria-label={`${index+1}페이지`} aria-current={index===historyPage?'page':undefined} onClick={()=>setHistoryPage(index)}>{index+1}</button>)}</nav>}
      </>}
    </main>}
    {path==='/settings'&&<main id="main-content" tabIndex={-1} className="wide-panel" aria-labelledby="page-title">
      <header className="heading"><h1 id="page-title">환경 설정</h1></header>
      <div className="settings-grid">
        <section className="setting-card profiles-card"><div className="setting-title"><Icon name="user"/><h2>Chrome 프로필</h2></div>
          <div className="profile-list" role="radiogroup" aria-label="댓글 게시 프로필">{profiles.map(name=><div className="profile-row" key={name}><label htmlFor={`setting-profile-${name}`}><input id={`setting-profile-${name}`} type="radio" name="posting-profile" value={name} checked={profile===name} disabled={pending||browserBusy} onChange={()=>changeProfile(name)}/><strong>{name}</strong></label><button className="btn light" disabled={browserBusy||pending} onClick={()=>void loginProfile(name)}>로그인·계정 관리 <Icon name="external" size={13}/></button></div>)}</div>
          {profiles.length<3&&<div className="profile-add">{['유튜브2','유튜브3'].filter(name=>!profiles.includes(name)).map(name=><button className="btn secondary" key={name} disabled={!!addingProfile} onClick={()=>void addProfile(name)}><Icon name="plus" size={14}/>{addingProfile===name?'추가 중…':`${name} 추가`}</button>)}</div>}

        </section>
        <section className="setting-card"><div className="setting-title"><Icon name={theme==='dark'?'moon':'sun'}/><h2>화면 테마</h2></div><div className="segmented theme-options" role="group" aria-label="화면 테마"><button aria-pressed={theme==='light'} onClick={()=>setTheme('light')}><Icon name="sun" size={16}/>라이트</button><button aria-pressed={theme==='dark'} onClick={()=>setTheme('dark')}><Icon name="moon" size={16}/>다크</button></div></section>
        <section className="setting-card"><div className="setting-title"><Icon name="copy"/><h2>임시 초안 · 7일 보관</h2></div><button className="btn light" onClick={clearLocal}>임시 초안 삭제</button></section>
      </div>
    </main>}
    {!routes[path]&&<main id="main-content" tabIndex={-1} className="wide-panel not-found" aria-labelledby="page-title"><span className="error-code">404</span><h1 id="page-title">페이지를 찾을 수 없습니다</h1><a className="btn primary" href="/" onClick={event=>follow(event,'/')}>영상 탐색으로 이동</a></main>}
    <footer className="app-footer"><a href="https://github.com/seo-gali/marketing-ai-agent" target="_blank" rel="noreferrer">© {new Date().getFullYear()} seo-gali/marketing-ai-agent</a></footer>
    {(error||notice)&&<div id="global-message" tabIndex={-1} role={error?'alert':'status'} className={`toast ${error?'toast-error':''} ${toastFading?'toast-fading':''}`}><span>{error||notice}</span>{!error&&historyUndo&&<button className="undo-button" onClick={()=>void restoreHistory()}>실행 취소</button>}{!error&&undo&&<button className="undo-button" onClick={()=>{setSearch(undo.search);setChannel(undo.channel);setSearchActive(undo.active);setUndo(null);success('이전 검색·필터로 돌아갔습니다.')}}>실행 취소</button>}<button aria-label="알림 닫기" onClick={closeToast}>×</button></div>}
    <dialog ref={analysisDialog} className="analysis-progress" aria-labelledby="analysis-progress-title" aria-describedby="analysis-progress-description" onCancel={event=>event.preventDefault()}>
      <div className="spinner" aria-hidden="true"/>
      <h2 id="analysis-progress-title">영상을 분석하고 있습니다</h2>
      <p id="analysis-progress-description" role="status">{analysisProgress??'영상 정보 확인 중'}</p>
      <p className="analysis-elapsed">{Math.floor(analysisElapsed/60)}분 {analysisElapsed%60}초 경과</p>
      <div className="analysis-progress-track" role="progressbar" aria-label="영상 분석 진행 중"><span/></div>
      <button className="btn light" disabled={cancelling} onClick={()=>void cancelAnalysis()}>{cancelling?'취소 중…':'취소'}</button>
    </dialog>
  </div>
}
