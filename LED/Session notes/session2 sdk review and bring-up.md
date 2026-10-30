# LED Display Board — Session 2 Notes: SDK Review + Bring-up Plan

Date: end of session 2. Status: hardware on the bench, ready to wire and power up.

---

## What was done this session

1. Requirements firmed up in `LED/AgentDocs/requirements-display.md`:
   R1 decoupling rules + acceptance, R2 content mirror (5 s latency target),
   R3 fixed decisions, SDK findings, open points 1 and 3 resolved.
2. Confirmed board layout: 12 modules, 4 wide x 3 high = 1280x480mm, 256x96 px,
   up to 3 flags in a row (mirrors RO start-event flag slots).
3. Reviewed the full SDK (`LED/SDK/SDK_FullColor V3.0`):
   - SDK 2.0 C# source read completely. Protocol: UDP discovery + XML commands
     over TCP, both on port 10001. Framing: 2-byte length + 2-byte cmd; SDK
     command XML chunked at 8000 bytes with a 12-byte header. ~40 methods.
   - Content model: screen -> programs -> areas -> items (text/image/video/clock).
     No countdown item in 2.0 or 3.0 — minute digit is rendered server-side
     into the published image (also guarantees LED matches display.html, R2).
   - `SDK3.0文档.rar` extracted with WinRAR (gitbook HTML, Chinese, in
     C:\Users\anton\AppData\Local\Temp\sdk30docs — move to LED/documents if
     we want to keep them). Headline: **`RealTimeUpdate`** command — updates a
     single text/image node by GUID without re-sending the program; supports
     remote HTTP image URLs (card downloads itself, replies kDownloadingFile
     then kSuccess). Like-for-like image swaps don't flicker. Preferred publish
     path if the C08L firmware speaks SDK 3.0; SDK 2.0 `UpdateProgram`
     (fixed GUIDs + temp image upload, type 128) is the fallback.
   - ~90 s idle TCP timeout — heartbeat or reconnect per publish.
4. Wrote and smoke-tested `LED/scripts/discover_card.py`:
   broadcasts the SDK discovery packet (UDP 10001), prints card IP + device ID,
   then probes TCP 10001 on each card found. Also does version negotiation.
   Runs clean with no card on the network (expected "No cards found").
5. Noted: real Python is `C:\ProgramData\miniconda3\python.exe`
   (START.bat's `C:\Users\anton\miniconda3` is stale).

---

## Bring-up sequence (next physical session, agreed)

1. Wire ONE module + card with the mains unplugged. Never hot-plug HUB75E
   ribbons or power connectors while the PSU is live.
   Ribbon: card HUB75E port 1 -> module IN, pin 1 aligned (red stripe/arrows).
   Card 5V terminal fed from the same PSU (card max 8W).
2. PSU powered, card still disconnected: verify 5.0-5.2V at the module feed
   with a multimeter. Mains side wired with the plug out of the wall,
   RCD-protected outlet.
3. Connect everything, LAN cable card -> router LAN port, PC on same router.
4. Power up. Check LEDs: PWR steady green, RUN flashing green, display
   indicator flashing (= FPGA OK). Module showing garbage/boot image is normal.
5. Discover the card from the PC:
   ```
   C:\ProgramData\miniconda3\python.exe C:\Users\anton\flagmachine\LED\scripts\discover_card.py --wait 5
   ```
6. First config in HDPlayer: screen 64x32 (one module), scan mode **1/8**
   (module is 1/8 scan — not the 1/16 typical indoor default), fix scan
   direction with smart config, send a test image.
7. Then switch to SDK publishing: publish a fixed-GUID program (one full-screen
   image area), test the update loop (temp image upload + RealTimeUpdate or
   UpdateProgram), measure latency vs the 5 s target.

## Then (after bring-up works)

- Publish loop from Flask (`led_publisher.py` in drag-drop-app, next to app.py).
- Expand to 12 modules, set screen 256x96 in HDPlayer.
- FlagMachine integration per R1/R2 with acceptance tests A1.x / A2.x.

## Open points snapshot

1. Module arrangement: resolved (4x3).
2. SDK publish latency vs 5 s target: measure at bench.
3. Native countdown: resolved by design (server-rendered digit).
4. Static IP for the card on the club Wi-Fi: decide at install.
5. HDPlayer scan config: 1/8 scan at first configuration.

## Key files

- `LED/AgentDocs/requirements-display.md` — governing requirements (R1/R2/R3).
- `LED/Session notes/session1 questions.md` — answered questionnaire.
- `LED/scripts/discover_card.py` — card discovery/probe tool.
- `LED/SDK/SDK_FullColor V3.0/.../SDK2.0/SDKLibrary/*.cs` — protocol source.
- `drag-drop-app/documents/HD-C08L Specification V1.0.pdf` — card spec.
