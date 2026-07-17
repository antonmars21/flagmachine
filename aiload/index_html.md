<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flag Machine - Race Officer Control Panel</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>

    <header class="global-control-panel">
        <div class="branding">
            <h1>⚓ FLAG MACHINE</h1>
            <span class="version-tag">v1.0 Demo Dashboard</span>
        </div>
        
        <div class="control-actions">
            <div class="input-group">
                <label for="master-start-input">Master Start Time:</label>
                <input type="time" id="master-start-input" value="{{ state.master_start_time }}">
            </div>
            
            <button id="btn-start" class="btn btn-green">⚡ Start</button>
            <button id="btn-stop" class="btn btn-red">🛑 Stop</button>
            <button id="btn-reset" class="btn btn-gray">🔄 Reset</button>
            <button id="btn-end-race" class="btn btn-blue" style="background-color: #007acc; color: white;">🏁 End Race</button>
        </div>

        <div class="system-clock-box" style="margin-left: 15px;">
            <div class="clock-label">RACE DURATION</div>
            <div id="race-duration-display">00:00:00</div>
        </div>

        <div class="system-clock-box">
            <div class="clock-label">TIME</div>
            <div id="live-system-clock">00:00:00</div>
        </div>
    </header>

    <main class="workspace-container">
        
        <aside class="sidebar-library">
            <h2>📋 Flags</h2>
            <p class="instruction-text">Drag items out into a specific Start grid below:</p>
            <div class="library-scroller">
                {% for asset in assets %}
                <div class="library-card" draggable="true" 
                     data-label="{{ asset.label }}" 
                     data-flag="{{ asset.flag_image }}" 
                     data-minutes="{{ asset.default_minutes }}">
                    
                    <div class="library-drag-handle"></div>
                    
                    <div class="library-flag-frame">
                        <img src="{{ url_for('static', filename='flags/' + asset.flag_image) }}" 
                             alt="{{ asset.label }}" 
                             style="width: 100%; height: 100%; object-fit: contain; border-radius: 2px;">
                    </div>
                    
                    <div class="library-meta">
                        <div class="asset-name">{{ asset.label }}</div>
                        <div class="asset-default-time">{{ asset.default_minutes }} </div>
                    </div>
                </div>
                {% else %}
                <div class="no-assets-alert" style="padding: 15px; color: #888; text-align: center; font-style: italic;">
                    No flags discovered in static/flags/
                </div>
                {% endfor %}
            </div>
        </aside>

        <section class="event-sequence-pane">
            <div class="pane-header">
                <h2>⏱️ Start Sequence</h2>
                <div id="global-status-badge" class="badge status-ready">STATE: READY</div>
            </div>

            <div id="event-grids-container">
                
                <div class="event-grid grid-primary" data-grid-index="1" id="event-grid-1">
                    <div class="event-grid-header">
                        <h3>Boat Class 1</h3>
                        <div class="grid-meta">
                            <span class="grid-countdown-label">Total Countdown: </span>
                            <span class="grid-timer" id="timer-grid-1">00:00</span>
                        </div>
                    </div>
                    <div class="flag-drop-zone" id="drop-zone-1" data-grid-index="1"></div>
                </div>

                <div class="event-grid grid-secondary" data-grid-index="2" id="event-grid-2">
                    <div class="event-grid-header">
                        <h3>Boat Class 2</h3>
                        <div class="grid-meta">
                            <span class="grid-countdown-label">Total Countdown: </span>
                            <span class="grid-timer" id="timer-grid-2">00:00</span>
                        </div>
                    </div>
                    <div class="flag-drop-zone" id="drop-zone-2" data-grid-index="2"></div>
                </div>

            </div>
        </section>
    </main>

    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
