# Warframe Arbitration Drone Kill Tracker

This tool watches your **Warframe EE.log** while you play and reports how many **Arbitration Drones** you killed each mission.

It works by:
1. Detecting when a mission ends  
2. Making sure the mission lasted at least **6 minutes**  
3. Waiting **5 minutes** for Warframe servers to sync stats  
4. Checking your official profile kill count via the api
5. Printing and logging how many drones were added

---

## What It Tracks

Enemy type:
```
/Lotus/Types/Enemies/Corpus/Drones/AIWeek/CorpusEliteShieldDroneAvatar
```

That is the **Arbitration Shield Drone**.

---

## Requirements

You only need:

- **Windows**
- **Warframe**
- **Python 3.10 or newer**

No extra Python packages are required.

Download Python here:  
https://www.python.org/downloads/

During install, make sure to check:

**✔ Add Python to PATH**

---

## How To Use

1. Put the script file in any folder.
2. Double-click `drone_tracker.py`  
   **OR** run in Command Prompt:

   ```
   python drone_tracker.py
   ```

3. Play Warframe normally.

---

## What Happens Automatically

When the script starts:

- It reads your **EE.log**
- Detects your **profile ID**
- Gets your current total drone kills
- Waits for the next mission completion to check again

---

## During Gameplay

When you finish an Arbitration mission that lasted **6+ minutes**, the script will:

```
Waiting 5 minutes for Warframe servers to sync kill counts...
```

After 5 minutes:

If the servers updated:
```
You killed 1,445 drones during the previous mission. Your total is now 825,087.
```

If the servers have NOT updated yet:
```
No change, waiting 5 more minutes...
```

It will keep checking every 5 minutes until the kill count increases.

---

## Log File

All results are saved to:

```
droneTracker.txt
```

This file is created in the **same folder as the script**.

---

## Important Notes

- Missions under **6 minutes** are ignored.
- The script only reads **new lines** in EE.log after it starts.
- It does **not** modify any game files, or interact with the client in any way.
- You can stop the script anytime with:

```
Ctrl + C
```

---

## Troubleshooting

### Script says it can’t find profile ID
Make sure you:
- Logged into Warframe at least once before running the script
- Did not delete or move EE.log

Default EE.log location:
```
C:\Users\<YourName>\AppData\Local\Warframe\EE.log
```

---

## Safe To Use?

Yes.  
This tool only reads a **player accessible** log file and a public profile endpoint.  
It does **not** interact with the game client.

---

If you'd like, you can expand this later to track mission counts, averages, or drones per hour.
