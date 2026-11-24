import { Bell } from 'lucide-react'

export interface Toast { id: number; text: string; kind: 'info' | 'reminder' }

export default function Toasts({ items }: { items: Toast[] }) {
  return (
    <div className="pointer-events-none fixed left-1/2 top-4 z-50 flex -translate-x-1/2 flex-col gap-2" aria-live="assertive">
      {items.map((t) => (
        <div key={t.id} className={`glass animate-fadeUp flex items-center gap-3 rounded-xl px-5 py-3 text-sm font-medium text-white shadow-xl ${t.kind === 'reminder' ? '!border-amber-400/60' : ''}`}>
          {t.kind === 'reminder' && <Bell size={18} className="text-amber-300" />} {t.text}
        </div>
      ))}
    </div>
  )
}
