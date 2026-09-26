<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Grid 1 - Outdoor Display</title>
    <style>
        :root {
            --bg-dark: #000000;
            --text-white: #ffffff;
            --border-color: #334155;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-white);
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Top Bar: Grid Name & Status */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            border-bottom: 2px solid var(--border-color);
            background-color: #111;
        }

        .grid-name {
            font-size: 3rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .status-badge {
            font-size: 1.5rem;
            padding: 10px 25px;
            border-radius: 8px;
            background-color: #333;
            text-transform: uppercase;
            font-weight: bold;
        }
        .status-running { background-color: #10b981; color: white; }
        .status-standby { background-color: #555; color: #ccc; }

        /* Main Display Area */
        .display-container {
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 60px;
            padding: 40px;
        }

        /* Flag Container (Kept for context) */
        #display-flag-container {
            width: 400px;
            height: 400px;
            background-color: #1a1a1a;
            border: 4px solid var(--border-color);
            border-radius: 12px;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }

        #display-flag-container img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        /* --- TIMER STYLES (UPDATED) --- */
        #display-class-timer {
            /* No background, no border, no box-shadow */
            background-color: transparent;
            border: none;
            box-shadow: none;
            
            /* Typography */
            font-family: 'Courier New', monospace; /* Monospace for stable width */
            font-size: 12rem; /* Extremely large */
            font-weight: 900;
            color: #ffffff; /* Pure White */
            
            /* Layout */
            display: flex;
            justify-content: center;
            align-items: center;
            height: auto;
            width: auto;
            
            /* Remove any padding that might look like a box */
            padding: 0;
            margin: 0;
        }

        /* Hidden State */
        .hidden { display: none !important; }
    </style>
</head>
<body>

    <div class="header">
        <div class="grid-name" id="display-grid-name">Event Grid 1</div>
        <div class="status-badge" id="display-status">STANDBY</div>
    </div>

    <div class="display-container">
        <!-- Flag Image -->
        <div id="display-flag-container">
            <span style="color: #555; font-size: 1.5rem;">NO FLAG</span>
        </div>

        <!-- Countdown Timer (Numbers Only) -->
        <div id="display-class-timer">--</div>
    </div>

    <script>
        const API_ENDPOINT = '/api/display-state';
        const POLL_INTERVAL_MS = 500; 

        const gridNameEl = document.getElementById('display-grid-name');
        const statusEl = document.getElementById('display-status');
        const flagContainer = document.getElementById('display-flag-container');
        const timerEl = document.getElementById('display-class-timer');

        let lastState = null;

        async function fetchDisplayState() {
            try {
                const response = await fetch(API_ENDPOINT);
                const data = await response.json();

                if (JSON.stringify(data) !== JSON.stringify(lastState)) {
                    updateUI(data);
                    lastState = data;
                }
            } catch (error) {
                console.error("Failed to fetch display state:", error);
            }
        }

        function updateUI(data) {
            // Update Status Badge
            statusEl.innerText = data.status;
            statusEl.className = `status-badge status-${data.status.toLowerCase()}`;

            // Update Grid Name
            gridNameEl.innerText = data.grid_name;

            // Update Flag Image
            if (data.flag_image && data.flag_image !== "") {
                const flagUrl = `/static/flags/${data.flag_image}`;
                const currentImg = flagContainer.querySelector('img');
                if (!currentImg || currentImg.src !== flagUrl) {
                    flagContainer.innerHTML = `<img src="${flagUrl}" alt="Race Flag">`;
                }
            } else {
                flagContainer.innerHTML = '<span class="no-flag-placeholder">NO FLAG</span>';
            }

            // Update Timer (Numbers Only)
            const timerValue = data.live_timer;
            
            if (timerValue === "GO" || timerValue === "0" || timerValue === "00") {
                timerEl.innerText = "GO";
                // Optional: You can add a class here if you want "GO" to blink
                // timerEl.classList.add('go'); 
            } else {
                // Just display the number (e.g., "4", "3", "2", "1")
                timerEl.innerText = timerValue;
                // timerEl.classList.remove('go');
            }
        }

        // Start Polling
        setInterval(fetchDisplayState, POLL_INTERVAL_MS);
        fetchDisplayState();
    </script>
</body>
</html>