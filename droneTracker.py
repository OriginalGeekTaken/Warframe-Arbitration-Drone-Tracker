#!/usr/bin/env python3
import os
import sys
import json
import time
import re
from datetime import datetime
from typing import Optional, List

DEBUG = False
EE_LOG_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Warframe", "EE.log")
LOG_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "droneTracker.txt")
MISSION_START_MARKERS = ["GameRulesImpl::StartRound()", "OnStateStarted, mission type"]
MISSION_END_MARKER = "Game [Info]: CommitInventoryChangesToDB"
LOGIN_REGEX = re.compile(r"Sys \[Info\]: Logged in .*\(([0-9a-fA-F]+)\)")
DRONE_TYPE = "/Lotus/Types/Enemies/Corpus/Drones/AIWeek/CorpusEliteShieldDroneAvatar"
SPAWN_LINE_SUBSTRING = "AI [Info]: OnAgentCreated /Npc/CorpusEliteShieldDroneAgent"
SERVER_SYNC_WAIT_SECONDS = 5 * 60
MAX_SYNC_QUERIES = 2  # initial + one retry
MIN_SPAWNS_TO_QUERY = 15  # proceed if spawned > 15
MIN_MISSION_SECONDS_FALLBACK = 6 * 60  # client failsafe if duration >= 6 minutes

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

def format_duration(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h}h {m}m {sec}s"
    return f"{m}m {sec}s"

def detect_profile_id_from_eelog(log_path: str) -> Optional[str]:
    if not os.path.exists(log_path):
        return None
    found: Optional[str] = None
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = LOGIN_REGEX.search(line)
            if m:
                found = m.group(1)
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

    raise RuntimeError("Drone kill entry not found in profile JSON")

def print_backlog_mission_summaries(log_path: str) -> None:
    if not os.path.exists(log_path):
        return

    mission_active = False
    start_ts: Optional[float] = None
    spawn_count = 0
    shown_index = 0

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if any(m in line for m in MISSION_START_MARKERS):
                ts = parse_leading_float_timestamp(line)
                if ts is not None:
                    mission_active = True
                    start_ts = ts
                    spawn_count = 0
                continue

            if mission_active and SPAWN_LINE_SUBSTRING in line:
                spawn_count += 1
                continue

            if mission_active and MISSION_END_MARKER in line:
                end_ts = parse_leading_float_timestamp(line)
                if end_ts and start_ts and spawn_count > MIN_SPAWNS_TO_QUERY:
                    shown_index += 1
                    print(
                        f"Mission {shown_index}: {fmt_int(spawn_count)} drone spawns in {format_duration(end_ts - start_ts)}",
                        flush=True
                    )

                mission_active = False
                start_ts = None
                spawn_count = 0

class EeLogTailer:
    def __init__(self, path: str):
        self.path = path
        self.marker = 0

    def prime_to_eof(self):
        self.marker = safe_stat_size(self.path)

    def read_new_lines_with_offsets(self):
        size = safe_stat_size(self.path)
        if size < self.marker:
            self.marker = 0

        out = []
        with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(self.marker)
            while True:
                start = f.tell()
                line = f.readline()
                if not line:
                    break
                out.append((line.rstrip("\n"), start))
            end_offset = f.tell()

        self.marker = end_offset
        return out, end_offset

def count_drone_spawns_between_offsets(file_path: str, start_offset: int, end_offset: int) -> int:
    count = 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(start_offset)
        while f.tell() < end_offset:
            line = f.readline()
            if not line:
                break
            if SPAWN_LINE_SUBSTRING in line:
                count += 1
    return count

def find_last_start_before_offset(file_path: str, end_file_offset: int, start_markers: List[str]):
    last_ts = None
    last_offset = None
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        while f.tell() < end_file_offset:
            off = f.tell()
            line = f.readline()
            if not line:
                break
            if any(m in line for m in start_markers):
                last_offset = off
                last_ts = parse_leading_float_timestamp(line)
    return last_ts, last_offset

def main():
    print_backlog_mission_summaries(EE_LOG_PATH)

    profile_id = detect_profile_id_from_eelog(EE_LOG_PATH)
    if not profile_id:
        print("Could not detect profile_id", file=sys.stderr)
        sys.exit(1)
    print(f"Profile ID: {profile_id}")

    last_total = fetch_drone_kill_total(profile_id)
    print(f"Drone KC: {fmt_int(last_total)}")

    tailer = EeLogTailer(EE_LOG_PATH)
    tailer.prime_to_eof()
    previous_file_size = safe_stat_size(EE_LOG_PATH)
    processed_end_ts = set()
    print("Watching EE.log...")

    while True:
        current_file_size = safe_stat_size(EE_LOG_PATH)
        if current_file_size != previous_file_size:
            previous_file_size = current_file_size
            items, _ = tailer.read_new_lines_with_offsets()

            for end_line, end_line_offset in items:
                if MISSION_END_MARKER not in end_line:
                    continue

                end_ts = parse_leading_float_timestamp(end_line)
                if end_ts is None or end_ts in processed_end_ts:
                    continue
                processed_end_ts.add(end_ts)

                start_ts, start_offset = find_last_start_before_offset(
                    EE_LOG_PATH, end_line_offset, MISSION_START_MARKERS
                )
                if start_offset is None or start_ts is None:
                    continue

                spawned = count_drone_spawns_between_offsets(
                    EE_LOG_PATH, start_offset, end_line_offset
                )

                duration_s = end_ts - start_ts

                # 1) Host: spawned > 15
                # 2) Client failsafe: spawned <= 15 AND duration >= 6 minutes
                proceed = False
                spawned_is_known = False

                if spawned > MIN_SPAWNS_TO_QUERY:
                    proceed = True
                    spawned_is_known = True
                elif duration_s >= MIN_MISSION_SECONDS_FALLBACK:
                    proceed = True
                    spawned_is_known = False

                if not proceed:
                    if DEBUG:
                        print(
                            f"Skipping mission (spawned={spawned}, duration={format_duration(duration_s)}).",
                            flush=True
                        )
                    continue

                if spawned_is_known:
                    print(f"Drone spawns for mission: {fmt_int(spawned)}.")
                else:
                    print(f"Drone spawns for mission: unknown (client). Duration: {format_duration(duration_s)}.")

                print("Waiting 5 minutes for Warframe api to sync player drone KC...")

                new_total = last_total
                for attempt in range(1, MAX_SYNC_QUERIES + 1):
                    time.sleep(SERVER_SYNC_WAIT_SECONDS)
                    try:
                        new_total = fetch_drone_kill_total(profile_id)
                    except Exception as e:
                        print(f"(WARNING) profile query failed: {e}", file=sys.stderr)
                        new_total = last_total

                    if new_total > last_total:
                        break

                    if attempt < MAX_SYNC_QUERIES:
                        print("No change, waiting 5 more minutes...")
                    else:
                        print("No change after 10 minutes. Skipping this mission update.")
                        new_total = last_total

                if new_total > last_total:
                    delta = new_total - last_total
                    last_total = new_total

                    if spawned_is_known:
                        emit(f"You killed {fmt_int(delta)} out of {fmt_int(spawned)} drones that mission.")
                    else:
                        emit(f"You killed {fmt_int(delta)} drones that mission.")

                    emit(f"Your drone KC is now {fmt_int(new_total)}.")

        time.sleep(0.25)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
