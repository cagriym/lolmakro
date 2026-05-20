"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [qrUrl, setQrUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/pair-qr")
      .then((r) => r.json())
      .then((data) => {
        if (data.qr_url) {
          setQrUrl(data.qr_url);
        } else {
          setError(data.error || "Pairing token alinamadi.");
        }
      })
      .catch(() => setError("Sunucuya ulasilamadi."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={containerStyle}>
      <h1 style={{ color: "#c8aa6e", fontSize: 28, margin: 0 }}>LoL Makro</h1>

      {loading && <p style={{ color: "#9fb0cc", marginTop: 8 }}>Baglanti kuruluyor...</p>}

      {error && (
        <>
          <p style={{ color: "#ff9ea1", marginTop: 12 }}>{error}</p>
          <p style={{ color: "#9fb0cc", marginTop: 8, fontSize: 14 }}>
            PC'de GameMode1 uygulamasini calistirin.
          </p>
        </>
      )}

      {qrUrl && (
        <>
          <p style={{ color: "#9fb0cc", marginTop: 16, fontSize: 14 }}>
            Mobil uygulama ile okut
          </p>
          <img
            src={`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(qrUrl)}`}
            alt="QR Kod"
            style={{ marginTop: 8, borderRadius: 12 }}
          />
          <p style={{ color: "#5b6a8a", marginTop: 12, fontSize: 12, wordBreak: "break-all" }}>
            {qrUrl}
          </p>
        </>
      )}
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  flexDirection: "column",
  padding: 20,
  textAlign: "center",
};
