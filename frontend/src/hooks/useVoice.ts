import { useCallback, useRef, useState } from 'react'
import { blobToWavBase64 } from '../lib/audio'

/** Push-to-talk microphone capture. Emits 16 kHz WAV (base64) when released. */
export function useVoice(opts: { onStart: () => void; onAudio: (wavB64: string) => void; onTooShort: () => void }) {
  const [listening, setListening] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const recRef = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const startedAt = useRef(0)
  const cb = useRef(opts)
  cb.current = opts

  const start = useCallback(async () => {
    if (recRef.current && recRef.current.state !== 'inactive') return
    try {
      cb.current.onStart()
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      const rec = new MediaRecorder(stream)
      chunks.current = []
      rec.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data) }
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const tooShort = performance.now() - startedAt.current < 400
        if (tooShort || !chunks.current.length) { cb.current.onTooShort(); return }
        try { cb.current.onAudio(await blobToWavBase64(new Blob(chunks.current, { type: rec.mimeType }))) }
        catch { setMicError('Could not process the recording.') }
      }
      startedAt.current = performance.now()
      rec.start()
      recRef.current = rec
      setMicError(null)
      setListening(true)
    } catch {
      setMicError('Microphone permission was denied.')
      setListening(false)
    }
  }, [])

  const stop = useCallback(() => {
    const rec = recRef.current
    if (rec && rec.state !== 'inactive') rec.stop()
    setListening(false)
  }, [])

  return { listening, micError, start, stop }
}
