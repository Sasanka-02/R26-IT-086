import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { SessionProvider } from "./context/SessionContext";
import { AuthProvider } from "./context/AuthContext";
import { IntakeProvider } from "./context/IntakeContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <IntakeProvider>
          <SessionProvider>
            <App />
          </SessionProvider>
        </IntakeProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);