#!/usr/bin/env python3
"""Periodic Arkeo cache fetcher for dashboard-core.

Fetches providers, contracts, validators, and services from arkeod every CACHE_FETCH_INTERVAL
seconds and writes JSON to CACHE_DIR for use by the UI or other helpers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from urllib import request
from urllib.parse import urlparse

ARKEOD_HOME = os.path.expanduser(os.getenv("ARKEOD_HOME", "/root/.arkeo"))
# These are dynamically refreshed from subscriber-settings.json before each fetch cycle (if present)
ARKEOD_NODE = os.getenv("ARKEOD_NODE") or "tcp://127.0.0.1:26657"
CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")
STATUS_FILE = os.path.join(CACHE_DIR, "_sync_status.json")
SUBSCRIBER_SETTINGS_PATH = os.path.join(CACHE_DIR, "subscriber-settings.json")
METADATA_CACHE_PATH = os.path.join(CACHE_DIR, "metadata.json")
# Allow localhost/127.x metadata_uri for testing if set
ALLOW_LOCALHOST_SENTINEL_URIS = str(
    os.getenv("ALLOW_LOCAL_METADATA") or os.getenv("ALLOW_LOCALHOST_SENTINEL_URIS") or "0"
).lower() in {"1", "true", "yes", "y", "on"}
# Static service type metadata (to merge chain fields) now lives under /app/admin
SERVICE_TYPE_RESOURCES_PATH = os.getenv("SERVICE_TYPE_RESOURCES_PATH", "/app/admin/service-type_resources.json")


def run_list(cmd: List[str]) -> Tuple[int, str]:
    """Run a command without a shell and return (exit_code, output)."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return 0, out.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output.decode("utf-8")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_cache_dir() -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except OSError:
        pass


def _write_status(payload: Dict[str, Any]) -> None:
    """Write sync status atomically."""
    path = STATUS_FILE
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
        os.replace(tmp_path, path)
    except OSError:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def mark_sync_start(started_at: str | None = None) -> None:
    ensure_cache_dir()
    payload = {
        "in_progress": True,
        "started_at": started_at or timestamp(),
    }
    _write_status(payload)


def mark_sync_end(ok: bool = True, error: str | None = None) -> None:
    ensure_cache_dir()
    finished = timestamp()
    payload = {
        "in_progress": False,
        "finished_at": finished,
    }
    if ok:
        payload["last_success"] = finished
    if error:
        payload["last_error"] = error
    _write_status(payload)


def _parse_service_types_text(raw: str) -> Dict[str, Any] | None:
    """Parse text output from `arkeod query arkeo all-services` into {"services": [...]}."""
    if not isinstance(raw, str):
        return None
    services = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("Arkeo Supported Provider Service List"):
            continue
        # Expect lines like "- name : id (Description)"
        m = re.match(r"-\s*(.+?)\s*:\s*([0-9]+)\s*\((.*?)\)\s*$", line)
        if not m:
            continue
        name = m.group(1).strip()
        sid = m.group(2).strip()
        desc = m.group(3).strip()
        try:
            sid_int = int(sid)
        except ValueError:
            sid_int = sid
        services.append({"service_id": sid_int, "name": name, "description": desc})
    if not services:
        return None
    return {"services": services}


def build_commands() -> Dict[str, List[str]]:
    base = ["arkeod", "--home", ARKEOD_HOME]
    if ARKEOD_NODE:
        base.extend(["--node", ARKEOD_NODE])
    return {
        "provider-services": [*base, "query", "arkeo", "list-providers", "-o", "json"],
        "provider-contracts": [*base, "query", "arkeo", "list-contracts", "-o", "json"],
        "validators": [*base, "query", "staking", "validators", "--page-limit", "1000", "--page-count-total", "--status", "BOND_STATUS_BONDED", "-o", "json"],
        "service-types": [*base, "query", "arkeo", "all-services", "-o", "json"],
    }


def normalize_result(name: str, code: int, out: str, cmd: List[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "fetched_at": timestamp(),
        "exit_code": code,
        "cmd": cmd,
    }
    if code == 0:
        try:
            payload["data"] = json.loads(out)
        except json.JSONDecodeError:
            payload["data"] = out
    else:
        payload["error"] = out
    return payload


def fetch_metadata_uri(url: str, timeout: float = 5.0) -> Tuple[Any, str | None, int]:
    """Fetch metadata from a URI; return (parsed_or_raw, error_string_or_None, status_flag)."""
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e), 0
    try:
        return json.loads(body), None, 1
    except json.JSONDecodeError:
        return body, None, 1


def merge_service_types_with_resources(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge service-types payload with static resources to add chain when available."""
    try:
        with open(SERVICE_TYPE_RESOURCES_PATH, "r", encoding="utf-8") as f:
            static_data = json.load(f)
    except Exception:
        return payload
    services_static = []
    data_static = static_data.get("data") if isinstance(static_data, dict) else {}
    if isinstance(data_static, list):
        services_static = data_static
    elif isinstance(data_static, dict):
        services_static = data_static.get("services") or data_static.get("service") or data_static.get("result") or []
    if not isinstance(services_static, list):
        return payload
    id_lookup: Dict[str, str] = {}
    name_lookup: Dict[str, str] = {}
    for s in services_static:
        if not isinstance(s, dict):
            continue
        chain_val = s.get("chain")
        if not chain_val:
            continue
        sid = s.get("service_id") or s.get("id")
        if sid is not None:
            id_lookup[str(sid)] = chain_val
        name_val = s.get("name") or s.get("service")
        if name_val:
            name_lookup[str(name_val).lower()] = chain_val

        data_live = payload.get("data")
        live_list = []
        if isinstance(data_live, list):
            live_list = data_live
        elif isinstance(data_live, dict):
            live_list = data_live.get("services") or data_live.get("service") or data_live.get("result") or []
        if not isinstance(live_list, list):
            return payload
    changed = False
    for svc in live_list:
        if not isinstance(svc, dict):
            continue
        if svc.get("chain"):
            continue
        sid = svc.get("service_id") or svc.get("id")
        sname = svc.get("name") or svc.get("service")
        chain_val = None
        if sid is not None and str(sid) in id_lookup:
            chain_val = id_lookup[str(sid)]
        elif sname and str(sname).lower() in name_lookup:
            chain_val = name_lookup[str(sname).lower()]
        if chain_val is not None:
            svc["chain"] = chain_val
            changed = True
    if not changed:
        return payload
    if isinstance(data_live, list):
        payload["data"] = live_list
    elif isinstance(data_live, dict):
        if isinstance(data_live.get("services"), list):
            data_live["services"] = live_list
        elif isinstance(data_live.get("service"), list):
            data_live["service"] = live_list
        elif isinstance(data_live.get("result"), list):
            data_live["result"] = live_list
        payload["data"] = data_live
    return payload


def _is_external(uri: str | None) -> bool:
    if not uri:
        return False
    try:
        parsed = urlparse(uri)
        host = (parsed.hostname or "").lower()
        if not parsed.scheme or not host:
            return False
        if host == "localhost" or host.startswith("127."):
            return ALLOW_LOCALHOST_SENTINEL_URIS
        return True
    except Exception:
        return False


def _is_localhost_uri(uri: str | None) -> bool:
    if not uri:
        return False
    try:
        parsed = urlparse(uri)
        host = (parsed.hostname or "").lower()
        return host == "localhost" or host.startswith("127.")
    except Exception:
        return False


def _refresh_runtime_settings() -> None:
    """Reload ARKEOD_NODE from env (preferred) or subscriber-settings.json."""
    global ARKEOD_NODE, ALLOW_LOCALHOST_SENTINEL_URIS
    settings = {}
    try:
        with open(SUBSCRIBER_SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f) or {}
    except Exception:
        settings = {}
    node_val = os.getenv("ARKEOD_NODE") or settings.get("ARKEOD_NODE") or ARKEOD_NODE
    allow_local = settings.get("ALLOW_LOCALHOST_SENTINEL_URIS") or os.getenv("ALLOW_LOCAL_METADATA") or os.getenv("ALLOW_LOCALHOST_SENTINEL_URIS") or "0"
    if node_val:
        ARKEOD_NODE = str(node_val).strip()
    ALLOW_LOCALHOST_SENTINEL_URIS = str(allow_local).lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


# Resolve fetch interval after helpers are defined
CACHE_FETCH_INTERVAL = _env_int("CACHE_FETCH_INTERVAL", 300)


def _load_metadata_cache() -> dict[str, dict[str, Any]]:
    try:
        with open(METADATA_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            items = data.get("metadata") or data
            if isinstance(items, dict):
                return items
    except Exception:
        pass
    return {}


def _save_metadata_cache(cache: dict[str, dict[str, Any]]) -> None:
    ensure_cache_dir()
    payload = {"metadata": cache}
    tmp_path = f"{METADATA_CACHE_PATH}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
        os.replace(tmp_path, METADATA_CACHE_PATH)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _update_metadata_cache_from_providers(provider_services_payload: Dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Fetch metadata for unique metadata_uri entries, storing only successful JSON parses."""
    cache_map = _load_metadata_cache()
    changed = False
    data = provider_services_payload.get("data") if isinstance(provider_services_payload, dict) else {}
    prov_entries = []
    if isinstance(data, dict):
        prov_entries = data.get("providers") or data.get("provider") or []
    if not isinstance(prov_entries, list):
        prov_entries = []

    uris = set()

    def _collect_mu(entry: dict[str, Any] | None):
        if not entry or not isinstance(entry, dict):
            return
        mu = entry.get("metadata_uri") or entry.get("metadataUri")
        if mu and _is_external(mu):
            uris.add(mu)

    for p in prov_entries:
        if not isinstance(p, dict):
            continue
        _collect_mu(p)
        if isinstance(p.get("services"), list):
            for s in p["services"]:
                _collect_mu(s if isinstance(s, dict) else None)
        if isinstance(p.get("service"), list):
            for s in p["service"]:
                _collect_mu(s if isinstance(s, dict) else None)

    for mu in uris:
        if mu in cache_map:
            continue
        data_val, err_val, status_val = fetch_metadata_uri(mu)
        if status_val == 1 and isinstance(data_val, dict):
            cache_map[mu] = {"metadata_uri": mu, "fetched_at": timestamp(), "data": data_val}
            changed = True
    if changed:
        _save_metadata_cache(cache_map)
    return cache_map


def _parse_int_value(val: Any) -> int | None:
    """Return an integer from various representations (raw int, numeric string, or coin string)."""
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None
    if isinstance(val, str):
        digits = ""
        for ch in val:
            if ch.isdigit():
                digits += ch
            elif digits:
                break
        if digits:
            try:
                return int(digits)
            except (TypeError, ValueError):
                return None
    return None


def _bond_amount_uarkeo(entry: Dict[str, Any]) -> int:
    """Extract a bond amount in uarkeo (best-effort)."""
    bond = entry.get("bond")
    if isinstance(bond, dict):
        denom = bond.get("denom") or bond.get("Denom")
        amount_val = bond.get("amount") or bond.get("Amount")
        if denom and str(denom).lower() != "uarkeo":
            return 0
        amt = _parse_int_value(amount_val)
        return amt if isinstance(amt, int) else 0
    amt = _parse_int_value(bond)
    return amt if isinstance(amt, int) else 0


def _min_payg_rate(raw: Dict[str, Any]) -> tuple[int | None, str | None]:
    """Return (amount_int, denom) for the lowest pay_as_you_go_rate entry, or (None, None) if missing."""
    if not isinstance(raw, dict):
        return None, None
    rates = raw.get("pay_as_you_go_rate") or raw.get("pay_as_you_go_rates") or []
    if not isinstance(rates, list):
        return None, None
    best_amt = None
    best_denom = None
    for r in rates:
        if not isinstance(r, dict):
            continue
        denom = r.get("denom") or r.get("Denom")
        amt = r.get("amount") or r.get("Amount")
        amt_int = _parse_int_value(amt)
        if amt_int is None:
            continue
        if best_amt is None or amt_int < best_amt:
            best_amt = amt_int
            best_denom = denom
    return best_amt, best_denom


def build_active_services(provider_services_payload: Dict[str, Any], metadata_cache: dict[str, dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Build active_services.json: pick ONLINE services whose metadata_uri resolved in metadata.json and meet bond threshold."""
    metadata_cache = metadata_cache or {}
    active_mu = set(metadata_cache.keys())
    data = provider_services_payload.get("data") if isinstance(provider_services_payload, dict) else {}
    prov_entries = []
    if isinstance(data, dict):
        prov_entries = data.get("providers") or data.get("provider") or []
    if not isinstance(prov_entries, list):
        prov_entries = []

    active_services: list[dict[str, Any]] = []

    for entry in prov_entries:
        if not isinstance(entry, dict):
            continue
        pk = entry.get("pub_key") or entry.get("pubkey") or entry.get("pubKey")
        if not pk:
            continue
        status_val = entry.get("status")
        status_str = str(status_val).strip().lower() if status_val is not None else ""
        if status_str != "online" and status_val not in (1, True, "1"):
            continue
        bond_amt = _bond_amount_uarkeo(entry)
        if bond_amt < 100_000_000:
            continue
        payg_amt, payg_denom = _min_payg_rate(entry)
        if payg_amt is None or payg_amt <= 0:
            continue
        mu = entry.get("metadata_uri") or entry.get("metadataUri")
        if not mu or not _is_external(mu) or mu not in active_mu:
            continue
        active_services.append(
            {
                "provider_pubkey": pk,
                "service_id": entry.get("service_id") or entry.get("id") or entry.get("service"),
                "service": entry.get("service") or entry.get("name"),
                "metadata_uri": mu,
                "pay_as_you_go_rate": {"amount": payg_amt, "denom": payg_denom},
                "raw": entry,
            }
        )

    return {
        "fetched_at": timestamp(),
        "source": "provider-services",
        "active_services": active_services,
    }


def build_active_providers_from_active_services(active_services_payload: Dict[str, Any], provider_services_payload: Dict[str, Any], metadata_cache: dict[str, dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Build active_providers.json: one entry per provider pubkey with online services and cached metadata."""
    active_services = active_services_payload.get("active_services") if isinstance(active_services_payload, dict) else []
    if not isinstance(active_services, list):
        active_services = []
    meta_cache = metadata_cache or {}

    active_provider_pks = set()
    for svc in active_services:
        if isinstance(svc, dict) and svc.get("provider_pubkey"):
            active_provider_pks.add(str(svc.get("provider_pubkey")))

    data = provider_services_payload.get("data") if isinstance(provider_services_payload, dict) else {}
    prov_entries = []
    if isinstance(data, dict):
        prov_entries = data.get("providers") or data.get("provider") or []
    if not isinstance(prov_entries, list):
        prov_entries = []

    providers: list[dict[str, Any]] = []
    seen_pubkeys: set[str] = set()
    providers_seen = 0

    for p in prov_entries:
        if not isinstance(p, dict):
            continue
        providers_seen += 1
        pk = p.get("pub_key") or p.get("pubkey") or p.get("pubKey")
        if not pk or pk not in active_provider_pks or pk in seen_pubkeys:
            continue

        status_val = p.get("status")
        status_str = str(status_val).strip().lower() if status_val is not None else ""
        if status_str != "online" and status_val not in (1, True, "1", "ONLINE", "online"):
            continue

        mu = p.get("metadata_uri") or p.get("metadataUri")
        if not mu or not _is_external(mu):
            continue

        meta_entry = meta_cache.get(mu)
        meta_ok = bool(meta_entry)
        meta_flag = bool(p.get("metadata_uri_active")) or (_is_localhost_uri(mu) and ALLOW_LOCALHOST_SENTINEL_URIS)
        if not meta_ok or not meta_flag:
            continue

        entry = dict(p)
        # Preserve the raw provider record under a dedicated key for downstream consumers/compat
        entry["provider"] = p
        entry["provider_pubkey"] = pk
        entry["metadata_uri_active"] = bool(meta_flag and meta_ok)
        entry["metadata"] = meta_entry.get("data")
        meta_val = entry["metadata"]
        if isinstance(meta_val, dict):
            cfg = meta_val.get("config") if isinstance(meta_val.get("config"), dict) else {}
            moniker_val = cfg.get("moniker") or meta_val.get("moniker")
            if moniker_val:
                entry["provider_moniker"] = moniker_val
        if not entry.get("provider_moniker"):
            entry["provider_moniker"] = pk

        providers.append(entry)
        seen_pubkeys.add(pk)

    return {
        "fetched_at": timestamp(),
        "source": "active_services",
        "providers": providers,
        "metadata_uri_sources": {
            "allow_localhost": ALLOW_LOCALHOST_SENTINEL_URIS,
            "node": ARKEOD_NODE,
        },
        "debug_counts": {
            "active_services": len(active_services),
            "providers_seen": providers_seen,
            "providers_kept": len(providers),
        },
    }


def build_active_service_types(active_services_payload: Dict[str, Any], service_types_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Derive active_service_types.json with unique service ids and counts, enriched with service type metadata."""
    active_services = []
    if isinstance(active_services_payload, dict):
        active_services = active_services_payload.get("active_services") or []
    if not isinstance(active_services, list):
        active_services = []

    service_types_list: List[Dict[str, Any]] = []
    st_data = service_types_payload.get("data") if isinstance(service_types_payload, dict) else {}
    if isinstance(st_data, list):
        service_types_list = st_data
    elif isinstance(st_data, dict):
        service_types_list = (
            st_data.get("services")
            or st_data.get("service")
            or st_data.get("result")
            or st_data.get("data")
            or st_data.get("entries")
            or []
        )
    if not isinstance(service_types_list, list):
        service_types_list = []

    st_lookup: Dict[str, Dict[str, Any]] = {}
    for st in service_types_list:
        if not isinstance(st, dict):
            continue
        sid = st.get("service_id") or st.get("id") or st.get("serviceID") or st.get("service")
        if sid is None:
            continue
        st_lookup[str(sid)] = st

    counts: Dict[str, int] = {}
    for svc in active_services:
        if not isinstance(svc, dict):
            continue
        sid = svc.get("service_id") or svc.get("id") or svc.get("service")
        if sid is None:
            continue
        key = str(sid)
        counts[key] = counts.get(key, 0) + 1

    entries = []
    for sid, cnt in counts.items():
        entries.append(
            {
                "service_id": sid,
                "count": cnt,
                "service_type": st_lookup.get(sid),
            }
        )

    def _sort_key(entry: Dict[str, Any]):
        st = entry.get("service_type") or {}
        desc = st.get("description") or st.get("desc") or ""
        name = st.get("name") or st.get("service") or ""
        return (str(desc).lower(), str(name).lower(), str(entry.get("service_id")))

    entries.sort(key=_sort_key)

    return {
        "fetched_at": timestamp(),
        "source": "active_services",
        "active_service_types": entries,
    }


def build_subscribers_from_contracts(contracts_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Derive subscribers.json from provider-contracts cache (unique subscriber addresses)."""
    contracts_list = []
    data = contracts_payload.get("data") if isinstance(contracts_payload, dict) else {}
    if isinstance(data, dict):
        contracts_list = data.get("contracts") or data.get("contract") or []
    if not isinstance(contracts_list, list):
        contracts_list = []

    subs: dict[str, dict[str, Any]] = {}
    for c in contracts_list:
        if not isinstance(c, dict):
            continue
        addr = c.get("client")
        if not addr:
            continue
        entry = subs.setdefault(addr, {"subscriber": addr, "contracts": 0, "services": set()})
        entry["contracts"] += 1
        svc = c.get("service") or c.get("service_id") or c.get("serviceID")
        if svc is not None:
            entry["services"].add(str(svc))

    subscribers: list[dict[str, Any]] = []
    for s in subs.values():
        subscribers.append(
            {
                "subscriber": s["subscriber"],
                "contracts": s["contracts"],
                "services": sorted(s["services"]),
            }
        )

    return {
        "fetched_at": timestamp(),
        "source": "provider-contracts",
        "subscribers": subscribers,
    }


def write_cache(name: str, payload: Dict[str, Any]) -> None:
    path = os.path.join(CACHE_DIR, f"{name}.json")
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
        os.replace(tmp_path, path)
        print(f"[cache] wrote {name} -> {path} (exit={payload.get('exit_code')})", flush=True)
    except OSError as e:
        print(f"[cache] failed to write {name}: {e}", flush=True)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def fetch_once(commands: Dict[str, List[str]] | None = None, record_status: bool = False) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    _refresh_runtime_settings()
    commands = commands or build_commands()
    start_ts = timestamp()
    print(f"[cache] sync started at {start_ts}", flush=True)
    if record_status:
        mark_sync_start(start_ts)
    ok = True
    error_msg = None
    try:
        metadata_cache: dict[str, dict[str, Any]] | None = None
        for name, cmd in commands.items():
            code, out = run_list(cmd)
            payload = normalize_result(name, code, out, cmd)
            if name == "service-types" and payload.get("exit_code") == 0:
                payload = merge_service_types_with_resources(payload)
            if code != 0:
                ok = False
                error_msg = f"{name} exit={code}"
            if name == "service-types" and payload.get("exit_code") == 0:
                # If the output was plaintext, parse into structured services list
                if isinstance(payload.get("data"), str):
                    parsed = _parse_service_types_text(payload.get("data"))
                    if parsed:
                        payload["data"] = parsed
                payload = merge_service_types_with_resources(payload)
            if name == "provider-services" and payload.get("exit_code") == 0:
                metadata_cache = _update_metadata_cache_from_providers(payload)
                try:
                    active_uris = set(metadata_cache.keys()) if metadata_cache else set()
                    data_block = payload.get("data")
                    prov_entries = data_block.get("providers") or data_block.get("provider") if isinstance(data_block, dict) else []
                    if isinstance(prov_entries, list):
                        for p in prov_entries:
                            if not isinstance(p, dict):
                                continue
                            mu = p.get("metadata_uri") or p.get("metadataUri")
                            if mu and mu in active_uris:
                                p["metadata_uri_active"] = True
                            services_field = []
                            if isinstance(p.get("services"), list):
                                services_field = p["services"]
                            elif isinstance(p.get("service"), list):
                                services_field = p["service"]
                            for s in services_field:
                                if not isinstance(s, dict):
                                    continue
                                mu_svc = s.get("metadata_uri") or s.get("metadataUri")
                                if mu_svc and mu_svc in active_uris:
                                    s["metadata_uri_active"] = True
                except Exception:
                    pass
            write_cache(name, payload)
            results[name] = payload

        if metadata_cache is None:
            try:
                metadata_cache = _load_metadata_cache()
            except Exception:
                metadata_cache = {}
        if metadata_cache is not None:
            results["metadata"] = {"metadata": metadata_cache, "exit_code": 0}

        active_services_payload = None
        if "provider-services" in results and results["provider-services"].get("exit_code") == 0:
            active_services_payload = build_active_services(results["provider-services"], metadata_cache or {})
            write_cache("active_services", active_services_payload)
            results["active_services"] = active_services_payload

        if active_services_payload is not None:
            providers_payload = build_active_providers_from_active_services(
                active_services_payload, results["provider-services"], metadata_cache or {}
            )
            write_cache("active_providers", providers_payload)
            results["active_providers"] = providers_payload
            if "service-types" in results and results["service-types"].get("exit_code") == 0:
                ast_payload = build_active_service_types(active_services_payload, results["service-types"])
                write_cache("active_service_types", ast_payload)
                results["active_service_types"] = ast_payload

        if "provider-contracts" in results and results["provider-contracts"].get("exit_code") == 0:
            subscribers_payload = build_subscribers_from_contracts(results["provider-contracts"])
            write_cache("subscribers", subscribers_payload)
            results["subscribers"] = subscribers_payload
    except Exception as e:
        ok = False
        error_msg = str(e)
        raise
    finally:
        if record_status:
            mark_sync_end(ok=ok, error=error_msg)
        end_ts = timestamp()
        status = "success" if ok else f"failed ({error_msg})"
        print(f"[cache] sync completed at {end_ts} [{status}]", flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Arkeo cache fetcher")
    parser.add_argument("--once", action="store_true", help="Run a single fetch cycle then exit")
    args = parser.parse_args()

    ensure_cache_dir()
    commands = build_commands()
    interval_raw = CACHE_FETCH_INTERVAL
    if interval_raw <= 0:
        print(
            f"[cache] background fetch loop disabled (CACHE_FETCH_INTERVAL={CACHE_FETCH_INTERVAL}); cache dir={CACHE_DIR}; node={ARKEOD_NODE}",
            flush=True,
        )
        while True:
            time.sleep(86400)

    interval = max(60, interval_raw) if interval_raw > 0 else 60
    print(
        f"[cache] starting fetch loop every {interval}s; cache dir={CACHE_DIR}; node={ARKEOD_NODE}",
        flush=True,
    )
    if args.once:
        fetch_once(commands, record_status=True)
        return
    while True:
        fetch_once(commands, record_status=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
