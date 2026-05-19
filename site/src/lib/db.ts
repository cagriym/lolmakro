import fs from "fs";
import path from "path";
import initSqlJs from "sql.js";

const DB_PATH = path.join(process.cwd(), "data", "lolmakro.db");

let db: any = null;

export async function getDb(): Promise<any> {
  if (db) return db;

  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const SQL = await initSqlJs();
  
  if (fs.existsSync(DB_PATH)) {
    const buffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(buffer);
  } else {
    db = new SQL.Database();
  }

  db.run("PRAGMA journal_mode=WAL");
  initTables(db);
  return db;
}

function initTables(db: any) {
  db.run(`
    CREATE TABLE IF NOT EXISTS pcs (
      device_id TEXT PRIMARY KEY,
      remote_url TEXT NOT NULL,
      pc_name TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now')),
      last_seen TEXT DEFAULT (datetime('now'))
    )
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS tokens (
      token TEXT PRIMARY KEY,
      device_id TEXT NOT NULL,
      purpose TEXT NOT NULL DEFAULT 'pair',
      expires_at TEXT NOT NULL,
      used INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (device_id) REFERENCES pcs(device_id)
    )
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS pairings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      device_id TEXT NOT NULL,
      mobile_id TEXT NOT NULL,
      paired_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (device_id) REFERENCES pcs(device_id)
    )
  `);
  saveDb();
}

function saveDb() {
  try {
    const data = db.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(DB_PATH, buffer);
  } catch {}
}

export function saveAfter(db: any, fn: () => void) {
  fn();
  saveDb();
}
