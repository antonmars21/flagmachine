// finishsheet.js - Finish Sheet UI Logic
// Handles sailor display, lap tallying, finish marking, and manual reordering

const state = {
    race_id: null,
    race_active: false,
    columns: [],
    start_time: null,
    drag_source: null,
    station: null,
    assignments: {},
    sheet_version: null,
    class_start_times: {},
    open_start_time: null,
    race_end_timestamp: null
};

/**
 * Station identity (feature 4): /finishsheet?station=1|2 - the URL is
 * authoritative and remembered per tab (sessionStorage) so two tabs on
 * the same machine keep different stations. Without the parameter the
 * screen defaults to station 1.
 */
function getStationFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = parseInt(params.get('station'), 10);
    if (fromUrl === 1 || fromUrl === 2) {
        sessionStorage.setItem('fs_station', String(fromUrl));
        return fromUrl;
    }
    const saved = parseInt(sessionStorage.getItem('fs_station'), 10);
    return (saved === 1 || saved === 2) ? saved : 1;
}

function updateStationBadge() {
    const badge = document.getElementById('station-badge');
    if (badge && state.station) badge.textContent = 'Station ' + state.station;
}

/**
 * Import sailors from the Sailwave boat_master.htm export
 */
async function refreshSailwaveData() {
    const btn = document.getElementById('btn-refresh-sailwave');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '📥 Importing...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/refresh-sailwave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert(`Sailwave sailors imported successfully!

` +
                  `Classes: ${data.imported.classes_new || 0} new, ${data.imported.classes_updated || 0} updated\n` +
                  `Sailors: ${data.imported.sailors_new || 0} new, ${data.imported.sailors_updated || 0} updated\n` +
                  `Total: ${data.imported.total_sailors || 0} sailors in database`);
            // Refresh the registry list
            await loadRegistryList();
        } else {
            alert(`Import failed: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Import failed: ${error.message}`);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

/**
 * Initialize the finish sheet on page load
 */
async function initFinishSheet() {
    console.log("Initializing Finish Sheet...");
    
    // Station identity (feature 4): this screen's station number
    state.station = getStationFromUrl();
    updateStationBadge();
    
    // Fetch sailors and render columns
    await loadAndRenderSailors();
    
    // Set up event listeners
    document.getElementById('btn-start-race').addEventListener('click', startRace);
    document.getElementById('btn-end-race').addEventListener('click', endRace);
    document.getElementById('btn-export-csv').addEventListener('click', exportRaceCsv);
    document.getElementById('btn-step-back').addEventListener('click', stepBack);
    
    // Add refresh button handler
    const refreshBtn = document.getElementById('btn-refresh-sailwave');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshSailwaveData);
    }
    
    // Update elapsed time every second (banner clock + per-class clocks, bug 15)
    setInterval(updateElapsedTime, 1000);
    setInterval(updateClassElapsedTimes, 1000);
    
    // Poll for class-start status every 500ms to unlock sailor buttons as classes start
    setInterval(pollClassStarts, 500);
    
    // Re-fetch dynamic columns every 3s pre-race (Start Sequence can change), stop once race is active
    setInterval(() => {
        if (!state.race_active) loadAndRenderSailors();
    }, 3000);
    
    // Registry sidebar
    initRegistrySidebar();
}

/**
 * Load sailors from backend and render dynamic columns
 */
async function loadAndRenderSailors() {
    try {
        const response = await fetch('/api/sailors-for-onwater?station=' + state.station);
        const data = await response.json();
        
        if (data.status !== 'success') {
            console.error("Failed to load sailors:", data.message);
            return;
        }
        
        state.columns = data.columns;
        state.assignments = data.assignments || {};
        renderColumns(data.columns);
    } catch (error) {
        console.error("Error loading sailors:", error);
    }
}

/**
 * Move a class column to the other station (column header toggle).
 * Server-truth: the assignment is stored and kept for the day; every
 * station re-renders when its poller sees the new assignments_version.
 */
async function moveClassToStation(classKey, station) {
    if (!classKey) return;
    try {
        const response = await fetch('/api/assign-class-station', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class_key: classKey, station })
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadAndRenderSailors();
        } else {
            alert(data.message || 'Could not move the class.');
        }
    } catch (error) {
        console.error("Error moving class to station:", error);
    }
}

/**
 * Step Back (feature 4): instantly reverse THIS station's most recent
 * capture (lap or finish, any sailor). No confirm dialog - the toast
 * that follows offers Restore with the original time as the safety net.
 */
async function stepBack() {
    try {
        const response = await fetch('/api/undo-last', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ station: state.station })
        });
        const data = await response.json();
        if (data.status === 'success') {
            const what = data.action === 'lap'
                ? `Lap ${data.lap_number} for ${data.sailor}`
                : `Finish for ${data.sailor}`;
            showStepBackToast(`Stepped back: ${what} (${fmtClock(data.timestamp)})`, true);
            loadAndRenderSailors();
        } else {
            showStepBackToast(data.message || 'Nothing to step back.', false);
        }
    } catch (error) {
        console.error("Error stepping back:", error);
    }
}

/**
 * Restore this station's most recently undone capture (original time).
 */
async function restoreLastStep() {
    try {
        const response = await fetch('/api/restore-last', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ station: state.station })
        });
        const data = await response.json();
        if (data.status === 'success') {
            const what = data.action === 'lap'
                ? `Lap ${data.lap_number} for ${data.sailor}`
                : `Finish for ${data.sailor}`;
            showStepBackToast(`Restored: ${what} (${fmtClock(data.timestamp)})`, false);
            loadAndRenderSailors();
        } else {
            showStepBackToast(data.message || 'Nothing to restore.', false);
        }
    } catch (error) {
        console.error("Error restoring:", error);
    }
}

function fmtClock(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    // Fixed 24h HH:MM:SS - toLocaleTimeString can render AM/PM depending on
    // the Windows locale, which is wrong for a race sheet.
    const p = n => String(n).padStart(2, '0');
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function showStepBackToast(message, withRestore) {
    let toast = document.getElementById('stepback-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'stepback-toast';
        document.body.appendChild(toast);
    }
    toast.innerHTML = `
        <span>${message}</span>
        ${withRestore ? '<button id="stepback-restore">Restore</button>' : ''}
    `;
    toast.style.display = 'flex';
    const restoreBtn = document.getElementById('stepback-restore');
    if (restoreBtn) restoreBtn.addEventListener('click', restoreLastStep);
    clearTimeout(state._toastTimer);
    state._toastTimer = setTimeout(() => { toast.style.display = 'none'; }, 10000);
}

/**
 * Render dynamic columns: one per boat class in the current Start Sequence
 * (ordered by sailor count, most on the left), plus a trailing Open Category column.
 */
function renderColumns(columns) {
    const wrapper = document.getElementById('columns-wrapper');

    // Capture scroll positions before rebuilding so periodic re-renders
    // (3s pre-race refresh) don't snap lists back to the top
    const savedWrapperScroll = wrapper.scrollTop;
    const savedListScrolls = {};
    wrapper.querySelectorAll('.sailors-list').forEach(listEl => {
        const key = listEl.dataset.scrollKey || ('idx-' + listEl.dataset.column);
        savedListScrolls[key] = listEl.scrollTop;
    });

    wrapper.innerHTML = '';

    if (!columns || columns.length === 0) {
        const emptyMsg = state.station
            ? `No classes assigned to Station ${state.station}. Move a class here with the toggle on the other screen.`
            : 'No classes in the Start Sequence yet. Drop flags into the Flag Machine to populate columns.';
        wrapper.innerHTML = `<div style="padding: 40px; text-align: center; color: #94a3b8; grid-column: 1/-1;">${emptyMsg}</div>`;
        return;
    }
    
    wrapper.style.gridTemplateColumns = `repeat(${columns.length}, 1fr)`;
    
    columns.forEach((colData, colIdx) => {
        const col_num = colIdx + 1;
        const sailors = colData.sailors || [];
        
        const column_div = document.createElement('div');
        column_div.className = 'column';
        column_div.dataset.column = col_num;
        
        const header = document.createElement('div');
        header.className = 'column-header';
        header.style.borderBottom = `3px solid ${colData.color_hex || '#334155'}`;
        const sequenceNumber = colData.sequence_number || 0;
        const sequenceLabel = sequenceNumber > 0 ? `Start ${sequenceNumber}: ` : '';
        const targetStation = state.station === 1 ? 2 : 1;
        const elapsedClassId = colData.class_id != null ? colData.class_id : '';
        // Tidy: class name + elapsed clock on ONE row, no sailor count, no
        // label - maximise the vertical space for the sailor list.
        header.innerHTML = `
            <div class="column-header-row">
                <div class="column-title" style="color: ${colData.color_hex || '#f8fafc'}">${sequenceLabel}${colData.class_name}</div>
                <div class="column-elapsed" data-class-id="${elapsedClassId}">--:--</div>
            </div>
            <button class="station-toggle" data-class-key="${colData.class_key}" title="Move ${colData.class_name} to Station ${targetStation}">&#10142; ${targetStation}</button>
        `;
        header.querySelector('.station-toggle').addEventListener('click', () => {
            moveClassToStation(colData.class_key, targetStation);
        });
        column_div.appendChild(header);
        
        const list = document.createElement('div');
        list.className = 'sailors-list';
        list.dataset.column = col_num;
        const scrollKey = colData.class_name + '|' + (colData.sequence_number || 0);
        list.dataset.scrollKey = scrollKey;

        sailors.forEach((sailor, index) => {
            const card = createSailorCard(sailor, col_num, index);
            list.appendChild(card);
        });
        resortColumn(list);
        
        column_div.appendChild(list);
        wrapper.appendChild(column_div);
        if (savedListScrolls[scrollKey] !== undefined) list.scrollTop = savedListScrolls[scrollKey];
    });

    wrapper.scrollTop = savedWrapperScroll;
}

/**
 * Create a sailor card element
 */
function createSailorCard(sailor, col_num, index) {
    const card = document.createElement('div');
    card.className = 'sailor-card';
    if (sailor.finish_time) {
        card.classList.add('finished');
    }
    
    card.dataset.uid = sailor.uid;
    card.dataset.column = col_num;
    card.dataset.index = index;
    card.dataset.classId = sailor.class_id != null ? sailor.class_id : '';
    card.dataset.openCategory = sailor.open_category ? 'true' : 'false';
    card.dataset.seed = sailor.seed != null ? sailor.seed : 9999;
    card.dataset.lapCount = sailor.lap_count || 0;
    card.dataset.handicap = sailor.handicap != null ? sailor.handicap : 9999;
    card.dataset.lastLapTime = sailor.last_lap_time || '';
    card.dataset.finishTime = sailor.finish_time || '';
    card.dataset.manualOverride = 'false';
    card.draggable = true;
    
    const finished_class = sailor.finish_time ? ' (Fin)' : '';
    const class_started = !!sailor.class_started;
    // Open-category sailors (no class in the countdown) record laps/finishes
    // against the race start rather than a class start
    const can_record = class_started;
    if (class_started) card.classList.add('class-started');
    
    card.innerHTML = `
        <div class="lap-counter">
            <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${can_record ? '' : 'disabled'}>+ Lap</button>
            <div class="lap-value">${sailor.lap_count || 0}</div>
        </div>
        <div class="sailor-details">
            <div class="sailor-name-row">
                <span class="sailor-name">${sailor.short_name}${finished_class}</span>
                <span class="sail-number">${sailor.sail_no}</span>
            </div>
        </div>
        <input type="checkbox" class="finish-checkbox" data-uid="${sailor.uid}" 
            ${sailor.finish_time ? 'checked disabled' : (can_record ? '' : 'disabled')}>
    `;
    
    // Event listeners
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);
    card.addEventListener('dragover', handleDragOver);
    card.addEventListener('drop', handleDrop);
    card.addEventListener('dragleave', handleDragLeave);
    
    const lapBtn = card.querySelector('.btn-lap');
    lapBtn.addEventListener('click', () => recordLap(sailor.uid, card));
    
    const finishCheckbox = card.querySelector('.finish-checkbox');
    finishCheckbox.addEventListener('change', () => markFinish(sailor.uid, finishCheckbox.checked, card));
    
    return card;
}

/**
 * Comparator for auto-sorting non-manual, unfinished cards:
 * lap_count asc (sailors approaching their next lap completion stay at the top;
 * completing a lap moves the sailor down the list), then last lap time asc,
 * then handicap asc, then seed asc.
 */
function compareByLapThenTimeThenHandicap(a, b) {
    const lapDiff = (parseInt(a.dataset.lapCount) || 0) - (parseInt(b.dataset.lapCount) || 0);
    if (lapDiff !== 0) return lapDiff;
    const aTime = a.dataset.lastLapTime || '';
    const bTime = b.dataset.lastLapTime || '';
    if (aTime !== bTime) return aTime < bTime ? -1 : 1;
    const hDiff = (parseFloat(a.dataset.handicap) || 9999) - (parseFloat(b.dataset.handicap) || 9999);
    if (hDiff !== 0) return hDiff;
    return (parseInt(a.dataset.seed) || 9999) - (parseInt(b.dataset.seed) || 9999);
}

/**
 * Re-sort a sailor list column:
 * - Finished sailors always drop to the bottom, ordered by finish time (first finisher on top of the finished group).
 * - Unfinished sailors are ordered by lap count (asc - lowest first), so sailors
 *   approaching lap completion stay at the top; completing a lap moves them down.
 * - Cards manually dragged (manualOverride='true') keep their current position among the unfinished group,
 *   unless/until they finish - finishing always overrides manual placement and drops them to the bottom.
 */
function resortColumn(listEl) {
    const allCards = Array.from(listEl.children);
    if (allCards.length === 0) return;
    
    const finished = allCards.filter(c => c.classList.contains('finished'));
    const unfinished = allCards.filter(c => !c.classList.contains('finished'));
    
    finished.sort((a, b) => new Date(a.dataset.finishTime || 0) - new Date(b.dataset.finishTime || 0));
    
    // Preserve manual cards at their current slot index within the unfinished group;
    // fill remaining slots with auto-sorted (by lap count, then seed) cards.
    const manualFlags = unfinished.map(c => c.dataset.manualOverride === 'true');
    const autoCards = unfinished.filter(c => c.dataset.manualOverride !== 'true').sort(compareByLapThenTimeThenHandicap);
    
    const merged = [];
    let autoIdx = 0;
    for (let i = 0; i < unfinished.length; i++) {
        if (manualFlags[i]) {
            merged.push(unfinished[i]);
        } else {
            merged.push(autoCards[autoIdx++]);
        }
    }
    
    const finalOrder = merged.concat(finished);
    finalOrder.forEach(card => listEl.appendChild(card));
}

/**
 * Record a lap for a sailor
 */
async function recordLap(uid, card) {
    try {
        const response = await fetch('/api/record-lap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid, station: state.station })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Update UI
            const lapValue = card.querySelector('.lap-value');
            lapValue.textContent = data.lap_count;
            card.dataset.lapCount = data.lap_count;
            // Lap timestamps keep being recorded per sailor (own timer from
            // the first lap onward - DB + CSV exports), but are NOT shown on
            // the card: no room on screen (RO 2026-10-22).
            if (data.last_lap_time) card.dataset.lastLapTime = data.last_lap_time;
            
            const list = card.parentElement;
            if (list) resortColumn(list);
            
            console.log(`Lap recorded for ${uid}: ${data.lap_count}`);
        } else {
            alert(data.message || 'Could not record lap.');
        }
    } catch (error) {
        console.error("Error recording lap:", error);
    }
}

/**
 * Mark a sailor as finished
 */
async function markFinish(uid, is_finished, card) {
    if (!is_finished) return;  // Only handle checking, not unchecking
    
    try {
        const response = await fetch('/api/mark-finish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid, station: state.station })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            card.classList.add('finished');
            card.dataset.finishTime = data.finish_time;
            card.dataset.manualOverride = 'false';  // finishing always overrides manual placement
            const checkbox = card.querySelector('.finish-checkbox');
            checkbox.disabled = true;
            
            const list = card.parentElement;
            if (list) resortColumn(list);
            
            console.log(`Finished marked for ${uid} at ${data.finish_time}`);
        } else {
            alert(data.message || 'Could not mark finish.');
            card.querySelector('.finish-checkbox').checked = false;
        }
    } catch (error) {
        console.error("Error marking finish:", error);
    }
}

/**
 * Poll for class-start status and unlock sailor buttons individually as their class starts.
 * Also detects auto-created race (from Flag Machine countdown) and syncs start/end race button state.
 */
async function pollClassStarts() {
    try {
        const response = await fetch('/api/race-status');
        const data = await response.json();
        if (data.status !== 'success') return;
        
        state.race_id = data.race_id;
        // Bug 35: race_id STAYS SET after End Race (only Reset clears it),
        // so "race_id exists" kept the sheet frozen in mid-race mode after
        // a race ended - registry ticks never loaded sailors into the start
        // list. "Active" means a race is RUNNING: once it is ENDED the
        // columns are live again (lap/finish inputs stay disabled while
        // fm_status is ENDED, and Start Race stays locked until a reset).
        state.race_active = !!data.race_id && !data.race_ended;
        state.race_ended = !!data.race_ended;
        // Bug 15: per-class elapsed clocks are computed from these
        state.class_start_times = data.class_start_times || {};
        state.open_start_time = data.open_start_time || null;
        state.race_end_timestamp = data.race_end_timestamp || null;
        // Bug 4 part B: while the RO control Start is running (or pausing)
        // the flag machine countdown, this manual Start Race button stays
        // locked out - all start buttons obey the RO control start button.
        // ENDED also locks it out (before any class start fired there is no
        // race record, so fm_status is the only truth) until a Reset
        // returns to READY.
        const fmEngaged = ['RUNNING', 'PAUSED', 'ENDED'].includes(data.fm_status);
        
        // Sheet change made on another station (column toggle, step back,
        // restore): re-render this station's columns.
        const av = data.sheet_version;
        if (av !== undefined && av !== state.sheet_version) {
            const firstSeen = state.sheet_version === null;
            state.sheet_version = av;
            if (!firstSeen) loadAndRenderSailors();
        }
        const startedClassIds = new Set(Object.keys(data.class_start_times || {}));
        
        if (state.race_ended) {
            document.getElementById('btn-start-race').disabled = true;
            document.getElementById('btn-end-race').disabled = true;
            document.querySelectorAll('.btn-lap').forEach(btn => btn.disabled = true);
            document.querySelectorAll('.finish-checkbox').forEach(cb => {
                if (!cb.checked) cb.disabled = true;
            });
            return;
        }
        
        document.querySelectorAll('.sailor-card').forEach(card => {
            const classId = card.dataset.classId;
            const isFinished = card.classList.contains('finished');
            // Open-category sailors activate when the open flag fires (if the
            // RO set one) or with the race start - backend reports via open_started
            const openStarted = !!data.open_started;
            const started = (classId && startedClassIds.has(classId)) || (card.dataset.openCategory === 'true' && openStarted);
            
            const lapBtn = card.querySelector('.btn-lap');
            const checkbox = card.querySelector('.finish-checkbox');
            
            if (lapBtn) lapBtn.disabled = !started;
            if (checkbox && !isFinished) checkbox.disabled = !started;
            
            if (started && !isFinished) {
                card.classList.add('class-started');
            } else {
                card.classList.remove('class-started');
            }
        });
        
        if (state.race_active || fmEngaged) {
            document.getElementById('btn-start-race').disabled = true;
            document.getElementById('btn-end-race').disabled = false;
        } else if (!state.race_ended) {
            // READY for the next race of the day (after end+reset or reset-race)
            document.getElementById('btn-start-race').disabled = false;
            document.getElementById('btn-end-race').disabled = true;
        }
    } catch (error) {
        console.error("Error polling class starts:", error);
    }
}

/**
 * Start the race
 */
async function startRace() {
    try {
        // Collect all sailors currently displayed (registered/racing_today sailors)
        const selected_sailors = state.columns
            ? state.columns.flatMap(col => col.sailors.map(s => s.uid))
            : [];
        
        const response = await fetch('/api/start-race', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected_sailors })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            state.race_id = data.race_id;
            state.race_active = true;
            state.start_time = new Date();
            
            document.getElementById('btn-start-race').disabled = true;
            document.getElementById('btn-end-race').disabled = false;
            
            console.log(`Race started with ID: ${state.race_id}`);
        }
    } catch (error) {
        console.error("Error starting race:", error);
    }
}

/**
 * End the race (bug 4: ONE button on ANY page stops ALL timers everywhere).
 * Calls the same two endpoints the RO control page uses, so the flag
 * machine countdown stops on the RO screen and the race status changes
 * from RUNNING to ENDED for everyone, even if this is pressed before the
 * first class start has created a race record.
 */
async function endRace() {
    try {
        // Same control action as the RO End Race button (stops flag machine)
        await fetch('/execute-control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'END_RACE' })
        });
        // Record the race end time (skipped when no race record exists yet)
        if (state.race_id) {
            const response = await fetch('/api/end-race', { method: 'POST' });
            const data = await response.json();
            if (data.status !== 'success') {
                alert(data.message || 'Could not end race.');
            }
        }
        
        state.race_active = false;
        state.race_ended = true;
        
        document.getElementById('btn-start-race').disabled = true;
        document.getElementById('btn-end-race').disabled = true;
        
        // Disable all lap buttons and finish checkboxes
        document.querySelectorAll('.btn-lap').forEach(btn => btn.disabled = true);
        document.querySelectorAll('.finish-checkbox').forEach(cb => {
            if (!cb.checked) cb.disabled = true;
        });
    } catch (error) {
        console.error("Error ending race:", error);
    }
}

/**
 * Export the current race to CSV (class, sailor, start time, laps, end time)
 */
function exportRaceCsv() {
    window.location.href = '/api/export-race-csv';
}

/**
 * Update elapsed time display (based on earliest class start time)
 */
async function updateElapsedTime() {
    try {
        const response = await fetch('/api/get-elapsed-time');
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('elapsed-time').textContent = data.formatted;
        } else {
            document.getElementById('elapsed-time').textContent = '00:00';
        }
    } catch (error) {
        console.error("Error fetching elapsed time:", error);
    }
}

/**
 * Bug 15: per-class elapsed clocks in every column header - the RO can see
 * how long each class has been racing and judge when the maximum allowed
 * race time is approaching. Ticks up from that class's own start; freezes
 * at the race end timestamp once the race has ended. The Open Category
 * column (data-class-id="") runs from the open start time. No label - just
 * the mm:ss clock on the class's header row.
 */
function updateClassElapsedTimes() {
    document.querySelectorAll('.column-elapsed').forEach(el => {
        const classId = el.dataset.classId;
        const startIso = classId !== '' ? state.class_start_times[String(classId)] : state.open_start_time;
        if (!startIso) {
            el.textContent = '--:--';
            return;
        }
        const startedAt = new Date(startIso);
        const reference = (state.race_ended && state.race_end_timestamp)
            ? new Date(state.race_end_timestamp)
            : new Date();
        let secs = Math.max(0, Math.floor((reference - startedAt) / 1000));
        const hh = Math.floor(secs / 3600);
        const mm = String(Math.floor((secs % 3600) / 60)).padStart(2, '0');
        const ss = String(secs % 60).padStart(2, '0');
        el.textContent = hh > 0 ? `${hh}:${mm}:${ss}` : `${mm}:${ss}`;
    });
}

/**
 * Drag and drop handlers for manual reordering
 */
function handleDragStart(e) {
    state.drag_source = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragEnd(e) {
    if (state.drag_source) {
        state.drag_source.classList.remove('dragging');
    }
    state.drag_source = null;
    
    document.querySelectorAll('.sailor-card').forEach(card => {
        card.style.borderColor = '';
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (this !== state.drag_source) {
        this.style.borderColor = '#f59e0b';
    }
}

function handleDragLeave(e) {
    if (e.target === this) {
        this.style.borderColor = '';
    }
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    if (state.drag_source === this) return;
    
    // Mark the dragged sailor as manually placed - keeps position until they finish
    state.drag_source.dataset.manualOverride = 'true';
    
    // Swap position in DOM
    this.parentNode.insertBefore(state.drag_source, this);
    
    console.log(`Sailor reordered: ${state.drag_source.dataset.uid}`);
}

/**
 * ========== SAILOR REGISTRY SIDEBAR ==========
 * Reinstated from Session 2 Sailor Scorer: full fleet list with search,
 * racing-today checkboxes, and add/edit/delete sailor management.
 */
async function initRegistrySidebar() {
    const toggleBtn = document.getElementById('btn-toggle-registry');
    const sidebar = document.getElementById('registry-sidebar');
    const closeBtn = document.getElementById('btn-close-registry');
    const searchInput = document.getElementById('registry-search');
    const addToggleBtn = document.getElementById('btn-add-toggle');
    const addForm = document.getElementById('add-sailor-form');
    
    if (!sidebar) return;  // sidebar markup not present
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (sidebar.classList.contains('open')) {
                loadRegistryList();
                loadFilterPreferences();
            }
        });
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
    }
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            applyRegistryFilters();
            saveFilterPreferences();
        });
    }
    if (addToggleBtn && addForm) {
        addToggleBtn.addEventListener('click', () => {
            addForm.classList.toggle('hidden');
        });
    }
    if (addForm) {
        addForm.addEventListener('submit', handleAddSailorSubmit);
    }
    
    // New registry controls
    const classFilter = document.getElementById('classFilter');
    const sortOrder = document.getElementById('sortOrder');
    const btnClearRegistry = document.getElementById('btnClearRegistry');
    const btnResetFinishSheet = document.getElementById('btnResetFinishSheet');
    
    // Load saved filter/sort preferences from localStorage
    function loadFilterPreferences() {
        if (classFilter) {
            const savedClass = localStorage.getItem('registry_class_filter') || '';
            if (savedClass) classFilter.value = savedClass;
        }
        if (sortOrder) {
            const savedSort = localStorage.getItem('registry_sort_order') || '';
            if (savedSort) sortOrder.value = savedSort;
        }
        if (searchInput) {
            const savedSearch = localStorage.getItem('registry_search_query') || '';
            if (savedSearch) searchInput.value = savedSearch;
        }
    }
    
    function saveFilterPreferences() {
        if (classFilter) localStorage.setItem('registry_class_filter', classFilter.value);
        if (sortOrder) localStorage.setItem('registry_sort_order', sortOrder.value);
        if (searchInput) localStorage.setItem('registry_search_query', searchInput.value);
    }
    
    // Populate class filter dropdown
    if (classFilter) {
        const response = await fetch('/api/sailors-registry');
        const data = await response.json();
        if (data.status === 'success' && data.sailors) {
            const allClasses = [...new Set(
                data.sailors.map(s => s.boat_class).filter(c => c && c.trim())
            )].sort();
            
            allClasses.forEach(cls => {
                const option = document.createElement('option');
                option.value = cls;
                option.textContent = cls;
                classFilter.appendChild(option);
            });
        }
        classFilter.addEventListener('change', () => {
            applyRegistryFilters();
            saveFilterPreferences();
        });
    }
    
    if (sortOrder) {
        sortOrder.addEventListener('change', () => {
            applyRegistryFilters();
            saveFilterPreferences();
        });
    }
    
    // Clear All Checkboxes button
    if (btnClearRegistry) {
        btnClearRegistry.addEventListener('click', () => {
            fetch('/api/clear-registry', { method: 'POST' })
                .then(res => {
                    if (res.ok) {
                        loadRegistryList();
                        loadAndRenderSailors();
                        // Reapply filters after clearing registry
                        setTimeout(applyRegistryFilters, 100);
                    }
                });
        });
    }
    
    // Reset Finish Sheet button
    if (btnResetFinishSheet) {
        btnResetFinishSheet.addEventListener('click', () => {
            if (!confirm('Reset the finish sheet?\nThe sheet will be cleared and made ready for the next race.\nRecorded results are kept in the database.')) return;
            fetch('/api/reset-finish-sheet', { method: 'POST' })
                .then(res => {
                    if (res.ok) {
                        loadRegistryList();
                        loadAndRenderSailors();
                        // Reapply filters after resetting finish sheet
                        setTimeout(applyRegistryFilters, 100);
                    } else {
                        res.json().then(d => alert(d.message || 'Reset failed')).catch(() => {});
                    }
                });
        });
    }
    
    await loadRegistryList();
}

async function loadRegistryList() {
    try {
        const response = await fetch('/api/sailors-registry');
        const data = await response.json();
        if (data.status !== 'success') return;
        
        state.registry_sailors = data.sailors;
        renderRegistryList(data.sailors);
        // Reapply filters after loading registry
        setTimeout(applyRegistryFilters, 50);
    } catch (error) {
        console.error("Error loading registry:", error);
    }
}

function renderRegistryList(sailors) {
    const listEl = document.getElementById('registry-list');
    if (!listEl) return;
    listEl.innerHTML = '';
    
    if (sailors.length === 0) {
        listEl.innerHTML = '<div class="empty-msg">No sailors in registry yet.</div>';
        return;
    }
    
    sailors.forEach(sailor => {
        const row = document.createElement('div');
        row.className = 'sailor-row-item' + (sailor.racing_today ? ' signed-on' : '');
        row.dataset.uid = sailor.uid;
        row.dataset.searchText = `${sailor.short_name} ${sailor.sailor_name} ${sailor.sail_no} ${sailor.boat_class}`.toLowerCase();
        row.dataset.boatClass = sailor.boat_class || '';
        row.dataset.shortName = sailor.short_name || '';
        row.dataset.sailorName = sailor.sailor_name || '';
        row.dataset.sailNo = sailor.sail_no || '';
        
        row.innerHTML = `
            <label class="racing-toggle-label">
                <input type="checkbox" class="racing-checkbox" ${sailor.racing_today ? 'checked' : ''}>
                <span class="racing-tick"></span>
            </label>
            <div class="sailor-info">
                <div class="sailor-primary">${sailor.short_name} <span class="sailor-sail">#${sailor.sail_no}</span></div>
                <div class="sailor-class">${sailor.boat_class}</div>
            </div>
            <button class="btn-edit-sailor" title="Edit">✎</button>
        `;
        
        row.querySelector('.racing-checkbox').addEventListener('change', (e) => {
            toggleRacingToday(sailor.uid, e.target.checked, row);
        });
        row.querySelector('.btn-edit-sailor').addEventListener('click', () => openEditSailorModal(sailor));
        
        listEl.appendChild(row);
    });
}

function filterRegistryList(query) {
    // Fallback for existing calls - just apply the query filter
    applyRegistryFilters();
}

// Combined filter and sort function for registry list
function applyRegistryFilters() {
    const searchInput = document.getElementById('registry-search');
    const classFilter = document.getElementById('classFilter');
    const sortOrder = document.getElementById('sortOrder');
    
    const searchQuery = searchInput?.value.toLowerCase().trim() || "";
    const selectedClass = classFilter?.value || "";
    const sortBy = sortOrder?.value || "";
    
    const rows = document.querySelectorAll('.sailor-row-item');
    const visibleRows = [];
    
    rows.forEach(row => {
        const text = row.dataset.searchText || row.textContent.toLowerCase();
        const className = row.dataset.boatClass?.toLowerCase() || 
                        (row.querySelector('.sailor-class')?.textContent || "").toLowerCase();
        
        const matchesSearch = !searchQuery || text.includes(searchQuery);
        const matchesClass = !selectedClass || className === selectedClass.toLowerCase();
        
        if (matchesSearch && matchesClass) {
            visibleRows.push(row);
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
    
    // Sort: sailors checked as racing today DROP TO THE BOTTOM of the list so
    // sailors still to sign on stay at the top (RO hotfix 2026-10-16). The chosen
    // sort order applies within each group; the default order keeps the
    // registry's original order within each group.
    if (visibleRows.length > 0) {
        const signedRank = r => r.classList.contains('signed-on') ? 1 : 0;
        const byCriterion = (a, b) => {
            if (sortBy === "name") {
                const nameA = (a.dataset.shortName || a.dataset.sailorName || a.querySelector('.sailor-primary')?.textContent || "").toLowerCase();
                const nameB = (b.dataset.shortName || b.dataset.sailorName || b.querySelector('.sailor-primary')?.textContent || "").toLowerCase();
                return nameA.localeCompare(nameB);
            } else if (sortBy === "sailno") {
                const sailA = (a.dataset.sailNo || a.querySelector('.sailor-sail')?.textContent || "").replace(/[^\d]/g, '').toLowerCase();
                const sailB = (b.dataset.sailNo || b.querySelector('.sailor-sail')?.textContent || "").replace(/[^\d]/g, '').toLowerCase();
                return sailA.localeCompare(sailB);
            } else if (sortBy === "class") {
                const classA = (a.dataset.boatClass || "").toLowerCase();
                const classB = (b.dataset.boatClass || "").toLowerCase();
                const cmp = classA.localeCompare(classB);
                if (cmp !== 0) return cmp;
                const nameA = (a.dataset.shortName || "").toLowerCase();
                const nameB = (b.dataset.shortName || "").toLowerCase();
                return nameA.localeCompare(nameB);
            }
            return 0;
        };
        visibleRows.sort((a, b) => signedRank(a) - signedRank(b) || byCriterion(a, b));
        
        // Re-append sorted rows to maintain visibility
        const container = document.getElementById('registry-list');
        if (container) {
            visibleRows.forEach(row => container.appendChild(row));
        }
    }
}

async function toggleRacingToday(uid, checked, row) {
    try {
        const response = await fetch('/api/toggle-racing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uid, racing_today: checked })
        });
        const data = await response.json();
        if (data.status === 'success') {
            row.classList.toggle('signed-on', checked);
            // Bug 35: a tick is a deliberate sign-on action - the columns must
            // refresh NOW, even mid-race (late sign-ons must be visible, bug 14)
            // and after End Race (preparing the next race of the day).
            loadAndRenderSailors();
            // Reapply filters to ensure row visibility is maintained
            applyRegistryFilters();
        }
    } catch (error) {
        console.error("Error toggling racing_today:", error);
    }
}

async function handleAddSailorSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const payload = {
        uid: form.querySelector('[name="uid"]').value.trim(),
        sailor_name: form.querySelector('[name="sailor_name"]').value.trim(),
        short_name: form.querySelector('[name="short_name"]').value.trim(),
        sail_no: form.querySelector('[name="sail_no"]').value.trim(),
        boat_class: form.querySelector('[name="boat_class"]').value.trim(),
        handicap: parseFloat(form.querySelector('[name="handicap"]').value) || 1.0,
        seed: parseInt(form.querySelector('[name="seed"]').value) || 0
    };
    
    try {
        const response = await fetch('/api/add-sailor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.status === 'success') {
            form.reset();
            document.getElementById('add-sailor-form').classList.add('hidden');
            // Clear saved filters so the new sailor is immediately visible:
            // a stale search filter previously hid the new row, the RO retried,
            // and the retry failed on the duplicate sail number.
            const searchInput = document.getElementById('registry-search');
            if (searchInput) { searchInput.value = ''; localStorage.setItem('registry_search_query', ''); }
            const classFilterEl = document.getElementById('classFilter');
            if (classFilterEl) { classFilterEl.value = ''; localStorage.setItem('registry_class_filter', ''); }
            await loadRegistryList();
        } else {
            alert(data.message || 'Could not add sailor.');
        }
    } catch (error) {
        console.error("Error adding sailor:", error);
    }
}

function openEditSailorModal(sailor) {
    const existing = document.querySelector('.modal-overlay');
    if (existing) existing.remove();
    
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal-box">
            <div class="modal-header">
                <h3>Edit Sailor</h3>
                <button class="close-btn" id="modal-close">✕</button>
            </div>
            <div class="modal-body">
                <div class="form-group"><label>UID</label><input type="text" value="${sailor.uid}" readonly></div>
                <div class="form-group"><label>Sailor Name</label><input type="text" id="edit-sailor-name" value="${sailor.sailor_name}"></div>
                <div class="form-group"><label>Short Name</label><input type="text" id="edit-short-name" value="${sailor.short_name}"></div>
                <div class="form-group"><label>Sail No</label><input type="text" id="edit-sail-no" value="${sailor.sail_no}"></div>
                <div class="form-group"><label>Boat Class</label><input type="text" id="edit-boat-class" value="${sailor.boat_class}"></div>
                <div class="form-group"><label>Handicap</label><input type="number" step="0.01" id="edit-handicap" value="${sailor.handicap}"></div>
                <div class="form-group"><label>Seed</label><input type="number" id="edit-seed" value="${sailor.seed}"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-submit" id="modal-save">Save</button>
                <button class="btn-delete" id="modal-delete">Delete</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    
    overlay.querySelector('#modal-close').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#modal-save').addEventListener('click', async () => {
        const payload = {
            sailor_name: overlay.querySelector('#edit-sailor-name').value.trim(),
            short_name: overlay.querySelector('#edit-short-name').value.trim(),
            sail_no: overlay.querySelector('#edit-sail-no').value.trim(),
            boat_class: overlay.querySelector('#edit-boat-class').value.trim(),
            handicap: parseFloat(overlay.querySelector('#edit-handicap').value) || 1.0,
            seed: parseInt(overlay.querySelector('#edit-seed').value) || 0
        };
        try {
            const response = await fetch(`/api/edit-sailor/${sailor.uid}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.status === 'success') {
                overlay.remove();
                await loadRegistryList();
                loadAndRenderSailors();
            } else {
                alert(data.message || 'Could not save changes.');
            }
        } catch (error) {
            console.error("Error saving sailor:", error);
        }
    });
    overlay.querySelector('#modal-delete').addEventListener('click', async () => {
        if (!confirm(`Delete sailor ${sailor.short_name}? This cannot be undone.`)) return;
        try {
            const response = await fetch(`/api/delete-sailor/${sailor.uid}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.status === 'success') {
                overlay.remove();
                await loadRegistryList();
                loadAndRenderSailors();
            }
        } catch (error) {
            console.error("Error deleting sailor:", error);
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initFinishSheet);
