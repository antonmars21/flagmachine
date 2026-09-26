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
            <div class="secondary-flag-box" data-row-id="${rowId}" style="width: 50px; height: 40px; background: #ddd; border: 2px dashed #999; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #666; cursor: cell; pointer-events: auto;">
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
    const box = row.querySelector('.secondary-flag-box');
    box.addEventListener('dragover', e => { e.preventDefault(); e.stopPropagation(); e.dataTransfer.dropEffect = 'copy'; box.style.backgroundColor = '#b3e5fc'; box.style.borderColor = '#0288d1'; });
    box.addEventListener('dragleave', e => { if(e.target === box) { box.style.backgroundColor = '#ddd'; box.style.borderColor = '#999'; } });
    box.addEventListener('drop', e => { e.preventDefault(); e.stopPropagation(); box.style.backgroundColor = '#ddd'; box.style.borderColor = '#999'; try { const d = JSON.parse(e.dataTransfer.getData('card-data')); const item = state.sequence.find(s => s.id === rowId); if (item && d && d.flag) { item.secondary_flag_image = d.flag; box.innerHTML = `<img src="/static/flags/${d.flag}" alt="Secondary" style="width: 40px; height: 35px; object-fit: contain;">`; syncToServer(); } } catch(err) { console.error('Secondary drop error:', err); } });
    row.addEventListener('dragstart', e => { if (state.isRunning) { e.preventDefault(); return; } e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('reorder-row', rowId); });
    row.addEventListener('dragover', e => { if (state.isRunning) return; e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
    row.addEventListener('drop', e => { if (state.isRunning) return; e.preventDefault(); const sr = e.dataTransfer.getData('reorder-row'); if (sr) { const srow = document.getElementById(sr); if (srow && srow.parentNode === row.parentNode) { row.parentNode.insertBefore(srow, row); syncToServer(); } } });
    return row;
}
