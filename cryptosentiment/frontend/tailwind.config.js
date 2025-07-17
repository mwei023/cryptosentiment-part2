module.exports = {
  darkMode: ['class'],
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        card: 'rgb(17, 24, 39)', // Dark card background
        muted: 'rgb(31, 41, 55)', // Slightly lighter than card
        accent: 'rgb(51, 65, 85)', // Hover effect
        border: 'rgb(75, 85, 99)' // Border color
      },
    },
  },
  plugins: [],
}