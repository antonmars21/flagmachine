# LED Display Board — Session 1: Plan, Hardware Review, Research Questions

Kit: Huidu HD-C08L asynchronous multimedia playback card (sold by TOPPOINT) + TOPPOINT SMD2020 P5 320x160mm indoor modules.
Source spec: drag-drop-app/documents/HD-C08L Specification V1.0.pdf

---

## 1. Hardware review

| Spec | Value | Impact |
|---|---|---|
| Module resolution | 64x32 px per 320x160mm module | 3x4 module board = 192x96 px, 1280x480mm physical |
| Card capacity | 196,608 px, 8x HUB75E, max width 2048 px | Huge headroom; 9 modules is 18,432 px |
| Content model | Asynchronous — plays programs from 4GB storage; no computer needed at the board | Board keeps running even if the RO laptop dies mid-sequence |
| Sources | Video, picture, text, clock, streaming, timing, counting | Built-in timing/counting may give a native countdown — test before building a render pipeline |
| Networking | preference = Wi-Fi then AP+STA, 100M LAN, USB, optional 4G/XiaoHui Cloud | Flask app can publish over club Wi-Fi or direct cable |
| Extras | Not required- Relay (AC 250V/3A or DC 30V/3A), sensor port, GPS, RTC battery | Relay can switch the PSU mains = remote power on/off; GPS gives time sync |
| Card power | DC 5V (4.6–5.5V), max 8W | Small dedicated feed from the main PSU |
| Module power | ~800W/m2 max white = ~8A per module at full white; ~0.5–2A with sparse flags/digit content | 5V high-current design — main wiring hazard |
| Environment | Card is a bare board, not waterproof; P5 SMD2020 is an indoor module | display is housed in the yacht club, LED are OutDoor rated brighness 


### Cautions

1. Indoor panel, outdoor sport. SMD2020 indoor modules are 5000 nits and unsealed. Outdoor spec board are designed to be sunlight

2. Digit size. A 3-module-tall board gives a ~480mm digit — likely marginal from the water. 
we can make the board 640mmx 980mm rearrange the configuration
A taller digit area (4–6 modules) costs mostly power and mounting, not control.

---

## 2. Plan (phases)

1. Decide board size and layout — module count and flags-vs-digit placement, driven by viewing distance. = 12 modules, arrange 3x4
2. Bench bring-up (one module, indoors) — wire card + one module, configure in HDPlayer, prove a test pattern. - yes agree
3. Content pipeline — get a rendered flag/digit image from Flask onto the card programmatically; measure update latency.
4. Wire the full board — data chains per HUB port, power distribution, enclosure, relay-switched PSU.
5. FlagMachine integration — publish board state on every minute tick / flag change; add config + watchdog.
6. Field install — mount, network to the RO laptop, failsafe test (kill the laptop, confirm the board keeps playing).

### Wiring detail for bench bring-up

``` 
5V PSU --+--> HD-C08L power terminal (DC 5V, 4.6-5.5V) - we have purchased a 400w 220v to 5 volt power supply
         +--> module power connector (5V + GND pair next to HUB75)
HD-C08L HUB75E port 1 --(16-pin flat ribbon)--> module INPUT header
Wi-Fi antenna --> card; RTC battery --> 2-pin battery header
```

Power-up check: PWR green steady, RUN green flashing, display indicator flashing (FPGA OK).
Then PC -> card via LAN (or its Wi-Fi AP), install HDPlayer, set screen config to 64x32, 1/16 scan (typical for P5 320x160 — confirm with TOPPOINT), fix scan direction with the smart-config tool, send a test picture.

### Shopping list still open

- 5V PSU sized for final module count (12 modules: ~20–40A with headroom; bench: 5V 10A plenty)
- 16-pin HUB75E flat ribbon cables (often not included — check the order) - are included
- 5.08mm terminal power cabling, fusing, enclosure, optional brightness sensor (card sensor port supports auto-dim)

---

## 3. Research questionnaire

### A. Location and legibility (drives everything)

1. Where is the board mounted  -in our race tower
— shore start line or committee boat - on shore we have  a race tower close to the waters edge, 
display indoord behind large window
— and what's the typical viewing distance from the furthest sailor? max 250m
2. Will it be in direct sun, shaded, or used only in overcast/evening conditions? sunny days
3. What does HYC currently use, 
and is a 480mm digit legible at that distance  - we made cardboard test images and 480 mm is suitable
— or should the digit area be 2x taller?

### B. Panel specifics (ask TOPPOINT)

4. Exact spec sheet for the module: scan type (1/16?), HUB75E pinout, max current per module, brightness in nits, refresh rate.
refresh rate 3840: 1\8 scan
5. Do they sell an outdoor/IP-rated P5 module or a matching cabinet, and front-service magnetic modules? - we purchased the modules only, will customise own case
6. What's included per module: ribbon cable, power harness, mounting brackets? - we have nesesary pwoer and ribbon cables

### C. Card API (decides the software design)

7. Does current C08L firmware support the Huidu async secondary-development protocol (local TCP/HTTP from the LAN), 
and can we get the doc? What port/defaults? - we have an SDK wich we will look at shortly
8. Does the built-in timing/counting source support a live synced countdown — or only free-running timers? - not sure
9. Does it accept an RTSP/stream source, and what's the practical latency over Wi-Fi?
10. Default IP/network config for LAN and AP mode; can it run STA on the club router with a static IP?

### D. Power and environment

11. Power source at the mount point: mains, --- from mains, we have power converter
12. Enclosure plan: IP rating, ventilation for the PSU, sun hood, salt-air protection for connectors. it will be indoors
13. Does the relay switching the PSU mains (AC 250V/3A) exceed the PSU inrush — or should it switch the low-voltage side instead?

### E. Operations

14. Update cadence and failure mode: if Wi-Fi drops mid-sequence, does the card keep showing the last published image (expected for async — verify)?
15. Who powers it on/off, and is LedArt relay control acceptable, or should screen on/off be tied to the CTRL input (12V sense)?

---

## 4. Recommended order

Research A + B first (determine module count and indoor-vs-outdoor choice), bench-bring-up one module as soon as it arrives, and in parallel chase question 7 (the Huidu API doc) since it shapes the whole FlagMachine integration.

## 5. FlagMachine integration context

- Existing sailor-facing display: templates/display.html fed by /api/display-state in app.py; shows minutes remaining (no seconds, World Sailing rules) + flags.
- Planned pipeline: render board state (flags + digit) to a PNG in Flask (Pillow) and push to the card once per minute and on flag changes — unless the native countdown (question 8) or streaming (question 9) turns out better.
- Failsafe: async card keeps playing the last published program if the laptop or Wi-Fi dies. 
ideal would be to allow image change - e.g, an urgent flag with low lag 5 seconds
