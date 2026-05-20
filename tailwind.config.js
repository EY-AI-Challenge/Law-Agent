/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ey: {
          yellow: '#FFE600',
          dark:   '#2E2E38',
          darker: '#1A1A24',
          panel:  '#23232F',
          card:   '#1E1E2A',
          border: '#333344',
          muted:  '#B0AFBA',
        }
      },
      fontFamily: {
        sans: ['"EYInterstate"', '"Segoe UI"', 'sans-serif'],
      }
    }
  },
  plugins: []
}
