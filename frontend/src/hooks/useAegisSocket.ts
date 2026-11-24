import { useCallback, useEffect, useRef, useState } from 'react'

/** WebSocket event bus to the FastAPI gateway with automatic reconnect. */
export function useAegisSocket(onMessage: (msg: any) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const handler = useRef(onMessage)
  handler.current = onMessage
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let closed = false
    let timer: number | undefined
    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws`)
      wsRef.current = ws
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!closed) timer = window.setTimeout(connect, 1500)
      }
      ws.onmessage = (e) => { try { handler.current(JSON.parse(e.data)) } catch { /* ignore malformed */ } }
    }
    connect()
    return () => { closed = true; window.clearTimeout(timer); wsRef.current?.close() }
  }, [])

  const send = useCallback((obj: unknown): boolean => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify(obj)); return true }
    return false
  }, [])

  return { connected, send }
}
