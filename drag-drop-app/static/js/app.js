// app.js - Fresh build matching current index.html structure
const state = { isRunning: false, raceStartTime: null, sequence: [], masterStartTime: "11:30" };

// Refresh Sailwave data from boat_master.json
async function refreshSailwaveData() {
    const btn = document.getElementById('btn-refresh-sailwave');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '\ud83d\udd04 Refreshing...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/refresh-sailwave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert(`Sailwave refresh successful!\n\n` +
                  `Classes: ${data.imported.classes_new || 0} new, ${data.imported.classes_updated || 0} updated\n` +
                  `Sailors: ${data.imported.sailors_new || 0} new, ${data.imported.sailors_updated || 0} updated\n` +
                  `Total: ${data.imported.total_sailors || 0} sailors in database`);
        } else {
            alert(`Refresh failed: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Refresh failed: ${error.message}`);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Add refresh button handler
    const refreshBtn = document.getElementById('btn-refresh-sailwave');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshSailwaveData);
    }
    
    document.querySelectorAll('.library-card').forEach(card => {
        card.addEventListener('dragstart', e => {
            if (state.isRunning) { e.preventDefault(); return; }
            e.dataTransfer.effectAllowed = 'copy';
            e.dataTransfer.setData('card-data', JSON.stringify({
                label: card.dataset.label, flag: card.dataset.flag, minutes: parseInt(card.dataset.minutes) || 5
            }));
        });
    });

    document.querySelectorAll('.flag-drop-zone').forEach(zone => {
        zone.addEventListener('dragover', e => {
            if (state.isRunning) return;
            e.preventDefault();
            zone.style.backgroundColor = '#e8f5e9';
            zone.style.borderColor = '#4caf50';
        });
        zone.addEventListener('dragleave', e => {
            if (e.target === zone) {
                zone.style.backgroundColor = '#ffffff';
                zone.style.borderColor = '#bbb';
            }
        });
        zone.addEventListener('drop', e => {
            e.preventDefault();
            if (state.isRunning) return;
            zone.style.backgroundColor = '#ffffff';
            zone.style.borderColor = '#bbb';
            const data = JSON.parse(e.dataTransfer.getData('card-data'));
            const gridIndex = zone.dataset.gridIndex || 1;
            const rowId = 'row_' + Date.now();
            const row = createRow(rowId, data, gridIndex);
            zone.appendChild(row);
            state.sequence.push({
                id: rowId, label: data.label, flag_image: data.flag, secondary_flag_image: null,
                countdown_minutes: data.minutes, status: 'PENDING', grid_index: parseInt(gridIndex),
                current_remaining_seconds: data.minutes * 60
            });
            syncToServer();
        });
    });

    document.getElementById('btn-start').addEventListener('click', () => {
        if (state.isRunning || state.sequence.length === 0) return;
        state.isRunning = true;
        state.raceStartTime = Date.now();
        state.sequence[0].status = 'ACTIVE';
        state.sequence[0].grid_index = state.sequence[0].grid_index || 1;
        syncToServer();
        fetch('/update-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active_id: state.sequence[0].id, grid_index: state.sequence[0].grid_index })
        }).catch(console.error);
        fetch('/execute-control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'START' })
        }).catch(console.error);
        updateStatusBadge('RUNNING');
        lockUI(true);
    });

    document.getElementById('btn-stop').addEventListener('click', () => {
        state.isRunning = false;
        lockUI(false);
        fetch('/execute-control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'STOP' }) }).catch(console.error);
        updateStatusBadge('PAUSED');
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
        state.isRunning = false;
        state.raceStartTime = null;
        state.sequence.forEach(s => { s.status = 'PENDING'; s.current_remaining_seconds = s.countdown_minutes * 60; });
        document.querySelectorAll('.event-row').forEach(row => {
            row.className = 'event-row state-pending';
            const d = row.querySelector('.live-countdown-display');
            if (d) d.textContent = '00:00';
        });
        document.querySelectorAll('.grid-timer').forEach(t => t.textContent = '00:00');
        document.getElementById('race-duration-display').textContent = '00:00:00';
        lockUI(false);
        fetch('/execute-control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'RESET' }) }).catch(console.error);
        fetch('/api/reset-race', { method: 'POST' }).catch(console.error);
        updateStatusBadge('READY');
    });

    document.getElementById('btn-end-race').addEventListener('click', () => {
        state.isRunning = false;
        lockUI(false);
        fetch('/execute-control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'END_RACE' }) }).catch(console.error);
        fetch('/api/end-race', { method: 'POST' }).catch(console.error);
        updateStatusBadge('ENDED');
    });

    document.getElementById('master-start-input').addEventListener('change', e => { state.masterStartTime = e.target.value; });

    // Display mode toggle buttons
    document.getElementById('btn-mode-flags').addEventListener('click', () => setDisplayMode('flags'));
    document.getElementById('btn-mode-both').addEventListener('click', () => setDisplayMode('both'));
    document.getElementById('btn-mode-number').addEventListener('click', () => setDisplayMode('number'));

    updateClock();
    setInterval(updateClock, 1000);
    setInterval(updateCountdown, 100);
    setInterval(syncRaceDurationFromServer, 1000);
    syncRaceDurationFromServer();
});

/**
 * Sync the RACE DURATION display from the server's authoritative elapsed-time endpoint
 * (same source Finish Sheet uses). This keeps both pages showing the same time and
 * ensures the duration survives page reloads/navigation and freezes correctly at race end.
 */
function syncRaceDurationFromServer() {
    fetch('/api/get-elapsed-time').then(r => r.json()).then(data => {
        if (data.status === 'success') {
            const totalSeconds = data.elapsed_seconds;
            const hh = Math.floor(totalSeconds / 3600);
            const mm = Math.floor((totalSeconds % 3600) / 60);
            const ss = totalSeconds % 60;
            document.getElementById('race-duration-display').textContent =
                `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
        }
    }).catch(() => {});
}

function setDisplayMode(mode) {
    fetch('/set-display-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    }).then(r => r.json()).then(data => {
        if (data.status === 'success') {
            document.querySelectorAll('.btn-mode').forEach(b => b.classList.remove('active'));
            document.getElementById(`btn-mode-${mode}`).classList.add('active');
        }
    }).catch(console.error);
}

function createRow(rowId, data, gridIndex) {
    const row = document.createElement('div');
    row.id = rowId;
    row.className = 'event-row state-pending';
    row.dataset.rowId = rowId;
    row.draggable = true;
    row.innerHTML = `
        <div class="event-row-col col-primary-flag">
            <div class="drag-handle">⋮⋮</div>
            <div class="flag-preview-box">
                <img src="/static/flags/${data.flag}" alt="${data.label}" style="width: 40px; height: 35px; object-fit: contain;">
            </div>
        </div>
        <div class="event-row-col col-secondary-flag">
            <div class="secondary-flag-box" data-row-id="${rowId}" draggable="false" style="width: 50px; height: 40px; background: #ddd; border: 2px dashed #999; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #666; cursor: copy;">
                <span>+Flag</span>
            </div>
        </div>
        <div class="event-row-col col-metadata">
            <div class="class-label">${data.label}</div>
            <div class="status-badge">state-pending</div>
        </div>
        <div class="event-row-col col-timer">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="live-countdown-display" style="font-family: monospace; font-size: 20px; font-weight: bold; color: #f59e0b; min-width: 50px;">00:00</div>
                <div style="display: flex; flex-direction: column; gap: 3px;">
                    <input type="number" class="minutes-editor" value="${data.minutes}" min="1" data-row-id="${rowId}" style="width: 50px; padding: 4px; font-size: 12px;">
                    <span style="font-size: 11px; color: #94a3b8;">mins</span>
                </div>
            </div>
            <button class="btn-remove-card" data-row-id="${rowId}" style="position: absolute; right: 0; top: 50%; transform: translateY(-50%); background: none; border: none; color: #ef4444; font-size: 20px; cursor: pointer; opacity: 0.7;">✕</button>
        </div>
    `;
    row.querySelector('.minutes-editor').addEventListener('change', e => {
        let m = parseInt(e.target.value);
        if (m < 1 || isNaN(m)) { m = 1; e.target.value = 1; }
        const item = state.sequence.find(s => s.id === rowId);
        if (item) { item.countdown_minutes = m; item.current_remaining_seconds = m * 60; }
    });
    row.querySelector('.btn-remove-card').addEventListener('click', () => {
        if (state.isRunning) return;
        row.remove();
        state.sequence = state.sequence.filter(s => s.id !== rowId);
        syncToServer();
    });

    // Secondary flag box drop handler
    const box = row.querySelector('.secondary-flag-box');
    box.addEventListener('dragover', e => { 
        e.preventDefault(); 
        e.stopPropagation();
        e.dataTransfer.dropEffect = 'copy'; 
        box.style.backgroundColor = '#90caf9';
        box.style.borderColor = '#1976d2';
    });
    box.addEventListener('dragleave', e => { 
        e.stopPropagation();
        box.style.backgroundColor = '#ddd';
        box.style.borderColor = '#999';
    });
    box.addEventListener('drop', e => {
        e.preventDefault();
        e.stopPropagation();
        box.style.backgroundColor = '#ddd';
        box.style.borderColor = '#999';
        try {
            const cardData = e.dataTransfer.getData('card-data');
            if (!cardData) {
                console.warn('No card data in drop');
                return;
            }
            const d = JSON.parse(cardData);
            const item = state.sequence.find(s => s.id === rowId);
            if (item) { 
                item.secondary_flag_image = d.flag; 
                box.innerHTML = `<img src="/static/flags/${d.flag}" alt="Secondary" style="width: 40px; height: 35px; object-fit: contain;">`; 
                syncToServer(); 
            }
        } catch (err) {
            console.error('Secondary flag drop failed:', err);
        }
    });

    row.addEventListener('dragstart', e => {
        if (state.isRunning) { e.preventDefault(); return; }
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('reorder-row', rowId);
    });
    row.addEventListener('dragover', e => { if (state.isRunning) return; e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
    row.addEventListener('drop', e => {
        if (state.isRunning) return;
        e.preventDefault();
        const sr = e.dataTransfer.getData('reorder-row');
        if (sr) { const srow = document.getElementById(sr); if (srow && srow.parentNode === row.parentNode) { row.parentNode.insertBefore(srow, row); syncToServer(); } }
    });
    return row;
}

function updateCountdown() {
    if (!state.isRunning || !state.raceStartTime) return;
    const e = Math.floor((Date.now() - state.raceStartTime) / 1000);
    let hasAnyActive = false;
    
    // SEQUENTIAL across grids: Start 1's rows run first, then Start 2's rows begin
    // only once Start 1 is fully complete. Single shared cumulative clock, ordered
    // by grid_index (grid 1 before grid 2), preserving each grid's internal row order.
    const orderedSequence = state.sequence.slice().sort((a, b) => (a.grid_index || 1) - (b.grid_index || 1));
    
    let cum = 0;
    orderedSequence.forEach(it => {
        const dur = it.countdown_minutes * 60, start = cum, end = cum + dur, rem = Math.max(0, end - e);
        const os = it.status;
        it.status = e < start ? 'PENDING' : e < end ? 'ACTIVE' : 'CLEAR';
        it.current_remaining_seconds = it.status === 'PENDING' ? dur : it.status === 'ACTIVE' ? rem : 0;
        if (it.status === 'ACTIVE' || it.status === 'PENDING') hasAnyActive = true;
        if (os !== 'ACTIVE' && it.status === 'ACTIVE') {
            fetch('/update-status', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active_id: it.id, grid_index: it.grid_index }) }).catch(console.error);
        }
        if (os !== 'CLEAR' && it.status === 'CLEAR') {
            // Countdown hit 00:00 for this flag's class -> notify Finish Sheet.
            // If a secondary flag is also present (multiple classes starting in the same slot),
            // fire a class-start for that class too.
            fetch('/api/class-start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ flag_image: it.flag_image }) }).catch(console.error);
            if (it.secondary_flag_image) {
                fetch('/api/class-start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ flag_image: it.secondary_flag_image }) }).catch(console.error);
            }
        }
        const re = document.getElementById(it.id);
        if (re) {
            re.className = `event-row state-${it.status.toLowerCase()}`;
            const de = re.querySelector('.live-countdown-display');
            if (de) { const mm = Math.floor(it.current_remaining_seconds / 60), ss = it.current_remaining_seconds % 60; de.textContent = `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`; }
        }
        cum = end;
    });
    
    // Per-grid "Total Countdown" display: time remaining until that grid's own rows
    // are all complete, accounting for the wait while earlier grids are still running.
    const grids = {}; orderedSequence.forEach(it => { const g = it.grid_index || 1; if (!grids[g]) grids[g] = []; grids[g].push(it); });
    let ag = null, at = 0;
    Object.entries(grids).forEach(([gi, rs]) => {
        let tot = 0, hap = false;
        rs.forEach(r => { if (r.status === 'ACTIVE' || r.status === 'PENDING') { tot += r.current_remaining_seconds || r.countdown_minutes * 60; hap = true; } });
        const te = document.getElementById(`timer-grid-${gi}`);
        if (te) { const mm = Math.floor(tot / 60), ss = tot % 60; te.textContent = `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`; }
        if (hap && ag === null) { ag = parseInt(gi); at = Math.max(0, Math.ceil(tot / 60)); }
    });
    if (hasAnyActive && ag !== null) {
        fetch('/update-status', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ grid_index: ag }) }).catch(console.error);
        fetch('/update-live-timer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ live_timer: String(at) }) }).catch(console.error);
    } else if (!hasAnyActive) {
        fetch('/update-live-timer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ live_timer: '0' }) }).catch(console.error);
    }
}

function updateClock() {
    const n = new Date(), hh = String(n.getHours()).padStart(2, '0'), mm = String(n.getMinutes()).padStart(2, '0'), ss = String(n.getSeconds()).padStart(2, '0');
    document.getElementById('live-system-clock').textContent = `${hh}:${mm}:${ss}`;
}

function updateStatusBadge(st) {
    const b = document.getElementById('global-status-badge');
    b.textContent = `STATE: ${st}`;
    b.className = `badge status-${st.toLowerCase()}`;
}

function lockUI(lk) {
    document.querySelectorAll('.flag-drop-zone').forEach(z => { z.style.pointerEvents = lk ? 'none' : 'auto'; z.style.opacity = lk ? '0.6' : '1'; });
    document.querySelectorAll('.event-row').forEach(r => {
        const h = r.querySelector('.drag-handle'), rb = r.querySelector('.btn-remove-card'), ri = r.querySelector('.minutes-editor');
        if (h) { h.style.opacity = lk ? '0.3' : '1'; h.style.cursor = lk ? 'not-allowed' : 'row-resize'; }
        if (rb) { rb.style.opacity = lk ? '0.3' : '0.7'; rb.disabled = lk; }
        if (ri) { ri.disabled = lk; ri.style.cursor = lk ? 'not-allowed' : 'text'; }
        r.draggable = !lk;
    });
}

function syncToServer() {
    const seq = Array.from(document.querySelectorAll('.event-row')).map(r => state.sequence.find(s => s.id === r.dataset.rowId)).filter(Boolean);
    fetch('/update-sequence', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sequence: seq }) }).catch(console.error);
}
