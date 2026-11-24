import { Plus, Sparkles, X } from 'lucide-react'
import { useState } from 'react'
import { usePoll } from '../hooks/usePoll'
import { api } from '../lib/api'
import type { MemoryEntry } from '../types'
import Drawer from './Drawer'

export default function MemoryDrawer({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<MemoryEntry[]>([])
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const load = async () => { try { setItems((await api.memories()).memories) } catch { /* offline */ } }
  usePoll(load, 8000)

  const add = async () => {
    if (!key.trim() || !value.trim()) return
    await api.saveMemory(key.trim(), value.trim())
    setKey(''); setValue(''); load()
  }
  const input = 'w-full rounded-xl border border-edge bg-black/30 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400/50 focus:outline-none'

  return (
    <Drawer title="Personal Memory" icon={Sparkles} onClose={onClose}>
      <p className="muted mb-5 text-[13.5px] leading-relaxed">
        Facts and preferences AEGIS should always remember about you. They're included as context whenever the reasoning engine answers.
      </p>
      <div className="card flex flex-col gap-3 p-5">
        <input className={input} aria-label="Memory name" value={key} onChange={(e) => setKey(e.target.value)} placeholder="What (e.g. favourite_drink)" />
        <input className={input} aria-label="Memory value" value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} placeholder="Value (e.g. filter coffee)" />
        <button onClick={add} className="flex items-center justify-center gap-2 rounded-xl bg-cyan-500 py-3 text-sm font-bold text-[#04101f] hover:bg-cyan-400">
          <Plus size={17} /> Remember this
        </button>
      </div>
      <ul className="mt-5 flex flex-col gap-3">
        {items.map((m) => (
          <li key={m.id} className="card flex items-start justify-between gap-3 p-4">
            <div>
              <p className="font-mono text-[12px] font-bold text-cyan-300">{m.key}</p>
              <p className="mt-1 text-sm text-slate-100">{m.value}</p>
            </div>
            <button aria-label={`Forget ${m.key}`} onClick={async () => { await api.deleteMemory(m.id); load() }} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-red-300"><X size={17} /></button>
          </li>
        ))}
        {items.length === 0 && <li className="muted text-center text-sm">Nothing saved yet.</li>}
      </ul>
    </Drawer>
  )
}
