/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // 赛博色系
        primary: {
          DEFAULT: '#3b82f6', // Electric Blue
          glow: '#60a5fa',
        },
        cyber: {
          purple: '#8b5cf6',
          pink: '#ec4899',
          cyan: '#06b6d4',
        },
        dark: {
          bg: '#0f172a', // 深邃蓝黑
          surface: '#1e293b',
          glass: 'rgba(30, 41, 59, 0.7)',
        }
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'spin-slow': 'spin 12s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: 1, boxShadow: '0 0 20px rgba(59, 130, 246, 0.5)' },
          '50%': { opacity: .8, boxShadow: '0 0 10px rgba(59, 130, 246, 0.2)' },
        },
        shimmer: {
          'from': { backgroundPosition: '0 0' },
          'to': { backgroundPosition: '-200% 0' },
        }
      },
      backgroundImage: {
        'glass-gradient': 'linear-gradient(145deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05))',
        'glass-gradient-dark': 'linear-gradient(145deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.6))',
        'neon-gradient': 'linear-gradient(to right, #4f46e5, #06b6d4)',
        'cyber-grid': 'radial-gradient(circle at center, rgba(59, 130, 246, 0.1) 1px, transparent 1px)',
      },
      boxShadow: {
        'neon': '0 0 20px rgba(59, 130, 246, 0.5)',
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
      },
      backdropBlur: {
        'xs': '2px',
      }
    },
  },
  plugins: [],
}
