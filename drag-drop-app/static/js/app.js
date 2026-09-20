// static/js/app.js

document.addEventListener('DOMContentLoaded', () => {
    // Engine State Selectors
    const gridDropzone = document.getElementById('event-grid-dropzone');
    const masterStartInput = document.getElementById('master-start-input');
    const systemClockEl = document.getElementById('live-system-clock');
    const globalStatusBadge = document.getElementById('global-status-badge');
    
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnReset = document.getElementById('btn-reset');

    // Runtime Control Variables
    let heartbeatIntervalId = null;
    let masterStateStatus = "READY"; 
    let currentRunningRowIndex = -1;
    let rowTimerRemainingSeconds = 0;
    let expectedRowEndTimeStamp = 0;

    // ==========================================================================
    // ⏰ SECTION A: THE TIMING LOOP SYSTEM
    // ==========================================================================
    
    // Constant 1-second system synchronization heart tick
    setInterval(updateSystemClock, 1000);
    updateSystemClock();

    function updateSystemClock() {
        const now = new Date();
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        const currentTimeString = `${hrs}:${mins}:${secs}`;
        
        systemClockEl.innerText = currentTimeString;

        // Auto-anchor evaluation logic: strikes exactly when HH:MM matches and real-world seconds click 00
        if (masterStateStatus === "READY") {
            const targetHHMM = masterStartInput.value;
            if (`${hrs}:${mins}` === targetHHMM && secs === "00") {
                console.log(`⏱️ Master anchor hit target time of ${targetHHMM}. Awakening sequence engine.`);
                startSequenceCascade();
            }
        }
    }

    function startSequenceCascade() {
        const rows = gridDropzone.querySelectorAll('.event-row');
        if (rows.length === 0) {
            alert("Cannot execute an empty event track. Add items out of the library palette first.");
            return;
        }

        masterStateStatus = "RUNNING";
        updateGlobalStatusUI("RUNNING");
        lockdownUIConfiguration(true);

        // Notify backend service endpoint about current lock state phase
        postToServer('/update-status', { status: "RUNNING" });

        // Spin up live animation frame thread
        currentRunningRowIndex = 0;
        activateRowTimer(currentRunningRowIndex);
        
        if (heartbeatIntervalId) clearInterval(heartbeatIntervalId);
        heartbeatIntervalId = setInterval(tickActiveRowTimer, 200);
    }

    function activateRowTimer(index) {
        const rows = gridDropzone.querySelectorAll('.event-row');
        if (index >= rows.length) {
            // Sequence completed successfully down the line
            terminateSequenceComplete();
            return;
        }

        currentRunningRowIndex = index;
        const activeRow = rows[index];
        
        // Mutate target structural flags from PENDING style properties over to ACTIVE properties
        activeRow.className = "event-row state-active";
        activeRow.querySelector('.status-badge').innerText = "ACTIVE";
        
        const inputMinutesEl = activeRow.querySelector('.minutes-editor');
        const clockDisplayEl = activeRow.querySelector('.live-countdown-clock');
        
        // Hide standard planning configurations, reveal running time tracking interface
        inputMinutesEl.parentElement.classList.add('hidden');
        clockDisplayEl.classList.remove('hidden');

        // Parse timing durations and cache anchor wall-clock time limit parameters
        const durationMinutes = parseInt(inputMinutesEl.value) || 1;
        rowTimerRemainingSeconds = durationMinutes * 60;
        expectedRowEndTimeStamp = Date.now() + (rowTimerRemainingSeconds * 1000);
        
        renderActiveClockDisplay(clockDisplayEl, rowTimerRemainingSeconds);
    }

    function tickActiveRowTimer() {
        if (masterStateStatus !== "RUNNING") return;

        const rows = gridDropzone.querySelectorAll('.event-row');
        const activeRow = rows[currentRunningRowIndex];
        if (!activeRow) return;

        const clockDisplayEl = activeRow.querySelector('.live-countdown-clock');
        
        // Absolute reference timestamp parsing to protect engine drift from standard tab sleeping parameters
        const deltaMillis = expectedRowEndTimeStamp - Date.now();
        rowTimerRemainingSeconds = Math.ceil(deltaMillis / 1000);

        if (rowTimerRemainingSeconds <= 0) {
            // Milestone complete trigger. Retire completed block and cascade to next down array indexes
            retireCompletedRow(activeRow);
            currentRunningRowIndex++;
            activateRowTimer(currentRunningRowIndex);
        } else {
            renderActiveClockDisplay(clockDisplayEl, rowTimerRemainingSeconds);
        }
    }

    function renderActiveClockDisplay(element, totalSeconds) {
        const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
        const s = String(totalSeconds % 60).padStart(2, '0');
        element.innerText = `${m}:${s}`;
    }

    function retireCompletedRow(rowElement) {
        rowElement.className = "event-row state-clear";
        rowElement.querySelector('.status-badge').innerText = "STARTED / CLEAR";
        const clockDisplayEl = rowElement.querySelector('.live-countdown-clock');
        clockDisplayEl.innerText = "00:00";
    }

    function terminateSequenceComplete() {
        masterStateStatus = "FINISHED";
        updateGlobalStatusUI("FINISHED");
        if (heartbeatIntervalId) clearInterval(heartbeatIntervalId);
        postToServer('/update-status', { status: "FINISHED" });
    }

    function stopSequenceOverride() {
        masterStateStatus = "READY";
        updateGlobalStatusUI("READY");
        if (heartbeatIntervalId) clearInterval(heartbeatIntervalId);
        
        // Re-illuminate and step back down to neutral layouts where execution paused
        const activeRow = gridDropzone.querySelector('.state-active');
        if (activeRow) {
            activeRow.className = "event-row state-pending";
            activeRow.querySelector('.status-badge').innerText = "PENDING";
            activeRow.querySelector('.minutes-editor').parentElement.classList.remove('hidden');
            activeRow.querySelector('.live-countdown-clock').classList.add('hidden');
        }
        lockdownUIConfiguration(false);
        postToServer('/update-status', { status: "READY" });
    }

    function resetSequenceOverride() {
        if (heartbeatIntervalId) clearInterval(heartbeatIntervalId);
        masterStateStatus = "READY";
        updateGlobalStatusUI("READY");
        lockdownUIConfiguration(false);

        // Wipe running elements and restore pristine layout fields across all row sets
        const rows = gridDropzone.querySelectorAll('.event-row');
        rows.forEach(row => {
            row.className = "event-row state-pending";
            row.querySelector('.status-badge').innerText = "PENDING";
            row.querySelector('.minutes-editor').parentElement.classList.remove('hidden');
            row.querySelector('.live-countdown-clock').classList.add('hidden');
        });

        postToServer('/update-status', { status: "READY" });
        synchronizeSequenceStateToServer();
    }

    function lockdownUIConfiguration(shouldLock) {
        masterStartInput.disabled = shouldLock;
        const inputs = gridDropzone.querySelectorAll('.minutes-editor');
        inputs.forEach(inp => inp.disabled = shouldLock);
        
        const rows = gridDropzone.querySelectorAll('.event-row');
        rows.forEach(row => {
            row.setAttribute('draggable', shouldLock ? "false" : "true");
            const btnDel = row.querySelector('.btn-remove-card');
            if (btnDel) btnDel.style.display = shouldLock ? "none" : "block";
        });
    }

    function updateGlobalStatusUI(status) {
        globalStatusBadge.innerText = `STATE: ${status}`;
        globalStatusBadge.className = `badge status-${status.toLowerCase()}`;
    }

    // ==========================================================================
    // 🔀 SECTION B: DRAG-AND-DROP MECHANISM & MUTATION SYNC
    // ==========================================================================
    
    // Bind global toolbar operational listener methods
    btnStart.addEventListener('click', startSequenceCascade);
    btnStop.addEventListener('click', stopSequenceOverride);
    btnReset.addEventListener('click', resetSequenceOverride);

    // Initial sequence input tracking setup
    bindGridInteractiveListeners();

    // Setup Sidebar Drag Starts
    document.querySelectorAll('.library-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
            if (masterStateStatus === "RUNNING") { e.preventDefault(); return; }
            e.dataTransfer.setData('text/plain', 'palette-item');
            e.dataTransfer.setData('asset-label', card.getAttribute('data-label'));
            e.dataTransfer.setData('asset-flag', card.getAttribute('data-flag'));
            e.dataTransfer.setData('asset-minutes', card.getAttribute('data-minutes'));
        });
    });

    // Setup Event Grid Interactivity Bound Limits
    gridDropzone.addEventListener('dragover', (e) => {
        e.preventDefault(); // Required authorization code allowing browser drop behaviors
    });

    gridDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        if (masterStateStatus === "RUNNING") return;

        const transportType = e.dataTransfer.getData('text/plain');
        
        if (transportType === 'palette-item') {
            // Dragged from Library Column -> Construct entirely new physical instance
            const label = e.dataTransfer.getData('asset-label');
            const flag = e.dataTransfer.getData('asset-flag');
            const mins = e.dataTransfer.getData('asset-minutes');
            const newCardId = 'seq_card_' + Date.now();

            const newCardHTML = `
                <div class="event-row state-pending" id="${newCardId}" draggable="true">
                    <div class="drag-handle">☰</div>
                    <div class="flag-preview-box">
                        <span class="flag-icon">🏁</span>
                        <small class="flag-filename-label">${flag}</small>
                    </div>
                    <div class="class-details">
                        <span class="class-label">${label}</span>
                        <span class="status-badge">PENDING</span>
                    </div>
                    <div class="timer-display-container">
                        <div class="duration-input-wrapper">
                            <input type="number" class="minutes-editor" min="1" max="60" value="${mins}">
                            <span class="unit-text">Min</span>
                        </div>
                        <div class="live-countdown-clock hidden">00:00</div>
                    </div>
                    <button class="btn-remove-card" title="Remove from sequence">×</button>
                </div>
            `;
            
            // Append card instance directly where dropped
            gridDropzone.insertAdjacentHTML('beforeend', newCardHTML);
            bindGridInteractiveListeners();
            synchronizeSequenceStateToServer();
        }
    });

    function bindGridInteractiveListeners() {
        const rows = gridDropzone.querySelectorAll('.event-row');
        
        rows.forEach(row => {
            // Duration field mutation interceptors
            const inputField = row.querySelector('.minutes-editor');
            inputField.removeEventListener('change', handleDurationFieldChange);
            inputField.addEventListener('change', handleDurationFieldChange);

            // Row close actions
            const btnRemove = row.querySelector('.btn-remove-card');
            if (btnRemove) {
                btnRemove.onclick = () => {
                    if (masterStateStatus === "RUNNING") return;
                    row.remove();
                    synchronizeSequenceStateToServer();
                };
            }

            // Bound vertical re-ordering events
            row.removeEventListener('dragstart', handleRowDragStart);
            row.addEventListener('dragstart', handleRowDragStart);
            
            row.removeEventListener('dragover', handleRowDragOver);
            row.addEventListener('dragover', handleRowDragOver);
        });
    }

    let activeDraggedRowInstance = null;

    function handleRowDragStart(e) {
        if (masterStateStatus === "RUNNING") { e.preventDefault(); return; }
        activeDraggedRowInstance = this;
        e.dataTransfer.setData('text/plain', 'reorder-item');
    }

    function handleRowDragOver(e) {
        e.preventDefault();
        if (masterStateStatus === "RUNNING" || !activeDraggedRowInstance || activeDraggedRowInstance === this) return;

        // Determine midpoint positioning threshold boundaries
        const boundingBox = this.getBoundingClientRect();
        const midpointY = boundingBox.top + (boundingBox.height / 2);
        
        if (e.clientY < midpointY) {
            gridDropzone.insertBefore(activeDraggedRowInstance, this);
        } else {
            gridDropzone.insertBefore(activeDraggedRowInstance, this.nextSibling);
        }
        synchronizeSequenceStateToServer();
    }

    function handleDurationFieldChange(e) {
        const rowElement = e.target.closest('.event-row');
        const cardId = rowElement.id;
        const currentMinsValue = e.target.value;

        postToServer('/update-settings', {
            card_id: cardId,
            countdown_minutes: currentMinsValue
        });
    }

    masterStartInput.addEventListener('change', () => {
        postToServer('/update-settings', {
            master_start_time: masterStartInput.value
        });
    });

    function synchronizeSequenceStateToServer() {
        const rows = gridDropzone.querySelectorAll('.event-row');
        const completeSequenceArray = [];

        rows.forEach(row => {
            completeSequenceArray.push({
                id: row.id,
                label: row.querySelector('.class-label').innerText,
                flag_image: row.querySelector('.flag-filename-label').innerText,
                countdown_minutes: parseInt(row.querySelector('.minutes-editor').value) || 5,
                status: "PENDING"
            });
        });

        postToServer('/update-sequence', { sequence: completeSequenceArray });
    }

    // Network transport layer abstraction helper
    function postToServer(endpoint, jsonPayload) {
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jsonPayload)
        })
        .then(res => res.json())
        .then(data => console.log(`💾 Sync response [${endpoint}]:`, data))
        .catch(err => console.error(`❌ Network error updating [${endpoint}]:`, err));
    }
});