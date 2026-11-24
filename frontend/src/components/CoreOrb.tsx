import { Sparkles } from 'lucide-react'
import type { CoreState } from '../types'

const LABEL: Record<CoreState, string> = {
  IDLE: 'Mindful & Attuned', LISTENING: 'Listening…', THINKING: 'Reasoning…', EXECUTING: 'Executing task…', SPEAKING: 'Speaking…',
}
const GLOW: Record<CoreState, string> = {
  IDLE: 'rgba(99,102,241,.38)', LISTENING: 'rgba(34,211,238,.65)', THINKING: 'rgba(168,85,247,.6)',
  EXECUTING: 'rgba(251,191,36,.5)', SPEAKING: 'rgba(52,211,153,.55)',
}

export default function CoreOrb({ state, onClick, compact = false }: { state: CoreState; onClick: () => void; compact?: boolean }) {
  const size = compact ? 150 : 220
  return (
    <div className="flex flex-col items-center gap-4">
      <button
        onClick={onClick}
        aria-label={state === 'LISTENING' ? 'Stop listening' : 'Tap to talk to AEGIS'}
        style={{ width: size, height: size }}
        className="relative rounded-full transition-transform duration-300 hover:scale-[1.02] active:scale-95"
      >
        <span className="orb-ring absolute inset-0 rounded-full" style={{ animationDuration: state === 'IDLE' ? '9s' : '2.4s' }} />
        <span
          className="orb-glow absolute inset-[12px] flex items-center justify-center rounded-full bg-[#040a1a]"
          style={{ ['--glow' as string]: GLOW[state] }}
        >
          <Sparkles size={compact ? 44 : 64} strokeWidth={1.5} className={`text-cyan-300 drop-shadow-[0_0_14px_rgba(34,211,238,.9)] ${state === 'THINKING' ? 'animate-pulse' : ''}`} />
        </span>
        {state === 'LISTENING' && <span className="absolute inset-0 animate-ping rounded-full border-2 border-cyan-300/50" />}
      </button>
      <div
        role="status"
        aria-live="polite"
        className="label-mono flex items-center gap-2 rounded-full border border-edge bg-white/[.03] px-4 py-2 text-[11px] normal-case tracking-normal text-slate-200"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-slate-200" /> {LABEL[state]}
      </div>
    </div>
  )
}
