import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="flex min-h-screen items-center justify-center">
      <h1 className="text-2xl font-semibold">ResourceLense</h1>
    </div>
  </StrictMode>,
);
