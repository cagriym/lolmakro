import { useCallback, useEffect, useMemo, useState } from "react";
import "./HomePage.css";

type RuneSlotKey = "keystone" | "primary1" | "primary2" | "primary3" | "secondary1" | "secondary2" | "shard1" | "shard2" | "shard3";
type QueueCategoryKey = "summoners_rift" | "aram" | "arena" | "other";

const API_BASE = import.meta.env.VITE_API_BASE || window.location.origin;
const SLOT_INDEX: Record<RuneSlotKey, number> = { keystone: 0, primary1: 1, primary2: 2, primary3: 3, secondary1: 4, secondary2: 5, shard1: 6, shard2: 7, shard3: 8 };
const SHARDS: Record<"shard1" | "shard2" | "shard3", number[]> = { shard1: [5008, 5005, 5007], shard2: [5008, 5002, 5003], shard3: [5001, 5002, 5003] };
const DEFAULT_PERKS = [8005, 9104, 9105, 8014, 8304, 8345, 5008, 5008, 5002];
const DDRAGON_SPELL_BASE = "https://ddragon.leagueoflegends.com/cdn/14.10.1/img/spell";
const SPELL_FALLBACK_META: Record<number, { name: string; icon: string }> = {
  1: { name: "Cleanse", icon: "SummonerBoost.png" },
  3: { name: "Exhaust", icon: "SummonerExhaust.png" },
  4: { name: "Flash", icon: "SummonerFlash.png" },
  6: { name: "Ghost", icon: "SummonerHaste.png" },
  7: { name: "Heal", icon: "SummonerHeal.png" },
  11: { name: "Smite", icon: "SummonerSmite.png" },
  12: { name: "Teleport", icon: "SummonerTeleport.png" },
  13: { name: "Clarity", icon: "SummonerMana.png" },
  14: { name: "Ignite", icon: "SummonerDot.png" },
  21: { name: "Barrier", icon: "SummonerBarrier.png" },
  32: { name: "Mark", icon: "SummonerSnowball.png" },
}
const CORE_QUEUE_IDS = new Set([400, 420, 430, 440, 450, 1700, 1704, 1900, 1020, 1010, 900, 840, 850, 860, 870, 880]);
const SEARCH_TIMER_STORAGE_KEY = "lol_mobile_search_started_at_ms";

const QUEUE_CATEGORY_META: Record<QueueCategoryKey, { title: string; subtitle: string; icon: string }> = {
  summoners_rift: { title: "Sihirdar Vadisi", subtitle: "5v5 Klasik", icon: "SR" },
  aram: { title: "ARAM", subtitle: "Howling Abyss", icon: "AR" },
  arena: { title: "Arena ve Arbedeler", subtitle: "Özel Modlar", icon: "AN" },
  other: { title: "Diğer", subtitle: "Alternatif Modlar", icon: "DG" },
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    const detail = typeof body === "object" && body && "detail" in body ? String((body as { detail?: unknown }).detail) : typeof body === "string" ? body : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return body as T;
}

function icon(path?: string, url?: string): string | undefined {
  if (url) return url.startsWith("http") ? url : `${API_BASE}${url}`;
  if (path) return `${API_BASE}/api/asset?path=${encodeURIComponent(path)}`;
  return undefined;
}

function normPerks(raw: unknown): number[] {
  const out: number[] = Array.isArray(raw) ? raw.filter((x): x is number => typeof x === "number") : [];
  while (out.length < 9) out.push(DEFAULT_PERKS[out.length]);
  return out.slice(0, 9);
}

function memberName(m: any, idx: number): string {
  const direct = [m?.displayName, m?.summonerName].find((x) => typeof x === "string" && x.trim() && !["unknown", "anonymous", "anon", "bilinmeyen oyuncu"].includes(x.trim().toLowerCase()));
  if (direct) return String(direct).trim();
  const g = typeof m?.gameName === "string" ? m.gameName.trim() : "";
  const t = typeof m?.tagLine === "string" ? m.tagLine.trim() : typeof m?.gameTag === "string" ? m.gameTag.trim() : "";
  if (g && t) return `${g}#${t}`;
  if (g) return g;
  return `Oyuncu ${idx + 1}`;
}

function currentAction(session: any, type: "pick" | "ban"): any | null {
  if (!session?.actions || !Array.isArray(session.actions)) return null;
  for (const turn of session.actions) {
    if (!Array.isArray(turn)) continue;
    for (const a of turn) {
      if (!a || a.type !== type || a.actorCellId !== session.localPlayerCellId || a.completed) continue;
      return a;
    }
  }
  return null;
}

function fromState(s: any): any | null {
  const fromPage = s?.currentRunePage;
  const fromSelection = s?.mySelection;
  const primaryStyleId = typeof fromPage?.primaryStyleId === "number"
    ? fromPage.primaryStyleId
    : (typeof fromSelection?.primaryStyleId === "number" ? fromSelection.primaryStyleId : null);
  const subStyleId = typeof fromPage?.subStyleId === "number"
    ? fromPage.subStyleId
    : (typeof fromSelection?.subStyleId === "number" ? fromSelection.subStyleId : null);
  const selectedPerkIds = Array.isArray(fromPage?.selectedPerkIds)
    ? fromPage.selectedPerkIds
    : (Array.isArray(fromSelection?.selectedPerkIds) ? fromSelection.selectedPerkIds : null);
  if (typeof primaryStyleId !== "number" || typeof subStyleId !== "number" || !Array.isArray(selectedPerkIds)) return null;
  return {
    name: fromPage?.name || "Mobil Set",
    primaryStyleId,
    subStyleId,
    selectedPerkIds: normPerks(selectedPerkIds),
    spell1Id: typeof s?.mySelection?.spell1Id === "number" ? s.mySelection.spell1Id : 4,
    spell2Id: typeof s?.mySelection?.spell2Id === "number" ? s.mySelection.spell2Id : 14,
  };
}

function presetMatch(presets: any[], w: any | null): number | null {
  if (!w || !presets.length) return null;
  let best = -1;
  let score = -1;
  presets.forEach((p, i) => {
    let s = 0;
    if (p.primaryStyleId === w.primaryStyleId) s += 3;
    if (p.subStyleId === w.subStyleId) s += 2;
    for (let k = 0; k < 9; k += 1) if (p.selectedPerkIds?.[k] === w.selectedPerkIds[k]) s += 1;
    if (p.spells?.spell1Id === w.spell1Id && p.spells?.spell2Id === w.spell2Id) s += 2;
    if (s > score) {
      score = s;
      best = i;
    }
  });
  return best >= 0 ? best : null;
}

function queueCategoryOf(queue: any): QueueCategoryKey {
  const id = typeof queue?.id === "number" ? queue.id : -1;
  const name = String(queue?.name || "").toLowerCase();

  if ([400, 420, 430, 440, 490].includes(id)) return "summoners_rift";
  if ([450, 900, 1010, 1020].includes(id) || name.includes("aram") || name.includes("abyss")) return "aram";
  if ([1700, 1704, 1900].includes(id) || name.includes("arena") || name.includes("urf") || name.includes("arbed")) return "arena";
  return "other";
}

function queueLabel(queue: any): string {
  const id = typeof queue?.id === "number" ? queue.id : -1;
  const custom: Record<number, string> = {
    400: "Normal Draft",
    420: "Dereceli Solo/Duo",
    430: "Normal Kör Seçim",
    440: "Dereceli Flex",
    450: "ARAM",
    490: "Quickplay",
    1700: "Arena",
    1704: "Arena 2v2",
    1900: "URF",
    1020: "Tekli ARAM",
    1010: "Kar Savaşı RURF",
    900: "ARURF",
    840: "Beginner Bot",
    850: "Intermediate Bot",
    860: "ARAM Bot",
    870: "Intro Bot",
    880: "Custom Bot",
  };
  return custom[id] || String(queue?.name || `Queue ${id}`);
}

function laneLabel(raw: unknown): string {
  const key = String(raw || "").toUpperCase();
  const map: Record<string, string> = {
    TOP: "ÜST",
    JUNGLE: "ORMAN",
    MIDDLE: "ORTA",
    MID: "ORTA",
    BOTTOM: "ALT",
    ADC: "ALT",
    UTILITY: "DESTEK",
    SUPPORT: "DESTEK",
    UNSELECTED: "BELİRSİZ",
    FILL: "DOLDUR",
  };
  return map[key] || (key ? key : "BELİRSİZ");
}

function memberLaneSummary(member: any): string {
  const first = laneLabel(member?.firstPositionPreference || member?.assignedPosition || member?.position);
  const second = laneLabel(member?.secondPositionPreference);
  return `${first} / ${second}`;
}

function toOptionalInt(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return Math.floor(value);
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return Math.floor(parsed);
  }
  return null;
}

function pickFirstInt(payload: any, keys: string[]): number | null {
  for (const key of keys) {
    const out = toOptionalInt(payload?.[key]);
    if (out !== null) return out;
  }
  return null;
}

function perkId(perk: any): number | null {
  if (typeof perk === "number" && Number.isFinite(perk)) return perk;
  if (perk && typeof perk.id === "number" && Number.isFinite(perk.id)) return perk.id;
  return null;
}

function firstPerkId(slot: any): number | null {
  const perks = Array.isArray(slot?.perks) ? slot.perks : [];
  for (const perk of perks) {
    const id = perkId(perk);
    if (id !== null) return id;
  }
  return null;
}

function buildDefaultPerksForStyles(primaryStyle: any, secondaryStyle: any, previous: number[]): number[] {
  const out = [...normPerks(previous)];
  const primarySlots = Array.isArray(primaryStyle?.slots) ? primaryStyle.slots : [];
  const secondarySlots = Array.isArray(secondaryStyle?.slots) ? secondaryStyle.slots : [];

  const primaryDefaults = [
    firstPerkId(primarySlots[0]),
    firstPerkId(primarySlots[1]),
    firstPerkId(primarySlots[2]),
    firstPerkId(primarySlots[3]),
  ];
  const secondaryDefaults = [firstPerkId(secondarySlots[1]), firstPerkId(secondarySlots[2])];

  primaryDefaults.forEach((id, idx) => {
    if (id !== null) out[idx] = id;
  });
  secondaryDefaults.forEach((id, idx) => {
    if (id !== null) out[4 + idx] = id;
  });

  return normPerks(out);
}

function normalizeSwapState(raw: unknown): string {
  const state = String(raw || "UNKNOWN").toUpperCase();
  if (state.includes("RECEIVE") || state.includes("INCOMING")) return "INCOMING";
  if (state.includes("SENT") || state.includes("OUTGOING") || state.includes("REQUESTED")) return "OUTGOING";
  if (state.includes("ACCEPT")) return "ACCEPTED";
  if (state.includes("DECLIN")) return "DECLINED";
  if (state.includes("CANCEL")) return "CANCELED";
  if (state.includes("COMPLETE")) return "COMPLETED";
  if (state.includes("PENDING")) return "PENDING";
  if (state.includes("AVAILABLE") || state.includes("IDLE") || state.includes("OPEN")) return "AVAILABLE";
  return state;
}

function swapStateLabel(raw: unknown): string {
  const state = normalizeSwapState(raw);
  const map: Record<string, string> = {
    INCOMING: "Sana İstek Geldi",
    OUTGOING: "İstek Gönderildi",
    ACCEPTED: "Kabul Edildi",
    DECLINED: "Reddedildi",
    CANCELED: "İptal Edildi",
    COMPLETED: "Tamamlandı",
    PENDING: "Beklemede",
    AVAILABLE: "Hazır",
    UNKNOWN: "Bilinmiyor",
  };
  return map[state] || state;
}

function buildSwapSummary(swap: any, rosterByCell: Map<number, string>): string {
  const fromCell = pickFirstInt(swap, ["requesterCellId", "offererCellId", "sourceCellId", "fromCellId", "initiatorCellId", "proposerCellId", "cellId"]);
  const toCell = pickFirstInt(swap, ["receiverCellId", "targetCellId", "toCellId", "requestedCellId", "acceptorCellId"]);
  const fromName = fromCell !== null ? rosterByCell.get(fromCell) : null;
  const toName = toCell !== null ? rosterByCell.get(toCell) : null;

  if (fromName && toName) return `${fromName} -> ${toName}`;
  if (fromName) return `İstek sahibi: ${fromName}`;
  if (toName) return `Hedef: ${toName}`;
  return "Oyuncu bilgisi alınamadı";
}

function getSwapActions(rawState: unknown): Array<{ type: "request" | "accept" | "decline" | "cancel"; label: string }> {
  const state = normalizeSwapState(rawState);
  if (state === "INCOMING") {
    return [
      { type: "accept", label: "Kabul" },
      { type: "decline", label: "Reddet" },
    ];
  }
  if (state === "OUTGOING" || state === "PENDING") {
    return [{ type: "cancel", label: "İptal Et" }];
  }
  if (state === "ACCEPTED" || state === "DECLINED" || state === "CANCELED" || state === "COMPLETED") {
    return [];
  }
  return [{ type: "request", label: "İstek Gönder" }];
}

function champIcon(championId: number | null | undefined): string | undefined {
  if (!championId || championId <= 0) return undefined;
  const path = `/lol-game-data/assets/v1/champion-icons/${championId}.png`;
  return `${API_BASE}/api/asset?path=${encodeURIComponent(path)}`;
}

function formatDuration(seconds: number): string {
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function spellNameById(spellMap: Map<number, any>, spellId: number): string {
  const known = spellMap.get(spellId)?.name;
  if (typeof known === "string" && known.trim()) return known;
  return SPELL_FALLBACK_META[spellId]?.name || `Büyü ${spellId}`;
}

function spellIconById(spellMap: Map<number, any>, spellId: number): string | undefined {
  const known = icon(spellMap.get(spellId)?.iconPath, spellMap.get(spellId)?.iconUrl);
  if (known) return known;
  const fallback = SPELL_FALLBACK_META[spellId];
  if (!fallback) return undefined;
  return `${DDRAGON_SPELL_BASE}/${fallback.icon}`;
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function parseSearchStartMs(raw: unknown): number | null {
  const num = toFiniteNumber(raw);
  if (num !== null) {
    if (num > 1_000_000_000_000) return Math.floor(num);
    if (num > 1_000_000_000) return Math.floor(num * 1000);
  }
  if (typeof raw === "string") {
    const ms = Date.parse(raw);
    if (Number.isFinite(ms)) return ms;
  }
  return null;
}

function searchElapsedFromLcu(searchState: any, nowMs: number): number | null {
  if (!searchState || typeof searchState !== "object") return null;

  const secondKeys = ["timeInQueueSeconds", "elapsedTimeSeconds", "searchTimeSeconds", "timeInQueueSec"];
  for (const key of secondKeys) {
    const value = toFiniteNumber(searchState[key]);
    if (value !== null && value >= 0) return Math.floor(value);
  }

  const millisKeys = ["timeInQueueMillis", "timeInQueueMs", "timeInQueueMilliseconds", "elapsedTimeMs", "elapsedTimeMillis"];
  for (const key of millisKeys) {
    const value = toFiniteNumber(searchState[key]);
    if (value !== null && value >= 0) return Math.floor(value / 1000);
  }

  const ambiguousTimeInQueue = toFiniteNumber(searchState.timeInQueue);
  if (ambiguousTimeInQueue !== null && ambiguousTimeInQueue >= 0) {
    if (ambiguousTimeInQueue > 8 * 60 * 60) return Math.floor(ambiguousTimeInQueue / 1000);
    return Math.floor(ambiguousTimeInQueue);
  }

  const startKeys = ["searchStartTime", "searchStartTimeMs", "searchStartTimeMillis", "queueStartTime", "queuedAt", "startTime", "createdAt"];
  for (const key of startKeys) {
    const startMs = parseSearchStartMs(searchState[key]);
    if (!startMs) continue;
    const elapsed = Math.floor((nowMs - startMs) / 1000);
    if (elapsed >= 0) return elapsed;
  }

  return null;
}

const ROLE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "TOP", label: "Üst" },
  { value: "JUNGLE", label: "Orman" },
  { value: "MIDDLE", label: "Orta" },
  { value: "BOTTOM", label: "Alt" },
  { value: "UTILITY", label: "Destek" },
  { value: "FILL", label: "Doldur" },
];

export function HomePage() {
  const [state, setState] = useState<any>({ connected: false, phase: "None" });
  const [champions, setChampions] = useState<any[]>([]);
  const [spells, setSpells] = useState<any[]>([]);
  const [styles, setStyles] = useState<any[]>([]);
  const [queues, setQueues] = useState<any[]>([]);
  const [presets, setPresets] = useState<any[]>([]);
  const [working, setWorking] = useState<any | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<number | null>(null);
  const [queueId, setQueueId] = useState<number | null>(null);
  const [queueCategory, setQueueCategory] = useState<QueueCategoryKey>("summoners_rift");
  const [openRune, setOpenRune] = useState<RuneSlotKey | null>(null);
  const [openSpell, setOpenSpell] = useState<1 | 2 | null>(null);
  const [championFilter, setChampionFilter] = useState("");
  const [selectedChampionId, setSelectedChampionId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [queueUpdatePending, setQueueUpdatePending] = useState<number | null>(null);
  const [searchStartedAtMs, setSearchStartedAtMs] = useState<number | null>(null);
  const [searchElapsedSec, setSearchElapsedSec] = useState(0);
  const [firstRole, setFirstRole] = useState<string>("TOP");
  const [secondRole, setSecondRole] = useState<string>("JUNGLE");
  const [roleUpdatePending, setRoleUpdatePending] = useState(false);

  const phase = state?.phase || "None";
  const rawSearchState = String(state?.matchmakingSearchState?.searchState || "");
  const isSearching = rawSearchState === "SEARCHING" || phase === "Matchmaking";
  const activeQueueId = Number(queueId ?? state?.lobby?.gameConfig?.queueId ?? 0);
  const isAramLikeMode = [450, 900, 1010, 1020].includes(activeQueueId);
  const queueNeedsRoleSelection = [400, 420, 440].includes(activeQueueId);
  const pickAction = currentAction(state?.champSelect, "pick");
  const banAction = currentAction(state?.champSelect, "ban");
  const action = banAction || pickAction;
  const championId = typeof state?.mySelection?.championId === "number" ? state.mySelection.championId : 0;
  const benchChampionIds = useMemo(() => {
    const rawBench = Array.isArray(state?.champSelect?.benchChampionIds) ? state.champSelect.benchChampionIds : [];
    const extraBench = Array.isArray(state?.champSelectOptions?.benchChampionIds) ? state.champSelectOptions.benchChampionIds : [];
    const uniq = new Set<number>();
    [...rawBench, ...extraBench].forEach((x: any) => {
      if (typeof x === "number" && x > 0) uniq.add(x);
    });
    return Array.from(uniq);
  }, [state?.champSelect?.benchChampionIds, state?.champSelectOptions?.benchChampionIds]);
  const benchChampions = useMemo(
    () => benchChampionIds.map((id: number) => champions.find((c) => c.id === id) || { id, name: `Şampiyon ${id}` }),
    [benchChampionIds, champions],
  );
  const availableChampionCards = useMemo(() => {
    const ids = new Set<number>();
    const pickableIds = Array.isArray(state?.champSelectOptions?.pickableChampionIds)
      ? state.champSelectOptions.pickableChampionIds
      : [];
    const mySelectionPickable = Array.isArray(state?.mySelection?.pickableChampionIds)
      ? state.mySelection.pickableChampionIds
      : [];
    const mergedPickable = [...pickableIds, ...mySelectionPickable].filter((id: any) => typeof id === "number" && id > 0);
    const looksLikeAramCards = mergedPickable.length > 0 && mergedPickable.length <= 20;
    if (championId > 0) ids.add(championId);
    if (isAramLikeMode || looksLikeAramCards) {
      mergedPickable.forEach((id: any) => {
        if (typeof id === "number" && id > 0) ids.add(id);
      });
    }
    benchChampionIds.forEach((id) => {
      if (id > 0) ids.add(id);
    });
    const rawCards = Array.from(ids).slice(0, 12).map((id) => champions.find((c) => c.id === id) || { id, name: `Şampiyon ${id}` });
    const uniqueByName = new Set<string>();
    const deduped: any[] = [];
    for (const card of rawCards) {
      const key = String(card?.name || "").trim().toLowerCase();
      if (!key) continue;
      if (uniqueByName.has(key)) continue;
      uniqueByName.add(key);
      deduped.push(card);
      if (deduped.length >= 6) break;
    }
    return deduped;
  }, [benchChampionIds, championId, champions, isAramLikeMode, state?.champSelectOptions?.pickableChampionIds, state?.mySelection?.pickableChampionIds]);
  const availableCardIdSet = useMemo(() => new Set(availableChampionCards.map((c: any) => Number(c?.id || 0))), [availableChampionCards]);
  const availableCardNameSet = useMemo(
    () =>
      new Set(
        availableChampionCards
          .map((c: any) => String(c?.name || "").trim().toLowerCase())
          .filter((x: string) => x.length > 0),
      ),
    [availableChampionCards],
  );
  const benchOnlyChampions = useMemo(
    () =>
      benchChampions.filter((c: any) => {
        const id = Number(c?.id || 0);
        const name = String(c?.name || "").trim().toLowerCase();
        if (availableCardIdSet.has(id)) return false;
        if (name && availableCardNameSet.has(name)) return false;
        return true;
      }),
    [availableCardIdSet, availableCardNameSet, benchChampions],
  );

  const perkMap = useMemo(() => {
    const map = new Map<number, any>();
    for (const st of styles) for (const slot of st?.slots || []) for (const perk of slot?.perks || []) if (typeof perk?.id === "number") map.set(perk.id, perk);
    return map;
  }, [styles]);

  const styleMap = useMemo(() => {
    const map = new Map<number, any>();
    for (const st of styles) map.set(st.id, st);
    return map;
  }, [styles]);

  const spellMap = useMemo(() => {
    const map = new Map<number, any>();
    for (const sp of spells) map.set(sp.id, sp);
    return map;
  }, [spells]);

  const queueGroups = useMemo(() => {
    const groups: Record<QueueCategoryKey, any[]> = {
      summoners_rift: [],
      aram: [],
      arena: [],
      other: [],
    };

    const seen = new Set<number>();
    for (const queue of queues) {
      const id = typeof queue?.id === "number" ? queue.id : -1;
      if (id <= 0 || seen.has(id)) continue;
      if (!CORE_QUEUE_IDS.has(id)) {
        const name = String(queue?.name || "").toLowerCase();
        const maybeUseful = name.includes("aram") || name.includes("arena") || name.includes("urf") || name.includes("dereceli") || name.includes("normal");
        if (!maybeUseful) continue;
      }
      seen.add(id);

      const category = queueCategoryOf(queue);
      groups[category].push({
        id,
        name: queueLabel(queue),
        description: String(queue?.description || ""),
      });
    }

    for (const key of Object.keys(groups) as QueueCategoryKey[]) {
      groups[key].sort((a, b) => a.name.localeCompare(b.name, "tr"));
    }
    return groups;
  }, [queues]);

  const refreshState = useCallback(async () => {
    try {
      const next = await api<any>("/api/state");
      setState(next);
      setError("");
      return next;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    }
  }, []);

  useEffect(() => {
    let stop = false;
    let timer: number | null = null;
    const tick = async () => {
      if (stop) return;
      await refreshState();
      if (!stop) timer = window.setTimeout(tick, 1000);
    };
    void Promise.all([
      api<any[]>("/api/champions").then((x) => setChampions(Array.isArray(x) ? x : [])).catch(() => undefined),
      api<any[]>("/api/spells").then((x) => setSpells(Array.isArray(x) ? x : [])).catch(() => undefined),
      api<any[]>("/api/runes/styles").then((x) => setStyles(Array.isArray(x) ? x : [])).catch(() => undefined),
      api<any[]>("/api/lobby/queues").then((x) => setQueues(Array.isArray(x) ? x : [])).catch(() => undefined),
    ]);
    void tick();
    return () => {
      stop = true;
      if (timer !== null) window.clearTimeout(timer);
    };
  }, [refreshState]);

  useEffect(() => {
    if (phase !== "ChampSelect") return;
    void api<any[]>("/api/spells").then((x) => setSpells(Array.isArray(x) ? x : [])).catch(() => undefined);
  }, [phase]);

  useEffect(() => {
    const f = fromState(state);
    if (!f) return;
    setWorking((prev: any) => {
      if (!prev) return f;
      const a = `${prev.primaryStyleId}|${prev.subStyleId}|${prev.selectedPerkIds.join(",")}|${prev.spell1Id}|${prev.spell2Id}`;
      const b = `${f.primaryStyleId}|${f.subStyleId}|${f.selectedPerkIds.join(",")}|${f.spell1Id}|${f.spell2Id}`;
      return a === b ? prev : f;
    });
  }, [state]);

  useEffect(() => {
    if (phase !== "ChampSelect") return;
    if (working) return;
    if (!Array.isArray(styles) || styles.length < 2) return;
    const primary = styles[0];
    const secondary = styles.find((s: any) => s?.id !== primary?.id) || styles[1];
    if (!primary || !secondary) return;
    setWorking({
      name: "Mobil Set",
      primaryStyleId: Number(primary.id),
      subStyleId: Number(secondary.id),
      selectedPerkIds: buildDefaultPerksForStyles(primary, secondary, DEFAULT_PERKS),
      spell1Id: typeof state?.mySelection?.spell1Id === "number" ? state.mySelection.spell1Id : 4,
      spell2Id: typeof state?.mySelection?.spell2Id === "number" ? state.mySelection.spell2Id : 14,
    });
  }, [phase, state?.mySelection?.spell1Id, state?.mySelection?.spell2Id, styles, working]);
  useEffect(() => {
    const currentQueueId = state?.lobby?.gameConfig?.queueId;
    if (!currentQueueId) return;

    if (queueUpdatePending !== null) {
      if (currentQueueId === queueUpdatePending) {
        setQueueUpdatePending(null);
      }
    } else {
      setQueueId(currentQueueId);
    }

    const match = queues.find((q) => q?.id === currentQueueId);
    if (match) setQueueCategory(queueCategoryOf(match));
  }, [queueUpdatePending, queues, state?.lobby?.gameConfig?.queueId]);

  useEffect(() => {
    if (roleUpdatePending) return;
    const first = String(state?.myLobbyMember?.firstPositionPreference || "").toUpperCase();
    const second = String(state?.myLobbyMember?.secondPositionPreference || "").toUpperCase();
    const allowed = new Set(ROLE_OPTIONS.map((x) => x.value));
    if (allowed.has(first)) setFirstRole(first);
    if (allowed.has(second)) setSecondRole(second);
  }, [roleUpdatePending, state?.myLobbyMember?.firstPositionPreference, state?.myLobbyMember?.secondPositionPreference]);

  useEffect(() => {
    if (!isSearching) {
      setSearchStartedAtMs(null);
      setSearchElapsedSec(0);
      try {
        window.localStorage.removeItem(SEARCH_TIMER_STORAGE_KEY);
      } catch {
        // ignore storage errors
      }
      return;
    }
    const serverNow = parseSearchStartMs(state?.timestamp) ?? Date.now();
    const lcuElapsed = searchElapsedFromLcu(state?.matchmakingSearchState, serverNow);
    if (lcuElapsed !== null) {
      setSearchElapsedSec(lcuElapsed);
      const computedStart = serverNow - lcuElapsed * 1000;
      setSearchStartedAtMs(computedStart);
      try {
        window.localStorage.setItem(SEARCH_TIMER_STORAGE_KEY, String(computedStart));
      } catch {
        // ignore storage errors
      }
      return;
    }

    let fallbackStart = searchStartedAtMs;
    if (fallbackStart === null) {
      try {
        const stored = window.localStorage.getItem(SEARCH_TIMER_STORAGE_KEY);
        const parsed = stored ? Number(stored) : NaN;
        if (Number.isFinite(parsed) && parsed > 0) fallbackStart = parsed;
      } catch {
        // ignore storage errors
      }
    }
    if (fallbackStart === null) {
      fallbackStart = serverNow;
      setSearchStartedAtMs(fallbackStart);
      try {
        window.localStorage.setItem(SEARCH_TIMER_STORAGE_KEY, String(fallbackStart));
      } catch {
        // ignore storage errors
      }
    }
    setSearchElapsedSec(Math.max(0, Math.floor((serverNow - fallbackStart) / 1000)));
  }, [isSearching, searchStartedAtMs, state?.matchmakingSearchState, state?.timestamp]);

  useEffect(() => {
    if (phase !== "ChampSelect" || championId <= 0) {
      setPresets([]);
      setSelectedPreset(null);
      return;
    }
    let stop = false;
    void api<any[]>(`/api/builds/suggestions/${championId}`)
      .then((rows) => {
        if (stop) return;
        const normalized = (Array.isArray(rows) ? rows : []).slice(0, 3).map((r, i) => ({ ...r, slotLabel: r.slotLabel || `Opsiyon ${i + 1}`, name: r.name || `Set ${i + 1}`, selectedPerkIds: normPerks(r.selectedPerkIds) }));
        setPresets(normalized);
      })
      .catch(() => {
        if (!stop) setPresets([]);
      });
    return () => {
      stop = true;
    };
  }, [championId, phase]);

  useEffect(() => {
    setSelectedPreset(presetMatch(presets, working));
  }, [presets, working]);

  const toast = useCallback((t: string) => {
    setMsg(t);
    window.setTimeout(() => setMsg((x) => (x === t ? "" : x)), 2200);
  }, []);

  const post = useCallback(async (path: string, payload: any, okText: string) => {
    setBusy(true);
    setError("");
    try {
      await api(path, { method: "POST", body: payload ? JSON.stringify(payload) : undefined });
      toast(okText);
      await refreshState();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [refreshState, toast]);

  const selectQueueAndApply = useCallback(
    async (nextQueueId: number) => {
      setQueueId(nextQueueId);
      setQueueUpdatePending(nextQueueId);
      setBusy(true);
      setError("");
      try {
        const applyQueue = async () =>
          api("/api/lobby/queue", {
            method: "POST",
            body: JSON.stringify({ queueId: nextQueueId }),
          });

        try {
          await applyQueue();
        } catch (firstError) {
          const text = firstError instanceof Error ? firstError.message : String(firstError);
          const maybeMatchmakingConflict =
            text.includes("Matchmaking") ||
            text.includes("Arama aciksa once durdur") ||
            text.includes("Queue change is not allowed");

          if (!maybeMatchmakingConflict) {
            throw firstError;
          }

          await api("/api/lobby/matchmaking/stop", { method: "POST" }).catch(() => undefined);
          await new Promise((resolve) => window.setTimeout(resolve, 400));
          await applyQueue();
        }

        toast("Lobi modu değişti");
        await refreshState();
      } catch (e) {
        setQueueUpdatePending(null);
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [refreshState, toast],
  );

  const applyPositionPreferences = useCallback(
    async (first: string, second: string) => {
      setRoleUpdatePending(true);
      try {
        await api("/api/lobby/position-preferences", {
          method: "POST",
          body: JSON.stringify({
            firstPreference: first,
            secondPreference: second,
          }),
        });
        await refreshState();
      } finally {
        setRoleUpdatePending(false);
      }
    },
    [refreshState],
  );

  const startMatchmaking = useCallback(async () => {
    if (queueNeedsRoleSelection) {
      if (!firstRole || !secondRole || firstRole === secondRole) {
        setError("Bu kuyrukta aramadan önce farklı iki mevki seçmelisin.");
        return;
      }
    }

    setBusy(true);
    setError("");
    try {
      if (queueNeedsRoleSelection) {
        await applyPositionPreferences(firstRole, secondRole);
      }
      await api("/api/lobby/matchmaking/start", { method: "POST" });
      toast("Arama başlatıldı");
      const startedAt = Date.now();
      setSearchStartedAtMs(startedAt);
      try {
        window.localStorage.setItem(SEARCH_TIMER_STORAGE_KEY, String(startedAt));
      } catch {
        // ignore storage errors
      }
      setSearchElapsedSec(0);
      await refreshState();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [applyPositionPreferences, firstRole, queueNeedsRoleSelection, refreshState, secondRole, toast]);

  const postSwap = useCallback(
    async (swapType: "champion" | "position" | "pickOrder", swapId: number, actionType: "request" | "accept" | "decline" | "cancel", okText: string) => {
      setBusy(true);
      setError("");
      try {
        await api("/api/champ-select/swap", {
          method: "POST",
          body: JSON.stringify({ swapType, swapId, action: actionType }),
        });
        toast(okText);
        await refreshState();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [refreshState, toast],
  );

  const applyLoadout = useCallback(async (next: any, okText: string) => {
    if (phase !== "ChampSelect") {
      setError("Rün ve büyü değişikliği sadece Şampiyon Seçimi aşamasında yapılabilir.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await Promise.all([
        api("/api/runes/apply", { method: "POST", body: JSON.stringify({ name: next.name, primaryStyleId: next.primaryStyleId, subStyleId: next.subStyleId, selectedPerkIds: normPerks(next.selectedPerkIds) }) }),
        api("/api/champ-select/spells", { method: "POST", body: JSON.stringify({ spell1Id: next.spell1Id, spell2Id: next.spell2Id }) }),
      ]);
      setWorking(next);
      toast(okText);
      await refreshState();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [phase, refreshState, toast]);

  const selectPreset = useCallback(async (idx: number) => {
    const p = presets[idx];
    if (!p) return;
    setSelectedPreset(idx);
    await applyLoadout({ name: p.name, primaryStyleId: p.primaryStyleId, subStyleId: p.subStyleId, selectedPerkIds: normPerks(p.selectedPerkIds), spell1Id: p.spells?.spell1Id || 4, spell2Id: p.spells?.spell2Id || 14 }, `${p.slotLabel} uygulandı`);
  }, [applyLoadout, presets]);

  const runeOptions = useCallback((slot: RuneSlotKey): any[] => {
    if (!working) return [];
    const primary = styleMap.get(working.primaryStyleId);
    const secondary = styleMap.get(working.subStyleId);
    if (slot === "keystone" || slot === "primary1" || slot === "primary2" || slot === "primary3") {
      const i = slot === "keystone" ? 0 : slot === "primary1" ? 1 : slot === "primary2" ? 2 : 3;
      return (primary?.slots?.[i]?.perks || []) as any[];
    }
    if (slot === "secondary1" || slot === "secondary2") {
      const i = slot === "secondary1" ? 1 : 2;
      const direct = (secondary?.slots?.[i]?.perks || []) as any[];
      if (direct.length) return direct;
      return (secondary?.slots || []).slice(1).flatMap((x: any) => x?.perks || []);
    }
    if (slot === "shard1" || slot === "shard2" || slot === "shard3") {
      return SHARDS[slot].map((id) => perkMap.get(id) || { id, name: `Perk ${id}` });
    }
    return [];
  }, [perkMap, styleMap, working]);

  const pickRune = useCallback(async (slot: RuneSlotKey, perkId: number) => {
    if (!working) return;
    const next = { ...working, selectedPerkIds: [...working.selectedPerkIds] };
    next.selectedPerkIds[SLOT_INDEX[slot]] = perkId;
    next.selectedPerkIds = normPerks(next.selectedPerkIds);
    setOpenRune(null);
    await applyLoadout(next, "Rün seçimi güncellendi");
  }, [applyLoadout, working]);

  const pickSpell = useCallback(async (slot: 1 | 2, spellId: number) => {
    if (!working) return;
    if ((slot === 1 && working.spell2Id === spellId) || (slot === 2 && working.spell1Id === spellId)) {
      setError("Aynı büyü iki slota atanamaz.");
      return;
    }
    const next = { ...working, spell1Id: slot === 1 ? spellId : working.spell1Id, spell2Id: slot === 2 ? spellId : working.spell2Id };
    setOpenSpell(null);
    await applyLoadout(next, "Büyüler güncellendi");
  }, [applyLoadout, working]);

  const applyStyleChange = useCallback(async (kind: "primary" | "secondary", nextStyleId: number) => {
    if (!working) return;
    if (!Number.isFinite(nextStyleId) || nextStyleId <= 0) return;

    const nextPrimary = kind === "primary" ? nextStyleId : working.primaryStyleId;
    const nextSecondary = kind === "secondary" ? nextStyleId : working.subStyleId;
    if (nextPrimary === nextSecondary) {
      setError("Ana rün ve alt rün ağacı farklı olmalı.");
      return;
    }

    const primaryStyle = styleMap.get(nextPrimary);
    const secondaryStyle = styleMap.get(nextSecondary);
    if (!primaryStyle || !secondaryStyle) {
      setError("Seçilen rün ağacı verisi yüklenemedi.");
      return;
    }

    const next = {
      ...working,
      primaryStyleId: nextPrimary,
      subStyleId: nextSecondary,
      selectedPerkIds: buildDefaultPerksForStyles(primaryStyle, secondaryStyle, working.selectedPerkIds),
    };
    setOpenRune(null);
    await applyLoadout(next, "Rün ağacı güncellendi");
  }, [applyLoadout, styleMap, working]);

  const filteredChampions = useMemo(() => {
    const pickableSet = new Set<number>(
      (Array.isArray(state?.champSelectOptions?.pickableChampionIds) ? state.champSelectOptions.pickableChampionIds : [])
        .filter((id: any) => typeof id === "number" && id > 0),
    );
    const source = phase === "ChampSelect" && pickableSet.size > 0
      ? champions.filter((c) => pickableSet.has(c.id))
      : champions;
    const q = championFilter.trim().toLowerCase();
    if (!q) return source;
    return source.filter((c) => String(c?.name || "").toLowerCase().includes(q));
  }, [championFilter, champions, phase, state?.champSelectOptions?.pickableChampionIds]);

  useEffect(() => {
    if (queueGroups[queueCategory].length > 0) return;
    const firstNonEmpty = (["summoners_rift", "aram", "arena", "other"] as QueueCategoryKey[]).find((key) => queueGroups[key].length > 0);
    if (firstNonEmpty) setQueueCategory(firstNonEmpty);
  }, [queueCategory, queueGroups]);

  const activeQueueOptions = queueGroups[queueCategory] || [];
  const myTeam = Array.isArray(state?.champSelect?.myTeam) ? state.champSelect.myTeam : [];
  const enemyTeam = Array.isArray(state?.champSelect?.theirTeam) ? state.champSelect.theirTeam : [];
  const bans = state?.champSelect?.bans || {};
  const myTeamBans = Array.isArray(bans?.myTeamBans) ? bans.myTeamBans : [];
  const enemyTeamBans = Array.isArray(bans?.theirTeamBans) ? bans.theirTeamBans : [];
  const championSwaps = Array.isArray(state?.champSelectSwaps?.champion) ? state.champSelectSwaps.champion : [];
  const positionSwaps = Array.isArray(state?.champSelectSwaps?.position) ? state.champSelectSwaps.position : [];
  const pickOrderSwaps = Array.isArray(state?.champSelectSwaps?.pickOrder) ? state.champSelectSwaps.pickOrder : [];
  const rosterByCell = useMemo(() => {
    const map = new Map<number, string>();
    const teams = [...myTeam, ...enemyTeam];
    teams.forEach((member: any, idx: number) => {
      const cellId = toOptionalInt(member?.cellId);
      if (cellId === null) return;
      map.set(cellId, memberName(member, idx));
    });
    return map;
  }, [enemyTeam, myTeam]);

  const renderPerkIcon = (perkId: number, spellLike = false) => {
    const perk = perkMap.get(perkId);
    const src = icon(perk?.iconPath, perk?.iconUrl);
    return src ? <img className={spellLike ? "spell-icon" : "rune-icon"} src={src} alt={perk?.name || String(perkId)} /> : <div className={spellLike ? "spell-icon-placeholder" : "rune-icon-placeholder"} />;
  };

  const renderTeamPlayer = (member: any, index: number, enemy = false) => {
    const display = memberName(member, index);
    const champId = typeof member?.championId === "number" ? member.championId : 0;
    const champName = champions.find((c) => c.id === champId)?.name || (champId > 0 ? `Şampiyon ${champId}` : "Seçilmedi");
    const role = laneLabel(member?.assignedPosition || member?.position);
    const isLocal = !enemy && state?.champSelect?.localPlayerCellId === member?.cellId;
    const iconUrl = champIcon(champId);

    return (
      <div key={`${enemy ? "e" : "m"}-${member?.cellId ?? index}`} className={`cs-player-card ${isLocal ? "local" : ""}`}>
        <div className="cs-player-champ">
          {iconUrl ? <img src={iconUrl} alt={champName} /> : <div className="cs-player-champ-placeholder" />}
        </div>
        <div className="cs-player-meta">
          <div className="cs-player-name">{display}</div>
          <div className="cs-player-sub">{role} | {champName}</div>
        </div>
      </div>
    );
  };

  const renderBanStrip = (title: string, banIds: any[]) => (
    <div className="cs-ban-strip">
      <div className="cs-ban-title">{title}</div>
      <div className="cs-ban-list">
        {banIds.slice(0, 5).map((id: any, idx: number) => {
          const champId = typeof id === "number" ? id : 0;
          const src = champIcon(champId);
          return (
            <div key={`${title}-${idx}`} className="cs-ban-item">
              {src ? <img src={src} alt={`Ban ${champId}`} /> : <div className="cs-ban-placeholder" />}
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderSwapSection = (label: string, swapType: "champion" | "position" | "pickOrder", items: any[]) => (
    <div className="cs-swap-section">
      <div className="cs-swap-title">{label}</div>
      {items.length === 0 ? (
        <div className="cs-swap-empty">Bu aşamada uygun takas kaydı yok.</div>
      ) : (
        items.map((swap, idx) => {
          const swapId = Number(swap?.id || 0);
          const swapState = String(swap?.state || "UNKNOWN");
          const normalizedState = normalizeSwapState(swapState);
          const summary = buildSwapSummary(swap, rosterByCell);
          const actions = getSwapActions(swapState);
          return (
            <div key={`${swapType}-${swapId || idx}`} className="cs-swap-row">
              <div className="cs-swap-info">
                <strong>#{swapId || "?"}</strong>
                <span className={`cs-swap-state state-${normalizedState.toLowerCase()}`}>{swapStateLabel(swapState)}</span>
              </div>
              <div className="cs-swap-summary">{summary}</div>
              {actions.length > 0 ? (
                <div className="cs-swap-actions">
                  {actions.map((action) => (
                    <button
                      key={`${swapId}-${action.type}`}
                      type="button"
                      onClick={() => void postSwap(swapType, swapId, action.type, `${label} aksiyonu: ${action.label}`)}
                      disabled={busy || !swapId}
                      className={`swap-action-btn action-${action.type}`}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="cs-swap-empty">Bu takas için şu an aksiyon yok.</div>
              )}
            </div>
          );
        })
      )}
    </div>
  );

  if (!state?.connected) {
    return (
      <div className="home-page loading">
        <div className="loading-spinner" />
        <h2>League istemcisi bekleniyor</h2>
      </div>
    );
  }

  return (
    <div className={`home-page ${phase === "ChampSelect" ? "champ-select" : phase === "Lobby" || phase === "Matchmaking" ? "lobby-page" : phase === "InProgress" ? "ingame-page" : "loading"}`}>
      {msg ? <div className="action-message">{msg}</div> : null}
      {error ? <div className="action-message">Hata: {error}</div> : null}

      {phase === "ReadyCheck" ? (
        <div className="home-page ready-check">
          <h1>Maç Bulundu</h1>
          <button className="accept-button" type="button" onClick={() => void post("/api/ready-check/accept", {}, "Maç onaylandı")} disabled={busy}>KABUL ET</button>
        </div>
      ) : null}

      {(phase === "Lobby" || phase === "Matchmaking") ? (
        <>
          <h2>Lobi</h2>
          {queueNeedsRoleSelection ? (
            <div className="lobby-card lobby-role-card">
              <h3>Mevki Tercihin</h3>
              <div className="position-pref-grid">
                <div className="position-pref-item">
                  <label>Birincil Mevki</label>
                  <select
                    value={firstRole}
                    onChange={(e) => {
                      const next = e.target.value;
                      setFirstRole(next);
                      if (next && secondRole && next !== secondRole) {
                        void applyPositionPreferences(next, secondRole);
                      }
                    }}
                    disabled={busy}
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option key={`role-first-${opt.value}`} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="position-pref-item">
                  <label>İkincil Mevki</label>
                  <select
                    value={secondRole}
                    onChange={(e) => {
                      const next = e.target.value;
                      setSecondRole(next);
                      if (firstRole && next && firstRole !== next) {
                        void applyPositionPreferences(firstRole, next);
                      }
                    }}
                    disabled={busy}
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option key={`role-second-${opt.value}`} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          ) : null}

          <div className="lobby-card lobby-search-card">
            <div className="lobby-row">
              {isSearching ? (
                <button type="button" className="btn-danger" onClick={() => void post("/api/lobby/matchmaking/stop", {}, "Arama durduruldu")} disabled={busy}>Aramayı Durdur</button>
              ) : (
                <button type="button" className="btn-primary" onClick={() => void startMatchmaking()} disabled={busy || roleUpdatePending}>Maç Ara</button>
              )}
            </div>

            <div className="lobby-row matchmaking-timer-row">
              <span>Durum</span>
              <div className="matchmaking-timer-text">
                {isSearching ? `Aranıyor (${formatDuration(searchElapsedSec)})` : "Beklemede"}
                {queueUpdatePending ? ` | Kuyruk değiştiriliyor (${queueUpdatePending})` : ""}
              </div>
            </div>
          </div>

          <div className="lobby-members">
            <h3>Lobi Oyuncuları</h3>
            <div className="member-list">
              {(state?.lobby?.members || []).map((m: any, i: number) => (
                <div className="member-item" key={`${m?.summonerId || "m"}-${i}`}>
                  <div>
                    <div className="member-name">{memberName(m, i)}</div>
                    <div className="member-meta">{memberLaneSummary(m)}</div>
                  </div>
                  {(state?.summoner?.summonerId && m?.summonerId === state.summoner.summonerId) ? <span className="member-badge">BEN</span> : null}
                </div>
              ))}
            </div>
          </div>

          <div className="lobby-card">
            <div className="queue-category-grid">
              {(Object.keys(QUEUE_CATEGORY_META) as QueueCategoryKey[]).map((key) => {
                const meta = QUEUE_CATEGORY_META[key];
                const hasItems = queueGroups[key].length > 0;
                return (
                  <button
                    key={key}
                    type="button"
                    className={`queue-category-card ${queueCategory === key ? "active" : ""}`}
                    onClick={() => setQueueCategory(key)}
                    disabled={!hasItems || busy}
                  >
                    <div className="queue-category-icon">{meta.icon}</div>
                    <div className="queue-category-title">{meta.title}</div>
                    <div className="queue-category-subtitle">{meta.subtitle}</div>
                  </button>
                );
              })}
            </div>

            <div className="queue-option-list">
              {activeQueueOptions.length === 0 ? (
                <div className="queue-option-empty">Bu kategoride uygun kuyruk bulunamadı.</div>
              ) : (
                activeQueueOptions.map((q) => (
                  <button
                    key={q.id}
                    type="button"
                    className={`queue-option-item ${queueId === q.id ? "active" : ""}`}
                    onClick={() => {
                      void selectQueueAndApply(q.id);
                      setQueueCategory(queueCategoryOf(q));
                    }}
                    disabled={busy}
                  >
                    <span>{q.name}</span>
                    {q.description ? <small>{q.description}</small> : null}
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      ) : null}

      {phase === "ChampSelect" ? (
        <>
          <h2>Şampiyon Seçimi</h2>
          <p className="mode-hint">Aşama: {state?.champSelect?.timer?.phase || "Bilinmiyor"}</p>

          <div className="champ-select-stage">
            <div className="cs-team-column">
              <h3>Bizim Takim</h3>
              <div className="cs-team-list">
                {myTeam.map((member: any, idx: number) => renderTeamPlayer(member, idx, false))}
              </div>
              {renderBanStrip("Bizim Banlar", myTeamBans)}
            </div>

            <div className="cs-center-column">
              <div className="cs-center-head">
                <div className="cs-center-title">{action?.type === "ban" ? "YASAKLAMA TURU" : "SECIM TURU"}</div>
                <div className="cs-center-sub">{state?.champSelect?.timer?.phase || "PLANNING"}</div>
              </div>

              <div className="cs-swap-grid">
                {renderSwapSection("Karakter Takası", "champion", championSwaps)}
                {renderSwapSection("Lane Takası", "position", positionSwaps)}
                {renderSwapSection("Sıra Takası", "pickOrder", pickOrderSwaps)}
              </div>
            </div>

            <div className="cs-team-column enemy">
              <h3>Karşı Takım</h3>
              <div className="cs-team-list">
                {enemyTeam.map((member: any, idx: number) => renderTeamPlayer(member, idx, true))}
              </div>
              {renderBanStrip("Rakip Banlar", enemyTeamBans)}
            </div>
          </div>

          {availableChampionCards.length > 0 ? (
            <div className="section-header">
              <h2>Mevcut Şampiyonlar</h2>
              <div className="aram-champion-row">
                {availableChampionCards.map((c: any) => {
                  const isCurrent = c.id === championId;
                  const portrait = champIcon(c.id);
                  return (
                    <button
                      key={`available-${c.id}`}
                      className={`aram-champion-card ${isCurrent ? "active" : ""}`}
                      type="button"
                      onClick={() => {
                        if (!isCurrent) void post("/api/champ-select/bench/select", { championId: c.id }, `${c.name} seçildi`);
                      }}
                      disabled={busy || isCurrent}
                    >
                      <div className="aram-champion-portrait">
                        {portrait ? <img src={portrait} alt={c.name} /> : <div className="cs-player-champ-placeholder" />}
                      </div>
                      <span className="aram-champion-name">{c.name}{isCurrent ? " (Seçili)" : ""}</span>
                      <span className="aram-champion-mark">{isCurrent ? "✓" : "Seç"}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          {action ? (
            <>
              <div className="section-header"><h2>{action.type === "ban" ? "Ban Aşaması" : "Pick Aşaması"}</h2></div>
              <input className="champion-search" value={championFilter} onChange={(e) => setChampionFilter(e.target.value)} placeholder="Şampiyon ara..." />

              {selectedChampionId ? (
                <div className="home-page champ-action">
                  <div className="selected-champion-info">
                    <h2>{champions.find((c) => c.id === selectedChampionId)?.name || `Şampiyon ${selectedChampionId}`}</h2>
                    <button className="btn-back" type="button" onClick={() => setSelectedChampionId(null)}>Geri Dön</button>
                  </div>
                  <div className="action-buttons">
                    {action.type === "pick" ? (
                      <>
                        <button className="btn-action btn-hover" type="button" onClick={() => void post("/api/champ-select/hover", { championId: selectedChampionId }, "Hover atıldı")} disabled={busy}>Hover</button>
                        <button className="btn-action btn-lock" type="button" onClick={() => void post("/api/champ-select/lock", { championId: selectedChampionId }, "Şampiyon kilitlendi")} disabled={busy}>Kilitle</button>
                      </>
                    ) : (
                      <button className="btn-action btn-ban" type="button" onClick={() => void post("/api/champ-select/ban", { championId: selectedChampionId }, "Şampiyon yasaklandı")} disabled={busy}>Yasakla</button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="champion-list">
                  {filteredChampions.map((c) => <button key={c.id} className="champion-item" type="button" onClick={() => setSelectedChampionId(c.id)}><span className="champion-name">{c.name}</span><span className="champion-arrow">&gt;</span></button>)}
                </div>
              )}
            </>
          ) : null}

          {benchOnlyChampions.length > 0 ? (
            <div className="section-header">
              <h2>Üst Çubuk (Boşta Şampiyonlar)</h2>
              <div className="aram-champion-row">
                {benchOnlyChampions.map((c: any) => (
                  <button
                    key={`bench-${c.id}`}
                    className="aram-champion-card"
                    type="button"
                    onClick={() => void post("/api/champ-select/bench/select", { championId: c.id }, `${c.name} seçildi`)}
                    disabled={busy}
                  >
                    <div className="aram-champion-portrait">
                      {champIcon(c.id) ? <img src={champIcon(c.id)} alt={c.name} /> : <div className="cs-player-champ-placeholder" />}
                    </div>
                    <span className="aram-champion-name">{c.name}</span>
                    <span className="aram-champion-mark">Seç</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {working ? (
            <>
              <div className="preset-selector">
                {presets.map((p, i) => <button key={`${p.slotLabel}-${i}`} className={`preset-option ${selectedPreset === i ? "active" : ""}`} type="button" onClick={() => void selectPreset(i)} disabled={busy}><span className="preset-number">{i + 1}</span><span className="preset-name">{p.slotLabel}</span><span className="preset-name">{p.name}</span></button>)}
              </div>

              <div className="runes-section">
                <div className="section-header"><h2>Rünler</h2></div>
                <div className="position-pref-grid">
                  <div className="position-pref-item">
                    <label>Ana Rün Ağacı</label>
                    <select
                      value={working.primaryStyleId}
                      onChange={(e) => void applyStyleChange("primary", Number(e.target.value))}
                      disabled={busy}
                    >
                      {styles.map((style: any) => (
                        <option key={`primary-style-${style.id}`} value={style.id}>
                          {style.name || `Stil ${style.id}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="position-pref-item">
                    <label>Alt Rün Ağacı</label>
                    <select
                      value={working.subStyleId}
                      onChange={(e) => void applyStyleChange("secondary", Number(e.target.value))}
                      disabled={busy}
                    >
                      {styles.map((style: any) => (
                        <option key={`secondary-style-${style.id}`} value={style.id}>
                          {style.name || `Stil ${style.id}`}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="rune-trees">
                  <div className="rune-tree primary">
                    <div className="tree-icon">{icon(styleMap.get(working.primaryStyleId)?.iconPath, styleMap.get(working.primaryStyleId)?.iconUrl) ? <img src={icon(styleMap.get(working.primaryStyleId)?.iconPath, styleMap.get(working.primaryStyleId)?.iconUrl)} alt="primary" /> : <div className="rune-icon-placeholder" />}</div>
                    <div className="rune-slots">{(["keystone", "primary1", "primary2", "primary3"] as RuneSlotKey[]).map((k, i) => <button key={k} type="button" className={`rune-slot ${i === 0 ? "keystone" : ""}`} onClick={() => { setOpenSpell(null); setOpenRune(k); }}>{renderPerkIcon(working.selectedPerkIds[SLOT_INDEX[k]])}</button>)}</div>
                  </div>
                  <div className="rune-tree">
                    <div className="tree-icon">{icon(styleMap.get(working.subStyleId)?.iconPath, styleMap.get(working.subStyleId)?.iconUrl) ? <img src={icon(styleMap.get(working.subStyleId)?.iconPath, styleMap.get(working.subStyleId)?.iconUrl)} alt="secondary" /> : <div className="rune-icon-placeholder" />}</div>
                    <div className="rune-slots">{(["secondary1", "secondary2"] as RuneSlotKey[]).map((k) => <button key={k} type="button" className="rune-slot" onClick={() => { setOpenSpell(null); setOpenRune(k); }}>{renderPerkIcon(working.selectedPerkIds[SLOT_INDEX[k]])}</button>)}</div>
                    <div className="stat-shards">{(["shard1", "shard2", "shard3"] as RuneSlotKey[]).map((k) => <button key={k} type="button" className="stat-shard" onClick={() => { setOpenSpell(null); setOpenRune(k); }}>{renderPerkIcon(working.selectedPerkIds[SLOT_INDEX[k]])}</button>)}</div>
                  </div>
                </div>

                {openRune ? <div className="picker-panel"><div className="picker-header"><h3>Rün Seçimi</h3><button type="button" onClick={() => setOpenRune(null)}>Kapat</button></div><div className="picker-grid">{runeOptions(openRune).map((p: any) => <button key={`${openRune}-${p.id}`} type="button" className="picker-item" onClick={() => void pickRune(openRune, p.id)}>{icon(p.iconPath, p.iconUrl) ? <img src={icon(p.iconPath, p.iconUrl)} alt={p.name} /> : <div className="picker-placeholder">{p.id}</div>}<span>{p.name}</span></button>)}</div></div> : null}
              </div>

              <div className="spells-section">
                <div className="section-header"><h2>Sihirdar Büyüleri</h2></div>
                <div className="spell-slots">
                  <button type="button" className="spell-slot" onClick={() => { setOpenRune(null); setOpenSpell(1); }}>{spellIconById(spellMap, working.spell1Id) ? <img className="spell-icon" src={spellIconById(spellMap, working.spell1Id)} alt="spell1" /> : <div className="spell-icon-placeholder" />}<span>{spellNameById(spellMap, working.spell1Id)}</span></button>
                  <button type="button" className="spell-slot" onClick={() => { setOpenRune(null); setOpenSpell(2); }}>{spellIconById(spellMap, working.spell2Id) ? <img className="spell-icon" src={spellIconById(spellMap, working.spell2Id)} alt="spell2" /> : <div className="spell-icon-placeholder" />}<span>{spellNameById(spellMap, working.spell2Id)}</span></button>
                </div>
                {openSpell ? <div className="picker-panel"><div className="picker-header"><h3>Büyü Seç (Slot {openSpell})</h3><button type="button" onClick={() => setOpenSpell(null)}>Kapat</button></div><div className="picker-grid spell-grid">{spells.map((s) => <button key={s.id} type="button" className="picker-item" onClick={() => void pickSpell(openSpell, s.id)}>{icon(s.iconPath, s.iconUrl) ? <img src={icon(s.iconPath, s.iconUrl)} alt={s.name} /> : <div className="picker-placeholder">{s.id}</div>}<span>{s.name}</span></button>)}</div></div> : null}
              </div>
            </>
          ) : null}
        </>
      ) : null}

      {phase === "InProgress" ? <><h2>Maçtasın</h2><p>Canlı takım bilgisi için InProgress paneli kullanılıyor.</p></> : null}
      {phase !== "Lobby" && phase !== "Matchmaking" && phase !== "ChampSelect" && phase !== "ReadyCheck" && phase !== "InProgress" ? <><h2>Oyun Bekleniyor...</h2><p>Faz: {String(phase)}</p></> : null}
    </div>
  );
}

