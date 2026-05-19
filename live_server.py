import asyncio
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from desktop_bridge.security import token_manager


@dataclass
class LockfileAuth:
    name: str
    pid: int
    port: int
    password: str
    protocol: str
    lockfile_path: str


class LcuClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._auth: LockfileAuth | None = None

    @staticmethod
    def _lockfile_candidates() -> list[Path]:
        env_path = os.environ.get("LOL_LOCKFILE_PATH")
        candidates = []
        if env_path:
            candidates.append(Path(env_path))

        candidates.extend(
            [
                Path(r"C:\Riot Games\League of Legends\lockfile"),
                Path(r"C:\Riot Games\League of Legends\Game\lockfile"),
                Path.home() / "AppData/Local/Riot Games/League of Legends/lockfile",
            ]
        )
        return candidates

    @staticmethod
    def _read_lockfile(path: Path) -> LockfileAuth | None:
        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8").strip()
            name, pid, port, password, protocol = content.split(":")
            return LockfileAuth(
                name=name,
                pid=int(pid),
                port=int(port),
                password=password,
                protocol=protocol,
                lockfile_path=str(path),
            )
        except Exception:
            return None

    def _find_auth(self) -> LockfileAuth | None:
        for candidate in self._lockfile_candidates():
            auth = self._read_lockfile(candidate)
            if auth:
                return auth
        return None

    async def _ensure_client(self) -> LockfileAuth | None:
        auth = self._find_auth()
        if not auth:
            await self.close()
            return None

        if self._auth and self._client:
            unchanged = (
                self._auth.port == auth.port
                and self._auth.password == auth.password
                and self._auth.protocol == auth.protocol
                and self._auth.lockfile_path == auth.lockfile_path
            )
            if unchanged:
                return self._auth

        await self.close()
        self._auth = auth
        self._client = httpx.AsyncClient(
            base_url=f"{auth.protocol}://127.0.0.1:{auth.port}",
            auth=("riot", auth.password),
            verify=False,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
        return auth

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        self._client = None
        self._auth = None

    async def get(self, path: str) -> Any:
        auth = await self._ensure_client()
        if not auth or not self._client:
            return None

        try:
            response = await self._client.get(path)
            response.raise_for_status()
            if not response.text:
                return None
            return response.json()
        except Exception:
            return None

    async def get_raw(self, path: str) -> tuple[bytes, str] | None:
        auth = await self._ensure_client()
        if not auth or not self._client:
            return None

        try:
            response = await self._client.get(path)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "application/octet-stream")
            return (response.content, content_type)
        except Exception:
            return None

    async def request_or_raise(self, method: str, path: str, payload: Any | None = None) -> Any:
        auth = await self._ensure_client()
        if not auth or not self._client:
            raise HTTPException(status_code=503, detail="League client lockfile not found")

        try:
            request_kwargs: dict[str, Any] = {"method": method, "url": path}
            if payload is not None:
                request_kwargs["json"] = payload
            response = await self._client.request(**request_kwargs)
            if response.status_code >= 400:
                detail = response.text
                raise HTTPException(status_code=response.status_code, detail=detail)
            if not response.text:
                return None
            return response.json()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LCU request failed: {exc}") from exc

    async def lockfile_info(self) -> dict[str, Any]:
        auth = await self._ensure_client()
        if not auth:
            return {"connected": False, "lockfilePath": None}
        return {
            "connected": True,
            "lockfilePath": auth.lockfile_path,
            "port": auth.port,
            "protocol": auth.protocol,
        }


class WSManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)

        for ws in stale:
            self.disconnect(ws)


def get_active_window_title() -> str:
    if os.name != "nt":
        return ""

    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    except Exception:
        return ""


async def get_liveclient_json(path: str) -> Any:
    url = f"https://127.0.0.1:2999{path}"
    try:
        async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(3.0, connect=1.0)) as client:
            response = await client.get(url)
            response.raise_for_status()
            if not response.text:
                return None
            return response.json()
    except Exception:
        return None


def normalize_champions(champions: Any) -> list[dict[str, Any]]:
    if not isinstance(champions, list):
        return []

    output = []
    for item in champions:
        if not isinstance(item, dict):
            continue
        champ_id = item.get("id")
        if champ_id is None:
            champ_id = item.get("championId")
        if champ_id is None:
            continue
        output.append({"id": champ_id, "name": item.get("name", f"Champion {champ_id}")})

    output.sort(key=lambda x: x["name"])
    return output


def normalize_champion_id_list(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []
    out: list[int] = []

    def _to_champion_id(value: Any) -> int | None:
        candidate: int | None = None
        if isinstance(value, int):
            candidate = value
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                candidate = int(stripped)
        if candidate is None or candidate <= 0:
            return None
        # Some payloads expose skin ids (championId * 1000 + skinId).
        normalized = candidate // 1000 if candidate >= 1000 else candidate
        return normalized if normalized > 0 else None

    for item in raw:
        direct_id = _to_champion_id(item)
        if direct_id is not None:
            out.append(direct_id)
            continue
        if isinstance(item, dict):
            candidate = item.get("championId")
            if candidate is None:
                candidate = item.get("id")
            nested_id = _to_champion_id(candidate)
            if nested_id is not None:
                out.append(nested_id)
    # Preserve order but de-duplicate
    seen: set[int] = set()
    uniq: list[int] = []
    for cid in out:
        if cid in seen:
            continue
        seen.add(cid)
        uniq.append(cid)
    return uniq


def collect_candidate_champion_lists(payload: Any) -> list[list[int]]:
    if not isinstance(payload, (dict, list)):
        return []
    collected: list[list[int]] = []
    keywords = ("pickable", "bench", "reroll", "trade", "swap", "eligible", "selection")

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_l = str(key).lower()
                if any(k in key_l for k in keywords):
                    ids = normalize_champion_id_list(value)
                    if ids:
                        collected.append(ids)
                if isinstance(value, (dict, list)):
                    _walk(value)
            return
        if isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    _walk(item)

    _walk(payload)
    return collected


def build_perk_lookup(perks: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(perks, list):
        return {}

    lookup: dict[int, dict[str, Any]] = {}
    for perk in perks:
        if not isinstance(perk, dict):
            continue
        perk_id = perk.get("id")
        if not isinstance(perk_id, int):
            continue
        lookup[perk_id] = {
            "id": perk_id,
            "name": perk.get("name", f"Perk {perk_id}"),
            "iconPath": perk.get("iconPath"),
        }
    return lookup


def asset_proxy_url(icon_path: str | None) -> str | None:
    if not icon_path:
        return None
    return f"/api/asset?path={quote(icon_path, safe='')}"


def normalize_rune_styles(styles: Any, perk_lookup: dict[int, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if not isinstance(styles, list):
        return []
    if perk_lookup is None:
        perk_lookup = {}

    output: list[dict[str, Any]] = []
    for style in styles:
        if not isinstance(style, dict):
            continue
        style_id = style.get("id")
        slots = style.get("slots")
        if not isinstance(style_id, int) or not isinstance(slots, list):
            continue

        normalized_slots: list[dict[str, Any]] = []
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            perks = slot.get("perks")
            if not isinstance(perks, list):
                continue

            normalized_perks: list[dict[str, Any]] = []
            for perk in perks:
                if isinstance(perk, dict):
                    perk_id = perk.get("id")
                    if not isinstance(perk_id, int):
                        continue
                    icon_path = perk.get("iconPath")
                    normalized_perks.append(
                        {
                            "id": perk_id,
                            "name": perk.get("name", f"Perk {perk_id}"),
                            "iconPath": icon_path,
                            "iconUrl": asset_proxy_url(icon_path),
                        }
                    )
                    continue

                if isinstance(perk, int):
                    meta = perk_lookup.get(perk, {})
                    icon_path = meta.get("iconPath")
                    normalized_perks.append(
                        {
                            "id": perk,
                            "name": meta.get("name", f"Perk {perk}"),
                            "iconPath": icon_path,
                            "iconUrl": asset_proxy_url(icon_path),
                        }
                    )

            if normalized_perks:
                normalized_slots.append({"perks": normalized_perks})

        if normalized_slots:
            style_icon_path = style.get("iconPath")
            output.append(
                {
                    "id": style_id,
                    "name": style.get("name", style.get("idName", f"Style {style_id}")),
                    "iconPath": style_icon_path,
                    "iconUrl": asset_proxy_url(style_icon_path),
                    "allowedSubStyles": style.get("allowedSubStyles", []),
                    "slots": normalized_slots,
                }
            )

    output.sort(key=lambda x: x["name"])
    return output


def normalize_summoner_spells(spells: Any, allowed_ids: set[int] | None = None) -> list[dict[str, Any]]:
    if not isinstance(spells, list):
        return []

    output_map: dict[int, dict[str, Any]] = {}
    for spell in spells:
        if not isinstance(spell, dict):
            continue
        spell_id = spell.get("id")
        if not isinstance(spell_id, int):
            continue
        if allowed_ids is not None and spell_id not in allowed_ids:
            continue

        spell_name = str(spell.get("name", "")).strip()
        if not spell_name:
            continue
        lower_name = spell_name.lower()
        if "eklenecek" in lower_name or "to be added" in lower_name or "placeholder" in lower_name:
            continue

        icon_path = spell.get("iconPath")
        if not isinstance(icon_path, str) or not icon_path.strip():
            continue

        output_map[spell_id] = {
            "id": spell_id,
            "name": spell_name,
            "description": spell.get("description", ""),
            "iconPath": icon_path,
            "iconUrl": asset_proxy_url(icon_path),
        }

    output = list(output_map.values())
    output.sort(key=lambda x: x["name"])
    return output


def normalize_queue_options(queues: Any) -> list[dict[str, Any]]:
    if not isinstance(queues, list):
        return []

    output: list[dict[str, Any]] = []
    for item in queues:
        if not isinstance(item, dict):
            continue
        queue_id = item.get("id")
        if not isinstance(queue_id, int) or queue_id <= 0:
            continue

        output.append(
            {
                "id": queue_id,
                "name": str(item.get("name", f"Queue {queue_id}")),
                "description": str(item.get("description", "")),
                "isRanked": bool(item.get("isRanked", False)),
            }
        )

    output.sort(key=lambda x: x["name"])
    return output


def fallback_queue_options() -> list[dict[str, Any]]:
    # Common queues shown when queue catalog is unavailable.
    return [
        {"id": 400, "name": "Normal Draft", "description": "5v5 Taslak", "isRanked": False},
        {"id": 420, "name": "Ranked Solo/Duo", "description": "Dereceli Tek/Cift", "isRanked": True},
        {"id": 430, "name": "Normal Blind", "description": "5v5 Kor Secim", "isRanked": False},
        {"id": 440, "name": "Ranked Flex", "description": "Dereceli Esnek", "isRanked": True},
        {"id": 450, "name": "ARAM", "description": "Howling Abyss", "isRanked": False},
        {"id": 490, "name": "Quickplay", "description": "Hizli Oyun", "isRanked": False},
        {"id": 700, "name": "Clash", "description": "Turnuva Modu", "isRanked": False},
        {"id": 1700, "name": "Arena", "description": "Arena", "isRanked": False},
    ]


def role_weight(roles: list[str]) -> str:
    priority = ["marksman", "assassin", "mage", "fighter", "tank", "support", "jungle"]
    role_set = {r.lower() for r in roles}
    for role in priority:
        if role in role_set:
            return role
    return "fighter"


def resolve_champion_role(champion_id: int, champions: list[dict[str, Any]]) -> str:
    for champ in champions:
        if champ.get("id") != champion_id:
            continue
        roles = champ.get("roles")
        if isinstance(roles, list):
            return role_weight([str(r) for r in roles])
    return "fighter"


def first_k_perks(style: dict[str, Any], slot_index: int, count: int = 1) -> list[int]:
    if not style:
        return []
    slots = style.get("slots")
    if not isinstance(slots, list) or len(slots) <= slot_index:
        return []
    perks = slots[slot_index].get("perks", [])
    if not isinstance(perks, list):
        return []
    output = []
    for perk in perks[:count]:
        perk_id = perk.get("id")
        if isinstance(perk_id, int):
            output.append(perk_id)
    return output


def build_rune_payload(
    name: str,
    primary_style_id: int,
    sub_style_id: int,
    normalized_styles: list[dict[str, Any]],
) -> dict[str, Any] | None:
    styles_by_id = {s["id"]: s for s in normalized_styles if isinstance(s.get("id"), int)}
    primary = styles_by_id.get(primary_style_id)
    sub = styles_by_id.get(sub_style_id)

    if not primary or not sub:
        return None

    selected_perk_ids: list[int] = []
    for idx in range(4):
        selected_perk_ids.extend(first_k_perks(primary, idx))
    selected_perk_ids.extend(first_k_perks(sub, 1))
    selected_perk_ids.extend(first_k_perks(sub, 2))
    selected_perk_ids.extend([5008, 5008, 5002])
    selected_perk_ids = selected_perk_ids[:9]

    if len(selected_perk_ids) != 9:
        return None

    return {
        "name": name,
        "primaryStyleId": primary_style_id,
        "subStyleId": sub_style_id,
        "selectedPerkIds": selected_perk_ids,
    }


def build_role_suggestions(role: str, styles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plans: dict[str, list[dict[str, Any]]] = {
        "marksman": [
            {"label": "DPS", "primary": 8000, "sub": 8300, "spells": (4, 7)},
            {"label": "Snowball", "primary": 8000, "sub": 8100, "spells": (4, 14)},
            {"label": "Güvenli", "primary": 8000, "sub": 8400, "spells": (4, 6)},
        ],
        "assassin": [
            {"label": "Patlayıcı", "primary": 8100, "sub": 8000, "spells": (4, 14)},
            {"label": "Takas", "primary": 8100, "sub": 8300, "spells": (4, 3)},
            {"label": "Mobil", "primary": 8100, "sub": 8200, "spells": (4, 6)},
        ],
        "mage": [
            {"label": "Kontrol", "primary": 8200, "sub": 8300, "spells": (4, 12)},
            {"label": "Agresif", "primary": 8200, "sub": 8100, "spells": (4, 14)},
            {"label": "Güvenli", "primary": 8200, "sub": 8400, "spells": (4, 21)},
        ],
        "fighter": [
            {"label": "Düello", "primary": 8000, "sub": 8400, "spells": (4, 14)},
            {"label": "Sürdürülebilir", "primary": 8000, "sub": 8300, "spells": (4, 12)},
            {"label": "Ön Hat", "primary": 8400, "sub": 8000, "spells": (4, 12)},
        ],
        "tank": [
            {"label": "Tank", "primary": 8400, "sub": 8300, "spells": (4, 12)},
            {"label": "Ön Hat", "primary": 8400, "sub": 8000, "spells": (4, 14)},
            {"label": "Destek Tank", "primary": 8400, "sub": 8200, "spells": (4, 3)},
        ],
        "support": [
            {"label": "Koruma", "primary": 8300, "sub": 8400, "spells": (4, 3)},
            {"label": "Baskı", "primary": 8100, "sub": 8300, "spells": (4, 14)},
            {"label": "Sürdürülebilir", "primary": 8200, "sub": 8300, "spells": (4, 7)},
        ],
        "jungle": [
            {"label": "Temizleme", "primary": 8000, "sub": 8100, "spells": (4, 11)},
            {"label": "Baskın", "primary": 8100, "sub": 8000, "spells": (4, 11)},
            {"label": "Kontrol", "primary": 8300, "sub": 8000, "spells": (4, 11)},
        ],
    }

    selected_plans = plans.get(role, plans["fighter"])
    output: list[dict[str, Any]] = []

    for idx, plan in enumerate(selected_plans):
        rune = build_rune_payload(
            name=f"{plan['label']} Seti",
            primary_style_id=plan["primary"],
            sub_style_id=plan["sub"],
            normalized_styles=styles,
        )
        if not rune:
            continue

        output.append(
            {
                "slotLabel": f"Opsiyon {idx + 1}",
                "name": rune["name"],
                "primaryStyleId": rune["primaryStyleId"],
                "subStyleId": rune["subStyleId"],
                "selectedPerkIds": rune["selectedPerkIds"],
                "spells": {
                    "spell1Id": plan["spells"][0],
                    "spell2Id": plan["spells"][1],
                },
            }
        )

    return output


def normalize_external_suggestions(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    output: list[dict[str, Any]] = []
    for idx, item in enumerate(payload[:3]):
        if not isinstance(item, dict):
            continue

        perks = item.get("selectedPerkIds")
        spells = item.get("spells", {})
        if not isinstance(perks, list) or len(perks) < 9:
            continue

        try:
            selected_perks = [int(x) for x in perks[:9]]
            primary = int(item.get("primaryStyleId"))
            sub = int(item.get("subStyleId"))
            spell1 = int(spells.get("spell1Id"))
            spell2 = int(spells.get("spell2Id"))
        except Exception:
            continue

        output.append(
            {
                "slotLabel": str(item.get("slotLabel", f"Opsiyon {idx + 1}")),
                "name": str(item.get("name", f"Öneri {idx + 1}")),
                "primaryStyleId": primary,
                "subStyleId": sub,
                "selectedPerkIds": selected_perks,
                "spells": {"spell1Id": spell1, "spell2Id": spell2},
            }
        )
    return output


def _extract_recommended_candidates(payload: Any, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 4:
        return []

    found: list[dict[str, Any]] = []

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                found.append(item)
            found.extend(_extract_recommended_candidates(item, depth + 1))
        return found

    if isinstance(payload, dict):
        # Direct candidate
        if payload.get("selectedPerkIds") or payload.get("selectedPerks"):
            found.append(payload)

        # Nested collections seen across different LCU payload shapes
        nested_keys = (
            "pages",
            "recommendedPages",
            "recommendations",
            "items",
            "data",
            "builds",
            "sets",
            "rows",
        )
        for key in nested_keys:
            value = payload.get(key)
            if value is not None:
                found.extend(_extract_recommended_candidates(value, depth + 1))

    return found


def normalize_lcu_recommended_suggestions(payload: Any) -> list[dict[str, Any]]:
    candidates = _extract_recommended_candidates(payload)
    output: list[dict[str, Any]] = []
    seen: set[tuple[int, int, tuple[int, ...]]] = set()

    for idx, item in enumerate(candidates):
        raw_perks = item.get("selectedPerkIds") or item.get("selectedPerks")
        if not isinstance(raw_perks, list):
            continue

        try:
            selected_perks = [int(x) for x in raw_perks if x is not None][:9]
        except Exception:
            continue
        if len(selected_perks) < 9:
            continue

        try:
            primary = int(
                item.get("primaryStyleId")
                or item.get("primaryStyle")
                or item.get("primaryTreeId")
            )
            sub = int(
                item.get("subStyleId")
                or item.get("secondaryStyleId")
                or item.get("subStyle")
                or item.get("secondaryStyle")
                or item.get("subTreeId")
            )
        except Exception:
            continue

        spell1 = 4
        spell2 = 14
        spell_block = item.get("spells")
        if isinstance(spell_block, dict):
            try:
                spell1 = int(spell_block.get("spell1Id", spell1))
                spell2 = int(spell_block.get("spell2Id", spell2))
            except Exception:
                pass
        if isinstance(item.get("summonerSpellIds"), list) and len(item["summonerSpellIds"]) >= 2:
            try:
                spell1 = int(item["summonerSpellIds"][0])
                spell2 = int(item["summonerSpellIds"][1])
            except Exception:
                pass

        key = (primary, sub, tuple(selected_perks))
        if key in seen:
            continue
        seen.add(key)

        output.append(
            {
                "slotLabel": str(item.get("slotLabel") or item.get("title") or f"Opsiyon {len(output) + 1}"),
                "name": str(item.get("name") or item.get("displayName") or f"Hızlı Öneri {len(output) + 1}"),
                "primaryStyleId": primary,
                "subStyleId": sub,
                "selectedPerkIds": selected_perks,
                "spells": {"spell1Id": spell1, "spell2Id": spell2},
            }
        )
        if len(output) >= 3:
            break

    return output


async def get_lcu_recommended_suggestions(
    champion_id: int, role: str, queue_id: int | None = None
) -> list[dict[str, Any]]:
    role_lower = role.lower().strip()
    role_tokens = [role_lower]
    role_aliases = {
        "middle": ["mid", "middle"],
        "mid": ["mid", "middle"],
        "bottom": ["bot", "adc", "bottom"],
        "adc": ["bot", "adc", "bottom"],
        "utility": ["support", "utility"],
        "support": ["support", "utility"],
        "jungle": ["jungle"],
        "top": ["top"],
        "unknown": ["middle", "top", "jungle", "bottom", "utility"],
    }
    if role_lower in role_aliases:
        role_tokens = role_aliases[role_lower]

    base_paths = [
        f"/lol-perks/v1/recommended-pages/champion/{champion_id}",
        f"/lol-perks/v1/recommended-pages/champion/{champion_id}/position/{{role}}",
        f"/lol-perks/v1/recommended-pages/champion/{champion_id}/queue/{{queue}}/position/{{role}}",
        f"/lol-perks/v1/recommended-pages/champion/{champion_id}/queue/{{queue}}",
        "/lol-perks/v1/recommended-pages",
    ]

    queue_token = str(queue_id) if isinstance(queue_id, int) and queue_id > 0 else ""
    candidate_paths: list[str] = []
    for template in base_paths:
        if "{queue}" in template and not queue_token:
            continue
        if "{role}" in template:
            for token in role_tokens:
                candidate_paths.append(template.replace("{role}", token).replace("{queue}", queue_token))
        else:
            candidate_paths.append(template.replace("{queue}", queue_token))

    for path in candidate_paths:
        payload = await lcu.get(path)
        suggestions = normalize_lcu_recommended_suggestions(payload)
        if suggestions:
            return suggestions

    return []


def get_current_action(session: dict[str, Any], action_type: str) -> dict[str, Any] | None:
    local_cell = session.get("localPlayerCellId")
    for turn in session.get("actions", []):
        for action in turn:
            if action.get("actorCellId") != local_cell:
                continue
            if action.get("type") != action_type:
                continue
            if action.get("completed"):
                continue
            return action
    return None


class PickPayload(BaseModel):
    championId: int = Field(gt=0)


class SpellPayload(BaseModel):
    spell1Id: int = Field(gt=0)
    spell2Id: int = Field(gt=0)


class RunePayload(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    primaryStyleId: int = Field(gt=0)
    subStyleId: int = Field(gt=0)
    selectedPerkIds: list[int] = Field(min_length=9, max_length=9)


class QueuePayload(BaseModel):
    queueId: int = Field(gt=0)


class PositionPreferencePayload(BaseModel):
    firstPreference: str = Field(min_length=2, max_length=16)
    secondPreference: str = Field(min_length=2, max_length=16)


class SwapActionPayload(BaseModel):
    swapType: str = Field(min_length=1, max_length=32)
    swapId: int = Field(gt=0)
    action: str = Field(min_length=1, max_length=16)


lcu = LcuClient()
ws_manager = WSManager()
state_cache: dict[str, Any] = {
    "connected": False,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
poller_task: asyncio.Task[Any] | None = None
_summoner_name_cache: dict[int, tuple[str, float]] = {}
_summoner_puuid_name_cache: dict[str, tuple[str, float]] = {}
_SUMMONER_NAME_CACHE_TTL_SECONDS = 300.0


def _safe_nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _extract_display_name(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    direct_keys = [
        "summonerName",
        "displayName",
        "name",
        "gameNameWithTagLine",
        "riotId",
    ]
    for key in direct_keys:
        value = _safe_nonempty_string(payload.get(key))
        if value and value.lower() not in {"unknown", "anon", "anonymous", "bilinmeyen oyuncu"}:
            return value

    game_name = _safe_nonempty_string(payload.get("gameName"))
    tag_line = _safe_nonempty_string(payload.get("tagLine") or payload.get("gameTag") or payload.get("tag"))
    if game_name and tag_line:
        return f"{game_name}#{tag_line}"
    if game_name:
        return game_name

    return None


async def _resolve_summoner_name_by_id(summoner_id: int) -> str | None:
    now = time.monotonic()
    cached = _summoner_name_cache.get(summoner_id)
    if cached and now - cached[1] <= _SUMMONER_NAME_CACHE_TTL_SECONDS:
        return cached[0]

    details = await lcu.get(f"/lol-summoner/v1/summoners/{summoner_id}")
    resolved = _extract_display_name(details)
    if resolved:
        _summoner_name_cache[summoner_id] = (resolved, now)
    return resolved


async def _resolve_summoner_name_by_puuid(puuid: str) -> str | None:
    key = puuid.strip()
    if not key:
        return None

    now = time.monotonic()
    cached = _summoner_puuid_name_cache.get(key)
    if cached and now - cached[1] <= _SUMMONER_NAME_CACHE_TTL_SECONDS:
        return cached[0]

    encoded = quote(key, safe="")
    candidates = [
        f"/lol-summoner/v1/summoners/puuid/{encoded}",
        f"/lol-summoner/v2/summoners/puuid/{encoded}",
        f"/lol-game-name-service/v1/summoners/{encoded}",
        f"/lol-chat/v1/friends/{encoded}",
    ]

    for path in candidates:
        details = await lcu.get(path)
        resolved = _extract_display_name(details)
        if resolved:
            _summoner_puuid_name_cache[key] = (resolved, now)
            return resolved

    return None


async def _resolve_member_display_name(member: dict[str, Any]) -> str | None:
    resolved = _extract_display_name(member)
    if resolved:
        return resolved

    summoner_id = member.get("summonerId")
    if isinstance(summoner_id, int):
        resolved = await _resolve_summoner_name_by_id(summoner_id)
        if resolved:
            return resolved

    for puuid_key in ("puuid", "summonerPuuid", "playerPuuid", "subject"):
        raw = member.get(puuid_key)
        if isinstance(raw, str) and raw.strip():
            resolved = await _resolve_summoner_name_by_puuid(raw)
            if resolved:
                return resolved

    return None


async def hydrate_lobby_member_names(lobby: Any) -> Any:
    if not isinstance(lobby, dict):
        return lobby

    members = lobby.get("members")
    if not isinstance(members, list):
        return lobby

    for member in members:
        if not isinstance(member, dict):
            continue

        resolved_name = await _resolve_member_display_name(member)

        if not resolved_name:
            continue

        member["displayName"] = resolved_name
        if not _safe_nonempty_string(member.get("summonerName")):
            member["summonerName"] = resolved_name

    return lobby


async def hydrate_champ_select_member_names(session: Any) -> Any:
    if not isinstance(session, dict):
        return session

    for team_key in ("myTeam", "theirTeam"):
        members = session.get(team_key)
        if not isinstance(members, list):
            continue

        for member in members:
            if not isinstance(member, dict):
                continue

            resolved_name = await _resolve_member_display_name(member)

            if not resolved_name:
                continue

            member["displayName"] = resolved_name
            if not _safe_nonempty_string(member.get("summonerName")):
                member["summonerName"] = resolved_name

    return session


def normalize_swap_entries(entries: Any) -> list[dict[str, Any]]:
    if not isinstance(entries, list):
        return []

    output: list[dict[str, Any]] = []
    for item in entries:
        if isinstance(item, dict):
            output.append(item)
    return output


async def get_first_available(paths: list[str]) -> Any:
    for path in paths:
        result = await lcu.get(path)
        if result is not None:
            return result
    return None


async def post_with_fallback(paths: list[str], payload: Any | None = None) -> Any:
    errors: list[str] = []
    for path in paths:
        try:
            return await lcu.request_or_raise("POST", path, payload)
        except HTTPException as exc:
            errors.append(f"{path} -> {exc.status_code}: {exc.detail}")
            if exc.status_code in {404, 405}:
                continue
            raise

    detail = "Swap action is not supported by this client build"
    if errors:
        detail = f"{detail}. Attempts: {' | '.join(errors[-3:])}"
    raise HTTPException(status_code=409, detail=detail)


async def build_state() -> dict[str, Any]:
    lock = await lcu.lockfile_info()
    title = get_active_window_title()

    data: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connected": lock.get("connected", False),
        "lockfilePath": lock.get("lockfilePath"),
        "isLolWindowActive": "league of legends" in title.lower(),
        "activeWindowTitle": title,
        "phase": None,
        "summoner": None,
        "champSelect": None,
        "mySelection": None,
        "currentRunePage": None,
        "lobby": None,
        "matchmakingSearchState": None,
        "myLobbyMember": None,
        "champSelectSwaps": {
            "champion": [],
            "position": [],
            "pickOrder": [],
        },
        "champSelectOptions": {
            "benchChampionIds": [],
            "pickableChampionIds": [],
        },
    }

    if not lock.get("connected"):
        return data

    gameflow = await lcu.get("/lol-gameflow/v1/gameflow-phase")
    summoner = await lcu.get("/lol-summoner/v1/current-summoner")
    champ_select = await lcu.get("/lol-champ-select/v1/session")
    if isinstance(champ_select, dict):
        champ_select = await hydrate_champ_select_member_names(champ_select)
    current_page = await lcu.get("/lol-perks/v1/currentpage")
    lobby = await lcu.get("/lol-lobby/v2/lobby")
    if isinstance(lobby, dict):
        lobby = await hydrate_lobby_member_names(lobby)
    search_state = await lcu.get("/lol-lobby/v2/lobby/matchmaking/search-state")

    data["phase"] = gameflow
    data["summoner"] = summoner
    data["champSelect"] = champ_select
    data["currentRunePage"] = current_page
    data["lobby"] = lobby
    data["matchmakingSearchState"] = search_state

    if isinstance(champ_select, dict):
        champion_swaps = normalize_swap_entries(champ_select.get("championSwaps"))
        if not champion_swaps:
            champion_swaps = normalize_swap_entries(
                await get_first_available(
                    [
                        "/lol-champ-select/v1/session/champion-swaps",
                        "/lol-lobby-team-builder/champ-select/v1/session/champion-swaps",
                    ]
                )
            )

        position_swaps = normalize_swap_entries(champ_select.get("positionSwaps"))
        if not position_swaps:
            position_swaps = normalize_swap_entries(
                await get_first_available(
                    [
                        "/lol-champ-select/v1/session/position-swaps",
                        "/lol-lobby-team-builder/champ-select/v1/session/position-swaps",
                    ]
                )
            )

        pick_order_swaps = normalize_swap_entries(champ_select.get("pickOrderSwaps"))
        if not pick_order_swaps:
            pick_order_swaps = normalize_swap_entries(
                await get_first_available(
                    [
                        "/lol-champ-select/v1/session/pick-order-swaps",
                        "/lol-lobby-team-builder/champ-select/v1/session/pick-order-swaps",
                    ]
                )
            )

        data["champSelectSwaps"] = {
            "champion": champion_swaps,
            "position": position_swaps,
            "pickOrder": pick_order_swaps,
        }

        local_cell = champ_select.get("localPlayerCellId")
        for member in champ_select.get("myTeam", []):
            if member.get("cellId") == local_cell:
                data["mySelection"] = member
                break

        # Some queues/modes expose local selection and pickable options via dedicated endpoints.
        my_selection = await lcu.get("/lol-champ-select/v1/session/my-selection")
        if isinstance(my_selection, dict):
            if isinstance(data["mySelection"], dict):
                merged = dict(data["mySelection"])
                merged.update(my_selection)
                data["mySelection"] = merged
            else:
                data["mySelection"] = my_selection

        # ARAM: extract eligible/reroll champion lists from the local team member entry
        local_player_member = data.get("mySelection")
        if isinstance(local_player_member, dict):
            for member in champ_select.get("myTeam", []):
                if isinstance(member, dict) and member.get("cellId") == local_cell:
                    local_player_member = member
                    break
            aram_eligible = normalize_champion_id_list(
                local_player_member.get("allEligibleChampionIds")
                or local_player_member.get("eligibleChampionIds")
                or local_player_member.get("playerChampionSelections")
            )
        else:
            aram_eligible = []

        # Parse actions for local player's available champion IDs (ARAM)
        action_source: list[int] = []
        if isinstance(champ_select.get("actions"), list):
            for action_group in champ_select["actions"]:
                if not isinstance(action_group, list):
                    continue
                for act in action_group:
                    if not isinstance(act, dict):
                        continue
                    if act.get("actorCellId") == local_cell:
                        act_ids = normalize_champion_id_list(act.get("availableChampionIds"))
                        action_source.extend(act_ids)
                        act_cid = normalize_champion_id_list([act.get("championId")])
                        action_source.extend(act_cid)

        bench_candidates: list[Any] = [
            champ_select.get("benchChampionIds"),
            champ_select.get("benchChampions"),
        ]
        pickable_candidates: list[Any] = [
            champ_select.get("pickableChampionIds"),
            champ_select.get("pickableChampions"),
        ]
        pickable_candidates.append(aram_eligible)
        pickable_candidates.append(action_source)
        if isinstance(my_selection, dict):
            bench_candidates.extend(
                [
                    my_selection.get("benchChampionIds"),
                    my_selection.get("benchChampions"),
                ]
            )
            pickable_candidates.extend(
                [
                    my_selection.get("pickableChampionIds"),
                    my_selection.get("pickableChampions"),
                ]
            )
            for ids in collect_candidate_champion_lists(my_selection):
                pickable_candidates.append(ids)
                bench_candidates.append(ids)
        for ids in collect_candidate_champion_lists(champ_select):
            pickable_candidates.append(ids)
            bench_candidates.append(ids)

        pickable_fallback = await get_first_available(
            [
                "/lol-champ-select/v1/pickable-champion-ids",
                "/lol-champ-select-legacy/v1/pickable-champions",
                "/lol-lobby-team-builder/champ-select/v1/pickable-champion-ids",
                "/lol-lobby-team-builder/champ-select/v1/pickable-champions",
                "/lol-champ-select/v1/session/pickable-champion-ids",
                "/lol-lobby-team-builder/champ-select/v1/session/pickable-champion-ids",
                # ARAM-specific endpoints
                "/lol-champ-select/v1/session/reroll-champion-ids",
                "/lol-champ-select/v1/session/reroll-champions",
                "/lol-lobby-team-builder/champ-select/v1/session/reroll-champion-ids",
                "/lol-champ-select/v1/session/trade-champion-ids",
                "/lol-champ-select/v1/session/all-eligible-champion-ids",
            ]
        )
        bench_fallback = await get_first_available(
            [
                "/lol-champ-select/v1/session/bench/champions",
                "/lol-lobby-team-builder/champ-select/v1/session/bench/champions",
                "/lol-champ-select/v1/session/bench-champions",
                "/lol-lobby-team-builder/champ-select/v1/session/bench-champions",
                "/lol-champ-select/v1/session/bench/enabled-champion-ids",
                "/lol-lobby-team-builder/champ-select/v1/session/bench/enabled-champion-ids",
            ]
        )
        pickable_candidates.append(pickable_fallback)
        bench_candidates.append(bench_fallback)

        bench_ids: list[int] = []
        for candidate in bench_candidates:
            for cid in normalize_champion_id_list(candidate):
                if cid not in bench_ids:
                    bench_ids.append(cid)

        pickable_ids: list[int] = []
        for candidate in pickable_candidates:
            for cid in normalize_champion_id_list(candidate):
                if cid not in pickable_ids:
                    pickable_ids.append(cid)

        data["champSelectOptions"] = {
            "benchChampionIds": bench_ids,
            "pickableChampionIds": pickable_ids,
        }

    if isinstance(lobby, dict):
        local_summoner_id = summoner.get("summonerId") if isinstance(summoner, dict) else None
        members = lobby.get("members")
        if isinstance(members, list):
            for member in members:
                if not isinstance(member, dict):
                    continue
                if member.get("summonerId") == local_summoner_id:
                    data["myLobbyMember"] = member
                    break

    return data


async def require_phase(allowed: set[str], action_name: str) -> str:
    phase = await lcu.get("/lol-gameflow/v1/gameflow-phase")
    if not isinstance(phase, str):
        raise HTTPException(status_code=409, detail="Gameflow phase is unavailable")
    if phase not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=409,
            detail=f"{action_name} is only allowed in: {allowed_text}. Current phase: {phase}",
        )
    return phase


async def poll_state() -> None:
    global state_cache

    while True:
        try:
            next_state = await build_state()
            state_cache = next_state
            await ws_manager.broadcast(next_state)
        except Exception as exc:
            state_cache = {
                "connected": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }
        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global poller_task
    poller_task = asyncio.create_task(poll_state())
    yield
    if poller_task:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
    await lcu.close()


app = FastAPI(title="LoL Mobile Bridge", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Multi-user site DB (PC registration, token, pairing)
# ---------------------------------------------------------------------------
SITE_DB_PATH = Path(__file__).resolve().parent / "data" / "lolmakro.db"


def _get_site_db() -> sqlite3.Connection:
    SITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pcs (
            device_id TEXT PRIMARY KEY,
            remote_url TEXT NOT NULL,
            pc_name TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'pair',
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (device_id) REFERENCES pcs(device_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pairings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            mobile_id TEXT NOT NULL,
            paired_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (device_id) REFERENCES pcs(device_id)
        )
    """)
    conn.commit()
    return conn


def _site_token() -> str:
    return secrets.token_hex(32)


def _site_device_id() -> str:
    return "pc_" + uuid.uuid4().hex[:16]


def _site_mobile_id() -> str:
    return "mob_" + uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    return state_cache


@app.get("/api/live/teams")
async def api_live_teams() -> dict[str, Any]:
    phase = await lcu.get("/lol-gameflow/v1/gameflow-phase")
    if phase != "InProgress":
        return {
            "phase": phase,
            "activePlayerName": None,
            "myTeam": None,
            "lobbyTeam": [],
            "enemyTeam": [],
        }

    player_list = await get_liveclient_json("/liveclientdata/playerlist")
    active_name = await get_liveclient_json("/liveclientdata/activeplayername")
    if not isinstance(player_list, list):
        return {
            "phase": phase,
            "activePlayerName": active_name if isinstance(active_name, str) else None,
            "myTeam": None,
            "lobbyTeam": [],
            "enemyTeam": [],
        }

    normalized_players: list[dict[str, Any]] = []
    my_team: str | None = None
    active_name_normalized = active_name.strip().lower() if isinstance(active_name, str) else None

    for player in player_list:
        if not isinstance(player, dict):
            continue
        team = str(player.get("team", "")).upper()
        if team not in {"ORDER", "CHAOS"}:
            continue

        summoner_name = str(player.get("summonerName", "")).strip()
        champion_name = str(player.get("championName", "")).strip()
        level = player.get("level")
        level_int = int(level) if isinstance(level, (int, float)) else None
        is_bot = bool(player.get("isBot", False))

        if active_name_normalized and summoner_name.lower() == active_name_normalized:
            my_team = team

        normalized_players.append(
            {
                "summonerName": summoner_name or "Unknown",
                "championName": champion_name or "Unknown",
                "team": team,
                "isBot": is_bot,
                "level": level_int,
            }
        )

    if my_team is None:
        # Fallback to ORDER as local side when we cannot infer active player.
        my_team = "ORDER"

    lobby_team = [p for p in normalized_players if p.get("team") == my_team]
    enemy_team = [p for p in normalized_players if p.get("team") != my_team]

    return {
        "phase": phase,
        "activePlayerName": active_name if isinstance(active_name, str) else None,
        "myTeam": my_team,
        "lobbyTeam": lobby_team,
        "enemyTeam": enemy_team,
    }


@app.get("/api/champions")
async def api_champions() -> list[dict[str, Any]]:
    # Merge owned champions with static champion summary so Champ Select/ARAM
    # still has names for temporary/pickable champions.
    owned = await lcu.get("/lol-champions/v1/owned-champions-minimal")
    summary = await lcu.get("/lol-game-data/assets/v1/champion-summary.json")

    merged: dict[int, dict[str, Any]] = {}
    for row in normalize_champions(summary):
        champ_id = row.get("id")
        if isinstance(champ_id, int):
            merged[champ_id] = row
    for row in normalize_champions(owned):
        champ_id = row.get("id")
        if isinstance(champ_id, int):
            merged[champ_id] = row

    return sorted(merged.values(), key=lambda x: str(x.get("name", "")))


@app.get("/api/lobby/state")
async def api_lobby_state() -> dict[str, Any]:
    lobby = await lcu.get("/lol-lobby/v2/lobby")
    if isinstance(lobby, dict):
        lobby = await hydrate_lobby_member_names(lobby)
    search_state = await lcu.get("/lol-lobby/v2/lobby/matchmaking/search-state")
    return {
        "phase": await lcu.get("/lol-gameflow/v1/gameflow-phase"),
        "lobby": lobby,
        "searchState": search_state,
    }


@app.get("/api/lobby/queues")
async def api_lobby_queues() -> list[dict[str, Any]]:
    queues = await lcu.get("/lol-game-queues/v1/queues")
    normalized = normalize_queue_options(queues)
    if normalized:
        return normalized
    return fallback_queue_options()


@app.post("/api/lobby/queue")
async def api_lobby_change_queue(payload: QueuePayload) -> Any:
    phase = await lcu.get("/lol-gameflow/v1/gameflow-phase")
    disallowed_phases = {"ReadyCheck", "ChampSelect", "InProgress", "EndOfGame", "PreEndOfGame"}
    if isinstance(phase, str) and phase in disallowed_phases:
        raise HTTPException(
            status_code=409,
            detail=f"Queue change is not allowed in phase: {phase}",
        )

    lobby = await lcu.get("/lol-lobby/v2/lobby")
    current_queue_id = None
    if isinstance(lobby, dict):
        game_config = lobby.get("gameConfig")
        if isinstance(game_config, dict):
            queue_id = game_config.get("queueId")
            if isinstance(queue_id, int):
                current_queue_id = queue_id
    if current_queue_id == payload.queueId:
        return {"success": True, "queueId": payload.queueId, "message": "Queue already selected"}

    if phase == "Matchmaking":
        try:
            await lcu.request_or_raise("DELETE", "/lol-lobby/v2/lobby/matchmaking/search")
        except HTTPException:
            pass
        # Give LCU a short window to settle after stopping search.
        for _ in range(10):
            await asyncio.sleep(0.2)
            phase = await lcu.get("/lol-gameflow/v1/gameflow-phase")
            if phase != "Matchmaking":
                break

    errors: list[str] = []

    async def try_lobby_request(method: str, path: str, body: Any | None = None) -> Any:
        try:
            return await lcu.request_or_raise(method, path, body)
        except HTTPException as exc:
            errors.append(f"{method} {path} -> {exc.status_code}: {exc.detail}")
            return None

    request_body = {"queueId": payload.queueId}

    # 1) Try direct lobby recreation flow first (works on strict client builds).
    if isinstance(lobby, dict):
        await try_lobby_request("DELETE", "/lol-lobby/v2/lobby")
        await asyncio.sleep(0.3)
        recreated = await try_lobby_request("POST", "/lol-lobby/v2/lobby", request_body)
        if recreated is not None:
            return {"success": True, "queueId": payload.queueId, "message": "Queue changed via lobby recreation"}

    # 2) Try standard update verbs for client variants.
    for method in ("PUT", "POST", "PATCH"):
        result = await try_lobby_request(method, "/lol-lobby/v2/lobby", request_body)
        if result is not None:
            return {"success": True, "queueId": payload.queueId, "message": f"Queue changed via {method}"}

    # 3) Legacy/fallback flows used by some client builds.
    legacy_variants: list[tuple[str, str, Any]] = [
        ("PUT", "/lol-lobby/v1/parties/queue", payload.queueId),
        ("PUT", "/lol-lobby/v1/parties/queue", {"queueId": payload.queueId}),
        ("POST", "/lol-lobby/v1/parties/queue", payload.queueId),
        ("POST", "/lol-lobby/v1/parties/queue", {"queueId": payload.queueId}),
    ]
    for method, path, body in legacy_variants:
        legacy_result = await try_lobby_request(method, path, body)
        if legacy_result is not None:
            return {"success": True, "queueId": payload.queueId, "message": "Queue changed via parties endpoint"}

    detail = "Queue change failed"
    if errors:
        detail = f"{detail}. Attempts: {' | '.join(errors[-6:])}"
    detail = (
        f"{detail}. Arama aciksa once durdur, sonra mod sec. "
        "Parti lobbisinde sadece lider mod degistirebilir."
    )
    if any("INVALID_LOBBY" in err for err in errors):
        detail = (
            f"{detail}. Secilen mod su an gecersiz olabilir. "
            "Baska bir mod secip tekrar dene (ornegin ARAM/Ranked/Flex)."
        )
    raise HTTPException(status_code=409, detail=detail)


@app.post("/api/lobby/position-preferences")
async def api_lobby_position_preferences(payload: PositionPreferencePayload) -> Any:
    await require_phase({"Lobby", "Matchmaking"}, "Position preference update")

    allowed = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", "FILL", "UNSELECTED"}
    first = payload.firstPreference.strip().upper()
    second = payload.secondPreference.strip().upper()

    if first not in allowed or second not in allowed:
        raise HTTPException(status_code=400, detail="Invalid position preference value")
    if first == second and first not in {"FILL", "UNSELECTED"}:
        raise HTTPException(status_code=400, detail="First and second preferences must be different")

    body = {"firstPreference": first, "secondPreference": second}
    attempts: list[tuple[str, str]] = [
        ("PUT", "/lol-lobby/v2/lobby/members/localMember/position-preferences"),
        ("PUT", "/lol-lobby/v1/lobby/members/localMember/position-preferences"),
    ]
    errors: list[str] = []

    for method, path in attempts:
        try:
            return await lcu.request_or_raise(method, path, body)
        except HTTPException as exc:
            errors.append(f"{method} {path} -> {exc.status_code}: {exc.detail}")
            if exc.status_code in {404, 405}:
                continue
            raise

    detail = "Position preference update failed"
    if errors:
        detail = f"{detail}. Attempts: {' | '.join(errors[-2:])}"
    raise HTTPException(status_code=409, detail=detail)


@app.post("/api/lobby/matchmaking/start")
async def api_lobby_start_matchmaking() -> Any:
    await require_phase({"Lobby", "Matchmaking"}, "Start matchmaking")
    return await lcu.request_or_raise("POST", "/lol-lobby/v2/lobby/matchmaking/search")


@app.post("/api/lobby/matchmaking/stop")
async def api_lobby_stop_matchmaking() -> Any:
    await require_phase({"Matchmaking"}, "Stop matchmaking")
    return await lcu.request_or_raise("DELETE", "/lol-lobby/v2/lobby/matchmaking/search")


@app.get("/api/runes/pages")
async def api_rune_pages() -> Any:
    pages = await lcu.get("/lol-perks/v1/pages")
    return pages or []


@app.get("/api/runes/styles")
async def api_rune_styles() -> list[dict[str, Any]]:
    styles = await lcu.get("/lol-perks/v1/styles")
    perks = await lcu.get("/lol-perks/v1/perks")
    return normalize_rune_styles(styles, build_perk_lookup(perks))


@app.get("/api/spells")
async def api_spells_catalog() -> list[dict[str, Any]]:
    spells = await lcu.get("/lol-game-data/assets/v1/summoner-spells.json")
    if isinstance(spells, dict):
        # Client variants may wrap payload under different keys.
        for key in ("spells", "data", "items"):
            value = spells.get(key)
            if isinstance(value, list):
                spells = value
                break
    allowed_ids: set[int] | None = None

    phase = await lcu.get("/lol-gameflow/v1/gameflow-phase")
    if phase == "ChampSelect":
        pickable = await lcu.get("/lol-champ-select/v1/pickable-summoner-spell-ids")
        if isinstance(pickable, list):
            ids = {spell_id for spell_id in pickable if isinstance(spell_id, int)}
            if ids:
                allowed_ids = ids

    return normalize_summoner_spells(spells, allowed_ids=allowed_ids)


@app.get("/api/builds/suggestions/{champion_id}")
async def api_build_suggestions(champion_id: int) -> list[dict[str, Any]]:
    if champion_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid champion id")

    owned = await lcu.get("/lol-champions/v1/owned-champions-minimal")
    lobby = await lcu.get("/lol-lobby/v2/lobby")
    styles_raw = await lcu.get("/lol-perks/v1/styles")
    perks_raw = await lcu.get("/lol-perks/v1/perks")

    owned = owned if isinstance(owned, list) else []
    styles = normalize_rune_styles(styles_raw, build_perk_lookup(perks_raw))
    role = resolve_champion_role(champion_id, owned)
    queue_id: int | None = None
    if isinstance(lobby, dict):
        game_config = lobby.get("gameConfig")
        if isinstance(game_config, dict):
            raw_queue = game_config.get("queueId")
            if isinstance(raw_queue, int):
                queue_id = raw_queue

    # Prefer Riot LCU's own recommended pages when available.
    lcu_suggestions = await get_lcu_recommended_suggestions(champion_id, role, queue_id)
    if lcu_suggestions:
        return lcu_suggestions

    # If styles are empty, return hardcoded fallback presets
    if not styles:
        return [
            {
                "slotLabel": "Opsiyon 1",
                "name": "Precision Build",
                "primaryStyleId": 8000,
                "subStyleId": 8300,
                "selectedPerkIds": [8005, 9101, 9111, 8014, 8304, 8345, 5008, 5008, 5002],
                "spells": {"spell1Id": 4, "spell2Id": 14}
            },
            {
                "slotLabel": "Opsiyon 2",
                "name": "Domination Build",
                "primaryStyleId": 8100,
                "subStyleId": 8000,
                "selectedPerkIds": [8112, 8126, 8138, 8135, 9101, 9111, 5008, 5008, 5002],
                "spells": {"spell1Id": 4, "spell2Id": 14}
            },
            {
                "slotLabel": "Opsiyon 3",
                "name": "Sorcery Build",
                "primaryStyleId": 8200,
                "subStyleId": 8100,
                "selectedPerkIds": [8214, 8226, 8210, 8237, 8126, 8135, 5008, 5008, 5002],
                "spells": {"spell1Id": 4, "spell2Id": 12}
            }
        ]

    provider_url = os.environ.get("BUILD_PROVIDER_URL")
    if provider_url:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0)) as client:
                response = await client.get(provider_url, params={"championId": champion_id})
                response.raise_for_status()
                external = normalize_external_suggestions(response.json())
                if external:
                    return external
        except Exception:
            pass

    suggestions = build_role_suggestions(role, styles)
    
    # If still empty, return hardcoded fallback
    if not suggestions:
        return [
            {
                "slotLabel": "Opsiyon 1",
                "name": "Precision Build",
                "primaryStyleId": 8000,
                "subStyleId": 8300,
                "selectedPerkIds": [8005, 9101, 9111, 8014, 8304, 8345, 5008, 5008, 5002],
                "spells": {"spell1Id": 4, "spell2Id": 14}
            },
            {
                "slotLabel": "Opsiyon 2",
                "name": "Domination Build",
                "primaryStyleId": 8100,
                "subStyleId": 8000,
                "selectedPerkIds": [8112, 8126, 8138, 8135, 9101, 9111, 5008, 5008, 5002],
                "spells": {"spell1Id": 4, "spell2Id": 14}
            },
            {
                "slotLabel": "Opsiyon 3",
                "name": "Sorcery Build",
                "primaryStyleId": 8200,
                "subStyleId": 8100,
                "selectedPerkIds": [8214, 8226, 8210, 8237, 8126, 8135, 5008, 5008, 5002],
                "spells": {"spell1Id": 4, "spell2Id": 12}
            }
        ]
    
    return suggestions


@app.get("/api/asset")
async def api_asset(path: str = Query(..., description="LCU asset path, e.g. /lol-game-data/assets/...")) -> Response:
    if not path:
        raise HTTPException(status_code=400, detail="Missing asset path")

    normalized_path = path if path.startswith("/") else f"/{path}"
    if not normalized_path.startswith("/lol-game-data/assets/"):
        raise HTTPException(status_code=400, detail="Asset path is not allowed")

    data = await lcu.get_raw(normalized_path)
    if not data:
        raise HTTPException(status_code=404, detail="Asset not found")

    content, content_type = data
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/compliance")
async def api_compliance() -> dict[str, Any]:
    return {
        "manualOnly": True,
        "automatedInGameActions": False,
        "allowedActionPhases": {
            "acceptReadyCheck": ["ReadyCheck"],
            "hoverLockBanSpellsRunes": ["ChampSelect"],
            "champSelectSwaps": ["ChampSelect"],
            "positionPreferences": ["Lobby", "Matchmaking"],
            "lobbyQueueChange": ["Lobby", "Matchmaking"],
            "matchmakingStart": ["Lobby", "Matchmaking"],
            "matchmakingStop": ["Matchmaking"],
        },
        "policyHint": "Register your product in Riot Developer Portal and keep features audited.",
    }


@app.post("/api/ready-check/accept")
async def api_ready_check_accept() -> Any:
    await require_phase({"ReadyCheck"}, "Ready check accept")
    return await lcu.request_or_raise("POST", "/lol-matchmaking/v1/ready-check/accept")


@app.post("/api/champ-select/hover")
async def api_hover(payload: PickPayload) -> Any:
    await require_phase({"ChampSelect"}, "Champion hover")
    session = await lcu.get("/lol-champ-select/v1/session")
    if not isinstance(session, dict):
        raise HTTPException(status_code=409, detail="Not in champion select")

    action = get_current_action(session, "pick")
    if not action:
        raise HTTPException(status_code=409, detail="No active pick action for local player")

    action_id = action.get("id")
    return await lcu.request_or_raise("PATCH", f"/lol-champ-select/v1/session/actions/{action_id}", {"championId": payload.championId})


@app.post("/api/champ-select/lock")
async def api_lock(payload: PickPayload) -> Any:
    await require_phase({"ChampSelect"}, "Champion lock")
    session = await lcu.get("/lol-champ-select/v1/session")
    if not isinstance(session, dict):
        raise HTTPException(status_code=409, detail="Not in champion select")

    action = get_current_action(session, "pick")
    if not action:
        raise HTTPException(status_code=409, detail="No active pick action for local player")

    action_id = action.get("id")
    return await lcu.request_or_raise(
        "PATCH",
        f"/lol-champ-select/v1/session/actions/{action_id}",
        {"championId": payload.championId, "completed": True},
    )


@app.post("/api/champ-select/bench/select")
async def api_bench_select(payload: PickPayload) -> Any:
    await require_phase({"ChampSelect"}, "Champion bench select")
    champion_id = payload.championId
    paths = [
        f"/lol-champ-select/v1/session/bench/swap/{champion_id}",
        f"/lol-lobby-team-builder/champ-select/v1/session/bench/swap/{champion_id}",
    ]
    last_error: HTTPException | None = None
    for path in paths:
        try:
            return await lcu.request_or_raise("POST", path)
        except HTTPException as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error
    raise HTTPException(status_code=500, detail="Bench select failed")


@app.post("/api/champ-select/ban")
async def api_ban(payload: PickPayload) -> Any:
    await require_phase({"ChampSelect"}, "Champion ban")
    session = await lcu.get("/lol-champ-select/v1/session")
    if not isinstance(session, dict):
        raise HTTPException(status_code=409, detail="Not in champion select")

    action = get_current_action(session, "ban")
    if not action:
        raise HTTPException(status_code=409, detail="No active ban action for local player")

    action_id = action.get("id")
    return await lcu.request_or_raise(
        "PATCH",
        f"/lol-champ-select/v1/session/actions/{action_id}",
        {"championId": payload.championId, "completed": True},
    )


@app.post("/api/champ-select/spells")
async def api_spells(payload: SpellPayload) -> Any:
    await require_phase({"ChampSelect"}, "Summoner spells update")
    return await lcu.request_or_raise(
        "PATCH",
        "/lol-champ-select/v1/session/my-selection",
        {"spell1Id": payload.spell1Id, "spell2Id": payload.spell2Id},
    )


@app.post("/api/champ-select/swap")
async def api_champ_select_swap(payload: SwapActionPayload) -> Any:
    await require_phase({"ChampSelect"}, "Champion select swap action")

    swap_type_key = payload.swapType.strip().lower().replace("-", "_")
    action = payload.action.strip().lower()

    swap_segment_map = {
        "champion": "champion-swaps",
        "champion_swap": "champion-swaps",
        "position": "position-swaps",
        "position_swap": "position-swaps",
        "lane": "position-swaps",
        "lane_swap": "position-swaps",
        "pick_order": "pick-order-swaps",
        "pickorder": "pick-order-swaps",
        "turn_order": "pick-order-swaps",
        "order": "pick-order-swaps",
    }
    action_set = {"request", "accept", "decline", "cancel"}

    segment = swap_segment_map.get(swap_type_key)
    if not segment:
        raise HTTPException(status_code=400, detail=f"Unsupported swapType: {payload.swapType}")
    if action not in action_set:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {payload.action}")

    swap_id = payload.swapId
    paths = [
        f"/lol-champ-select/v1/session/{segment}/{swap_id}/{action}",
        f"/lol-lobby-team-builder/champ-select/v1/session/{segment}/{swap_id}/{action}",
    ]
    return await post_with_fallback(paths)


@app.post("/api/runes/apply")
async def api_apply_runes(payload: RunePayload) -> Any:
    await require_phase({"ChampSelect"}, "Rune apply")
    base_payload = {
        "name": payload.name,
        "current": True,
        "primaryStyleId": payload.primaryStyleId,
        "subStyleId": payload.subStyleId,
        "selectedPerkIds": payload.selectedPerkIds,
        "isDeletable": True,
        "isEditable": True,
        "order": 0,
    }

    # Prefer updating the current rune page to avoid creating new pages on each edit.
    current_page = await lcu.get("/lol-perks/v1/currentpage")
    current_page_id = current_page.get("id") if isinstance(current_page, dict) else None
    if isinstance(current_page_id, int):
        update_payload = {**base_payload, "id": current_page_id}
        try:
            return await lcu.request_or_raise("PUT", f"/lol-perks/v1/pages/{current_page_id}", update_payload)
        except HTTPException as exc:
            if exc.status_code not in {400, 403, 404}:
                raise

    # Fallback: create a page only when update is not possible.
    pages = await lcu.get("/lol-perks/v1/pages")
    if isinstance(pages, list) and len(pages) >= 20:
        deletable_ids: list[int] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_id = page.get("id")
            if not isinstance(page_id, int):
                continue
            if page_id == current_page_id:
                continue
            if page.get("isDeletable") is not True:
                continue
            deletable_ids.append(page_id)

        for page_id in deletable_ids:
            try:
                await lcu.request_or_raise("DELETE", f"/lol-perks/v1/pages/{page_id}")
                break
            except HTTPException:
                continue

    try:
        return await lcu.request_or_raise("POST", "/lol-perks/v1/pages", base_payload)
    except HTTPException as exc:
        detail_text = str(exc.detail) if exc.detail is not None else ""
        if exc.status_code == 400 and "Max pages reached" in detail_text:
            raise HTTPException(
                status_code=409,
                detail="Rune page limiti dolu. Silinebilir bir rune sayfasi silip tekrar dene.",
            ) from exc
        raise


@app.websocket("/ws")
async def websocket_state(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(state_cache)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "timestamp": datetime.now(timezone.utc).isoformat()}

# ---------------------------------------------------------------------------
# Site API — PC registration, token, pairing, APK version
# ---------------------------------------------------------------------------

@app.post("/api/pc/register")
async def site_pc_register(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    remote_url = body.get("remote_url")
    if not remote_url:
        raise HTTPException(status_code=400, detail="remote_url required")
    device_id = body.get("device_id") or _site_device_id()
    pc_name = body.get("pc_name", "")
    conn = _get_site_db()
    existing = conn.execute("SELECT device_id FROM pcs WHERE device_id = ?", (device_id,)).fetchone()
    if existing:
        conn.execute("UPDATE pcs SET remote_url = ?, pc_name = COALESCE(?, pc_name), last_seen = datetime('now') WHERE device_id = ?", (remote_url, pc_name, device_id))
    else:
        conn.execute("INSERT INTO pcs (device_id, remote_url, pc_name) VALUES (?, ?, ?)", (device_id, remote_url, pc_name))
    conn.commit()
    conn.close()
    return JSONResponse({"status": "ok", "device_id": device_id})


@app.post("/api/pc/token")
async def site_pc_token(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    device_id = body.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")
    conn = _get_site_db()
    pc = conn.execute("SELECT device_id FROM pcs WHERE device_id = ?", (device_id,)).fetchone()
    if not pc:
        conn.close()
        raise HTTPException(status_code=404, detail="PC not registered")
    token = _site_token()
    expires_at = datetime.now(timezone.utc).isoformat()  # +10m simplified
    conn.execute("INSERT INTO tokens (token, device_id, purpose, expires_at) VALUES (?, ?, 'pair', datetime('now', '+10 minutes'))", (token, device_id))
    conn.commit()
    conn.close()
    return JSONResponse({"status": "ok", "token": token})


@app.post("/api/mobile/pair")
async def site_mobile_pair(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    mobile_id = body.get("mobile_id") or _site_mobile_id()
    conn = _get_site_db()
    row = conn.execute(
        "SELECT t.*, p.remote_url, p.pc_name FROM tokens t JOIN pcs p ON p.device_id = t.device_id WHERE t.token = ? AND t.used = 0 AND t.expires_at > datetime('now')",
        (token,)
    ).fetchone()
    if not row:
        used = conn.execute("SELECT used FROM tokens WHERE token = ?", (token,)).fetchone()
        msg = "Token already used" if used else "Token invalid or expired"
        conn.close()
        raise HTTPException(status_code=401, detail=msg)
    device_id = row["device_id"]
    remote_url = row["remote_url"]
    pc_name = row["pc_name"]
    conn.execute("UPDATE tokens SET used = 1 WHERE token = ?", (token,))
    conn.execute("INSERT OR IGNORE INTO pairings (device_id, mobile_id) VALUES (?, ?)", (device_id, mobile_id))
    conn.commit()
    conn.close()
    return JSONResponse({"status": "ok", "device_id": device_id, "remote_url": remote_url, "pc_name": pc_name, "mobile_id": mobile_id})


@app.get("/api/pair-qr")
async def site_pair_qr(request: Request) -> JSONResponse:
    conn = _get_site_db()
    row = conn.execute("SELECT device_id, remote_url FROM pcs ORDER BY rowid DESC LIMIT 1").fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Kayitli PC bulunamadi. Uygulamayi PC'nde calistir.")
    device_id = row["device_id"]
    remote_url = row["remote_url"]
    token = _site_token()
    conn.execute("INSERT INTO tokens (token, device_id, purpose, expires_at) VALUES (?, ?, 'pair', datetime('now', '+10 minutes'))", (token, device_id))
    conn.commit()
    conn.close()
    site_origin = os.environ.get("NEXT_PUBLIC_SITE_URL", "").rstrip("/") or str(request.base_url).rstrip("/")
    qr_url = f"{site_origin}/qrcode?token={quote(token)}"
    return JSONResponse({"status": "ok", "token": token, "qr_url": qr_url, "remote_url": remote_url})


@app.get("/api/latestapk")
async def site_latest_apk() -> JSONResponse:
    ver_path = Path(__file__).resolve().parent / "site" / "public" / "apps" / "version.json"
    if ver_path.exists():
        try:
            data = json.loads(ver_path.read_text(encoding="utf-8"))
            data["download_url"] = "/apps/app-release.apk"
            return JSONResponse(data)
        except Exception:
            pass
    return JSONResponse({"version": "0.0.0", "error": "Version info not found", "download_url": ""})



# ---------------------------------------------------------------------------

@app.get("/api/mobile/session")
async def mobile_session_state(request: Request) -> dict[str, Any]:
    # Minimal mobile session gate check. Pairing route sets lolsiken_pair cookie.
    return {"paired": request.cookies.get("lolsiken_pair") == "ok"}

@app.get("/mobile/pair")
async def mobile_pair(token: str = Query(..., min_length=16)) -> Response:
    if not token_manager.consume_token(token):
        raise HTTPException(status_code=401, detail="Pairing token gecersiz veya suresi doldu.")
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="lolsiken_pair",
        value="ok",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600,
    )
    return response


@app.get("/mobile/connect")
async def mobile_connect(
    token: str = Query(..., min_length=16),
    local: str = Query(..., min_length=8),
    remote: str = Query(default=""),
) -> Response:
    token_esc = token.replace("'", "\\'")
    local_esc = local.replace("'", "\\'")
    remote_esc = remote.replace("'", "\\'")
    html = f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Baglanti Kontrolu</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0a1428; color:#fff; margin:0; }}
    .wrap {{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }}
    .card {{ width:100%; max-width:460px; background:#101d37; border:1px solid #2a3f66; border-radius:14px; padding:18px; }}
    h2 {{ margin:0 0 10px; color:#c8aa6e; font-size:22px; }}
    p {{ margin:8px 0; color:#d7dbe5; line-height:1.45; }}
    .muted {{ color:#9fb0cc; font-size:14px; }}
    .err {{ color:#ff9ea1; font-weight:700; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h2>Baglanti kontrol ediliyor</h2>
      <p id="status">Uygun baglanti bulunuyor...</p>
      <p class="muted">Ayni agdaysaniz local, degilseniz remote otomatik secilecektir.</p>
      <p id="error" class="err" style="display:none;">Internet baglantinizi kontrol edin.</p>
    </div>
  </div>
  <script>
    const token = '{token_esc}';
    const localBase = decodeURIComponent('{local_esc}');
    const remoteBase = decodeURIComponent('{remote_esc}');
    const statusEl = document.getElementById('status');
    const errorEl = document.getElementById('error');

    async function reachable(base, timeoutMs) {{
      if (!base) return false;
      try {{
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), timeoutMs);
        const res = await fetch(base + '/api/health', {{ method:'GET', cache:'no-store', mode:'cors', credentials:'omit', signal: ctrl.signal }});
        clearTimeout(t);
        return res.ok;
      }} catch {{
        return false;
      }}
    }}

    (async () => {{
      statusEl.textContent = 'Local baglanti kontrol ediliyor...';
      if (await reachable(localBase, 1800)) {{
        window.location.replace(localBase + '/mobile/pair?token=' + encodeURIComponent(token));
        return;
      }}
      if (remoteBase) {{
        statusEl.textContent = 'Remote baglanti kontrol ediliyor...';
        if (await reachable(remoteBase, 3500)) {{
          window.location.replace(remoteBase + '/mobile/pair?token=' + encodeURIComponent(token));
          return;
        }}
      }}
      statusEl.textContent = 'Baglanti kurulamadi.';
      errorEl.style.display = 'block';
    }})();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# Serve Next.js static assets and APK files
_next_static = Path(__file__).resolve().parent / "site" / "out" / "_next" / "static"
if _next_static.exists():
    app.mount("/_next/static", StaticFiles(directory=str(_next_static)), name="next-static")

_site_public = Path(__file__).resolve().parent / "site" / "public"

_out_root = Path(__file__).resolve().parent / "site" / "out"

_html_cache: dict[str, str] = {}
if _out_root.exists():
    for f in _out_root.iterdir():
        if f.suffix == ".html":
            name = "index" if f.stem == "index" else f.stem
            _html_cache[name] = f.read_text(encoding="utf-8")


@app.get("/")
async def next_index() -> HTMLResponse:
    return HTMLResponse(content=_html_cache.get("index", "<h1>LoL Makro</h1>"))


@app.get("/qrcode")
async def next_qrcode() -> HTMLResponse:
    return HTMLResponse(content=_html_cache.get("qrcode", "<h1>QR Code</h1>"))


@app.get("/apps")
async def apps_landing() -> HTMLResponse:
    apps_index = Path(__file__).resolve().parent / "site" / "public" / "apps" / "index.html"
    if apps_index.exists():
        return HTMLResponse(content=apps_index.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Uygulamalar</h1><p>Henuz yuklenmedi.</p>")


_apps_dir = Path(__file__).resolve().parent / "site" / "public" / "apps"


@app.get("/apps/{file_path:path}")
async def apps_static(file_path: str) -> FileResponse:
    target = (_apps_dir / file_path).resolve()
    if not str(target).startswith(str(_apps_dir.resolve())):
        raise HTTPException(status_code=404)
    if target.exists() and target.is_file():
        return FileResponse(path=str(target))
    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("LOL_BRIDGE_HOST", "0.0.0.0")
    port = int(os.environ.get("LOL_BRIDGE_PORT", "8765"))
    uvicorn.run("live_server:app", host=host, port=port, reload=False)
