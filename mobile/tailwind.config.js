/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        marca: { DEFAULT: '#0F766E', claro: '#CCFBF1', escuro: '#134E4A' },
        aterro: '#B45309',
      },
    },
  },
  plugins: [],
};
