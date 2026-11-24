import { LogOut, Save, Settings as Cog } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { SettingsInfo, User } from '../types'
import Drawer from './Drawer'

interface Props { user: User | null; onUser: (u: User | null) => void; onClose: () => void; notify: (t: string) => void }

export default function SettingsDrawer({ user, onUser, onClose, notify }: Props) {
  const [name, setName] = useState(user?.name ?? '')
  const [role, setRole] = useState(user?.role ?? '')
  const [key, setKey] = useState('')
  const [settings, setSettings] = useState<SettingsInfo | null>(null)
  useEffect(() => { api.settings().then(setSettings).catch(() => {}) }, [])

  const input = 'w-full rounded-xl border border-edge bg-black/30 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400/50 focus:outline-none'
  const btn = 'flex items-center justify-center gap-2 rounded-xl bg-cyan-500 py-2.5 text-sm font-bold text-[#04101f] hover:bg-cyan-400'

  const saveProfile = async () => {
    try { onUser((await api.updateProfile({ name, role })).user); notify('Profile updated') } catch (e: any) { notify(e.message) }
  }
  const saveKey = async () => {
    await api.updateSettings({ GEMINI_API_KEY: key.trim() })
    setKey(''); setSettings(await api.settings()); notify('Gemini key saved for this session')
  }
  const toggle = async (k: 'LEARNING_ENABLED' | 'LOCATION_ENABLED', v: boolean) => {
    await api.updateSettings({ [k]: v }); setSettings(await api.settings())
  }

  return (
    <Drawer title="Settings" icon={Cog} onClose={onClose}>
      <h3 className="label-mono muted mb-3">Profile</h3>
      {user ? (
        <div className="card flex flex-col gap-3 p-5">
          <input className={input} aria-label="Display name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
          <input className={input} aria-label="Role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role (e.g. Software Engineer)" />
          <p className="muted text-xs">{user.provider === 'google' ? `Signed in with Google · ${user.email}` : 'Local profile'}</p>
          <div className="grid grid-cols-2 gap-3">
            <button className={btn} onClick={saveProfile}><Save size={16} /> Save</button>
            <button className="flex items-center justify-center gap-2 rounded-xl border border-red-400/40 py-2.5 text-sm font-bold text-red-300 hover:bg-red-500/10"
              onClick={() => { onUser(null); notify('Signed out') }}><LogOut size={16} /> Sign out</button>
          </div>
        </div>
      ) : <p className="muted card p-4 text-sm">You're using a guest session. Sign in from the intro screen to keep a profile.</p>}

      <h3 className="label-mono muted mb-3 mt-7">Reasoning engine</h3>
      <div className="card flex flex-col gap-3 p-5">
        <p className="text-sm text-slate-200">
          Model: <span className="font-mono text-cyan-300">{settings?.GEMINI_MODEL ?? '…'}</span> ·{' '}
          {settings?.has_api_key ? <span className="text-emerald-400">API key active</span> : <span className="text-amber-300">no key — running offline mode</span>}
        </p>
        <input className={input} type="password" aria-label="Gemini API key" value={key} onChange={(e) => setKey(e.target.value)} placeholder="Paste Gemini API key" autoComplete="off" />
        <button className={btn} onClick={saveKey} disabled={!key.trim()}><Save size={16} /> Use this key</button>
        <p className="muted text-xs">Stored in memory only. Put GEMINI_API_KEY in .env to keep it permanently.</p>
      </div>

      <h3 className="label-mono muted mb-3 mt-7">Privacy</h3>
      <div className="flex flex-col gap-3">
        {([['LEARNING_ENABLED', 'Learn my routines', 'Track app usage by time of day to suggest habits.'],
           ['LOCATION_ENABLED', 'Use my location', 'Allow maps/directions to start from your current location.']] as const).map(([k, label, hint]) => (
          <label key={k} className="card flex cursor-pointer items-center justify-between gap-4 p-4">
            <span><span className="block font-semibold text-white">{label}</span><span className="muted text-[13px]">{hint}</span></span>
            <input type="checkbox" className="h-5 w-5 accent-cyan-400" checked={!!settings?.[k]} onChange={(e) => toggle(k, e.target.checked)} />
          </label>
        ))}
      </div>
    </Drawer>
  )
}
