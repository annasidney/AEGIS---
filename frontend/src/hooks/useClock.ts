import { useEffect, useState } from 'react'

export function useClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t) }, [])
  return {
    time: now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }),
    date: now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
  }
}
