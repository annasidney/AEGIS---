import { Bell, Plus, X } from 'lucide-react'
import { useState } from 'react'
import { usePoll } from '../hooks/usePoll'
import { api } from '../lib/api'
import type { ReminderItem } from '../types'
import Drawer from './Drawer'

export default function RemindersDrawer({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<ReminderItem[]>([])
  const [task, setTask] = useState('')
  const [when, setWhen] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const load = async () => { try { setItems((await api.reminders()).reminders ?? []) } catch { /* offline */ } }
  usePoll(load, 5000)

  const create = async () => {
    if (!task.trim() || !when.trim()) { setMsg({ ok: false, text: 'Enter both a task and a time.' }); return }
    try {
      const r = await api.createReminder(task.trim(), when.trim())
      const ok = r.status === 'created'
      setMsg({ ok, text: r.message })
      if (ok) { setTask(''); setWhen(''); load() }
    } catch (e: any) { setMsg({ ok: false, text: e.message }) }
  }

  const input = 'w-full rounded-xl border border-edge bg-black/30 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400/50 focus:outline-none'

  return (
    <Drawer
      title="User-Defined Reminders"
      icon={Bell}
      accent="#fbbf24"
      onClose={onClose}
      footer={<p className="muted text-center text-[13px]">Reminders are strictly user-defined &amp; synced to real Windows clock.</p>}
    >
      <div className="card p-5">
        <h3 className="mb-3 font-mono text-[12px] font-bold uppercase tracking-wide text-slate-200">Set new reminder</h3>
        <div className="flex flex-col gap-3">
          <input className={input} aria-label="Reminder task" value={task} onChange={(e) => setTask(e.target.value)} placeholder="Reminder task (e.g. Submit assignment)" />
          <input className={input} aria-label="Reminder time" value={when} onChange={(e) => setWhen(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && create()} placeholder="When? (e.g. tomorrow at 5 PM, in 10 mins)" />
          <button onClick={create} className="flex items-center justify-center gap-2 rounded-xl bg-cyan-500 py-3 text-sm font-bold text-[#04101f] hover:bg-cyan-400">
            <Plus size={17} /> Create Reminder
          </button>
          {msg && <p role="status" className={`text-[13px] ${msg.ok ? 'text-emerald-400' : 'text-amber-300'}`}>{msg.text}</p>}
        </div>
      </div>

      {items.length === 0 ? (
        <p className="muted mx-auto mt-16 max-w-xs text-center text-sm leading-relaxed">
          No active reminders. Speak naturally: "Remind me tomorrow at 5 PM to submit assignment"
        </p>
      ) : (
        <ul className="mt-5 flex flex-col gap-3">
          {items.map((r) => (
            <li key={r.id} className="card animate-fadeUp flex items-start justify-between gap-3 p-4">
              <div>
                <p className="font-semibold text-white">{r.text}</p>
                <p className="mt-1 font-mono text-[12px] text-amber-300">{r.time}</p>
              </div>
              <button aria-label={`Cancel reminder ${r.text}`} onClick={async () => { await api.deleteReminder(r.id); load() }} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-red-300">
                <X size={17} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Drawer>
  )
}
