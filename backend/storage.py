"""Owner-scoped durable documents. Raw session tokens are never stored."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import httpx


def now():
    return datetime.now(timezone.utc).isoformat()


class StoreError(Exception):
    pass


class SQLiteStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS documents (owner TEXT, kind TEXT, id TEXT, data TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(owner, kind, id))")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    async def put(self, owner, kind, key, data, create_only=False):
        with self.connect() as db:
            if create_only:
                cursor = db.execute("INSERT OR IGNORE INTO documents VALUES (?,?,?,?,?)", (owner, kind, key, json.dumps(data, ensure_ascii=False), now()))
                return cursor.rowcount > 0
            db.execute("INSERT INTO documents VALUES (?,?,?,?,?) ON CONFLICT(owner,kind,id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at", (owner, kind, key, json.dumps(data, ensure_ascii=False), now()))
        return True

    async def get(self, owner, kind, key):
        with self.connect() as db:
            row = db.execute("SELECT data FROM documents WHERE owner=? AND kind=? AND id=?", (owner, kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    async def list(self, owner, kind):
        with self.connect() as db:
            rows = db.execute("SELECT id,data FROM documents WHERE owner=? AND kind=? ORDER BY updated_at DESC LIMIT 100", (owner, kind)).fetchall()
        return [{**json.loads(row[1]), "id": row[0]} for row in rows]

    async def delete(self, owner, kind, key):
        with self.connect() as db:
            db.execute("DELETE FROM documents WHERE owner=? AND kind=? AND id=?", (owner, kind, key))


class SupabaseStore:
    def __init__(self, settings):
        self.url = settings.supabase_url.rstrip("/") + "/rest/v1/documents"
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": "Bearer " + settings.supabase_service_role_key,
            "Accept-Profile": settings.supabase_schema,
            "Content-Profile": settings.supabase_schema,
        }

    async def request(self, method, params=None, data=None, prefer=None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.request(method, self.url, params=params, json=data, headers=headers)
            if response.status_code == 409:
                return None
            response.raise_for_status()
            return response.json() if response.content else []
        except (httpx.HTTPError, ValueError) as exc:
            raise StoreError("Supabase 접근 실패: 서버 키·스키마 노출·documents 테이블을 확인하세요.") from exc

    async def put(self, owner, kind, key, data, create_only=False):
        result = await self.request("POST", params={"on_conflict": "owner,kind,id"}, data={"owner": owner, "kind": kind, "id": key, "data": data, "updated_at": now()}, prefer="return=representation" + ("" if create_only else ",resolution=merge-duplicates"))
        return result is not None

    async def get(self, owner, kind, key):
        result = await self.request("GET", {"owner": "eq." + owner, "kind": "eq." + kind, "id": "eq." + key, "select": "data", "limit": "1"})
        return result[0]["data"] if result else None

    async def list(self, owner, kind):
        result = await self.request("GET", {"owner": "eq." + owner, "kind": "eq." + kind, "select": "id,data", "order": "updated_at.desc", "limit": "100"})
        return [{**row["data"], "id": row["id"]} for row in result]

    async def delete(self, owner, kind, key):
        await self.request("DELETE", {"owner": "eq." + owner, "kind": "eq." + kind, "id": "eq." + key})
