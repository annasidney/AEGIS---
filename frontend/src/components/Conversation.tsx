import { Terminal } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { ChatMessage, CoreState } from '../types'
import { formatLatency } from './Header'

export default function Conversation({ messages, state }: { messages: ChatMessage[]; state: CoreState }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages.length, state])

  if (!messages.length) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-edge bg-white/[.03]">
          <Terminal size={24} className="text-cyan-300" />
        </div>
        <p className="font-semibold text-slate-200">Ready for your input.</p>
        <p className="muted text-sm">
          Type a request, click the Core, or hold <span className="font-semibold text-cyan-300">Spacebar</span> for voice.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 px-2 py-2" role="log" aria-live="polite">
      {messages.map((m) =>
        m.role === 'system' ? (
          <div key={m.id} className="label-mono muted animate-fadeUp self-center rounded-full border border-edge px-3 py-1 normal-case">{m.text}</div>
        ) : (
          <div key={m.id} className={`animate-fadeUp flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-[15px] leading-relaxed ${
                m.role === 'user'
                  ? 'border border-cyan-400/30 bg-gradient-to-br from-cyan-500/20 to-blue-600/25 text-white'
                  : 'glass text-slate-100'
              }`}
            >
              {m.text}
            </div>
            {m.role === 'aegis' && (m.tool || m.latency != null) && (
              <div className="label-mono muted mt-1 flex flex-wrap items-center gap-2 pl-1 normal-case">
                {m.tool && <span className="rounded bg-white/5 px-1.5 py-0.5 text-cyan-300">{m.tool}</span>}
                {m.route && <span>{m.route === 'router' ? 'deterministic router' : 'Gemini ReAct'}</span>}
                {m.latency != null && <span>{formatLatency(m.latency)}</span>}
                {m.steps && m.steps.length > 0 && <span>→ {m.steps.map((s) => s.tool).join(' → ')}</span>}
              </div>
            )}
          </div>
        ),
      )}
      {state === 'THINKING' || state === 'EXECUTING' ? (
        <div className="glass flex w-fit items-center gap-1.5 rounded-2xl px-4 py-3" aria-label="AEGIS is working">
          {[0, 1, 2].map((i) => <span key={i} className="h-2 w-2 animate-dot rounded-full bg-cyan-300" style={{ animationDelay: `${i * 0.18}s` }} />)}
        </div>
      ) : null}
      <div ref={end} />
    </div>
  )
}
