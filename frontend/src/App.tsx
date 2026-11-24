import { useCallback, useEffect, useRef, useState } from 'react'
import AccessibilityDrawer from './components/AccessibilityDrawer'
import CameraPanel from './components/CameraPanel'
import CommandBar from './components/CommandBar'
import Conversation from './components/Conversation'
import CoreOrb from './components/CoreOrb'
import Header, { type Panel } from './components/Header'
import Landing from './components/Landing'
import MemoryDrawer from './components/MemoryDrawer'
import RemindersDrawer from './components/RemindersDrawer'
import RoutinesDrawer from './components/RoutinesDrawer'
import SettingsDrawer from './components/SettingsDrawer'
import Suggestions from './components/Suggestions'
import Toasts, { type Toast } from './components/Toasts'
import VisualMemoryDrawer from './components/VisualMemoryDrawer'
import { useA11y } from './hooks/useA11y'
import { useAegisSocket } from './hooks/useAegisSocket'
import { useCamera } from './hooks/useCamera'
import { usePoll } from './hooks/usePoll'
import { useVoice } from './hooks/useVoice'
import { api, getToken, setToken } from './lib/api'
import type { ChatMessage, CoreState, DetectionBox, StatusInfo, User } from './types'

const SKIP_KEY = 'aegis.skipIntro'
let uid = 0
const nextId = () => `m${++uid}`

export default function App() {
  const { prefs, setPrefs } = useA11y()
  const [screen, setScreen] = useState<'landing' | 'workspace'>(() => (localStorage.getItem(SKIP_KEY) === '1' ? 'workspace' : 'landing'))
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<StatusInfo | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [backendState, setBackendState] = useState<CoreState>('IDLE')
  const [speaking, setSpeaking] = useState(false)
  const [panel, setPanel] = useState<Panel | null>(null)
  const [camPanel, setCamPanel] = useState(false)
  const [boxes, setBoxes] = useState<DetectionBox[]>([])
  const [engine, setEngine] = useState('yolov5m')
  const [toasts, setToasts] = useState<Toast[]>([])
  const [shutdown, setShutdown] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const ackRef = useRef<() => void>(() => {})

  // ---------- helpers ----------
  const notify = useCallback((text: string, kind: Toast['kind'] = 'info') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, text, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'reminder' ? 9000 : 3500)
  }, [])
  const addMessage = useCallback((m: Omit<ChatMessage, 'id' | 'ts'>) => setMessages((prev) => [...prev, { ...m, id: nextId(), ts: Date.now() }]), [])

  const stopAudio = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
    setSpeaking(false)
  }, [])
  const playAudio = useCallback((b64?: string | null) => {
    if (!b64) return
    stopAudio()
    const a = new Audio(`data:audio/mpeg;base64,${b64}`)
    audioRef.current = a
    a.onended = a.onerror = () => setSpeaking(false)
    setSpeaking(true)
    a.play().catch(() => setSpeaking(false))
  }, [stopAudio])

  // ---------- websocket event bus ----------
  const onMessage = useCallback((m: any) => {
    switch (m.type) {
      case 'state_change':
        setBackendState(m.state === 'THINKING' || m.state === 'EXECUTING' ? m.state : 'IDLE')
        break
      case 'agent_response':
        addMessage({ role: 'aegis', text: m.response, tool: m.tool, route: m.route, latency: m.latency_ms, steps: m.steps })
        if (m.route === 'router') api.status().then(setStatus).catch(() => {})
        playAudio(m.audio_base64)
        if (m.action === 'exit_app') setTimeout(() => setShutdown(true), 1800)
        break
      case 'transcript':
        if (m.text) addMessage({ role: 'user', text: m.text })
        else addMessage({ role: 'system', text: "I didn't catch that — try again closer to the mic." })
        break
      case 'live_detections':
        setBoxes(m.boxes); setEngine(m.engine); ackRef.current()
        break
      case 'reminder_alert':
        notify(`Reminder: ${m.text}`, 'reminder')
        addMessage({ role: 'system', text: `⏰ ${m.message}` })
        playAudio(m.audio_base64)
        break
    }
  }, [addMessage, notify, playAudio])

  const { connected, send } = useAegisSocket(onMessage)
  const camera = useCamera(send)
  ackRef.current = camera.ackFrame

  // ---------- auth + status ----------
  useEffect(() => {
    if (!getToken()) return
    api.me().then((r) => setUser(r.user)).catch(() => setToken(null))
  }, [])
  const handleUser = (u: User | null) => { if (!u) setToken(null); setUser(u) }
  usePoll(async () => { try { setStatus(await api.status()) } catch { /* offline */ } }, 8000, screen === 'workspace')

  // ---------- actions ----------
  const sendText = useCallback((text: string) => {
    const t = text.trim()
    if (!t) return
    stopAudio()
    addMessage({ role: 'user', text: t })
    if (!send({ type: 'message', text: t, is_voice: false })) {
      addMessage({ role: 'system', text: 'Not connected to the AEGIS engine yet — retrying…' })
    }
  }, [addMessage, send, stopAudio])

  const voice = useVoice({
    onStart: () => { stopAudio(); send({ type: 'barge_in' }) },          // barge-in: talking cuts AEGIS off
    onAudio: (b64) => { setBackendState('THINKING'); send({ type: 'audio_chunk', audio_base64: b64 }) },
    onTooShort: () => {},
  })

  const toggleCamera = () => {
    if (camera.active) { camera.stop(); setBoxes([]); setCamPanel(false) }
    else { setCamPanel(true); camera.start() }
  }
  const closeCamera = () => { camera.stop(); setBoxes([]); setCamPanel(false) }
  const snapshot = () => {
    const url = camera.snapshot()
    if (!url) return notify('No camera frame to save yet')
    const a = document.createElement('a')
    a.href = url; a.download = `aegis-snapshot-${Date.now()}.png`; a.click()
  }
  const togglePanel = (p: Panel) => setPanel((cur) => (cur === p ? null : p))

  // hold Spacebar = push to talk
  useEffect(() => {
    if (screen !== 'workspace') return
    const typing = (el: EventTarget | null) => {
      const t = el as HTMLElement | null
      return !!t && (['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName) || t.isContentEditable)
    }
    const down = (e: KeyboardEvent) => { if (e.code === 'Space' && !e.repeat && !typing(e.target)) { e.preventDefault(); voice.start() } }
    const up = (e: KeyboardEvent) => { if (e.code === 'Space' && !typing(e.target)) { e.preventDefault(); voice.stop() } }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => { window.removeEventListener('keydown', down); window.removeEventListener('keyup', up) }
  }, [screen, voice])

  const core: CoreState = voice.listening ? 'LISTENING' : speaking ? 'SPEAKING' : backendState

  // ---------- render ----------
  if (screen === 'landing') {
    return (
      <>
        <Landing user={user} onUser={handleUser} onEnter={(skip) => { if (skip) localStorage.setItem(SKIP_KEY, '1'); setScreen('workspace') }} />
        <Toasts items={toasts} />
      </>
    )
  }

  return (
    <div className="relative flex h-full flex-col">
      <Header
        connected={connected}
        status={status}
        user={user}
        cameraActive={camera.active}
        panel={panel}
        onToggleCamera={toggleCamera}
        onPanel={togglePanel}
      />

      <main className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex shrink-0 justify-center pb-4 pt-5 transition-all duration-300">
          <CoreOrb state={core} compact={messages.length > 0} onClick={() => (voice.listening ? voice.stop() : voice.start())} />
        </div>
        <Suggestions onPick={sendText} />
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          <Conversation messages={messages} state={core} />
        </div>
        <CommandBar
          state={core}
          listening={voice.listening}
          micError={voice.micError}
          onSend={sendText}
          onTalkStart={voice.start}
          onTalkEnd={voice.stop}
        />

        {camPanel && (
          <CameraPanel
            active={camera.active}
            devices={camera.devices}
            deviceId={camera.deviceId}
            error={camera.error}
            boxes={boxes}
            engine={engine}
            attachVideo={camera.attachVideo}
            onStart={camera.start}
            onClose={closeCamera}
            onAsk={sendText}
            onSnapshot={snapshot}
          />
        )}

        {panel === 'visual' && <VisualMemoryDrawer onClose={() => setPanel(null)} />}
        {panel === 'routines' && <RoutinesDrawer onClose={() => setPanel(null)} onRun={(c) => { sendText(c); setPanel(null) }} />}
        {panel === 'reminders' && <RemindersDrawer onClose={() => setPanel(null)} />}
        {panel === 'memory' && <MemoryDrawer onClose={() => setPanel(null)} />}
        {panel === 'access' && <AccessibilityDrawer prefs={prefs} setPrefs={setPrefs} onClose={() => setPanel(null)} />}
        {panel === 'settings' && <SettingsDrawer user={user} onUser={handleUser} onClose={() => setPanel(null)} notify={notify} />}
      </main>

      <Toasts items={toasts} />
      {shutdown && (
        <div className="fixed inset-0 z-[60] flex flex-col items-center justify-center gap-3 bg-black/95 text-center">
          <p className="text-3xl font-bold text-white">AEGIS has shut down.</p>
          <p className="muted">Goodbye! You can close this tab. Run <code className="font-mono text-cyan-300">start_aegis.ps1</code> to start again.</p>
        </div>
      )}
    </div>
  )
}
