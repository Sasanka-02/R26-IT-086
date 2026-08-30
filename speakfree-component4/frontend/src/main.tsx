import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { SessionProvider } from "./context/SessionContext";
import { PracticeHistoryProvider } from "./context/PracticeHistoryContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <PracticeHistoryProvider>
          <SessionProvider>
            <App />
          </SessionProvider>
        </PracticeHistoryProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);