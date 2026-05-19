import { NextRequest, NextResponse } from "next/server";
import { getDb, saveAfter } from "@/lib/db";
import { generateToken } from "@/lib/token";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { device_id } = body;

    if (!device_id) {
      return NextResponse.json({ error: "device_id required" }, { status: 400 });
    }

    const db = await getDb();
    const pc = db.exec(
      "SELECT device_id FROM pcs WHERE device_id = ?", { bind: [device_id] }
    );
    if (pc.length === 0) {
      return NextResponse.json({ error: "PC not registered" }, { status: 404 });
    }

    const token = generateToken();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

    saveAfter(db, () => {
      db.run(
        "INSERT INTO tokens (token, device_id, purpose, expires_at) VALUES (?, ?, 'pair', ?)",
        [token, device_id, expiresAt]
      );
    });

    return NextResponse.json({ status: "ok", token, expires_at: expiresAt });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
