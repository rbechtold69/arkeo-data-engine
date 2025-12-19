#!/usr/bin/env python3
"""
Simple concurrency smoke test for the single-lane listener.

Run inside the container after startup:
    python3 scripts/lane_smoke_test.py --port 62001 --count 10 --concurrency 10

It fires JSON-RPC status requests at the listener and prints the HTTP code,
round-trip time, and the order in which responses return. This is aimed at
verifying that requests serialize through the lane without nonce collisions.
"""

import argparse
import json
import threading
import time
import http.client
from typing import List, Tuple


def send_request(host: str, port: int, path: str, payload: str, idx: int, results: List[Tuple[int, float, float, str]]):
    start = time.time()
    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        body = resp.read()
        status = resp.status
        conn.close()
    except Exception as e:
        status = 0
        body = str(e).encode()
    elapsed = time.time() - start
    try:
        body_preview = body.decode(errors="ignore")[:200]
    except Exception:
        body_preview = ""
    results.append((idx, elapsed, status, body_preview))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Listener host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=62001, help="Listener port (default: 62001)")
    parser.add_argument("--path", default="/", help="Request path (default: /)")
    parser.add_argument("--count", type=int, default=10, help="Total requests to fire")
    parser.add_argument("--concurrency", type=int, default=10, help="Thread concurrency")
    parser.add_argument(
        "--payload",
        default=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "status", "params": []}),
        help="JSON payload to POST",
    )
    args = parser.parse_args()

    threads: List[threading.Thread] = []
    results: List[Tuple[int, float, float, str]] = []

    sem = threading.Semaphore(args.concurrency)

    def worker(idx: int):
        with sem:
            send_request(args.host, args.port, args.path, args.payload, idx, results)

    print(f"[lane-smoke] host={args.host} port={args.port} count={args.count} concurrency={args.concurrency}")
    t0 = time.time()
    for i in range(args.count):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    total = time.time() - t0

    results.sort(key=lambda r: r[0])
    for idx, elapsed, status, body in results:
        print(f"req={idx:02d} status={status} elapsed={elapsed:.3f}s body_preview={body}")
    print(f"[lane-smoke] completed {len(results)} requests in {total:.3f}s")


if __name__ == "__main__":
    main()
