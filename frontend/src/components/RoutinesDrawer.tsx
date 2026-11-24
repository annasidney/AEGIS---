import { Check, Sparkles, Workflow } from 'lucide-react'
import { useState } from 'react'
import { usePoll } from '../hooks/usePoll'
import { api } from '../lib/api'
import type { RoutineItem, RoutineSuggestion } from '../types'
import Drawer from './Drawer'

export default function RoutinesDrawer({ onClose, onRun }: { onClose: () => void; onRun: (cmd: string) => void }) {
  const [routines, setRoutines] = useState<RoutineItem[]>([])
  const [suggestions, setSuggestions] = useState<RoutineSuggestion[]>([])
  const load = async () => {
    try { const r = await api.routines(); setRoutines(r.routines); setSuggestions(r.suggestions) } catch { /* offline */ }
  }
  usePoll(load, 5000)

  return (
    <Drawer
      title="Learned Routines (SIH)"
      icon={Workflow}
      accent="#a78bfa"
      onClose={onClose}
      footer={
        <button onClick={async () => { await api.clearRoutines(); load() }} className="text-sm font-semibold text-red-400 hover:text-red-300">
          Forget learned habits
        </button>
      }
    >
      <h3 className="mb-3 flex items-center gap-2 font-mono text-[13px] font-bold uppercase tracking-wide text-amber-300">
        <Sparkles size={15} /> Proactive habit suggestions
      </h3>
      {suggestions.length === 0 ? (
        <p className="muted mb-6 rounded-xl border border-dashed border-edge p-4 text-sm">
          No suggestions right now. AEGIS suggests an app once you've opened it at least 3 times around the same time of day.
        </p>
      ) : (
        <div className="mb-7 flex flex-col gap-3">
          {suggestions.map((s) => (
            <div key={s.id} className="animate-fadeUp rounded-xl border border-amber-700/40 bg-gradient-to-br from-amber-900/30 to-orange-950/30 p-4">
              <p className="text-[14.5px] leading-snug text-slate-100">{s.message}</p>
              <button
                onClick={() => onRun(`open ${s.target}`)}
                className="mt-3 flex items-center gap-2 rounded-lg border border-amber-500/50 bg-amber-500/15 px-3 py-1.5 text-sm font-bold text-amber-200 hover:bg-amber-500/25"
              >
                <Check size={15} /> Yes, open {s.target}
              </button>
            </div>
          ))}
        </div>
      )}

      <h3 className="muted mb-3 font-mono text-[12px] font-bold uppercase tracking-wide">Tracked frequency</h3>
      {routines.length === 0 ? (
        <p className="muted text-sm">Open apps and sites through AEGIS and your habits will appear here.</p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {routines.map((r) => (
            <li key={r.id} className="card flex items-center justify-between px-4 py-3">
              <span className="text-[15px] font-semibold text-white">
                {r.target} <span className="muted font-normal">({r.time_of_day})</span>
              </span>
              <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-0.5 font-mono text-xs font-bold text-cyan-300">{r.frequency}x</span>
            </li>
          ))}
        </ul>
      )}
    </Drawer>
  )
}
