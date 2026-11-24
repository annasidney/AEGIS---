import { Layers, MapPin, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { usePoll } from '../hooks/usePoll'
import { api } from '../lib/api'
import type { VisualMemoryItem } from '../types'
import Drawer from './Drawer'

export default function VisualMemoryDrawer({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<VisualMemoryItem[]>([])
  const load = async () => { try { setItems((await api.visualMemories()).visual_memories) } catch { /* offline */ } }
  usePoll(load, 4000)

  const title = (m: VisualMemoryItem, idx: number) => {
    if (m.object !== 'person') return m.object.replace(/\b\w/g, (c) => c.toUpperCase())
    return 'Person'
  }

  return (
    <Drawer
      title="Environmental Visual Memory"
      icon={Layers}
      onClose={onClose}
      footer={
        <div className="flex items-center justify-between text-sm font-semibold">
          <button onClick={async () => { await api.clearVisualMemories(); load() }} className="flex items-center gap-2 text-red-400 hover:text-red-300">
            <Trash2 size={16} /> Clear Visual Memory
          </button>
          <button onClick={load} className="flex items-center gap-2 text-cyan-300 hover:text-cyan-200">
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      }
    >
      <p className="muted mb-5 text-[13.5px] leading-relaxed">
        AEGIS maintains semantic short-term spatial memory of surroundings observed by the camera without storing raw video.
      </p>
      {items.length === 0 ? (
        <p className="muted rounded-xl border border-dashed border-edge p-6 text-center text-sm">
          Nothing remembered yet. Turn the camera on and show AEGIS your surroundings.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((m, i) => (
            <li key={m.id} className="card animate-fadeUp p-4">
              <div className="flex items-center justify-between">
                <span className="text-[15px] font-bold text-white">{title(m, i)}</span>
                <span className="font-mono text-[11px] font-bold text-emerald-400">{Math.round(m.confidence * 100)}% conf</span>
              </div>
              <p className="mt-2 flex items-start gap-2 text-sm text-slate-100">
                <MapPin size={15} className="mt-0.5 shrink-0 text-cyan-300" />
                {m.location_context}{m.spatial_relationship && m.spatial_relationship !== 'in view' ? ` (${m.spatial_relationship})` : ''}
              </p>
              <div className="muted mt-3 flex justify-between border-t border-edge pt-2 font-mono text-[11px]">
                <span>Room: {m.room}</span>
                <span>Last seen: {m.last_seen}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Drawer>
  )
}
