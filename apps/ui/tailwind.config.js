/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Tokens are RGB channel triplets in index.css, wrapped here with
        // <alpha-value> so Tailwind's alpha modifiers compose — e.g.
        // `bg-theme-panel/50` -> rgb(var(--bg-panel) / 0.5).
        theme: {
          app: 'rgb(var(--bg-app) / <alpha-value>)',
          header: 'rgb(var(--bg-header) / <alpha-value>)',
          panel: 'rgb(var(--bg-panel) / <alpha-value>)',
          'panel-hover': 'rgb(var(--bg-panel-hover) / <alpha-value>)',
          card: 'rgb(var(--bg-card) / <alpha-value>)',
          'card-subtle': 'rgb(var(--bg-card-subtle) / <alpha-value>)',
          desk: 'rgb(var(--bg-desk) / <alpha-value>)',
          border: 'rgb(var(--border-subtle) / <alpha-value>)',
          'border-card': 'rgb(var(--border-card) / <alpha-value>)',
          'border-active': 'rgb(var(--border-active) / <alpha-value>)',
          primary: 'rgb(var(--text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--text-secondary) / <alpha-value>)',
          muted: 'rgb(var(--text-muted) / <alpha-value>)',
          brand: 'rgb(var(--accent-brand) / <alpha-value>)',
          pass: 'rgb(var(--accent-pass) / <alpha-value>)',
          'pass-bg': 'rgb(var(--accent-pass-bg) / <alpha-value>)',
          'pass-border': 'rgb(var(--accent-pass-border) / <alpha-value>)',
          flag: 'rgb(var(--accent-flag) / <alpha-value>)',
          'flag-bg': 'rgb(var(--accent-flag-bg) / <alpha-value>)',
          'flag-border': 'rgb(var(--accent-flag-border) / <alpha-value>)',
          unknown: 'rgb(var(--accent-unknown) / <alpha-value>)',
          'unknown-bg': 'rgb(var(--accent-unknown-bg) / <alpha-value>)',
          'unknown-border': 'rgb(var(--accent-unknown-border) / <alpha-value>)',
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
