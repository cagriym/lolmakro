import { NextRequest, NextResponse } from "next/server";
import { getDb, saveAfter } from "@/lib/db";
import { generateMobileId } from "@/lib/token";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { token, mobile_id } = body;

    if (!token) {
      return NextResponse.json({ error: "token required" }, { status: 400 });
    }

    const db = await getDb();

    const rows = db.exec(
      `SELECT t.*, p.remote_url, p.pc_name
       FROM tokens t
       JOIN pcs p ON p.device_id = t.device_id
       WHERE t.token = ? AND t.used = 0 AND t.expires_at > datetime('now')`,
      { bind: [token] }
    );

    if (rows.length === 0) {
      const exists = db.exec(
        "SELECT used FROM tokens WHERE token = ?", { bind: [token] }
      );
      const msg = exists.length > 0 ? "Token already used" : "Token invalid or expired";
      return NextResponse.json({ error: msg }, { status: 401 });
    }

    const row = rows[0].values[0];
    const deviceId = row[1] as string;
    const remoteUrl = row[5] as string;
    const pcName = row[6] as string;
    const mid = mobile_id || generateMobileId();

    saveAfter(db, () => {
      db.run("UPDATE tokens SET used = 1 WHERE token = ?", [token]);
      db.run(
        "INSERT OR IGNORE INTO pairings (device_id, mobile_id) VALUES (?, ?)",
        [deviceId, mid]
      );
    });

    return NextResponse.json({
      status: "ok",
      device_id: deviceId,
      remote_url: remoteUrl,
      pc_name: pcName,
      mobile_id: mid,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
