/* static/css/style.css */
:root {
    --bg-dark: #121824;
    --panel-bg: #1e2640;
    --card-pending: #2a355c;
    --card-active: #1a1f36;
    --border-pending: #3d4b7c;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --neon-amber: #f59e0b;
    --neon-green: #10b981;
    --danger-red: #ef4444;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

body {
    background-color: var(--bg-dark);
    color: var(--text-main);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.display-container {
    display: flex;              /* Enables flexbox layout */
    flex-direction: row;        /* Ensures left-to-right alignment */
    align-items: center;        /* Vertically centers the items */
    gap: 15px;                  /* Adds spacing between elements */
}

/* Optional styling to visualize the layout */
#display-grid-name,
#display-flag-container,
#display-class-timer {
    border: 1px solid #ccc;
    padding: 10px;
    text-align: center;
    background-color: #000;
    color: #fff;
    font-size: 24px;
    font-weight: bold;
}

#display-flag-container img {
    max-width: 100px;           /* Adjust image size as needed */
    height: auto;
}

/* Header Control Dashboard */
.global-control-panel {
    background-color: var(--panel-bg);
    padding: 15px 25px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 3px solid #0f172a;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.branding h1 {
    font-size: 20px;
    letter-spacing: 2px;
    color: var(--text-main);
}
.version-tag {
    font-size: 11px;
    color: var(--neon-amber);
    text-transform: uppercase;
}

.control-actions {
    display: flex;
    align-items: center;
    gap: 15px;
}

.input-group {
    display: flex;
    align-items: center;
    gap: 10px;
}

.input-group label {
    font-size: 14px;
    font-weight: 600;
}

#master-start-input {
    background: #0f172a;
    border: 1px solid var(--border-pending);
    color: #fff;
    padding: 8px 12px;
    font-size: 16px;
    border-radius: 6px;
    font-weight: bold;
}

.btn {
    padding: 10px 20px;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    transition: transform 0.1s;
}
.btn:active { transform: scale(0.97); }
.btn-green { background-color: var(--neon-green); color: #fff; }
.btn-red { background-color: var(--danger-red); color: #fff; }
.btn-gray { background-color: #475569; color: #fff; }

.system-clock-box {
    text-align: right;
    background: #0f172a;
    padding: 5px 15px;
    border-radius: 6px;
    border: 1px solid #334155;
}
.clock-label { font-size: 10px; color: var(--text-muted); }
#live-system-clock { font-size: 18px; font-family: monospace; font-weight: bold; color: #38bdf8; }

/* Main Workspace Framework Split */
.workspace-container {
    flex: 1;
    display: flex;
    overflow: hidden;
}

/* Left Sidebar Asset Palette */
.sidebar-library {
    width: 300px;
    background-color: #171e30;
    border-right: 2px solid #0f172a;
    padding: 20px;
    display: flex;
    flex-direction: column;
}

.sidebar-library h2 { font-size: 16px; margin-bottom: 5px; border-bottom: 1px solid #334155; padding-bottom: 5px;}
.instruction-text { font-size: 12px; color: var(--text-muted); margin-bottom: 15px; }
.library-scroller { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }

.library-card {
    background: var(--panel-bg);
    border: 1px solid #334155;
    padding: 12px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: grab;
}

.library-drag-handle { color: var(--text-muted); font-size: 18px; }
.library-flag-frame { background: #0f172a; width: 40px; height: 35px; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
.asset-name { font-weight: bold; font-size: 14px; }
.asset-default-time { font-size: 12px; color: var(--neon-amber); }

/* Right Column Main Execution Track */

/* updated*/

/* Base Event Grid Card Styles */
.event-grid {
    margin-bottom: 25px;
    padding: 20px;
    border-radius: 8px;
   /* background-color: #fafafa;*/
	background-color: #121824;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    transition: all 0.2s ease;
}

/* Event Grid 1: Explicit Blue Outline */
.grid-primary {
    border: 3px solid #0056b3; 
}

/* Event Grid 2: Explicit Green Outline */
.grid-secondary {
    border: 3px solid #1e7e34; 
}

/* Header design within the grid blocks */
.event-grid-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 10px;
    margin-bottom: 15px;
}

.grid-timer {
    font-family: 'Courier New', Courier, monospace;
    font-weight: bold;
    font-size: 1.25rem;
    background-color: #222;
    color: #00ff00;
    padding: 4px 8px;
    border-radius: 4px;
}

/* Drop targets */
.flag-drop-zone {
    min-height: 120px;
    background-color: #ffffff;
    border: 2px dashed #bbb;
    border-radius: 6px;
    padding: 12px;
    display: flex;
    flex-direction: column; /* Rows pile vertically or side-by-side inside */
    gap: 10px;
}
/* end of updated 050726*/


.event-sequence-pane {
    flex: 1;
    padding: 25px;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.pane-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

/* Add to static/css/style.css */
.timer-go-animation {
    animation: pulse-green 1s infinite alternate;
}

@keyframes pulse-green {
    0% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }
    100% { box-shadow: 0 0 50px rgba(16, 185, 129, 0.8); }
}


.badge { padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
.status-ready { background-color: #1e3a8a; color: #93c5fd; }
.status-running { background-color: #78350f; color: #fde68a; animation: pulse 1.5s infinite alternate; }
.status-finished { background-color: #064e3b; color: #6ee7b7; }

.event-grid-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 200px;
}

/* ==========================================================================
   THE THREE-STATE INTERFACE BLOCKS
   ========================================================================== */

/* Base Structural Wrapper Row */
.event-row {
    background-color: var(--card-pending);
    border: 2px solid var(--border-pending);
    border-radius: 10px;
    padding: 15px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    transition: all 0.2s ease;
}

.drag-handle { cursor: row-resize; font-size: 20px; color: var(--text-muted); padding-right: 10px; }
.flag-preview-box { display: flex; flex-direction: column; align-items: center; background: #0f172a; padding: 5px 10px; border-radius: 6px; min-width: 80px; }
.flag-filename-label { font-size: 10px; color: var(--text-muted); margin-top: 2px; }

.class-details { flex: 1; padding-left: 25px; display: flex; flex-direction: column; }
.class-label { font-size: 18px; font-weight: bold; letter-spacing: 0.5px; }
.event-row .status-badge { font-size: 11px; font-weight: bold; color: var(--text-muted); margin-top: 4px; display: inline-block; }

/* 1. Dynamic Pending Neutral Blueprint */
.state-pending { opacity: 1; }
.minutes-editor {
    background: #0f172a;
    border: 1px solid #475569;
    color: #fff;
    width: 60px;
    padding: 6px;
    font-size: 16px;
    border-radius: 6px;
    text-align: center;
    font-weight: bold;
}
.unit-text { font-size: 13px; color: var(--text-muted); margin-left: 5px; }

/* 2. HIGH-CONTRAST ACTIVE SPOTLIGHT STATE BLUEPRINT */
.state-active {
    background-color: var(--card-active) !important;
    border: 4px solid var(--neon-amber) !important; /* Thick glowing high-visibility border frame */
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
    transform: scale(1.01);
}
.state-active .class-label { color: #fff; }
.state-active .status-badge { color: var(--neon-amber) !important; font-weight: 900; }
.state-active .live-countdown-clock {
    font-size: 32px;
    font-family: monospace;
    font-weight: 900;
    color: var(--neon-amber); /* Vibrant tracking timepiece color */
    letter-spacing: 1px;
}

/* 3. DISSOLVED COMPLETED CLEAR STATE BLUEPRINT */
.state-clear {
    opacity: 0.40 !important; /* Muted scale opacity drop representing historical context */
    background-color: #111524 !important;
    border: 2px dashed #334155 !important;
}
.state-clear .class-label { text-decoration: line-through; color: var(--text-muted); }
.state-clear .status-badge { color: var(--neon-green) !important; }
.state-clear .live-countdown-clock { font-size: 24px; font-family: monospace; color: var(--text-muted); font-weight: bold; }

/* Global Utilities */
.hidden { display: none !important; }
.btn-remove-card {
    position: absolute; right: 8px; top: 8px; background: none; border: none;
    color: var(--danger-red); font-size: 20px; cursor: pointer; opacity: 0.7;
}
.btn-remove-card:hover { opacity: 1; }

@keyframes pulse {
    0% { opacity: 0.6; }
    100% { opacity: 1; }
}