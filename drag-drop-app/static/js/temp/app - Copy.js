// static/js/app.js - Flag Machine Control Panel

// ============================================================================
// STATE & GLOBALS
// ============================================================================
let app_state = {
    sequence: [],
    master_start_time: "11:30",
    status: "READY"
};

let draggedCard = null;
let dragSource = null;

// ============================================================================
// DOM REFERENCES
// ============================================================================
const masterStartInput = document.getElementById('master-start-input');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnReset = document.getElementById('btn-reset');
const btnEndRace = document.getElementById('btn-end-race');
const globalStatusBadge = document.getElementById('global-status-badge');
const liveClock = document.getElementById('live-system-clock');
const raceDurationDisplay = document.getElementById('race-duration-display');
const libraryCards = document.querySelectorAll('.library-card');
const dropZones = document.querySelectorAll('.flag-drop-zone');

// ============================================================================
// INITIALIZATION
// ============================================================================
function init() {
    attachLibraryCardDragListeners();
    attachDropZoneListeners();
    attachControlButtonListeners();
    updateLiveClock();
    setInterval(updateLiveClock, 1000);
}

// ============================================================================
// DRAG & DROP: Library Cards → Drop Zones
// ============================================================================
function attachLibraryCardDragListeners() {
    const cards = document.querySelectorAll('.library-card');
    cards.forEach(card => {
        card.addEventListener('dragstart', onLibraryCardDragStart);
        card.addEventListener('dragend', onLibraryCardDragEnd);
    });
}

function onLibraryCardDragStart(e) {
    draggedCard = {
        label: this.dataset.label,
        flag: this.dataset.flag,
        minutes: parseInt(this.dataset.minutes) || 5
    };
    dragSource = 'library';
    this.style.opacity = '0.5';
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('text/html', this.innerHTML);
}

function onLibraryCardDragEnd(e) {
    this.style.opacity = '1';
    draggedCard = null;
    dragSource = null;
}

// ============================================================================
// DRAG & DROP: Drop Zones
// ============================================================================
function attachDropZoneListeners() {
    dropZones.forEach(zone => {
        zone.addEventListener('dragover', onDropZoneDragOver);
        zone.addEventListener('dragleave', onDropZoneDragLeave);
        zone.addEventListener('drop', onDropZoneDrop);
    });
}

function onDropZoneDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    this.style.backgroundColor = '#e8f5e9';
    this.style.borderColor = '#4caf50';
}

function onDropZoneDragLeave(e) {
    if (e.target === this) {
        this.style.backgroundColor = '#ffffff';
        this.style.borderColor = '#bbb';
    }
}

function onDropZoneDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    this.style.backgroundColor = '#ffffff';
    this.style.borderColor = '#bbb';

    if (!draggedCard) return;

    const gridIndex = this.dataset.gridIndex || 1;
    
    // Create new row element
    const rowId = `row_${Date.now()}`;
    const newRow = createEventRow(rowId, draggedCard, gridIndex);
    
    // Append to drop zone
    this.appendChild(newRow);
    
    // Update backend sequence
    app_state.sequence.push({
        id: rowId,
        label: draggedCard.label,
        flag_image: draggedCard.flag,
        countdown_minutes: draggedCard.minutes,
        status: "PENDING",
        grid_index: gridIndex
    });
    
    // Sync with server
    syncSequenceToServer();
}

// ============================================================================
// EVENT ROW CREATION
// ============================================================================
function createEventRow(rowId, cardData, gridIndex) {
    const row = document.createElement('div');
    row.id = rowId;
    row.className = 'event-row state-pending';
    row.dataset.rowId = rowId;
    row.draggable = true;
    
    row.innerHTML = `
        <div class="drag-handle">⋮⋮</div>
        <div class="flag-preview-box">
            <img src="/static/flags/${cardData.flag}" 
                 alt="${cardData.label}" 
                 style="width: 40px; height: 35px; object-fit: contain;">
            <div class="flag-filename-label">${cardData.flag}</div>
        </div>
        <div class="class-details">
            <div class="class-label">${cardData.label}</div>
            <div class="status-badge">state-pending</div>
        </div>
        <div style="display: flex; align-items: center; gap: 5px;">
            <input type="number" class="minutes-editor" value="${cardData.minutes}" 
                   data-row-id="${rowId}">
            <span class="unit-text">mins</span>
        </div>
        <button class="btn-remove-card" data-row-id="${rowId}">✕</button>
    `;
    
    // Attach event listeners
    const minutesInput = row.querySelector('.minutes-editor');
    minutesInput.addEventListener('change', onMinutesChange);
    
    const removeBtn = row.querySelector('.btn-remove-card');
    removeBtn.addEventListener('click', onRemoveCard);
    
    // Row reordering
    row.addEventListener('dragstart', onEventRowDragStart);
    row.addEventListener('dragover', onEventRowDragOver);
    row.addEventListener('drop', onEventRowDrop);
    row.addEventListener('dragend', onEventRowDragEnd);
    
    return row;
}

// ============================================================================
// ROW REORDERING WITHIN DROP ZONES
// ============================================================================
let draggedRow = null;

function onEventRowDragStart(e) {
    draggedRow = this;
    this.style.opacity = '0.5';
    e.dataTransfer.effectAllowed = 'move';
}

function onEventRowDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (this !== draggedRow) {
        this.style.borderTop = '3px solid #4caf50';
    }
}

function onEventRowDrop(e) {
    e.preventDefault();
    if (draggedRow && draggedRow !== this) {
        const parent = this.parentNode;
        if (parent === draggedRow.parentNode) {
            parent.insertBefore(draggedRow, this);
            syncSequenceToServer();
        }
    }
}

function onEventRowDragEnd(e) {
    this.style.opacity = '1';
    this.style.borderTop = 'none';
    draggedRow = null;
}

// ============================================================================
// EVENT HANDLERS
// ============================================================================
function onMinutesChange(e) {
    const rowId = e.target.dataset.rowId;
    const minutes = parseInt(e.target.value);
    
    // Update local state
    const item = app_state.sequence.find(s => s.id === rowId);
    if (item) item.countdown_minutes = minutes;
    
    // Sync with server
    fetch('/update-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_id: rowId, countdown_minutes: minutes })
    }).catch(err => console.error('Failed to update minutes:', err));
}

function onRemoveCard(e) {
    const rowId = e.currentTarget.dataset.rowId;
    const row = document.getElementById(rowId);
    if (row) {
        row.remove();
        app_state.sequence = app_state.sequence.filter(s => s.id !== rowId);
        syncSequenceToServer();
    }
}

// ============================================================================
// CONTROL BUTTONS
// ============================================================================
function attachControlButtonListeners() {
    btnStart.addEventListener('click', onStartClick);
    btnStop.addEventListener('click', onStopClick);
    btnReset.addEventListener('click', onResetClick);
    btnEndRace.addEventListener('click', onEndRaceClick);
    masterStartInput.addEventListener('change', onMasterStartTimeChange);
}

function onStartClick() {
    executeControl('START');
}

function onStopClick() {
    executeControl('STOP');
}

function onResetClick() {
    executeControl('RESET');
}

function onEndRaceClick() {
    executeControl('END_RACE');
}

function onMasterStartTimeChange(e) {
    fetch('/update-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ master_start_time: e.target.value })
    }).catch(err => console.error('Failed to update master start time:', err));
}

// ============================================================================
// CONTROL EXECUTION
// ============================================================================
function executeControl(action) {
    fetch('/execute-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
    })
    .then(r => r.json())
    .then(data => {
        app_state.status = data.current_state;
        updateStatusBadge();
    })
    .catch(err => console.error('Control execution failed:', err));
}

// ============================================================================
// UI UPDATES
// ============================================================================
function updateStatusBadge() {
    const badgeMap = {
        'READY': 'status-ready',
        'RUNNING': 'status-running',
        'PAUSED': 'status-running',
        'FINISHED': 'status-finished'
    };
    const className = badgeMap[app_state.status] || 'status-ready';
    globalStatusBadge.textContent = `STATE: ${app_state.status}`;
    globalStatusBadge.className = `badge ${className}`;
}

function updateLiveClock() {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    liveClock.textContent = `${hh}:${mm}:${ss}`;
}

// ============================================================================
// SERVER SYNC
// ============================================================================
function syncSequenceToServer() {
    // Extract ordered IDs from visible rows
    const orderedIds = Array.from(document.querySelectorAll('.event-row'))
        .map(row => row.dataset.rowId);
    
    fetch('/update-sequence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ordered_ids: orderedIds })
    }).catch(err => console.error('Failed to sync sequence:', err));
}

// ============================================================================
// START
// ============================================================================
document.addEventListener('DOMContentLoaded', init);
