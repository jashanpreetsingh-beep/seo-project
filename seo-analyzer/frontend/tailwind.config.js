/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: '#1e3a5f',
        gold: '#b8860b',
        forest: '#2d6a4f',
        amber: '#d4740e',
        crimson: '#c53030',
        cream: '#faf9f7',
      },
    },
  },
  plugins: [],
}
