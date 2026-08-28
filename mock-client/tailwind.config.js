/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#FBF8F3',
          100: '#F5EFE6',
          200: '#E8DCCF',
          300: '#D6C3B1',
          400: '#BEA690',
          500: '#A48870',
          600: '#876B55',
          700: '#69513F',
          800: '#4D3B2E',
          900: '#2A1F17',
          950: '#140E0A',
        },
        gold: {
          400: '#FBBF24',
          500: '#D4A017',
          600: '#B8860B',
        },
      },
      fontFamily: {
        display: ['Outfit', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-gold': '0 0 0 1px rgba(212,160,23,0.30), 0 8px 32px -4px rgba(212,160,23,0.18)',
        'card': '0 2px 10px rgba(0,0,0,0.06)',
        'elevated': '0 16px 48px -8px rgba(20,14,10,0.12)',
      },
    },
  },
  plugins: [],
}
