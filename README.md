# Warframe Arbitration Drone Tracker

This script watches your **Warframe EE.log** and tracks **Arbitration Shield Drone** activity per mission.

It automatically:
- Detects when a mission ends
- Counts how many Arbitration drones spawned during that mission
- Waits for Warframe servers to update your stats
- Reports how many drones **you personally killed**
- Logs results to a file

---

## Safe To Use?

This script:
- Reads a log file
- Queries a public Warframe profile endpoint

This application is not endorsed by Digital Extremes and is fan-made. It reads your ee.log file (which is meant to be user-accessible). It does not interact with the game client or memory. However, it's important to use your own judgement and use it at your own risk. 

According to section 2.f of https://www.warframe.com/EULA, you agree that you will not under any circumstance "use... unauthorized third-party software, tools or content designed to modify the ...Game experience". By using any kind of macros, overlays, or any third-party tool (including this one), you are breaking this clause to my understanding. You should read the EULA yourself, read the code to see what it is doing and come to your own conclusion if you want to use this tool. Refer to this PSA from Digital Extremes about third-party software to get an idea of their stance: https://forums.warframe.com/topic/1320042-third-party-software-and-you/.

---

## What It Tracks

Enemy type tracked:

`Arbitration Shield Drone`  
Internal name:
```
/Lotus/Types/Enemies/Corpus/Drones/AIWeek/CorpusEliteShieldDroneAvatar
```

Spawn detection is based on log lines like:
```
AI [Info]: OnAgentCreated /Npc/CorpusEliteShieldDroneAgent
```

---

## Requirements

- Windows PC
- Warframe
- Python **3.10+**

No extra Python packages are required.

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
2. Print summaries of past missions that had **more than 15 drone spawns**
   Example:
   ```
   Mission 1: 1,240 drone spawns in 47m 36s
   Mission 2: 2,912 drone spawns in 2h 14m 11s
   ```
3. Detect your Warframe **Profile ID**
4. Fetch your current **total drone kills**
5. Begin watching for new missions

---

## During Gameplay

When a mission ends, the script:

1. Looks backward in the log to find when the mission started
2. Counts drone spawns during that mission
3. **If 15 or fewer drones spawned → mission is ignored**
4. If more than 15 spawned:

```
Drone spawns for mission: 1,842
Waiting 5 minutes for Warframe api to sync player drone KC...
```

After 5 minutes it checks your kill count.

If stats updated:
```
You killed 1,203 out of 1,842 drones that mission. 
Your drone KC is now 825,087.
```

If stats did not update yet:
```
No change, waiting 5 more minutes...
```

If still no update after 10 minutes total:
```
No change after 10 minutes. Skipping this mission update.
```

---

## Log File

Mission results are saved to:

```
droneTracker.txt
```

Located in the same folder as the script.

---

## Important Rules

✔ Script only queries content.warframe.com if **more than 15 drones spawned**  
✔ Script only reads the **PLAYER ACCESSIBLE** EE.log  
✔ It does **NOT** modify game files, or interact with the game client in any way  
✔ You can stop anytime with **Ctrl + C**

---

## Default EE.log Location

```
%localappdata%\Warframe\EE.log
```
