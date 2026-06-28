import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { StudentDemo } from "./components/character/StudentDemo.tsx";
import "./index.css";

const preview = new URLSearchParams(window.location.search).get("preview") === "student";

createRoot(document.getElementById("root")!).render(
  <StrictMode>{preview ? <StudentDemo /> : <App />}</StrictMode>,
);
