# Warframe Arbitration Drone Tracker

This script watches your **Warframe EE.log** and tracks **Arbitration Shield Drone** activity per mission.

It automatically:
- Detects when a mission ends
- Counts how many Arbitration drones spawned during that mission **(host only)**
- Uses a client failsafe when spawns are not visible in EE.log
- Waits for Warframe servers to update your stats
- Reports how many drones **you personally killed**
- Logs results to a file

---

## Safety / Rate-Limit Protection (Important)

This script queries this public endpoint:

```
http://content.warframe.com/dynamic/getProfileViewingData.php?playerId=<your_profile_id>
```

To reduce the chance of a user accidentally spamming the endpoint by repeatedly restarting the script:

- Whenever the script fetches the kill count, it logs an `API_FETCH` line to `droneTracker.txt` with a timestamp.
- Whenever the script fetches a **baseline** kill count, it also writes a cache line:
  - `BASELINE_CACHE kill_total=<number>`
- If the script starts and it finds a cached baseline from **within the last 5 minutes**, it uses that value instead of making another baseline API call.

This is designed to help prevent users from getting rate-limited if they restart the script repeatedly.

---

## Safe To Use?

This application is not endorsed by Digital Extremes and is fan-made. It reads your `EE.log` file (which is user-accessible). It does not interact with the game client or memory. However, it's important to use your own judgement and use it at your own risk. 

According to section 2.f of the Warframe EULA, you agree that you will not under any circumstance use unauthorized third‑party tools designed to modify the game experience. You should read the EULA and the code yourself and decide whether you want to use this tool.

Digital Extremes PSA about third‑party software:
https://forums.warframe.com/topic/1320042-third-party-software-and-you/

---

## What It Tracks

Enemy type tracked:

`Arbitration Shield Drone`  
Internal name:
```
/Lotus/Types/Enemies/Corpus/Drones/AIWeek/CorpusEliteShieldDroneAvatar
```

**Host-side spawn detection** (not always visible to clients) is based on lines like:
```
AI [Info]: OnAgentCreated /Npc/CorpusEliteShieldDroneAgent
```

---

## Host vs Client Behavior

Warframe is peer-to-peer. The host often logs drone spawn lines, but a client might not.

This script uses:

1) **Host path**: If it detects more than 15 drone spawns in EE.log, it treats that as a real Arbitration mission and proceeds.

2) **Client failsafe**: If spawn lines are missing or too low, it will still proceed **if the mission lasted at least 6 minutes**.

---

## Requirements

- Windows PC
- Warframe
- Python **3.10+**

No extra Python packages are required. (`requests` is optional; the script falls back to `urllib` if you don't have it.)

Download Python:  
https://www.python.org/downloads/

During installation, check:

**✔ Add Python to PATH**

---

## How To Run

1. Save the script in a folder
2. Double-click the script  
   **OR**
   Run from Command Prompt:

```
python drone_tracker.py
```

---

## What Happens On Startup

When launched, the script will:

1. Scan your existing `EE.log`
2. Print summaries of past missions that had **more than 15 drone spawns** (host-visible only)
3. Detect your Warframe **Profile ID**
4. Load your baseline drone kill count:
   - Uses a cached value from `droneTracker.txt` if it was fetched in the last 5 minutes
   - Otherwise fetches from the Warframe endpoint and caches it
5. Begin watching for new missions

---

## During Gameplay

When a mission ends, the script:

1. Finds mission start and end in `EE.log`
2. Counts drone spawns during that mission
3. Proceeds when either:
   - **Drone spawns > 15** (host), or
   - **Mission duration >= 6 minutes** (client failsafe)
4. Waits 5 minutes, then checks your kill count. If no change, it waits 5 more minutes (max 2 checks).

Example output:

```
Drone spawns for mission: 1,842. Duration: 47m 34s.
Waiting 5 minutes for Warframe api to sync player drone KC...
You killed 1,203 out of 1,842 drones that mission.
Your drone KC is now 825,087.
```

Client output example:

```
Drone spawns for mission: unknown (client). Duration: 47m 34s.
Waiting 5 minutes for Warframe api to sync player drone KC...
You killed 1,203 drones that mission.
Your drone KC is now 825,087.
```

---

## Log File

Mission results and API fetch events are saved to:

```
droneTracker.txt
```

Located in the same folder as the script.

---

## Default EE.log Location

```
%localappdata%\Warframe\EE.log
```

---

## Notes

- The cache reduces baseline calls, but mission-completion checks can still call the API.
- The script caps mission sync checks to **2 queries** (5 minutes + 5 minutes) and then skips the mission if no change is observed.
