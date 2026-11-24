import { Aperture, Armchair, Box, ChevronDown, Image as ImageIcon, Layers, Maximize2, Minimize2, Monitor, Radio, ScanEye, Smartphone, User, UserCheck, Video, X, Eye } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'
import { colorFor } from '../lib/colors'
import type { DetectionBox } from '../types'

const ICONS: Record<string, LucideIcon> = { person: User, painting: ImageIcon, screen: Monitor, chair: Armchair, phone: Smartphone }

interface Props {
  active: boolean
  devices: MediaDeviceInfo[]
  deviceId: string
  error: string | null
  boxes: DetectionBox[]
  engine: string
  attachVideo: (el: HTMLVideoElement | null) => void
  onStart: (id?: string) => void
  onClose: () => void
  onAsk: (text: string) => void
  onSnapshot: () => void
}

const engineLabel = (e: string) => (e === 'yolov5m' ? 'YOLOv5m' : e === 'yolox' ? 'YOLOX' : 'LOCAL CV')

export default function CameraPanel({ active, devices, deviceId, error, boxes, engine, attachVideo, onStart, onClose, onAsk, onSnapshot }: Props) {
  const [hud, setHud] = useState(true)
  const [tags, setTags] = useState(true)
  const [collapsed, setCollapsed] = useState(false)
  const [full, setFull] = useState(false)
  const [aspect, setAspect] = useState(16 / 9)

  const sorted = [...boxes].sort((a, b) => b.confidence - a.confidence)
  const currentLabel = devices.find((d) => d.deviceId === deviceId)?.label || 'Default camera'

  return (
    <section
      aria-label="AEGIS AR Vision"
      className={`glass absolute z-20 animate-fadeUp rounded-2xl p-4 shadow-[0_20px_60px_rgba(0,0,0,.55)] ${
        full ? 'inset-4' : 'right-4 top-4 w-[min(850px,calc(100%-2rem))]'
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="h-3.5 w-3.5 rounded-full bg-sky-400 shadow-[0_0_12px_#38bdf8]" />
        <h3 className="font-mono text-[15px] font-bold tracking-wider text-white">AEGIS AR VISION</h3>
        {active && (
          <span className="flex items-center gap-1.5 rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-2.5 py-1 font-mono text-[11px] font-semibold text-emerald-300">
            <Radio size={12} /> {boxes.length} Target{boxes.length === 1 ? '' : 's'} Locked
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setHud((v) => !v)}
            aria-pressed={hud}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold ${hud ? 'border-emerald-400/50 bg-emerald-400/10 text-emerald-300' : 'border-edge text-slate-400'}`}
          >
            <Eye size={14} /> HUD {hud ? 'Active' : 'Off'}
          </button>
          <IconBtn label="Save snapshot" onClick={onSnapshot}><Aperture size={17} /></IconBtn>
          <IconBtn label={full ? 'Exit full view' : 'Expand'} onClick={() => setFull((v) => !v)}><Maximize2 size={17} /></IconBtn>
          <IconBtn label={collapsed ? 'Restore' : 'Minimize'} onClick={() => setCollapsed((v) => !v)}><Minimize2 size={17} /></IconBtn>
          <IconBtn label="Close and turn camera off" onClick={onClose}><X size={18} /></IconBtn>
        </div>
      </div>

      {!collapsed && (
        <>
          <div className="mt-4 flex items-center gap-3">
            <div className="relative flex-1">
              <Video size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-cyan-300" />
              <select
                value={deviceId}
                onChange={(e) => onStart(e.target.value)}
                aria-label="Camera device"
                className="w-full appearance-none rounded-xl border border-edge bg-black/30 py-2.5 pl-9 pr-9 text-sm text-white focus:border-cyan-400/50 focus:outline-none"
              >
                {devices.length === 0 && <option value="">No camera found</option>}
                {devices.map((d, i) => (
                  <option key={d.deviceId || i} value={d.deviceId}>{d.deviceId === deviceId ? '✓ ' : ''}{d.label || `Camera ${i + 1}`}</option>
                ))}
              </select>
              <ChevronDown size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
            </div>
            <button
              onClick={() => setTags((v) => !v)}
              aria-pressed={tags}
              className="flex items-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-200"
            >
              <Layers size={15} /> Tags: {tags ? 'On' : 'Off'}
            </button>
          </div>
          <span className="sr-only">{currentLabel}</span>

          <div
            className="relative mt-3 w-full overflow-hidden rounded-xl border border-edge bg-[#2a2f3a]"
            style={{ aspectRatio: aspect, maxHeight: full ? '62vh' : undefined }}
          >
            <video
              ref={attachVideo}
              muted
              playsInline
              onLoadedMetadata={(e) => setAspect(e.currentTarget.videoWidth / e.currentTarget.videoHeight || 16 / 9)}
              className={`h-full w-full object-fill ${active ? '' : 'invisible'}`}
            />
            {!active && (
              <div className="scanlines absolute inset-0 flex flex-col items-center justify-center gap-3 text-center">
                <p className="max-w-sm rounded-lg bg-black/55 px-4 py-2 text-sm text-slate-200">{error ?? 'Camera is off.'}</p>
                <button onClick={() => onStart()} className="rounded-xl bg-cyan-500/90 px-5 py-2 text-sm font-bold text-[#04101f] hover:bg-cyan-400">Start camera</button>
              </div>
            )}
            {active && <div className="scanlines pointer-events-none absolute inset-0 opacity-40" />}
            {active && (
              <span className="absolute left-3 top-3 z-10 flex items-center gap-2 rounded-md bg-black/60 px-2.5 py-1 font-mono text-[11px] text-cyan-300">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" /> {engineLabel(engine)} • LIVE_TRACK
              </span>
            )}
            {active && hud && sorted.map((b) => {
              const c = colorFor(b.name)
              const labelInside = b.rel_y < 0.09
              return (
                <div
                  key={b.id}
                  className="pointer-events-none absolute transition-all duration-100 ease-linear"
                  style={{
                    left: `${b.rel_x * 100}%`, top: `${b.rel_y * 100}%`, width: `${b.rel_w * 100}%`, height: `${b.rel_h * 100}%`,
                    border: `2px solid ${c}`, background: `${c}12`, boxShadow: `0 0 14px ${c}44`, opacity: b.stable ? 1 : 0.7,
                  }}
                >
                  <span className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ background: c }} />
                  {tags && (
                    <span
                      className="absolute left-[-2px] flex items-center gap-1.5 whitespace-nowrap rounded px-2 py-[3px] font-mono text-[11px] font-bold"
                      style={{ [labelInside ? 'top' : 'bottom']: labelInside ? 2 : 'calc(100% + 4px)', background: '#050b1ce6', border: `1px solid ${c}`, color: c }}
                    >
                      {b.name.toUpperCase()}
                      <span className="rounded bg-white/10 px-1 text-white">{Math.round(b.confidence * 100)}%</span>
                      <span className="text-[9px] uppercase text-slate-200">{b.location}</span>
                      <span className="h-1.5 w-6 overflow-hidden rounded bg-white/15"><span className="block h-full" style={{ width: `${b.confidence * 100}%`, background: c }} /></span>
                    </span>
                  )}
                </div>
              )
            })}
          </div>

          <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-slate-300">
            <span className="flex items-center gap-2"><Radio size={13} className="text-cyan-300" /> TRACKED TARGETS <span className="muted normal-case">(Tap chip to ask AEGIS)</span></span>
            <span className="font-bold text-cyan-300">{boxes.length} detected</span>
          </div>
          <div className="no-scrollbar mt-2 flex min-h-[40px] gap-2 overflow-x-auto pb-1">
            {sorted.length === 0 && <span className="muted self-center text-xs">{active ? 'Scanning…' : 'Turn the camera on to see tracked targets.'}</span>}
            {sorted.map((b) => {
              const c = colorFor(b.name)
              const Icon = ICONS[b.name] ?? Box
              return (
                <button
                  key={b.id}
                  onClick={() => onAsk(b.name === 'person' ? 'Is there a person in front of the camera?' : `Where is the ${b.name}?`)}
                  className="flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2 font-mono text-[11px] font-bold transition hover:brightness-125"
                  style={{ borderColor: `${c}88`, background: `${c}14`, color: '#fff' }}
                >
                  <Icon size={13} style={{ color: c }} /> {b.name.toUpperCase()}
                  <span className="rounded px-1" style={{ background: `${c}33`, color: c }}>{Math.round(b.confidence * 100)}%</span>
                  <span className="muted font-normal normal-case">({b.location})</span>
                </button>
              )
            })}
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <button onClick={() => onAsk('What do you see?')} className="flex items-center justify-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-400/10 py-3 text-sm font-bold text-cyan-200 hover:bg-cyan-400/20">
              <ScanEye size={18} /> What do you see?
            </button>
            <button onClick={() => onAsk('Is there a person in front of the camera?')} className="flex items-center justify-center gap-2 rounded-xl border border-indigo-400/40 bg-indigo-400/10 py-3 text-sm font-bold text-indigo-200 hover:bg-indigo-400/20">
              <UserCheck size={18} /> Person Check
            </button>
          </div>
        </>
      )}
    </section>
  )
}

function IconBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button aria-label={label} title={label} onClick={onClick} className="rounded-lg p-2 text-slate-300 hover:bg-white/10 hover:text-white">
      {children}
    </button>
  )
}
