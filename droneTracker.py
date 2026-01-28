#!/usr/bin/env python3
import os
import sys
import json
import time
import re
from datetime import datetime
from typing import Optional

DEBUG = False  # True = print mission duration info even when < 6 minutes
EE_LOG_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Warframe", "EE.log")
LOG_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "droneTracker.txt")
MISSION_START_MARKERS = ["GameRulesImpl::StartRound()", "OnStateStarted, mission type",]
MISSION_END_MARKER = "Game [Info]: CommitInventoryChangesToDB"
LOGIN_REGEX = re.compile(r"Sys \[Info\]: Logged in .*\(([0-9a-fA-F]+)\)")
DRONE_TYPE = "/Lotus/Types/Enemies/Corpus/Drones/AIWeek/CorpusEliteShieldDroneAvatar"
MIN_MISSION_SECONDS_TO_QUERY = 6 * 60  # 6 minutes
SERVER_SYNC_WAIT_SECONDS = 5 * 60      # 5 minutes

def fmt_int(n: int) -> str:
    return f"{n:,}"

def emit(message: str) -> None:
    print(message, flush=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_OUTPUT_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception as e:
        print(f"(warning) failed to write {LOG_OUTPUT_PATH}: {e}", flush=True)

def parse_leading_float_timestamp(line: str) -> Optional[float]:
    try:
        return float(line.split(" ", 1)[0])
    except Exception:
        return None

def safe_stat_size(path: str) -> int:
    try:
        return os.stat(path).st_size
    except FileNotFoundError:
        return 0

def detect_profile_id_from_eelog(log_path: str) -> Optional[str]:
    if not os.path.exists(log_path):
        return None
    found: Optional[str] = None
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = LOGIN_REGEX.search(line)
            if m:
                found = m.group(1)  # keep most recent
    return found

def http_get_text(url: str, timeout_s: int = 12) -> str:
    try:
        import requests  # type: ignore
        r = requests.get(url, timeout=timeout_s)
        r.raise_for_status()
        return r.text
    except Exception:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            return resp.read().decode("utf-8", errors="replace")

def fetch_drone_kill_total(profile_id: str) -> int:
    url = f"http://content.warframe.com/dynamic/getProfileViewingData.php?playerId={profile_id}"
    text = http_get_text(url)
    data = json.loads(text)

    def walk(obj):
        if isinstance(obj, dict):
            yield obj
            for v in obj.values():
                yield from walk(v)
        elif isinstance(obj, list):
            for it in obj:
                yield from walk(it)

    for node in walk(data):
        if node.get("type") == DRONE_TYPE:
            return int(node.get("kills"))

    raise RuntimeError(f"Could not find drone type entry in profile JSON: {DRONE_TYPE}")

def find_last_start_timestamp_before_offset(
    file_path: str,
    end_file_offset: int,
    start_markers: list[str],
    max_bytes_to_scan: int = 32 * 1024 * 1024,  # last 32MB
    chunk_size: int = 256 * 1024
) -> Optional[float]:
    try:
        file_size = os.stat(file_path).st_size
    except FileNotFoundError:
        return None

    end_pos = min(end_file_offset, file_size)
    start_pos_limit = max(0, end_pos - max_bytes_to_scan)

    with open(file_path, "rb") as f:
        pos = end_pos
        carry = b""
        while pos > start_pos_limit:
            read_start = max(start_pos_limit, pos - chunk_size)
            read_len = pos - read_start
            f.seek(read_start)
            chunk = f.read(read_len)
            pos = read_start

            data = chunk + carry
            text = data.decode("utf-8", errors="ignore")

            best_idx = -1
            for m in start_markers:
                idx = text.rfind(m)
                if idx > best_idx:
                    best_idx = idx

            if best_idx != -1:
                line_start = text.rfind("\n", 0, best_idx)
                line_start = 0 if line_start == -1 else line_start + 1
                line_end = text.find("\n", best_idx)
                line_end = len(text) if line_end == -1 else line_end
                line = text[line_start:line_end]
                return parse_leading_float_timestamp(line)

            carry = data[-8192:] if len(data) > 8192 else data

    return None

class EeLogTailer:
    def __init__(self, path: str):
        self.path = path
        self.marker = 0

    def prime_to_eof(self) -> None:
        self.marker = safe_stat_size(self.path)

    def read_new_lines(self):
        size = safe_stat_size(self.path)
        if size == 0:
            self.marker = 0
            return [], 0

        if size < self.marker:
            self.marker = 0

        lines = []
        with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(self.marker)
            for line in f:
                lines.append(line.rstrip("\n"))
            end_offset = f.tell()

        self.marker = end_offset
        return lines, end_offset

def main():
    profile_id = detect_profile_id_from_eelog(EE_LOG_PATH)
    if not profile_id:
        print("Could not detect profile_id from EE.log (no 'Logged in ... (id)' line found).", file=sys.stderr)
        sys.exit(1)

    print(f"Detected profile_id: {profile_id}")

    try:
        last_total = fetch_drone_kill_total(profile_id)
    except Exception as e:
        print(f"Failed initial profile query: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Baseline: drone kills = {fmt_int(last_total)}")

    tailer = EeLogTailer(EE_LOG_PATH)
    tailer.prime_to_eof()

    previous_file_size = safe_stat_size(EE_LOG_PATH)
    processed_end_ts: set[float] = set()

    print("Watching EE.log (size-change driven). Press Ctrl+C to stop.")

    while True:
        current_file_size = safe_stat_size(EE_LOG_PATH)
        if current_file_size != previous_file_size:
            previous_file_size = current_file_size

            lines, end_offset = tailer.read_new_lines()
            if not lines:
                time.sleep(0.25)
                continue

            for ln in lines:
                if MISSION_END_MARKER not in ln:
                    continue

                end_ts = parse_leading_float_timestamp(ln)
                if end_ts is None or end_ts in processed_end_ts:
                    continue

                processed_end_ts.add(end_ts)

                start_ts = find_last_start_timestamp_before_offset(
                    EE_LOG_PATH,
                    end_file_offset=end_offset,
                    start_markers=MISSION_START_MARKERS,
                )
                if start_ts is None:
                    if DEBUG:
                        print("Mission end detected, but couldn't find start marker.")
                    continue

                duration_s = end_ts - start_ts

                if duration_s < MIN_MISSION_SECONDS_TO_QUERY:
                    if DEBUG:
                        print(f"Mission end detected; duration {duration_s:.1f}s (< 6 min). Skipping profile query.")
                    continue

                # Mission was long enough — wait and poll profile until it changes
                emit("Waiting 5 minutes for Warframe api to sync kill counts...")

                while True:
                    time.sleep(SERVER_SYNC_WAIT_SECONDS)

                    try:
                        new_total = fetch_drone_kill_total(profile_id)
                    except Exception as e:
                        print(f"(warning) profile query failed: {e}", file=sys.stderr)
                        continue

                    if new_total == last_total:
                        emit("No change, waiting 5 more minutes...")
                        continue

                    delta = new_total - last_total
                    last_total = new_total

                    emit(f"You killed {fmt_int(delta)} drones during the previous mission. Your total is now {fmt_int(new_total)}.")
                    break

                break

        time.sleep(0.25)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
