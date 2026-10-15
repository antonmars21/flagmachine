# LED Hardware Components

## Background

Windows PC software has two parts. Part 1 sets up and manages the countdown for the yacht race — under different conditions different flags need to be displayed. Part 2 is a LED digital board visible to the sailors. Both parts are web HTML and JS served from localhost (Flask, `app.py`).

Two hardware designs were considered:

- **Design 1** — TOPPOINT Dual-mode LED Display Player **HD-A4 / A4L** (synchronous): laptop HDMI output is mirrored to the LED screen in real time via the A4 box and receiving cards. The existing `display.html` page would render on the screen unchanged.
- **Design 2** — TOPPOINT **HD-C08L Huidu Asynchronous Control System** (adopted): the C08L has no HDMI input. It stores content on the card and plays it standalone; the app pushes updates to the card over Wi-Fi/Ethernet/USB. Part 2 changes from "render a web page on the screen" to "push state updates to the card".

**Decision: Design 2 (HD-C08L)** — chosen because the screen runs standalone (laptop can sleep, Wi-Fi can drop, the board keeps showing the last pushed state), and the display only needs whole-minute timer updates and event-driven flag changes, which suits an asynchronous card.

## Design 2 — Final MVP specification

### Screen

- P5 (5 mm pitch) LED, 960 mm x 480 mm
- Resolution: 192 x 96 px = **18,432 pixels** (~9% of the C08L's 196,000-pixel capacity)
- Built from 18 standard P5 modules (160 x 160 mm, 32 x 32 px each; 6 across x 3 down)
- Design constraint: 192 x 96 px is a low-resolution canvas — large flag artwork and big countdown digits only, no small text

### Wiring

```
Windows 11 laptop ──(Wi-Fi hotspot, ~5 m)── HD-C08L ──(HUB75E ribbon cables)── 18x P5 modules
                                                    └── DC 5V power supply
```

- **Laptop -> C08L**: the C08L's built-in Wi-Fi hotspot (AP mode). Laptop sits within ~5 m of the board, so no Ethernet adapter or router is required. A USB-to-Ethernet adapter remains a fallback if Wi-Fi proves unreliable on site.
- **C08L -> LED matrix**: the C08L is a 2-in-1 card (sender + playback); it drives the P5 modules directly via its HUB75E ribbon-cable ports. No separate receiving cards at this pixel count.
- **First-time setup**: define the module layout and scan configuration in Huidu HDPlayer PC software; config is stored on the card.

### Application changes (Part 2)

- Part 1 (`index.html`), the Finish Sheet, and the Flask API are unchanged.
- `display.html` is retained as a fallback/test display for any laptop or monitor.
- New `led_bridge.py` module: hooks into `app_state` updates and pushes changes to the C08L over the network — image/program switch for flags, text-notice update for the timer (whole minutes, plus a "GO" push at zero).
- All hardware-specific logic lives in `led_bridge.py` behind a small config (card IP, protocol), so other sailing clubs can swap hardware without touching the rest of the app.
- **Pending**: obtain the C08L secondary-development/API documentation from the vendor to confirm the LAN protocol is enabled on the shipped firmware (some units are locked to HDPlayer/LedArt/XiaoHui Cloud only).

### Failure behaviour

If the Wi-Fi link drops mid-countdown, the board freezes on the last pushed state rather than going blank. Because the timer displays whole minutes, one missed update costs one minute of staleness.

## Future scenarios (out of MVP scope)

This is an open-source project; other clubs may adapt it:

- **Mobile device control** — the bridge design (config-driven, HTTP/LAN push) means any device that can reach the Flask server can drive the board; a phone cannot host the Flask app itself, so this would involve serving the app from a small always-on box (e.g. Raspberry Pi) at the club.
- **Start boat deployment** — the asynchronous model is an advantage: the C08L keeps playing pushed content standalone, so the screen does not need a live laptop link; the laptop pushes over the Wi-Fi hotspot whenever in range.
