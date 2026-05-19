"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

function QrCodeInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState("Baglanti kuruluyor...");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setError("Token bulunamadi. QR kodu tekrar tarayin.");
      return;
    }

    fetch("/api/mobile/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          setError(data.error);
          return;
        }
        const base = data.remote_url.replace(/\/+$/, "");
        const redirectUrl = `${base}/mobile/pair?token=${encodeURIComponent(token)}`;
        setStatus("PC'ye baglaniyor...");
        window.location.href = redirectUrl;
      })
      .catch(() => {
        setError("Sunucuya ulasilamadi. Internet baglantinizi kontrol edin.");
      });
  }, []);

  if (error) {
    return (
      <div style={containerStyle}>
        <h2 style={{ color: "#c8aa6e", margin: 0 }}>Hata</h2>
        <p style={{ color: "#ff9ea1", marginTop: 12 }}>{error}</p>
        <button onClick={() => router.push("/")} style={btnStyle}>Geri Don</button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={spinnerStyle} />
      <p style={{ color: "#d7dbe5", marginTop: 16, fontSize: 16 }}>{status}</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  );
}

export default function QrCodePage() {
  return (
    <Suspense fallback={
      <div style={containerStyle}>
        <div style={spinnerStyle} />
        <p style={{ color: "#d7dbe5", marginTop: 16, fontSize: 16 }}>Yukleniyor...</p>
      </div>
    }>
      <QrCodeInner />
    </Suspense>
  );
}

const containerStyle: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: 20,
  textAlign: "center",
};

const spinnerStyle: React.CSSProperties = {
  width: 40,
  height: 40,
  border: "3px solid #c8aa6e",
  borderTopColor: "transparent",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
};

const btnStyle: React.CSSProperties = {
  marginTop: 16,
  padding: "10px 24px",
  background: "#c8aa6e",
  color: "#0a1428",
  border: "none",
  borderRadius: 8,
  fontSize: 15,
  fontWeight: 600,
  cursor: "pointer",
};
