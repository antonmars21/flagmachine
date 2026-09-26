function updateCountdown() {
    if (!state.isRunning || !state.raceStartTime) return;
    const e = Math.floor((Date.now() - state.raceStartTime) / 1000);
    const h = Math.floor(e / 3600), m = Math.floor((e % 3600) / 60), s = e % 60;
    document.getElementById('race-duration-display').textContent = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    let cum = 0;
    state.sequence.forEach(it => {
        const dur = it.countdown_minutes * 60, start = cum, end = cum + dur, rem = Math.max(0, end - e);
        const os = it.status;
        it.status = e < start ? 'PENDING' : e < end ? 'ACTIVE' : 'CLEAR';
        it.current_remaining_seconds = it.status === 'PENDING' ? dur : it.status === 'ACTIVE' ? rem : 0;
        if (os !== 'ACTIVE' && it.status === 'ACTIVE') {
            fetch('/update-status', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active_id: it.id, grid_index: it.grid_index }) }).catch(console.error);
        }
        const re = document.getElementById(it.id);
        if (re) {
            re.className = `event-row state-${it.status.toLowerCase()}`;
            const de = re.querySelector('.live-countdown-display');
            if (de) { const mm = Math.floor(it.current_remaining_seconds / 60), ss = it.current_remaining_seconds % 60; de.textContent = `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`; }
        }
        cum = end;
    });
    const grids = {}; state.sequence.forEach(it => { const g = it.grid_index || 1; if (!grids[g]) grids[g] = []; grids[g].push(it); });
    let ag = null, at = 0, hasAnyActive = false;
    Object.entries(grids).forEach(([gi, rs]) => {
        let tot = 0, hap = false;
        rs.forEach(r => { if (r.status === 'ACTIVE' || r.status === 'PENDING') { tot += r.current_remaining_seconds || r.countdown_minutes * 60; hap = true; hasAnyActive = true; } });
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
