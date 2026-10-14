import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` serves the desk at http://localhost:5173 (or the next free port)
// and opens it in your browser. The page calls the backend at http://localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, open: true },
});
