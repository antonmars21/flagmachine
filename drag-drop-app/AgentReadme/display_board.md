# ⛵ Flag Machine — Timer Synchronization Architecture  
### Race Officer Control Panel → Outdoor Display Board  
### Technical Overview (v1.0)

---

## 📌 Purpose of This Document
This document explains how the race‑officer interface (`index.html`) synchronizes timing information with the outdoor sailor‑facing display (`display.html`). It covers:

- What timers exist  
- Which timer is authoritative  
- What value is sent to the backend  
- What the display board shows  
- Why this matches World Sailing / ISAF start‑sequence rules  
- Where the sync happens in JavaScript  

This is the definitive reference for future development.

---

# 🧭 1. Two Different Timer Worlds

## A. Race Officer Timers (index.html)
These are detailed, second‑accurate timers:

- Active row countdown (MM:SS)  
- Grid total countdown (MM:SS)  
- Race duration (HH:MM:SS)  
- System clock  

These timers are **for the race officer only**.

## B. Sailor‑Facing Timer (display.html)
Sailors see **only the number of minutes remaining** until their start.

Seconds are **never** shown.

This matches:
- World Sailing  
- ISAF  
- Kona Sailing Club  
- The race‑officer document  

---

# ⏱ 2. The Authoritative Timer: Grid Total

The **Event Grid Total Remaining Time** is the *only* timer that should be sent to the outdoor display.

This is the large red/green box in the race‑officer interface.

Example:

| Grid total | Sailor sees |
|-----------|-------------|
| 03:59 → 03:00 | **4** |
| 02:59 → 02:00 | **3** |
| 01:59 → 01:00 | **2** |
| 00:59 → 00:01 | **1** |
| 00:00 | **GO** |

This is the correct sailing logic. -- the current format is 1 minute earlier aand the final 1 minute displays as 00

---

# 🔄 3. How Synchronization Works

## A. index.html calculates the grid total
Inside `calculateGridTotal(zone)`:

1. Sum all row durations  
2. Subtract active row’s remaining seconds  
3. Convert to MM:SS  
4. Update the officer UI  
5. **Send MM:SS to backend**  
   ```js
   syncTimerToServer(`${displayMins}:${displaySecs}`);

# make a toggle to show/hide the count down Timer

# Make a grid 1 row high and 4 columns wide with div tages, dynamically place the flag in the left most div subsuquently flags in the same event grid will be dispalyed in the 2nd div and the timer/countdown in the next avaible grid