import { useEffect, useRef } from 'react'

/** Run `fn` immediately and then every `ms` while `enabled`. */
export function usePoll(fn: () => void | Promise<void>, ms: number, enabled = true) {
  const ref = useRef(fn)
  ref.current = fn
  useEffect(() => {
    if (!enabled) return
    ref.current()
    const t = setInterval(() => ref.current(), ms)
    return () => clearInterval(t)
  }, [ms, enabled])
}
