import { Mic, SendHorizontal } from 'lucide-react'
import { useState } from 'react'
import type { CoreState } from '../types'

interface Props {
  state: CoreState
  listening: boolean
  micError: string | null
  onSend: (text: string) => void
  onTalkStart: () => void
  onTalkEnd: () => void
}

export default function CommandBar({ state, listening, micError, onSend, onTalkStart, onTalkEnd }: Props) {
  const [text, setText] = useState('')
  const busy = state === 'THINKING' || state === 'EXECUTING'

  const submit = () => {
    const t = text.trim()
    if (!t) return
    onSend(t)
    setText('')
  }

  return (
    <div className="mx-auto w-full max-w-[1120px] px-6 pb-3">
      <div className="mb-3 flex items-center justify-center gap-[14px]" aria-hidden>
        {Array.from({ length: 12 }).map((_, i) => (
          <span
            key={i}
            className={`h-[6px] w-[6px] rounded-full bg-slate-400/60 ${state !== 'IDLE' ? 'animate-dot !bg-cyan-300' : ''}`}
            style={{ animationDelay: `${i * 0.09}s` }}
          />
        ))}
      </div>
      <div className="glass flex items-center gap-3 rounded-[22px] p-2">
        <button
          onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); onTalkStart() }}
          onPointerUp={onTalkEnd}
          onPointerCancel={onTalkEnd}
          aria-pressed={listening}
          className={`flex shrink-0 select-none items-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold tracking-wide text-white shadow-[0_0_24px_rgba(34,211,238,.25)] transition ${
            listening ? 'bg-gradient-to-r from-red-500 to-rose-600' : 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:brightness-110'
          }`}
        >
          <Mic size={18} /> {listening ? 'LISTENING… RELEASE' : 'PUSH TO TALK'}
        </button>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Ask AEGIS anything or give a command (e.g. 'What do you see?', 'Where is my phone?')..."
          aria-label="Command input"
          className="min-w-0 flex-1 rounded-2xl border border-edge bg-black/30 px-5 py-3 text-[15px] text-white placeholder:text-slate-500 focus:border-cyan-400/50 focus:outline-none"
        />
        <button
          onClick={submit}
          disabled={!text.trim() || busy}
          aria-label="Send"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-cyan-500/15 text-cyan-300 transition enabled:hover:bg-cyan-500/30 disabled:opacity-40"
        >
          <SendHorizontal size={20} />
        </button>
      </div>
      <div className="label-mono muted mt-2 flex justify-between px-3 text-[10px] normal-case">
        <span>{micError ?? 'Hold Spacebar for Voice Core'}</span>
        <span>Press Enter to send</span>
      </div>
    </div>
  )
}
