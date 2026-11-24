import { SlidersHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { A11yPrefs } from '../types'
import Drawer from './Drawer'

interface Props { prefs: A11yPrefs; setPrefs: (p: A11yPrefs) => void; onClose: () => void }

function Toggle({ label, hint, on, set }: { label: string; hint: string; on: boolean; set: (v: boolean) => void }) {
  return (
    <button onClick={() => set(!on)} role="switch" aria-checked={on} className="card flex w-full items-center justify-between gap-4 p-4 text-left">
      <span>
        <span className="block font-semibold text-white">{label}</span>
        <span className="muted text-[13px]">{hint}</span>
      </span>
      <span className={`relative h-6 w-11 shrink-0 rounded-full transition ${on ? 'bg-cyan-500' : 'bg-slate-600'}`}>
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${on ? 'left-[22px]' : 'left-0.5'}`} />
      </span>
    </button>
  )
}

export default function AccessibilityDrawer({ prefs, setPrefs, onClose }: Props) {
  const [speak, setSpeak] = useState(false)
  useEffect(() => { api.settings().then((s) => setSpeak(!!s.VOICE_FIRST_MODE)).catch(() => {}) }, [])

  return (
    <Drawer title="Accessibility" icon={SlidersHorizontal} onClose={onClose}>
      <div className="flex flex-col gap-3">
        <Toggle label="Speak every reply" hint="Voice-first: AEGIS reads every answer aloud (Edge-TTS neural voice)." on={speak}
          set={(v) => { setSpeak(v); api.updateSettings({ VOICE_FIRST_MODE: v }) }} />
        <Toggle label="High contrast" hint="Pure black background and strong borders for low-vision readability." on={prefs.contrast} set={(v) => setPrefs({ ...prefs, contrast: v })} />
        <Toggle label="OpenDyslexic font" hint="Weighted-bottom letterforms designed to reduce letter swapping." on={prefs.dyslexic} set={(v) => setPrefs({ ...prefs, dyslexic: v })} />
        <Toggle label="Reduce motion" hint="Turns off orb, ring and transition animations." on={prefs.reduceMotion} set={(v) => setPrefs({ ...prefs, reduceMotion: v })} />
        <div className="card p-4">
          <p className="font-semibold text-white">Text size</p>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {[1, 1.15, 1.3].map((s) => (
              <button key={s} onClick={() => setPrefs({ ...prefs, textScale: s })} aria-pressed={prefs.textScale === s}
                className={`rounded-lg border py-2 text-sm font-semibold ${prefs.textScale === s ? 'border-cyan-400 bg-cyan-400/15 text-cyan-200' : 'border-edge text-slate-300'}`}>
                {s === 1 ? 'Normal' : s === 1.15 ? 'Large' : 'Larger'}
              </button>
            ))}
          </div>
        </div>
        <div className="card p-4 text-[13.5px] leading-relaxed text-slate-300">
          <p className="mb-1 font-semibold text-white">Alternative inputs</p>
          Hold <kbd className="rounded bg-white/10 px-1.5">Space</kbd> or the Push&nbsp;To&nbsp;Talk button to speak, tap the Core to start/stop listening,
          or type. Speaking while AEGIS is talking instantly interrupts it (barge-in). All controls are keyboard reachable.
        </div>
      </div>
    </Drawer>
  )
}
