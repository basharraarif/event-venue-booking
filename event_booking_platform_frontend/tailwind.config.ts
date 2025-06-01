import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}", // Include if using Pages Router
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}", // For App Router
  ],
  theme: {
    extend: {
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      // You can extend other theme properties here
      // colors: {
      //   primary: '#your-primary-color',
      //   secondary: '#your-secondary-color',
      // },
    },
  },
  plugins: [
    // You can add Tailwind plugins here, e.g., @tailwindcss/forms, @tailwindcss/typography
  ],
};
export default config;
