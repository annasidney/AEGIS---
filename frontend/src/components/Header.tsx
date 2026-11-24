import { Bell, Camera, Layers, Settings, SlidersHorizontal, Sparkles, Workflow } from 'lucide-react'
import { useClock } from '../hooks/useClock'
import type { StatusInfo, User } from '../types'

export type Panel = 'visual' | 'routines' | 'reminders' | 'memory' | 'access' | 'settings'

interface Props {
  connected: boolean
  status: StatusInfo | null
  user: User | null
  cameraActive: boolean
  panel: Panel | null
  onToggleCamera: () => void
  onPanel: (p: Panel) => void
}

export const formatLatency = (ms: number | null | undefined) => (ms == null ? '<1ms' : ms < 1 ? '<1ms' : `${ms.toFixed(ms < 10 ? 1 : 0)}ms`)

export default function Header({ connected, status, user, cameraActive, panel, onToggleCamera, onPanel }: Props) {
  const { time, date } = useClock()
  const engine = status?.vision_engine === 'yolox' ? 'YOLOX-tiny +' : 'YOLOv5m +'
  const reasoner = status?.has_api_key ? 'Gemini 2.5 Vision' : 'Spatial Memory'
  const [t, ...ampm] = time.split(' ')

  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-3 border-b border-edge px-6 py-4">
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-500 shadow-[0_0_24px_rgba(59,130,246,.45)]">
            <Sparkles size={24} className="text-white" />
          </div>
          <span
            title={connected ? 'Connected to AEGIS engine' : 'Reconnecting…'}
            className={`absolute -bottom-1 -right-1 h-3.5 w-3.5 rounded-full border-2 border-[#03060f] ${connected ? 'bg-emerald-400' : 'animate-pulse bg-red-500'}`}
          />
        </div>
        <div className="max-w-[260px]">
          <div className="flex items-center gap-2">
            <span className="text-xl font-extrabold tracking-wide text-white">AEGIS</span>
            <span className="label-mono rounded border border-cyan-400/50 bg-cyan-400/10 px-1.5 py-0.5 text-cyan-300">SIH26204</span>
          </div>
          <p className="muted text-[12.5px] leading-snug">Assisted Executive Guidance and Intelligence System</p>
        </div>
      </div>

      <div className="glass hidden items-center gap-5 rounded-xl px-4 py-2 font-mono text-[11px] lg:flex">
        <Stat label="LATENCY" value={formatLatency(status?.router_latency_ms)} dot />
        <Stat label={engine} value={reasoner} />
        <Stat label="SECURE" value="VAULT" />
      </div>

      <div className="glass hidden items-center gap-3 rounded-xl px-4 py-2 xl:flex">
        <span className="h-2 w-2 rounded-full bg-cyan-400" />
        <div className="font-mono text-[15px] font-bold leading-tight text-white" aria-label="Current time">
          {t}<br />{ampm.join(' ').toLowerCase()}
        </div>
        <div className="muted font-mono text-[11px]">{date}</div>
      </div>

      <button
        onClick={() => onPanel('settings')}
        className="glass flex items-center gap-3 rounded-xl px-3 py-2 text-left hover:border-cyan-400/40"
        aria-label="Open profile settings"
      >
        {user?.picture ? (
          <img src={user.picture} alt="" className="h-8 w-8 rounded-full" referrerPolicy="no-referrer" />
        ) : (
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 text-sm font-bold text-white">
            {user?.initial ?? 'G'}
          </span>
        )}
        <span>
          <span className="block text-sm font-bold leading-tight text-white">{user?.name ?? 'Guest'}</span>
          <span className="label-mono block text-[9px] text-cyan-300">{user?.role || (user ? 'AEGIS USER' : 'LOCAL SESSION')}</span>
        </span>
      </button>

      <nav className="ml-auto flex flex-wrap items-center gap-2" aria-label="Workspace tools">
        <button className="btn-hdr !px-3" data-active={panel === 'memory'} onClick={() => onPanel('memory')} aria-label="Personal memory" title="Personal memory">
          <Sparkles size={18} className="text-cyan-300" />
        </button>
        <button
          onClick={onToggleCamera}
          aria-pressed={cameraActive}
          className={`btn-hdr ${cameraActive ? '!border-red-500/60 !bg-red-950/50 !text-red-200' : ''}`}
        >
          <Camera size={17} />
          {cameraActive ? <span className="leading-tight">Camera<br />ON</span> : 'Camera'}
        </button>
        <button className="btn-hdr" data-active={panel === 'visual'} onClick={() => onPanel('visual')}>
          <Layers size={17} /> <span className="leading-tight">Visual<br />Memory</span>
        </button>
        <button className="btn-hdr" data-active={panel === 'routines'} onClick={() => onPanel('routines')}>
          <Workflow size={17} className="text-violet-300" /> Routines
        </button>
        <button className="btn-hdr" data-active={panel === 'reminders'} onClick={() => onPanel('reminders')}>
          <Bell size={17} className="text-amber-300" /> Reminders
        </button>
        <button className="btn-hdr !px-3" data-active={panel === 'access'} onClick={() => onPanel('access')} aria-label="Accessibility" title="Accessibility">
          <SlidersHorizontal size={18} />
        </button>
        <button className="btn-hdr !px-3" data-active={panel === 'settings'} onClick={() => onPanel('settings')} aria-label="Settings" title="Settings">
          <Settings size={18} />
        </button>
      </nav>
    </header>
  )
}

function Stat({ label, value, dot }: { label: string; value: string; dot?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />}
      <div className="leading-tight">
        <div className="text-slate-300">{label}</div>
        <div className="text-cyan-300">{value}</div>
      </div>
    </div>
  )
}
