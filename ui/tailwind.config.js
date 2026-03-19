/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#060d18',
        foreground: '#f0f4f8',
        primary: {
          DEFAULT: '#7aacaf',
          hover: '#a3cacc',
        },
        muted: {
          DEFAULT: '#1a2535',
          foreground: '#8ea0b0',
        },
        border: 'rgba(104,146,150,0.35)',
        accent: {
          yellow: '#f1e38b',
          teal: '#79d2b8',
          pink: '#edadaf',
          blue: '#68baec',
          orange: '#fdbd79',
        },
        success: '#79d2b8',
        warning: '#f1e38b',
        danger: '#edadaf',
      },
      fontFamily: {
        sans: ['"Sora"', 'sans-serif'],
        heading: ['"Nunito Sans"', 'sans-serif'],
        mono: ['"Geist Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
