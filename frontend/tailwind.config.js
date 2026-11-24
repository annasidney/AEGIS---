/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        void: '#03060f',
        panel: '#0a1224',
        panel2: '#0d1730',
        edge: 'rgba(148,163,184,0.14)',
        cyan: { aegis: '#22d3ee' },
      },
      keyframes: {
        orbSpin: { to: { transform: 'rotate(360deg)' } },
        orbPulse: { '0%,100%': { transform: 'scale(1)', opacity: '.9' }, '50%': { transform: 'scale(1.04)', opacity: '1' } },
        slideIn: { from: { transform: 'translateX(24px)', opacity: '0' }, to: { transform: 'translateX(0)', opacity: '1' } },
        fadeUp: { from: { transform: 'translateY(8px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
        dot: { '0%,100%': { transform: 'scale(1)', opacity: '.35' }, '50%': { transform: 'scale(1.7)', opacity: '1' } },
        scan: { from: { backgroundPosition: '0 0' }, to: { backgroundPosition: '0 8px' } },
      },
      animation: {
        orbSpin: 'orbSpin 9s linear infinite',
        orbPulse: 'orbPulse 3.2s ease-in-out infinite',
        slideIn: 'slideIn .28s ease-out',
        fadeUp: 'fadeUp .3s ease-out',
        dot: 'dot 1.1s ease-in-out infinite',
        scan: 'scan .6s linear infinite',
      },
    },
  },
  plugins: [],
}
