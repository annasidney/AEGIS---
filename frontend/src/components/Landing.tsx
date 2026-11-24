import { ArrowRight, Brain, Eye, Mic, ShieldCheck, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, setToken } from '../lib/api'
import type { User } from '../types'

interface Props { user: User | null; onUser: (u: User | null) => void; onEnter: (skipNextTime: boolean) => void }

const FEATURES = [
  { icon: Eye, tint: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/30', title: 'Spatial Vision', body: 'Real-time YOLOv5m object detection with spatial-relationship reasoning and smoothed live tracking.' },
  { icon: Mic, tint: 'text-indigo-300 bg-indigo-400/10 border-indigo-400/30', title: 'Conversational Voice', body: 'Fluid speaking presence, instant voice barge-in, and natural auditory pacing.' },
  { icon: Brain, tint: 'text-fuchsia-300 bg-fuchsia-400/10 border-fuchsia-400/30', title: 'Personal Memory', body: 'Persistent memory of who you are, daily routines, habits, and lost items.' },
]

export default function Landing({ user, onUser, onEnter }: Props) {
  const [cfg, setCfg] = useState<{ google_enabled: boolean; google_client_id: string } | null>(null)
  const [skip, setSkip] = useState(false)
  const [localOpen, setLocalOpen] = useState(false)
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => { api.authConfig().then(setCfg).catch(() => setCfg({ google_enabled: false, google_client_id: '' })) }, [])

  const google = () => {
    const oauth = window.google?.accounts?.oauth2
    if (!cfg?.google_enabled || !oauth) {
      setLocalOpen(true)
      setNote(cfg?.google_enabled ? 'Google sign-in could not load (are you offline?). Create a local profile instead.' : 'Google sign-in is not configured yet — create a local profile to continue.')
      return
    }
    const client = oauth.initTokenClient({
      client_id: cfg.google_client_id,
      scope: 'openid email profile',
      callback: async (resp: any) => {
        if (resp.error || !resp.access_token) { setNote('Google sign-in was cancelled.'); return }
        try { const r = await api.googleLogin(resp.access_token); setToken(r.token); onUser(r.user); setNote('') }
        catch (e: any) { setNote(e.message) }
      },
    })
    client.requestAccessToken({ prompt: '' })
  }

  const createLocal = async () => {
    if (!name.trim()) { setNote('Please enter your name.'); return }
    try { const r = await api.localLogin(name.trim(), role.trim()); setToken(r.token); onUser(r.user); setLocalOpen(false); setNote('') }
    catch (e: any) { setNote(e.message) }
  }

  const input = 'w-full rounded-xl border border-edge bg-black/30 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400/50 focus:outline-none'

  return (
    <div className="flex h-full items-center justify-center overflow-y-auto p-6">
      <div className="card glass w-full max-w-[840px] animate-fadeUp rounded-[28px] px-10 py-12 text-center shadow-[0_30px_90px_rgba(0,0,0,.6)]">
        <div className="relative mx-auto h-[100px] w-[100px]">
          <div className="flex h-full w-full items-center justify-center rounded-[26px] border-2 border-indigo-400/70 bg-[#050b1c] shadow-[0_0_34px_rgba(99,102,241,.45)]">
            <Sparkles size={46} strokeWidth={1.6} className="text-cyan-300" />
          </div>
          <span className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full border-[3px] border-[#0b1226] bg-emerald-400" />
        </div>

        <div className="label-mono mx-auto mt-7 flex w-fit items-center gap-2 rounded-full border border-cyan-400/40 bg-cyan-400/10 px-4 py-1.5 text-[12px] font-bold text-cyan-300">
          <ShieldCheck size={14} /> Problem Statement SIH26204
        </div>
        <h1 className="mt-5 text-5xl font-extrabold tracking-tight text-white">
          Welcome to <span className="bg-gradient-to-r from-cyan-300 to-blue-500 bg-clip-text text-transparent">AEGIS</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-[17px] leading-relaxed text-slate-300">
          Assisted Executive Guidance &amp; Intelligence System — an organic, voice-first companion with continuous spatial perception and personal memory.
        </p>
        {user && (
          <p className="mt-4 text-[15px] font-semibold text-emerald-400" role="status">
            Welcome back, {user.name}! Your profile and environmental memories are loaded.
          </p>
        )}

        <div className="mt-9 grid gap-4 text-left sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, tint, title, body }) => (
            <div key={title} className="card p-5">
              <span className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl border ${tint}`}><Icon size={20} /></span>
              <h3 className="text-[15px] font-bold text-white">{title}</h3>
              <p className="muted mt-2 text-[13px] leading-relaxed">{body}</p>
            </div>
          ))}
        </div>

        <div className="mt-9 grid gap-4 sm:grid-cols-2">
          <button onClick={google} className="flex items-center justify-center gap-3 rounded-2xl bg-white py-4 text-[15px] font-semibold text-slate-800 shadow-lg transition hover:bg-slate-100">
            <GoogleG /> {user ? `Signed in as ${user.name.split(' ')[0]}` : 'Sign In with Google'}
          </button>
          <button
            onClick={() => onEnter(skip)}
            className="flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-600 to-blue-600 py-4 text-[15px] font-extrabold tracking-wide text-white shadow-[0_0_30px_rgba(37,99,235,.45)] transition hover:brightness-110"
          >
            ENTER WORKSPACE <ArrowRight size={18} />
          </button>
        </div>

        {localOpen && (
          <div className="card mx-auto mt-5 flex max-w-md animate-fadeUp flex-col gap-3 p-5 text-left">
            <p className="text-sm font-semibold text-white">Create a local profile</p>
            <input className={input} aria-label="Your name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoFocus />
            <input className={input} aria-label="Your role" value={role} onChange={(e) => setRole(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && createLocal()} placeholder="Role (optional, e.g. Software Engineer)" />
            <button onClick={createLocal} className="rounded-xl bg-cyan-500 py-2.5 text-sm font-bold text-[#04101f] hover:bg-cyan-400">Continue</button>
          </div>
        )}
        {note && <p role="alert" className="mt-4 text-sm text-amber-300">{note}</p>}

        <label className="muted mt-6 inline-flex cursor-pointer items-center gap-2.5 text-[13.5px]">
          <input type="checkbox" checked={skip} onChange={(e) => setSkip(e.target.checked)} className="h-4 w-4 accent-cyan-400" />
          Don't show this intro on next startup
        </label>
      </div>
    </div>
  )
}

function GoogleG() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17.1z" />
      <path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-2.9-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C.9 16.4 0 20.1 0 24s.9 7.6 2.6 10.8l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.3-8.5 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
    </svg>
  )
}
