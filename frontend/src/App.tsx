import { FormEvent, useEffect, useRef, useState } from 'react'

type Role = 'user' | 'assistant' | 'system'
type ChatMessage = { id: string; role: Role; content: string }
type SseFrame = {
  type: string
  content?: string
  role?: string
  value?: unknown
  name?: string
}

function parseSseChunk(buffer: string): { frames: SseFrame[]; rest: string } {
  const parts = buffer.split('\n\n')
  const rest = parts.pop() ?? ''
  const frames: SseFrame[] = []
  for (const part of parts) {
    const line = part.split('\n').find((l) => l.startsWith('data: '))
    if (!line) continue
    try {
      frames.push(JSON.parse(line.slice(6)))
    } catch {
      /* ignore malformed frames */
    }
  }
  return { frames, rest }
}

export default function App() {
  const [graphId, setGraphId] = useState('hello')
  const [graphs, setGraphs] = useState<string[]>(['hello'])
  const [threadId, setThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [interrupt, setInterrupt] = useState<unknown>(null)
  const [status, setStatus] = useState('idle')
  const assistantRef = useRef('')

  useEffect(() => {
    fetch('/graphs')
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data.graphs) && data.graphs.length) {
          setGraphs(data.graphs)
          setGraphId(data.graphs[0])
        }
      })
      .catch(() => undefined)
  }, [])

  async function ensureThread(nextGraph = graphId): Promise<string> {
    if (threadId) return threadId
    const res = await fetch('/threads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ graph_id: nextGraph }),
    })
    if (!res.ok) throw new Error('create thread failed')
    const data = await res.json()
    setThreadId(data.thread_id)
    return data.thread_id as string
  }

  async function stream(body: Record<string, unknown>) {
    setBusy(true)
    setStatus('streaming')
    assistantRef.current = ''
    try {
      const res = await fetch('/runs/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok || !res.body) throw new Error(`stream ${res.status}`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parsed = parseSseChunk(buffer)
        buffer = parsed.rest
        for (const frame of parsed.frames) applyFrame(frame)
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'system', content: String(err) },
      ])
      setStatus('error')
    } finally {
      setBusy(false)
      setStatus((s) => (s === 'error' ? s : 'idle'))
    }
  }

  function applyFrame(frame: SseFrame) {
    if (frame.type === 'token' && frame.content) {
      assistantRef.current += frame.content
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.role === 'assistant' && last.id === 'streaming') {
          return [...prev.slice(0, -1), { ...last, content: assistantRef.current }]
        }
        return [...prev, { id: 'streaming', role: 'assistant', content: assistantRef.current }]
      })
      return
    }
    if (frame.type === 'message' && frame.content) {
      assistantRef.current = frame.content
      setMessages((prev) => {
        const withoutStream = prev.filter((m) => m.id !== 'streaming')
        return [
          ...withoutStream,
          { id: crypto.randomUUID(), role: 'assistant', content: frame.content ?? '' },
        ]
      })
      return
    }
    if (frame.type === 'tool') {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'system',
          content: `tool ${frame.name ?? ''}: ${frame.content ?? ''}`,
        },
      ])
      return
    }
    if (frame.type === 'interrupt') {
      setInterrupt(frame.value)
      setStatus('interrupt')
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'system',
          content: `等待确认: ${JSON.stringify(frame.value)}`,
        },
      ])
      return
    }
    if (frame.type === 'error') {
      setStatus('error')
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'system', content: frame.content ?? 'error' },
      ])
    }
    if (frame.type === 'done') {
      setMessages((prev) =>
        prev.map((m) => (m.id === 'streaming' ? { ...m, id: crypto.randomUUID() } : m)),
      )
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setInterrupt(null)
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: text }])
    const tid = await ensureThread()
    await stream({ graph_id: graphId, thread_id: tid, message: text })
  }

  async function resume(decision: string) {
    if (!threadId) return
    setInterrupt(null)
    await stream({ graph_id: graphId, thread_id: threadId, resume: decision })
  }

  async function resetThread(nextGraph: string) {
    setGraphId(nextGraph)
    setThreadId(null)
    setMessages([])
    setInterrupt(null)
  }

  return (
    <div className="app">
      <header>
        <h1>lg agent</h1>
        <select value={graphId} disabled={busy} onChange={(e) => resetThread(e.target.value)}>
          {graphs.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </header>
      <div className="meta">thread: {threadId ?? '(new)'} · {status}</div>
      <div className="messages">
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
      </div>
      {interrupt != null && (
        <div className="interrupt">
          <div>Human-in-the-loop</div>
          <pre>{JSON.stringify(interrupt, null, 2)}</pre>
          <div>
            <button type="button" onClick={() => resume('approve')} disabled={busy}>
              approve
            </button>{' '}
            <button type="button" onClick={() => resume('reject')} disabled={busy}>
              reject
            </button>
          </div>
        </div>
      )}
      <form onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="发一条消息，或让 agent 执行敏感操作以触发 interrupt"
          disabled={busy}
        />
        <button type="submit" disabled={busy}>
          发送
        </button>
      </form>
    </div>
  )
}
