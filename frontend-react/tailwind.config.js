/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'fugaz': ['"Fugaz One"', 'cursive'],
        'inter': ['Inter', 'sans-serif']
      },
      colors: {
        primary: '#2563eb',
        secondary: '#fbbf24',
      }
    },
  },
  plugins: [],
}
