import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "nes.css/css/nes.min.css";
import "@fontsource/press-start-2p";
import "./index.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);