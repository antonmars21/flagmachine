// finishsheet.js - Finish Sheet UI Logic
// Handles sailor display, lap tallying, finish marking, and manual reordering

const state = {
    race_id: null,
    race_active: false,
    columns: [],
    start_time: null,
    drag_source: null
};

/**
 * Refresh Sailwave data from boat_master.json
 */
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
            // Refresh the registry list
            await loadRegistryList();
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

/**
 * Initialize the finish sheet on page load
 */
async function initFinishSheet() {
    console.log("Initializing Finish Sheet...");
    
    // Fetch sailors and render columns
    await loadAndRenderSailors();
    
    // Set up event listeners
    document.getElementById('btn-start-race').addEventListener('click', startRace);
    document.getElementById('btn-end-race').addEventListener('click', endRace);
    document.getElementById('btn-export-csv').addEventListener('click', exportRaceCsv);
    
    // Add refresh button handler
    const refreshBtn = document.getElementById('btn-refresh-sailwave');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshSailwaveData);
    }
    
    // Update elapsed time every second
    setInterval(updateElapsedTime, 1000);
    
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
        const response = await fetch('/api/sailors-for-onwater');
        const data = await response.json();
        
        if (data.status !== 'success') {
            console.error("Failed to load sailors:", data.message);
            return;
        }
        
        state.columns = data.columns;
        renderColumns(data.columns);
    } catch (error) {
        console.error("Error loading sailors:", error);
    }
}

/**
 * Render dynamic columns: one per boat class in the current Start Sequence
 * (ordered by sailor count, most on the left), plus a trailing Open Category column.
 */
function renderColumns(columns) {
    const wrapper = document.getElementById('columns-wrapper');
    wrapper.innerHTML = '';
    
    if (!columns || columns.length === 0) {
        wrapper.innerHTML = '<div style="padding: 40px; text-align: center; color: #94a3b8; grid-column: 1/-1;">No classes in the Start Sequence yet. Drop flags into the Flag Machine to populate columns.</div>';
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
        header.innerHTML = `
            <div class="column-title" style="color: ${colData.color_hex || '#f8fafc'}">${colData.class_name}</div>
            <div class="column-count">${sailors.length} sailors</div>
        `;
        column_div.appendChild(header);
        
        const list = document.createElement('div');
        list.className = 'sailors-list';
        list.dataset.column = col_num;
        
        sailors.forEach((sailor, index) => {
            const card = createSailorCard(sailor, col_num, index);
            list.appendChild(card);
        });
        resortColumn(list);
        
        column_div.appendChild(list);
        wrapper.appendChild(column_div);
    });
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
    card.dataset.seed = sailor.seed != null ? sailor.seed : 9999;
    card.dataset.lapCount = sailor.lap_count || 0;
    card.dataset.finishTime = sailor.finish_time || '';
    card.dataset.manualOverride = 'false';
    card.draggable = true;
    
    const finished_class = sailor.finish_time ? ' (Finished)' : '';
    const class_started = !!sailor.class_started;
    if (class_started) card.classList.add('class-started');
    
    card.innerHTML = `
        <div class="sailor-header">
            <span class="sail-number">${sailor.sail_no}</span>
            <span class="sailor-class">${sailor.boat_class}</span>
        </div>
        <div class="sailor-nickname">${sailor.short_name}${finished_class}</div>
        <div class="sailor-controls">
            <div class="lap-counter">
                <button class="btn-lap" data-action="lap" data-uid="${sailor.uid}" ${class_started ? '' : 'disabled'}>+ Lap</button>
                <div class="lap-value">${sailor.lap_count || 0}</div>
            </div>
            <input type="checkbox" class="finish-checkbox" data-uid="${sailor.uid}" 
                ${sailor.finish_time ? 'checked disabled' : (class_started ? '' : 'disabled')}>
        </div>
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
 * Comparator for auto-sorting non-manual, unfinished cards: lap_count desc, then seed asc.
 */
function compareByLapThenSeed(a, b) {
    const lapDiff = (parseInt(b.dataset.lapCount) || 0) - (parseInt(a.dataset.lapCount) || 0);
    if (lapDiff !== 0) return lapDiff;
    return (parseInt(a.dataset.seed) || 9999) - (parseInt(b.dataset.seed) || 9999);
}

/**
 * Re-sort a sailor list column:
 * - Finished sailors always drop to the bottom, ordered by finish time (first finisher on top of the finished group).
 * - Unfinished sailors are ordered by lap count (desc), then seed (asc) as tie-break.
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
    const autoCards = unfinished.filter(c => c.dataset.manualOverride !== 'true').sort(compareByLapThenSeed);
    
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
            body: JSON.stringify({ uid })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Update UI
            const lapValue = card.querySelector('.lap-value');
            lapValue.textContent = data.lap_count;
            card.dataset.lapCount = data.lap_count;
            
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
            body: JSON.stringify({ uid })
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
        state.race_active = !!data.race_id;
        state.race_ended = !!data.race_ended;
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
            const started = classId && startedClassIds.has(classId);
            
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
        
        if (state.race_active) {
            document.getElementById('btn-start-race').disabled = true;
            document.getElementById('btn-end-race').disabled = false;
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
 * End the race - stops all timers, records end time, disables lap/finish inputs.
 */
async function endRace() {
    try {
        const response = await fetch('/api/end-race', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            state.race_active = false;
            state.race_ended = true;
            
            document.getElementById('btn-start-race').disabled = true;
            document.getElementById('btn-end-race').disabled = true;
            
            // Disable all lap buttons and finish checkboxes
            document.querySelectorAll('.btn-lap').forEach(btn => btn.disabled = true);
            document.querySelectorAll('.finish-checkbox').forEach(cb => {
                if (!cb.checked) cb.disabled = true;
            });
            
            console.log(`Race ended at ${data.race_end_timestamp}`);
        } else {
            alert(data.message || 'Could not end race.');
        }
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
            if (sidebar.classList.contains('open')) loadRegistryList();
        });
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
    }
    if (searchInput) {
        searchInput.addEventListener('input', () => filterRegistryList(searchInput.value));
    }
    if (addToggleBtn && addForm) {
        addToggleBtn.addEventListener('click', () => {
            addForm.classList.toggle('hidden');
        });
    }
    if (addForm) {
        addForm.addEventListener('submit', handleAddSailorSubmit);
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
    const q = query.trim().toLowerCase();
    document.querySelectorAll('.sailor-row-item').forEach(row => {
        row.style.display = row.dataset.searchText.includes(q) ? '' : 'none';
    });
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
            // Refresh the dynamic columns since fleet selection changed
            if (!state.race_active) loadAndRenderSailors();
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
                if (!state.race_active) loadAndRenderSailors();
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
                if (!state.race_active) loadAndRenderSailors();
            }
        } catch (error) {
            console.error("Error deleting sailor:", error);
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initFinishSheet);
