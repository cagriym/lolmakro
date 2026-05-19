import { NextRequest, NextResponse } from "next/server";
import { getDb, saveAfter } from "@/lib/db";
import { generateDeviceId } from "@/lib/token";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { remote_url, device_id, pc_name } = body;

    if (!remote_url) {
      return NextResponse.json({ error: "remote_url required" }, { status: 400 });
    }

    const db = await getDb();
    const id = device_id || generateDeviceId();

    saveAfter(db, () => {
      const existing = db.exec(
        "SELECT device_id FROM pcs WHERE device_id = ?", { bind: [id] }
      );
      if (existing.length > 0) {
        db.run(
          "UPDATE pcs SET remote_url = ?, pc_name = COALESCE(?, pc_name), last_seen = datetime('now') WHERE device_id = ?",
          [remote_url, pc_name || "", id]
        );
      } else {
        db.run(
          "INSERT INTO pcs (device_id, remote_url, pc_name) VALUES (?, ?, ?)",
          [id, remote_url, pc_name || ""]
        );
      }
    });

    return NextResponse.json({ status: "ok", device_id: id });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
