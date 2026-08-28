/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          50:  '#F7F4EF',
          100: '#EDE9E2',
          200: '#D9D0C4',
          300: '#BFB3A2',
          400: '#A0917F',
          500: '#857260',
          600: '#6A5A48',
          700: '#4D4033',
          800: '#302820',
          900: '#1A150F',
          950: '#0D0A06',
        },
        canvas: {
          DEFAULT: '#FAF8F4',
          warm:    '#F5F0E6',
          card:    '#EEEAE1',
          muted:   '#E6E0D4',
          border:  '#D4CBBF',
          subtle:  '#C2B8A8',
        },
        terra: {
          50:  '#FEF6F0',
          100: '#FDE8D6',
          200: '#F9C9A6',
          300: '#F4A572',
          400: '#ED8244',
          500: '#D9641E',
          600: '#B84E16',
          700: '#943B10',
          800: '#6E2B0C',
          900: '#481C08',
        },
        gold: {
          50:  '#FFFBEB',
          100: '#FEF3C7',
          200: '#FDE68A',
          300: '#FCD34D',
          400: '#FBBF24',
          500: '#D4A017',
          600: '#A07C10',
          700: '#78590A',
          800: '#503B06',
          900: '#2C2003',
        },
        risk: {
          low:    '#1D6B3E',
          medium: '#856305',
          high:   '#8B1616',
        },
        decision: {
          auto:      '#1D6B3E',
          escalated: '#856305',
          pending:   '#1A4D7A',
          rejected:  '#8B1616',
        },
      },
      fontFamily: {
        display: ['Outfit', 'system-ui', 'sans-serif'],
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.03em' }],
        '4xl': ['2.25rem', { lineHeight: '2.6rem',  letterSpacing: '-0.04em' }],
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
      boxShadow: {
        'glow-gold': '0 0 0 1px rgba(212,160,23,0.25), 0 4px 24px -4px rgba(212,160,23,0.12)',
        'nav':       '0 4px 32px -4px rgba(26,21,15,0.14), 0 1px 8px -1px rgba(26,21,15,0.06)',
        'nav-scrolled': '0 8px 48px -6px rgba(26,21,15,0.20), 0 2px 12px -2px rgba(26,21,15,0.10)',
        'card':      '0 1px 4px rgba(26,21,15,0.05)',
        'card-md':   '0 4px 20px -2px rgba(26,21,15,0.10)',
        'card-lg':   '0 12px 40px -6px rgba(26,21,15,0.14)',
        'lift':      '0 16px 48px -8px rgba(26,21,15,0.16)',
        'inset-top': 'inset 0 1px 0 rgba(255,255,255,0.6)',
      },
      backgroundImage: {
        'gradient-luxury':  'linear-gradient(135deg, #FAF8F4 0%, #F0EAE0 100%)',
        'gradient-card':    'linear-gradient(145deg, rgba(255,255,255,0.55) 0%, rgba(238,234,225,0.70) 100%)',
        'gradient-gold':    'linear-gradient(135deg, #FDE68A 0%, #D4A017 100%)',
        'shimmer':          'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
      },
      animation: {
        'fade-in-up':   'fadeInUp 0.32s cubic-bezier(0.22,1,0.36,1) forwards',
        'fade-in':      'fadeIn 0.24s ease forwards',
        'slide-in-right': 'slideInRight 0.28s cubic-bezier(0.22,1,0.36,1) forwards',
        'pulse-soft':   'pulseSoft 2.4s ease-in-out infinite',
        'shimmer':      'shimmer 2s linear infinite',
        'scale-in':     'scaleIn 0.20s cubic-bezier(0.22,1,0.36,1) forwards',
      },
      keyframes: {
        fadeInUp: {
          '0%':   { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInRight: {
          '0%':   { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.45' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        scaleIn: {
          '0%':   { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      transitionTimingFunction: {
        'luxury': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}
