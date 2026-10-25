"""Supabase integration service.
Supports two modes:
1. Direct PostgreSQL via DATABASE_URL / SUPABASE_DB_URL in Django DATABASES (primary recommended mode).
2. REST API synchronization via SUPABASE_URL + SUPABASE_KEY (PostgREST) when running with local SQLite cache.
"""
import json
import logging
import threading
import urllib.error
import urllib.request
from django.conf import settings

logger = logging.getLogger(__name__)


def is_postgres_active() -> bool:
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    return "postgresql" in engine or "postgis" in engine


def is_rest_configured() -> bool:
    url = getattr(settings, "SUPABASE_URL", "") or ""
    key = getattr(settings, "SUPABASE_KEY", "") or ""
    return bool(url.strip() and key.strip() and not url.startswith("https://your-project"))


def get_status() -> dict:
    pg = is_postgres_active()
    rest = is_rest_configured()
    db_host = settings.DATABASES.get("default", {}).get("HOST", "")
    is_supabase_pg = pg and ("supabase.co" in str(db_host) or "supabase.com" in str(db_host))
    if is_supabase_pg:
        backend_label = "supabase-postgres"
    elif pg:
        backend_label = "postgresql"
    elif rest:
        backend_label = "sqlite+supabase-rest"
    else:
        backend_label = "sqlite-fallback"
    return {
        "backend": backend_label,
        "supabase_connected": bool(is_supabase_pg or rest),
        "postgres_active": pg,
        "rest_sync_enabled": rest,
        "host": db_host if pg else "local (db.sqlite3)",
    }


def _rest_request(method: str, table: str, payload=None, query: str = ""):
    if not is_rest_configured():
        return None
    base_url = settings.SUPABASE_URL.rstrip("/")
    api_key = settings.SUPABASE_KEY.strip()
    url = f"{base_url}/rest/v1/{table}{('?' + query) if query else ''}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal,resolution=merge-duplicates",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except Exception as exc:
        logger.debug("Supabase REST sync (%s %s) skipped/failed: %s", method, table, exc)
        return None


def sync_async(method: str, table: str, payload=None, query: str = ""):
    """Fire-and-forget sync to Supabase PostgREST when running on SQLite with SUPABASE_URL+SUPABASE_KEY."""
    if is_postgres_active() or not is_rest_configured():
        return
    threading.Thread(
        target=_rest_request,
        args=(method, table, payload, query),
        daemon=True,
    ).start()


def sync_person(person):
    sync_async("POST", "door_person", {
        "id": person.id,
        "full_name": person.full_name,
        "role": person.role,
        "status": person.status,
        "created_at": person.created_at.isoformat() if person.created_at else None,
    })


def delete_person_remote(person_id: int):
    sync_async("DELETE", "door_person", None, f"id=eq.{person_id}")


def sync_face_profile(fp):
    sync_async("POST", "door_faceprofile", {
        "id": fp.id,
        "person_id": fp.person_id,
        "embedding": fp.embedding,
        "quality": fp.quality,
        "image_path": fp.image_path,
        "created_at": fp.created_at.isoformat() if fp.created_at else None,
    })


def sync_access_log(log_obj):
    sync_async("POST", "door_accesslog", {
        "id": log_obj.id,
        "person_id": log_obj.person_id,
        "event_type": log_obj.event_type,
        "confidence": log_obj.confidence,
        "device": log_obj.device,
        "detail": log_obj.detail,
        "timestamp": log_obj.timestamp.isoformat() if log_obj.timestamp else None,
    })
