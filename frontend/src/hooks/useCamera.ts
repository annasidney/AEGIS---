import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Browser camera -> JPEG frames -> WebSocket. Frames are acknowledgement-driven: the next frame is
 * only sent once the previous detection result came back, so slow machines never build a backlog.
 */
export function useCamera(send: (m: unknown) => boolean) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const busy = useRef(false)
  const busySince = useRef(0)
  const canvas = useRef<HTMLCanvasElement>(document.createElement('canvas'))
  const [active, setActive] = useState(false)
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const attachVideo = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el
    if (el && streamRef.current) { el.srcObject = streamRef.current; el.play().catch(() => {}) }
  }, [])

  const refreshDevices = useCallback(async () => {
    try {
      const all = await navigator.mediaDevices.enumerateDevices()
      setDevices(all.filter((d) => d.kind === 'videoinput'))
    } catch { /* ignore */ }
  }, [])

  const stopStream = () => { streamRef.current?.getTracks().forEach((t) => t.stop()); streamRef.current = null }

  const start = useCallback(async (id?: string) => {
    try {
      stopStream()
      const video: MediaTrackConstraints = { width: { ideal: 1280 }, height: { ideal: 720 } }
      if (id) video.deviceId = { exact: id }
      const stream = await navigator.mediaDevices.getUserMedia({ video, audio: false })
      streamRef.current = stream
      setDeviceId(stream.getVideoTracks()[0]?.getSettings().deviceId || id || '')
      if (videoRef.current) { videoRef.current.srcObject = stream; videoRef.current.play().catch(() => {}) }
      await refreshDevices()
      setError(null)
      setActive(true)
      send({ type: 'camera_state', active: true })
    } catch (e: any) {
      setActive(false)
      setError(e?.name === 'NotAllowedError'
        ? 'Camera permission was denied. Allow camera access for this site in the browser address bar.'
        : 'Unable to open the camera. Is it in use by another app?')
    }
  }, [send, refreshDevices])

  const stop = useCallback(() => {
    stopStream()
    setActive(false)
    send({ type: 'camera_state', active: false })
  }, [send])

  const ackFrame = useCallback(() => { busy.current = false }, [])

  const snapshot = useCallback((): string | null => {
    const v = videoRef.current
    if (!v || !v.videoWidth) return null
    const c = document.createElement('canvas')
    c.width = v.videoWidth; c.height = v.videoHeight
    c.getContext('2d')?.drawImage(v, 0, 0)
    return c.toDataURL('image/png')
  }, [])

  // frame pump
  useEffect(() => {
    if (!active) return
    let timer: number
    const tick = () => {
      const v = videoRef.current
      if (v && v.readyState >= 2 && v.videoWidth) {
        const now = performance.now()
        if (!busy.current || now - busySince.current > 2500) {
          const w = 640
          const h = Math.round((w * v.videoHeight) / v.videoWidth)
          const c = canvas.current
          c.width = w; c.height = h
          c.getContext('2d')?.drawImage(v, 0, 0, w, h)
          const b64 = c.toDataURL('image/jpeg', 0.7).split(',')[1]
          if (send({ type: 'camera_frame_sync', frame_base64: b64, live_detect: true })) {
            busy.current = true; busySince.current = now
          }
        }
      }
      timer = window.setTimeout(tick, 80)
    }
    tick()
    return () => window.clearTimeout(timer)
  }, [active, send])

  useEffect(() => () => stopStream(), [])

  return { active, devices, deviceId, error, attachVideo, start, stop, ackFrame, snapshot }
}
