/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#fdfcfa',
          100: '#f8f6f0',
          200: '#ECE3CE',
          300: '#e0d3b8',
          400: '#d4c3a2',
        },
        sage: {
          50: '#e8ebe7',
          100: '#c5cdc3',
          200: '#9fac9c',
          300: '#739072',
          400: '#638060',
          500: '#537050',
        },
        forest: {
          50: '#e0e7e1',
          100: '#b3c5b5',
          200: '#809e84',
          300: '#4F6F52',
          400: '#456349',
          500: '#3A4D39',
          600: '#2f3f2e',
          700: '#253024',
        },
        accent: {
          purple: '#8b5cf6',
          green: '#739072',
          orange: '#f97316',
        },
        // Amber for warning states (replaces generic yellow)
        amber: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#ca8a04',
        },
        // Semantic status colors
        status: {
          live: '#ef4444',      // Red for universal recognition
          waiting: '#ca8a04',   // amber-600
          ended: '#9fac9c',     // sage-200
          error: '#dc2626',     // red-600
          success: '#537050',   // sage-500
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-subtle': 'pulseSubtle 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
      },
      boxShadow: {
        'flat': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'flat-md': '0 2px 4px 0 rgba(0, 0, 0, 0.06)',
        'flat-hover': '0 2px 6px 0 rgba(0, 0, 0, 0.08)',
        'flat-inset': 'inset 0 1px 2px 0 rgba(0, 0, 0, 0.04)',
      },
    },
  },
  plugins: [],
}