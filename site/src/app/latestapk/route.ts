import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), "public", "apk", "version.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    const data = JSON.parse(raw);
    const origin = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
    data.download_url = `${origin}/apk/app-release.apk`;
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { version: "0.0.0", error: "Version info not found" },
      { status: 500 }
    );
  }
}
