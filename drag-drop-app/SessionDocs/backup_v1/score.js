// ============================================================
// SCORE.JS — Race Scoring Board
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    // ─────────────────────────────────────────────────────────
    // SCROLL PERSISTENCE
    // Save scroll position of all scrollable panels to localStorage
    // and restore on load. Fleet list defaults to bottom.
    // ─────────────────────────────────────────────────────────
    const SCROLL_KEYS = {
        'registry-list-container': 'scroll_registry',
        'racingContainer':         'scroll_racing',
        'finishedContainer':       'scroll_finished'
    };

    function saveScroll(el, key) {
        localStorage.setItem(key, el.scrollTop);
    }

    function restoreScroll(el, key, defaultToBottom) {
        const saved = localStorage.getItem(key);
        if (saved !== null) {
            el.scrollTop = parseInt(saved, 10);
        } else if (defaultToBottom) {
            el.scrollTop = el.scrollHeight;
        }
    }

    // Restore on load
    Object.entries(SCROLL_KEYS).forEach(([id, key]) => {
        const el = id === 'registry-list-container'
            ? document.querySelector('.registry-list-container')
            : document.getElementById(id);
        if (!el) return;
        const defaultBottom = (id === 'registry-list-container');
        restoreScroll(el, key, defaultBottom);
        el.addEventListener('scroll', () => saveScroll(el, key));
    });

    // ─────────────────────────────────────────────────────────
    // REFS
    // ─────────────────────────────────────────────────────────
    const dashboardContainer = document.querySelector(".score-dashboard-container");
    const btnCollapse   = document.getElementById("btnCollapseSidebar");
    const btnExpand     = document.getElementById("btnExpandSidebar");
    const uidInput      = document.getElementById("inputUid");
    const searchInput   = document.getElementById("registrySearchInput");
    const formElement   = document.getElementById("sailorEntryForm");

    const racingContainer   = document.getElementById("racingContainer");
    const finishedContainer = document.getElementById("finishedContainer");
    const dnfContainer      = document.getElementById("dnfContainer");
    const dqContainer       = document.getElementById("dqContainer");
    const finishedDropGap   = document.getElementById("finishedDropGap");

    // Track finish times captured this session (uid -> "HH:MM:SS")
    // Once recorded they survive reloads via data-finish-time attribute
    const sessionFinishTimes = {};

    // ─────────────────────────────────────────────────────────
    // RESET DAY
    // ─────────────────────────────────────────────────────────
    const btnReset = document.getElementById("btnResetDay");
    if (btnReset) {
        btnReset.addEventListener("click", () => {
            if (!confirm("Reset the day?\nThis clears all Racing Today flags, finish times, and results. The fleet registry is kept.")) return;
            fetch("/reset-day", { method: "POST" })
                .then(res => {
                    if (res.ok) {
                        // Clear saved scroll so fleet list defaults to bottom again
                        Object.values(SCROLL_KEYS).forEach(k => localStorage.removeItem(k));
                        window.location.reload();
                    }
                });
        });
    }

    // ─────────────────────────────────────────────────────────
    // 1. SIDEBAR COLLAPSE
    // ─────────────────────────────────────────────────────────
    if (btnCollapse && dashboardContainer && btnExpand) {
        btnCollapse.addEventListener("click", () => {
            dashboardContainer.classList.add("sidebar-collapsed");
            btnExpand.style.display = "block";
        });
        btnExpand.addEventListener("click", () => {
            dashboardContainer.classList.remove("sidebar-collapsed");
            btnExpand.style.display = "none";
        });
    }

    // ─────────────────────────────────────────────────────────
    // 1b. ADD SAILOR FORM TOGGLE
    // ─────────────────────────────────────────────────────────
    const btnToggleAdd = document.getElementById("btnToggleAddForm");
    const addFormDiv   = document.getElementById("addSailorForm");
    if (btnToggleAdd && addFormDiv) {
        btnToggleAdd.addEventListener("click", () => {
            const open = addFormDiv.style.display !== "none";
            addFormDiv.style.display = open ? "none" : "block";
            btnToggleAdd.textContent = open ? "＋ Add New Sailor" : "▲ Hide Form";
        });
    }

    // ─────────────────────────────────────────────────────────
    // 1c. LANE COUNTS
    // ─────────────────────────────────────────────────────────
    function updateLaneCounts() {
        const set = (id, sel) => {
            const el = document.getElementById(id);
            if (!el) return;
            const n = document.querySelectorAll(sel).length;
            el.textContent = n > 0 ? n : "";
        };
        set("countRacing",   "#racingContainer .competitor-tile");
        set("countFinished", "#finishedContainer .competitor-tile");
        set("countDnf",      "#dnfContainer .competitor-tile");
        set("countDq",       "#dqContainer .competitor-tile");
    }
    updateLaneCounts();

    // ─────────────────────────────────────────────────────────
    // 2. AUTO-GENERATED UID
    // ─────────────────────────────────────────────────────────
    function generateUID() {
        if (!uidInput) return;
        const ts   = Math.floor(Date.now() / 1000).toString().slice(-6);
        const salt = Math.floor(100 + Math.random() * 900);
        uidInput.value = `SL-${ts}${salt}`;
    }
    generateUID();
    if (formElement) {
        formElement.addEventListener("submit", () => setTimeout(generateUID, 500));
    }

    // ─────────────────────────────────────────────────────────
    // 3. REAL-TIME REGISTRY SEARCH
    // ─────────────────────────────────────────────────────────
    if (searchInput) {
        searchInput.addEventListener("input", e => {
            const q = e.target.value.toLowerCase().trim();
            document.querySelectorAll("#savedSailorsList .sailor-row-item").forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(q) ? "flex" : "none";
            });
        });
    }

    // ─────────────────────────────────────────────────────────
    // 4. DRAG & DROP ENGINE
    // ─────────────────────────────────────────────────────────

    // Which container was the drag SOURCE?
    let dragSourceContainer = null;
    // Was this drag left-to-right (from racing → finished)?
    let dragStartX = 0;

    // Snapshot of tile positions taken at dragstart — used for stable
    // insert-position calculation that works for both up and down reorder
    let tilePositionSnapshot = [];

    function snapshotTilePositions(container) {
        tilePositionSnapshot = [...container.querySelectorAll(".competitor-tile")]
            .map(el => ({
                el,
                midY: el.getBoundingClientRect().top + el.getBoundingClientRect().height / 2
            }));
    }

    function attachTileListeners(tile) {
        tile.addEventListener("dragstart", e => {
            tile.classList.add("dragging");
            dragSourceContainer = tile.parentElement;
            dragStartX = e.clientX;
            // Snapshot positions BEFORE the tile goes transparent/moves
            if (dragSourceContainer === racingContainer) {
                snapshotTilePositions(racingContainer);
            }
            e.dataTransfer.setData("text/plain", tile.dataset.uid);
        });
        tile.addEventListener("dragend", () => {
            tile.classList.remove("dragging");
            tilePositionSnapshot = [];
            dragSourceContainer = null;
        });
    }

    document.querySelectorAll(".competitor-tile").forEach(attachTileListeners);

    // ── FINISHED container ──────────────────────────────────
    // Reorder within finished: normal insert-above logic
    // Incoming from LEFT (racing): always append to bottom
    finishedContainer.addEventListener("dragover", e => {
        e.preventDefault();
        const dragging = document.querySelector(".dragging");
        if (!dragging) return;

        const comingFromRacing = dragSourceContainer === racingContainer;
        if (comingFromRacing) {
            // Show visual hint but don't reorder — will append on drop
            return;
        }
        // Reorder within finished
        const after = getDragAfterElement(finishedContainer, e.clientY);
        if (after == null) {
            finishedContainer.appendChild(dragging);
        } else {
            finishedContainer.insertBefore(dragging, after);
        }
    });

    finishedContainer.addEventListener("drop", e => {
        e.preventDefault();
        const dragging = document.querySelector(".dragging");
        if (!dragging) return;

        const comingFromRacing = dragSourceContainer === racingContainer;
        if (comingFromRacing) {
            // Stamp finish time
            const uid = dragging.dataset.uid;
            if (!dragging.dataset.finishTime) {
                const now = new Date();
                const hh  = String(now.getHours()).padStart(2, "0");
                const mm  = String(now.getMinutes()).padStart(2, "0");
                const ss  = String(now.getSeconds()).padStart(2, "0");
                const ts  = `${hh}:${mm}:${ss}`;
                dragging.dataset.finishTime = ts;
                sessionFinishTimes[uid]     = ts;
                // Update the time badge if it exists
                const badge = dragging.querySelector(".finish-time-badge");
                if (badge) badge.textContent = ts;
            }
            finishedContainer.appendChild(dragging);
        }
        saveKanbanState(finishedContainer);
    });

    // ── Open DROP GAP (also routes to finishedContainer bottom) ──
    finishedDropGap.addEventListener("dragover", e => {
        e.preventDefault();
        finishedDropGap.classList.add("drag-over");
    });
    finishedDropGap.addEventListener("dragleave", () => {
        finishedDropGap.classList.remove("drag-over");
    });
    finishedDropGap.addEventListener("drop", e => {
        e.preventDefault();
        finishedDropGap.classList.remove("drag-over");
        const dragging = document.querySelector(".dragging");
        if (!dragging) return;
        const uid = dragging.dataset.uid;
        if (!dragging.dataset.finishTime) {
            const now = new Date();
            const ts  = [now.getHours(), now.getMinutes(), now.getSeconds()]
                .map(n => String(n).padStart(2, "0")).join(":");
            dragging.dataset.finishTime = ts;
            sessionFinishTimes[uid]     = ts;
            const badge = dragging.querySelector(".finish-time-badge");
            if (badge) badge.textContent = ts;
        }
        finishedContainer.appendChild(dragging);
        saveKanbanState(finishedContainer);
    });

    // ── RACING container ─────────────────────────────────────
    // dragover: show live insert preview for REORDERING only
    // Tiles coming from finished/penalty just get appended on drop
    racingContainer.addEventListener("dragover", e => {
        e.preventDefault();
        const dragging = document.querySelector(".dragging");
        if (!dragging) return;
        // Only do live preview when reordering within racing
        if (dragSourceContainer !== racingContainer) return;
        const after = getDragAfterElement(racingContainer, e.clientY);
        if (after == null) {
            racingContainer.appendChild(dragging);
        } else {
            racingContainer.insertBefore(dragging, after);
        }
    });

    racingContainer.addEventListener("drop", e => {
        e.preventDefault();
        const dragging = document.querySelector(".dragging");
        if (!dragging) return;

        if (dragSourceContainer !== racingContainer) {
            // Coming from finished or penalty — append to bottom
            racingContainer.appendChild(dragging);
        }
        // For within-racing reorder the tile is already in the right spot
        // from live dragover — just clear any stale finish time and save
        dragging.dataset.finishTime = "";
        const badge = dragging.querySelector(".finish-time-badge");
        if (badge) badge.textContent = "";
        saveKanbanState(racingContainer);
    });

    // ── PENALTY zones (DNF / DQ) ────────────────────────────
    [dnfContainer, dqContainer].forEach(zone => {
        const tilesDiv = zone.querySelector(".penalty-tiles");

        zone.addEventListener("dragover", e => {
            e.preventDefault();
            zone.classList.add("drag-over");
        });
        zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
        zone.addEventListener("drop", e => {
            e.preventDefault();
            zone.classList.remove("drag-over");
            const dragging = document.querySelector(".dragging");
            if (!dragging) return;
            tilesDiv.appendChild(dragging);
            // Clear finish time
            dragging.dataset.finishTime = "";
            const badge = dragging.querySelector(".finish-time-badge");
            if (badge) badge.textContent = "";
            const lane = zone.dataset.lane; // 'dnf' or 'dq'
            savePenaltyState(tilesDiv, lane);
        });
    });

    // ─────────────────────────────────────────────────────────
    // HELPERS
    // ─────────────────────────────────────────────────────────
    function getDragAfterElement(container, y) {
        // Use snapshot if available (stable positions from before drag started)
        const items = tilePositionSnapshot.length > 0
            ? tilePositionSnapshot.filter(s => !s.el.classList.contains("dragging"))
            : [...container.querySelectorAll(".competitor-tile:not(.dragging)")]
                .map(el => ({ el, midY: el.getBoundingClientRect().top + el.getBoundingClientRect().height / 2 }));

        // Find the first element whose midpoint is BELOW the cursor
        for (const item of items) {
            if (y < item.midY) return item.el;
        }
        return null; // cursor is below all elements — append to end
    }

    function nowHHMMSS() {
        const now = new Date();
        return [now.getHours(), now.getMinutes(), now.getSeconds()]
            .map(n => String(n).padStart(2, "0")).join(":");
    }

    function saveKanbanState(container) {
        if (!container) return;
        // Determine lane from container id
        let lane;
        if (container === finishedContainer) lane = "finished";
        else if (container === racingContainer) lane = "racing";
        else return;

        const tiles       = [...container.querySelectorAll(".competitor-tile")];
        const orderedUids = tiles.map(t => t.dataset.uid).filter(Boolean);

        // Build finish_times map for newly stamped tiles
        const finish_times = {};
        tiles.forEach(t => {
            const uid = t.dataset.uid;
            if (uid && t.dataset.finishTime) {
                finish_times[uid] = t.dataset.finishTime;
            }
        });

        fetch("/update-kanban", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lane, ordered_uids: orderedUids, finish_times })
        }).then(res => { if (res.ok) window.location.reload(); });
    }

    function savePenaltyState(tilesDiv, lane) {
        const orderedUids = [...tilesDiv.querySelectorAll(".competitor-tile")]
            .map(t => t.dataset.uid).filter(Boolean);
        fetch("/update-kanban", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lane, ordered_uids: orderedUids, finish_times: {} })
        }).then(res => { if (res.ok) window.location.reload(); });
    }

    // ─────────────────────────────────────────────────────────
    // 5. EDIT MODAL
    // ─────────────────────────────────────────────────────────
    const overlay   = document.getElementById("editModalOverlay");
    const btnClose  = document.getElementById("btnCloseModal");
    const btnSave   = document.getElementById("btnSaveEdit");
    const btnDelete = document.getElementById("btnDeleteSailor");

    btnClose.addEventListener("click", closeModal);
    overlay.addEventListener("click", e => { if (e.target === overlay) closeModal(); });

    function closeModal() { overlay.style.display = "none"; }

    btnSave.addEventListener("click", () => {
        const uid = document.getElementById("editUid").value;
        const payload = {
            sailor_name: document.getElementById("editSailorName").value.trim(),
            short_name:  document.getElementById("editShortName").value.trim(),
            sail_no:     document.getElementById("editSailNo").value.trim(),
            boat_class:  document.getElementById("editBoatClass").value.trim(),
            handicap:    parseFloat(document.getElementById("editHandicap").value) || 1.0,
            seed:        parseInt(document.getElementById("editSeed").value) || 0
        };
        if (!payload.sailor_name || !payload.short_name || !payload.sail_no || !payload.boat_class) {
            alert("Full name, short name, sail number and boat class are required.");
            return;
        }
        fetch(`/edit-sailor/${uid}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        }).then(res => {
            if (res.ok) { closeModal(); window.location.reload(); }
            else        { alert("Save failed."); }
        });
    });

    btnDelete.addEventListener("click", () => {
        const uid  = document.getElementById("editUid").value;
        const name = document.getElementById("editSailorName").value;
        if (!confirm(`Delete "${name}" permanently?`)) return;
        fetch(`/delete-sailor/${uid}`, { method: "DELETE" })
            .then(res => { if (res.ok) { closeModal(); window.location.reload(); } });
    });

});

// ─────────────────────────────────────────────────────────────
// GLOBALS — called from inline HTML attributes
// ─────────────────────────────────────────────────────────────
window.toggleRacingToday = function(uid, isChecked) {
    fetch("/toggle-racing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uid, racing_today: isChecked })
    }).then(res => { if (res.ok) window.location.reload(); });
};

window.openEditModal = function(btn) {
    const row = btn.closest(".sailor-row-item");
    document.getElementById("editUid").value        = row.dataset.uid;
    document.getElementById("editSailorName").value = row.dataset.sailorName;
    document.getElementById("editShortName").value  = row.dataset.shortName;
    document.getElementById("editSailNo").value     = row.dataset.sailNo;
    document.getElementById("editBoatClass").value  = row.dataset.boatClass;
    document.getElementById("editHandicap").value   = row.dataset.handicap;
    document.getElementById("editSeed").value       = row.dataset.seed;
    document.getElementById("editModalOverlay").style.display = "flex";
};
