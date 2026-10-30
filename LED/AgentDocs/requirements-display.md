# LED Display Board — Display Integration Requirements

Sources: LED/Session notes/session1 questions.md (answered), drag-drop-app/documents/HD-C08L Specification V1.0.pdf, app.py `/api/display-state`.

---

## R1 — Core requirement

> The LED display board is added to FlagMachine. FlagMachine must continue to function
> perfectly with the existing HTML display. If the LED is out of order, FlagMachine must
> function normally.

### R1.1 Decoupling rules (binding for all LED code)

1. The LED publisher is an **optional, side-effect-free module**. It reads existing
   backend state — the same fields `/api/display-state` serves (`status`,
   `grid_name`, `flag_image`, `secondary_flag_image`, `live_timer`, `display_mode`) —
   and pushes rendered content to the card. It introduces no new shared state and
   performs no writes into app state.
2. **No failure propagation.** Any LED publish failure (card off, Wi-Fi dead, timeout,
   malformed response) is logged and swallowed. It must never raise into request
   handlers, timer logic, or the RO UI. All network calls run with a timeout.
3. **The HTML display remains the source of truth.** `display.html` +
   `/api/display-state` are unchanged in behavior. The LED mirrors them; they never
   wait on the LED.
4. **Kill switch.** A config flag (env var or config file) enables/disables the LED
   integration. Disabled = zero publish attempts, zero overhead.
5. **RO status indicator (nice to have).** RO page shows LED status:
   published / stale / unreachable, so the RO knows without leaving the tower.

### Acceptance — R1

- A1.1 LED enabled but card unplugged: all existing human browser tests still pass;
  only LED warnings in the log.
- A1.2 LED disabled via kill switch: no publish attempts occur (log-provable).
- A1.3 RO laptop killed mid-sequence: card keeps showing the last published image
  (async-card failsafe, verify in bench test).
- A1.4 Repeated LED failures never degrade app response times (publish path is
  asynchronous with timeouts).

---

## R2 — Content mirror

The LED is a mirror of the sailor-facing HTML display, not a separate content source.

1. **Same content rules.** The LED shows the same flags and the same minutes-remaining
   digit as `display.html`, using the existing World Sailing minute logic
   (minutes only, seconds never shown).
2. **Latency targets.** Flag changes and urgent changes are visible on the LED within
   **5 seconds** of the RO action (session 1 target). Minute-digit ticks are visible
   within the minute they describe.
3. **No divergence.** Both outputs derive from the same state snapshot; if the LED
   cannot be updated, the HTML display is unaffected (see R1).

### Acceptance — R2

- A2.1 Side-by-side test: run a standard 5-4-1 start sequence; LED flags and digit
  match the HTML display at every step within the 5 s target.
- A2.2 Timing source: LED digit and HTML digit never disagree by more than one minute
  boundary during a sequence.

---

## R3 — Fixed design decisions (from session 1 answers)

| Item | Decision |
|---|---|
| Modules | 12 x TOPPOINT P5 SMD2020 320x160mm (64x32 px), **1/8 scan**, 3840 Hz refresh, 5000 nits |
| Arrangement | **Confirmed: 4 wide x 3 high** = 1280x480mm, 256x96 px (landscape, up to 3 flags in a row — mirrors the RO start-event flag slots) |
| Board content layout | Flags area left, large minute digit right (per approved mock) |
| Location | Indoors, race tower behind large window; max viewing distance 250 m; sunny-day operation |
| Power | Purchased 400W 220V-to-5V PSU (80A capacity); ribbon cables included; fusing TBD |
| Networking | Wi-Fi preferred (STA on club router), AP fallback; no relay/sensor/GPS extras used |
| Card | Huidu HD-C08L async; SDK in hand — API path confirmed at bench bring-up |
| Content pipeline (working assumption) | Flask renders board state to an image (Pillow) and publishes on flag change + minute tick; native countdown used only if the SDK proves it can be set/synced |

---

## SDK findings (Huidu SDK_FullColor V3.0 — reviewed)

- **Protocol (SDK 2.0):** UDP discovery broadcast on port **10001**; all commands are
  length-prefixed **XML over TCP port 10001** (`<sdk guid="..."><in method="...">`),
  8000-byte chunks, 12-byte header. SDK 1.0 was TCP 9527, single-client, and conflicts
  with HDPlayer — use SDK 2.0. Protocol is simple enough to implement **directly in
  Python** (no .NET dependency needed for `led_publisher.py`).
- **Content model:** screen -> programs -> areas (x/y/w/h) -> items: **text, image,
  video, clock. No native countdown/timer item in SDK 2.0.**
- **Dynamic update path (the one we use):** `UpdateProgram` updates an existing
  program/area/item **only when the GUIDs match** what is stored on the card. Design:
  publish the board program once with fixed GUIDs (single full-screen image area,
  fixed filename), then per update: upload new temp image file (type 128, temp files
  total <= 10MB) + `UpdateProgram`. This is the low-latency path.
- **Connection care:** ~90 s idle timeout — keep a heartbeat or reconnect per publish.
- **Files in the kit:** C# source of the .NET SDKLibrary (2.0.10), English CHM API docs,
  SDKTest 3.6 tool (protocol tester), `SDK3.0文档.rar` (V3.0 docs — **needs WinRAR or
  7-Zip to open**; not yet read).
- **SDK 3.0 docs extracted** (gitbook HTML, Chinese; `SDK3.0文档.rar`): headline
  feature is **`RealTimeUpdate`** — a first-class command that updates individual
  program nodes (text/image) **by GUID, without re-sending the whole program**.
  Rules: the node must exist with the same GUID and type; multiple nodes per
  command allowed; image updates reference a local temp file by name+MD5 or a
  **remote HTTP URL** (the card downloads it, replies `kDownloadingFile` then
  `kSuccess`). Known quirk: switching a dynamic image against a static one causes
  a brief flicker; like-for-like updates don't. This is the intended publish path
  if the C08L firmware speaks 3.0 — confirm at bench bring-up; SDK 2.0
  `UpdateProgram` is the fallback.
- **Countdown decision:** supplier's confidence most likely refers to HDPlayer's
  counting widget or SDK 3.0, not the 2.0 command set. We do not need it:
  the minute digit is **rendered server-side into the published image**, which also
  guarantees LED and HTML display can never disagree (R2). Native countdown is not
  required; revisit only if image publish latency disappoints on the bench.

## Open points

1. ~~Module arrangement~~ **Resolved:** 4 wide x 3 high, 1280x480mm, 256x96 px.
2. SDK publish latency vs the 5 s R2 target — expected well under 1 s (image is
   ~10-20 KB; a few TCP round trips). Measure at bench bring-up.
3. ~~Native countdown~~ **Resolved by design:** server-rendered digit image (see SDK
   findings). V3.0 docs reviewed: no countdown node either — `RealTimeUpdate` is
   the better path; confirm the card's firmware speaks SDK 3.0 at the bench.
4. Club-router plan: static IP for the card on the club Wi-Fi.
5. HDPlayer scan config must be **1/8 scan** (not the 1/16 typical for indoor P5) —
   set at first configuration.
