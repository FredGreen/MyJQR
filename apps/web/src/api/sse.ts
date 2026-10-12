/** SSE 客户端：fetch 流式解析 event/data 帧（支持 token 头，EventSource 不支持） */
export interface SseHandlers {
  onEvent: (event: string, data: any) => void
  onError?: (err: unknown) => void
  onDone?: () => void
}

export async function openSse(url: string, h: SseHandlers) {
  const token = localStorage.getItem('access_token')
  const resp = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok || !resp.body) throw new Error(`SSE HTTP ${resp.status}`)
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  let finished = false

  while (!finished) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      let event = 'message'
      const dataLines: string[] = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      if (!dataLines.length) continue
      let data: any = dataLines.join('\n')
      try { data = JSON.parse(data) } catch { /* 纯文本 */ }
      h.onEvent(event, data)
      if (event === 'done' || event === 'error') {
        finished = true
        h.onDone?.()
        break
      }
    }
  }
  reader.cancel().catch(() => {})
}
