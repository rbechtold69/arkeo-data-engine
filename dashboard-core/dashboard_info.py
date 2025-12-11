#!/usr/bin/env python3
"""Lightweight dashboard info writer for dashboard-core.

Fetches the current block height on a short interval and writes dashboard_info.json
so the UI/API can read fresh height data without waiting for the full cache sync.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Tuple

ARKEOD_HOME = os.path.expanduser(os.getenv("ARKEOD_HOME", "/root/.arkeo"))
ARKEOD_NODE = (
    os.getenv("ARKEOD_NODE")
    or "tcp://127.0.0.1:26657"
)
CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")
DASHBOARD_INFO_FILE = os.getenv("DASHBOARD_INFO_FILE", os.path.join(CACHE_DIR, "dashboard_info.json"))
BLOCK_TIME_SECONDS = os.getenv("BLOCK_TIME_SECONDS", "5.79954919")
try:
    BLOCK_HEIGHT_INTERVAL = int(os.getenv("BLOCK_HEIGHT_INTERVAL", "60"))
except ValueError:
    BLOCK_HEIGHT_INTERVAL = 60

NODE_ARGS = ["--node", ARKEOD_NODE] if ARKEOD_NODE else []


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_cache_dir() -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except OSError:
        pass


def run_list(cmd: list[str]) -> Tuple[int, str]:
    """Run a command without a shell and return (exit_code, output)."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return 0, out.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output.decode("utf-8")


def latest_block_height() -> tuple[int | None, str | None]:
    cmd = ["arkeod", "--home", ARKEOD_HOME, "status", "--output", "json"]
    if NODE_ARGS:
        cmd[1:1] = NODE_ARGS
    code, out = run_list(cmd)
    if code != 0:
        return None, f"arkeod status failed: {out}"
    try:
        payload = json.loads(out)
        sync_info = payload.get("SyncInfo") or payload.get("sync_info") or {}
        height_raw = sync_info.get("latest_block_height") or sync_info.get("latestBlockHeight")
        if height_raw is None:
            return None, "missing latest_block_height"
        try:
            return int(height_raw), None
        except (TypeError, ValueError):
            return None, f"invalid height: {height_raw}"
    except json.JSONDecodeError as e:
        return None, f"parse error: {e}"


def write_info(height: int | None, error: str | None) -> None:
    ensure_cache_dir()
    payload = {
        "updated_at": timestamp(),
        "block_height": height,
        "height_error": error,
        "block_time_seconds": BLOCK_TIME_SECONDS,
        "arkeod_node": ARKEOD_NODE,
    }
    path = DASHBOARD_INFO_FILE
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, indent=2)
        os.replace(tmp_path, path)
        print(
            f"[dashboard-info] wrote {path} (height={height}, error={error}, block_time={BLOCK_TIME_SECONDS}, updated_at={payload['updated_at']})",
            flush=True,
        )
    except OSError as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        print(f"[dashboard-info] failed to write {path}: {e}", flush=True)


def main() -> None:
    ensure_cache_dir()
    interval = max(10, BLOCK_HEIGHT_INTERVAL)
    print(
        f"[dashboard-info] starting loop every {interval}s; node={ARKEOD_NODE}; file={DASHBOARD_INFO_FILE}",
        flush=True,
    )
    while True:
        h, err = latest_block_height()
        write_info(h, err)
        time.sleep(interval)


if __name__ == "__main__":
    main()
