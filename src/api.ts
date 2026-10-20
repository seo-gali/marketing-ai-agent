export interface Video { id: string; channel_id: string; title: string; channel: string; published_at: string; thumbnail: string; description: string; allowed: boolean }
export interface Health { status: string; ollama: string; model: string; youtube: string; daily_max: number; min_chars: number; max_chars: number; channels: Record<string,string>; test_video_ids: string[] }

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch('/api' + path, { method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `입력값을 확인하세요 (${response.status})`)
  return data
}
