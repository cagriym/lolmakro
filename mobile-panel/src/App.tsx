// Main application component

import { useEffect, useState } from "react";
import { HomePage } from "@/pages/HomePage";

const API_BASE = import.meta.env.VITE_API_BASE || window.location.origin;

function isMobileClient(): boolean {
  const ua = navigator.userAgent.toLowerCase();
  return /android|iphone|ipad|ipod|mobile/.test(ua);
}

function App() {
  const [checked, setChecked] = useState(false);
  const [paired, setPaired] = useState(false);

  useEffect(() => {
    const run = async () => {
      if (!isMobileClient()) {
        setPaired(true);
        setChecked(true);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/api/mobile/session`, { credentials: "include" });
        const data = await res.json();
        setPaired(Boolean(data?.paired));
      } catch {
        setPaired(false);
      } finally {
        setChecked(true);
      }
    };
    void run();
  }, []);

  if (!checked) {
    return <div className="app"><div className="action-message">Erişim doğrulanıyor...</div></div>;
  }

  if (!paired) {
    return (
      <div className="app">
        <div className="action-message">
          Telefon eşleşmesi yok. Lütfen PC uygulamasından QR kodu yeniden okut.
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <HomePage />
    </div>
  );
}

export default App;
