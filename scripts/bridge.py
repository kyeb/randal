#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyserial", "websockets"]
# ///
"""IMU WebSocket server — reads robot JSONL (serial or TCP) and broadcasts to clients.

Usage:
    ./scripts/bridge.py [PORT]            # serial (default /dev/cu.usbserial-0001)
    ./scripts/bridge.py tcp:<ip>[:port]   # WiFi TCP (default port 3333)

Broadcasts IMU data via WebSocket on ws://localhost:8080/ws.
Data is saved to data/<timestamp>.jsonl for later analysis.

Run the dashboard frontend separately:
    cd dashboard && npm run dev    # http://localhost:3000
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import serial
import websockets
from websockets.asyncio.server import serve

PORT = "/dev/cu.usbserial-0001"
BAUD = 921600
WEB_PORT = 8080

clients: set = set()
log_file = None
capture_file = None

# Queue for commands from dashboard → serial (avoids thread-safety issues)
cmd_queue: asyncio.Queue = asyncio.Queue()


async def ws_handler(websocket):
    global capture_file
    clients.add(websocket)
    try:
        async for message in websocket:
            msg = message.strip()
            if not msg:
                continue
            if msg == "SHUTDOWN":
                print("[shutdown] requested")
                os._exit(0)
            elif msg == "CAPTURE_START":
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cap_path = Path(__file__).parent.parent / "data" / f"capture_{ts}.jsonl"
                capture_file = open(cap_path, "w")
                print(f"[capture] started → {cap_path}")
                await websocket.send(json.dumps({"capture": "started", "file": str(cap_path.name)}))
            elif msg == "CAPTURE_STOP":
                if capture_file:
                    capture_file.close()
                    print(f"[capture] stopped")
                    capture_file = None
                await websocket.send(json.dumps({"capture": "stopped"}))
            else:
                print(f"[cmd] {msg}")
                await cmd_queue.put(msg)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)


async def broadcast(data: str):
    if clients:
        websockets.broadcast(clients, data)


def open_log():
    # Open only after a successful connection — opening before caused a new
    # empty file per 2s reconnect retry (543k zero-byte files over 3 months)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(__file__).parent.parent / "data" / f"{timestamp}.jsonl"
    f = open(log_path, "a")
    print(f"Logging to {log_path}")
    return f


async def serial_reader(port: str, baud: int):
    global log_file

    ser = serial.Serial(port, baud, timeout=0.01)
    log_file = open_log()
    print("Resetting ESP32...", end=" ", flush=True)
    ser.dtr = False
    ser.rts = True
    await asyncio.sleep(0.1)
    ser.rts = False
    await asyncio.sleep(3)
    ser.read(ser.in_waiting or 4096)
    print("ready!")
    await broadcast(json.dumps({"bridge": "connected"}))

    print(f"WebSocket: ws://localhost:{WEB_PORT}/ws")
    print(f"Dashboard: cd dashboard && npm run dev")

    loop = asyncio.get_event_loop()
    while True:
        # Drain command queue → serial (all in this single thread, no races)
        while not cmd_queue.empty():
            cmd = cmd_queue.get_nowait()
            ser.write((cmd + "\n").encode())

        line = await loop.run_in_executor(None, ser.readline)
        if not line:
            continue

        line = line.decode("utf-8", errors="replace").strip()
        if not line.startswith("{"):
            if line:
                print(f"[log] {line}")
            continue

        try:
            json.loads(line)
        except json.JSONDecodeError:
            continue

        log_file.write(line + "\n")
        log_file.flush()

        if capture_file:
            capture_file.write(line + "\n")
            capture_file.flush()

        await broadcast(line)


TCP_DEFAULT_PORT = 3333


async def tcp_reader(host: str, tcp_port: int):
    global log_file

    reader, writer = await asyncio.open_connection(host, tcp_port)
    log_file = open_log()
    print(f"Connected to robot at {host}:{tcp_port}")
    await broadcast(json.dumps({"bridge": "connected"}))
    print(f"WebSocket: ws://localhost:{WEB_PORT}/ws")

    try:
        while True:
            while not cmd_queue.empty():
                cmd = cmd_queue.get_nowait()
                writer.write((cmd + "\n").encode())
                await writer.drain()

            try:
                line = await asyncio.wait_for(reader.readline(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            if not line:
                raise ConnectionError("robot closed connection")

            line = line.decode("utf-8", errors="replace").strip()
            if not line.startswith("{"):
                if line:
                    print(f"[log] {line}")
                continue

            try:
                json.loads(line)
            except json.JSONDecodeError:
                continue

            log_file.write(line + "\n")
            log_file.flush()

            if capture_file:
                capture_file.write(line + "\n")
                capture_file.flush()

            await broadcast(line)
    finally:
        writer.close()


async def main(port=PORT):
    server = await serve(ws_handler, "0.0.0.0", WEB_PORT)
    print(f"WebSocket server on :{WEB_PORT}")

    tcp_target = None
    if port.startswith("tcp:"):
        rest = port[4:]
        host, _, p = rest.partition(":")
        tcp_target = (host, int(p) if p else TCP_DEFAULT_PORT)

    while True:
        try:
            if tcp_target:
                await tcp_reader(*tcp_target)
            else:
                await serial_reader(port, BAUD)
        except (serial.SerialException, ConnectionError, OSError) as e:
            print(f"\nLink error: {e}")
            await broadcast(json.dumps({"bridge": "disconnected"}))
            print("Reconnecting in 2s...")
            await asyncio.sleep(2)
        except KeyboardInterrupt:
            break

    if log_file:
        log_file.close()
    server.close()
    print("\nDone.")


def is_running():
    async def probe():
        try:
            async with websockets.connect(f"ws://localhost:{WEB_PORT}", open_timeout=0.5):
                return True
        except Exception:
            return False
    return asyncio.run(probe())


async def send_shutdown():
    try:
        async with websockets.connect(f"ws://localhost:{WEB_PORT}") as ws:
            await ws.send("SHUTDOWN")
    except Exception:
        pass


def stop():
    if not is_running():
        print("not running")
        return
    asyncio.run(send_shutdown())
    for _ in range(20):
        if not is_running():
            print("stopped")
            return
        time.sleep(0.1)
    print("warning: still running after 2s")


def start(port=PORT):
    if is_running():
        print(f"already running on :{WEB_PORT}")
        sys.exit(1)
    try:
        asyncio.run(main(port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd == "status":
        print("running" if is_running() else "not running")
    elif cmd == "stop":
        stop()
    elif cmd == "restart":
        stop()
        log = Path(__file__).parent.parent / "data" / "bridge.log"
        subprocess.Popen(
            [__file__],
            stdout=open(log, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        for _ in range(30):
            if is_running():
                print(f"started (log: {log})")
                break
            time.sleep(0.1)
        else:
            print("warning: did not come up within 3s")
    elif cmd:
        start(cmd)  # treat positional arg as serial port path
    else:
        start()
