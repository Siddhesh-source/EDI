/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        'buy': '#10b981',
        'sell': '#ef4444',
        'hold': '#6b7280',
      }
    },
  },
  plugins: [],
}
