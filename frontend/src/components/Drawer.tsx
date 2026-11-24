import type { LucideIcon } from 'lucide-react'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

interface Props { title: string; icon: LucideIcon; onClose: () => void; children: ReactNode; footer?: ReactNode; accent?: string }

/** Right-hand slide-in panel shared by Visual Memory, Routines, Reminders, Memory, Accessibility, Settings. */
export default function Drawer({ title, icon: Icon, onClose, children, footer, accent = '#22d3ee' }: Props) {
  return (
    <aside
      role="dialog"
      aria-label={title}
      className="absolute bottom-0 right-0 top-0 z-30 flex w-[min(480px,100%)] animate-slideIn flex-col border-l border-edge shadow-[-24px_0_60px_rgba(0,0,0,.5)]"
      style={{ background: 'linear-gradient(180deg, #0e1832, #070c1c)' }}
    >
      <div className="flex items-center justify-between px-6 pb-4 pt-6">
        <h2 className="flex items-center gap-3 text-[1.35rem] font-bold text-white">
          <Icon size={22} style={{ color: accent }} /> {title}
        </h2>
        <button aria-label="Close panel" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white">
          <X size={20} />
        </button>
      </div>
      <div className="mx-6 border-t border-edge" />
      <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
      {footer && <div className="border-t border-edge px-6 py-4">{footer}</div>}
    </aside>
  )
}
