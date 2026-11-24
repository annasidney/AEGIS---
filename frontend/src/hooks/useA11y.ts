import { useEffect, useState } from 'react'
import type { A11yPrefs } from '../types'

const KEY = 'aegis.a11y'
const DEFAULTS: A11yPrefs = { contrast: false, dyslexic: false, reduceMotion: false, textScale: 1 }

export function useA11y() {
  const [prefs, setPrefs] = useState<A11yPrefs>(() => {
    try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || '{}') } } catch { return DEFAULTS }
  })
  useEffect(() => {
    const el = document.documentElement
    el.classList.toggle('a11y-contrast', prefs.contrast)
    el.classList.toggle('a11y-dyslexic', prefs.dyslexic)
    el.classList.toggle('a11y-motion', prefs.reduceMotion)
    el.style.setProperty('--text-scale', String(prefs.textScale))
    localStorage.setItem(KEY, JSON.stringify(prefs))
  }, [prefs])
  return { prefs, setPrefs }
}
