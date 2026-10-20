export interface Video { id: string; channel_id: string; title: string; channel: string; published_at: string; thumbnail: string; description: string; allowed: boolean }
export interface Health { status: string; ollama: string; model: string; youtube: string; daily_max: number; min_chars: number; max_chars: number; channels: Record<string,string>; test_video_ids: string[] }
export interface Analysis { concern: string; comment: string; evidence: {source_id: string; quote: string; label: string; url: string}[]; warnings: string[]; scene_verified: boolean; model: string; created_at: string }
export interface Job { id: string; video_id: string; title?: string; profile: string; text: string; status: string; error: string | null; screenshot: string | null; comment_url: string | null; created_at: string }
export interface Activities { jobs: Job[]; logs: {id:number; video_id: string; stage: string; detail: string; created_at: string}[]; quota: {used:number; max:number; day:string}; blocked_video_ids: string[] }
export const labels: Record<string,string> = {queued:'게시 대기',opening:'프로필 여는 중',navigating:'영상 여는 중',typing:'입력 중',submitting:'게시 중',verifying:'댓글 확인 중',success:'게시 완료',failed:'실패',uncertain:'확인 불가',analysis_complete:'분석 완료',analysis_failed:'분석 실패',draft_saved:'초안 저장',rejected:'게시 차단'}
export interface BrowserStatus { open: boolean; signed_in: boolean; needs_action: string; busy: boolean; profile: string }

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch('/api' + path, { method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  const data = await response.json().catch(() => {throw new Error(`서버 응답을 읽을 수 없습니다 (${response.status})`)})
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `입력값을 확인하세요 (${response.status})`)
  return data
}
