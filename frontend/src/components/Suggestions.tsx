import { Clock, FileCode2, LogOut, Music, Navigation, Plane, ScanEye, Search, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

const ITEMS: { label: string; cmd: string; icon: LucideIcon; color: string }[] = [
  { label: 'Play Believer on YouTube', cmd: 'play Believer on YouTube', icon: Music, color: '#f43f5e' },
  { label: 'Book Flight Ticket', cmd: 'book a flight ticket', icon: Plane, color: '#38bdf8' },
  { label: 'Explain Quantum Computing', cmd: 'explain quantum computing', icon: Sparkles, color: '#a78bfa' },
  { label: 'Time & Date', cmd: 'what time is it', icon: Clock, color: '#60a5fa' },
  { label: 'Scan Surroundings', cmd: 'scan surroundings', icon: ScanEye, color: '#34d399' },
  { label: 'Where is my phone?', cmd: 'where is my phone', icon: Search, color: '#c084fc' },
  { label: 'Directions to Airport', cmd: 'directions to airport', icon: Navigation, color: '#818cf8' },
  { label: 'Python Calculator', cmd: 'create a python calculator', icon: FileCode2, color: '#4ade80' },
  { label: 'Goodbye', cmd: 'goodbye', icon: LogOut, color: '#f43f5e' },
]

export default function Suggestions({ onPick }: { onPick: (cmd: string) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const [thumb, setThumb] = useState({ left: 0, width: 100 })

  const update = () => {
    const el = ref.current
    if (!el) return
    const width = Math.min(100, (el.clientWidth / el.scrollWidth) * 100)
    const max = el.scrollWidth - el.clientWidth
    setThumb({ width, left: max > 0 ? (el.scrollLeft / max) * (100 - width) : 0 })
  }
  useEffect(() => { update(); window.addEventListener('resize', update); return () => window.removeEventListener('resize', update) }, [])

  return (
    <section aria-label="Suggestions" className="px-6">
      <div className="flex items-center gap-3">
        <span className="label-mono muted shrink-0">Suggestions:</span>
        <div ref={ref} onScroll={update} className="no-scrollbar flex gap-3 overflow-x-auto py-1">
          {ITEMS.map(({ label, cmd, icon: Icon, color }) => (
            <button
              key={label}
              onClick={() => onPick(cmd)}
              className="flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2 text-[13.5px] font-medium transition hover:-translate-y-0.5"
              style={{ color, borderColor: `${color}55`, background: `${color}14` }}
            >
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-2 h-[3px] w-full rounded bg-white/5" aria-hidden>
        <div className="h-full rounded bg-gradient-to-r from-blue-500 to-cyan-400 transition-all" style={{ width: `${thumb.width}%`, marginLeft: `${thumb.left}%` }} />
      </div>
    </section>
  )
}
