/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="obsidian"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          app: 'var(--bg-app)',
          header: 'var(--bg-header)',
          panel: 'var(--bg-panel)',
          'panel-hover': 'var(--bg-panel-hover)',
          card: 'var(--bg-card)',
          'card-subtle': 'var(--bg-card-subtle)',
          desk: 'var(--bg-desk)',
          border: 'var(--border-subtle)',
          'border-card': 'var(--border-card)',
          'border-active': 'var(--border-active)',
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          brand: 'var(--accent-brand)',
          pass: 'var(--accent-pass)',
          'pass-bg': 'var(--accent-pass-bg)',
          'pass-border': 'var(--accent-pass-border)',
          flag: 'var(--accent-flag)',
          'flag-bg': 'var(--accent-flag-bg)',
          'flag-border': 'var(--accent-flag-border)',
          unknown: 'var(--accent-unknown)',
          'unknown-bg': 'var(--accent-unknown-bg)',
          'unknown-border': 'var(--accent-unknown-border)',
        },
        parchment: {
          50: '#FBF9F5',
          100: '#F8F6F1',
          200: '#F2EDE4',
          300: '#E3DDD3',
          400: '#D5CFC5',
        },
        desk: '#F5F2EB',
        racing: {
          DEFAULT: '#14532D',
          light: '#F0FDF4',
          border: '#BBF7D0',
        },
        claret: {
          DEFAULT: '#991B1B',
          light: '#FEF2F2',
        },
        tobacco: {
          DEFAULT: '#92400E',
          light: '#FDF8EE',
        },
        terminal: {
          border: '#E3DDD3',
        },
      },
      fontFamily: {
        serif: ['Newsreader', 'Playfair Display', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        xs: '0 1px 2px rgba(0,0,0,0.04)',
        '2xs': '0 1px 1px rgba(0,0,0,0.03)',
      },
      borderRadius: {
        xs: '2px',
        sm: '3px',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(2px)' },
          to: { opacity: '1', transform: 'none' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.15s ease-out',
      },
    },
  },
  plugins: [],
};
