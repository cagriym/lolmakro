import { NextResponse } from "next/server";
import { getDb, saveAfter } from "@/lib/db";
import { generateToken } from "@/lib/token";

export async function GET() {
  try {
    const db = await getDb();

    const rows = db.exec(
      "SELECT device_id, remote_url FROM pcs ORDER BY rowid DESC LIMIT 1"
    );

    if (rows.length === 0 || rows[0].values.length === 0) {
      return NextResponse.json(
        { error: "Kayitli PC bulunamadi. Uygulamayi PC'nde calistir." },
        { status: 404 }
      );
    }

    const [device_id, remote_url] = rows[0].values[0] as [string, string];
    const token = generateToken();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

    saveAfter(db, () => {
      db.run(
        "INSERT INTO tokens (token, device_id, purpose, expires_at) VALUES (?, ?, 'pair', ?)",
        [token, device_id, expiresAt]
      );
    });

    const siteOrigin = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

    return NextResponse.json({
      status: "ok",
      token,
      qr_url: `${siteOrigin}/qrcode?token=${encodeURIComponent(token)}`,
      remote_url,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
