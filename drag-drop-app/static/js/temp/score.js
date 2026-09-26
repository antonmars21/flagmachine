document.addEventListener("DOMContentLoaded", () => {
    const dashboardContainer = document.querySelector(".roster-dashboard-container");
    const btnCollapse = document.getElementById("btnCollapseSidebar");
    const btnExpand = document.getElementById("btnExpandSidebar");
    const uidInput = document.getElementById("inputUid");
    const searchInput = document.getElementById("registrySearchInput");
    const formElement = document.getElementById("sailorEntryForm");

    // ==========================================
    // 1. COLLAPSIBLE PANEL LOGIC
    // ==========================================
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

    // ==========================================
    // 2. AUTO-GENERATED UID INTERACTION
    // ==========================================
    function generateAutocompleteUID() {
        if (!uidInput) return;
        // Generates a clean, unique serial tag (e.g., SL-17174921)
        const timestampToken = Math.floor(Date.now() / 1000).toString().slice(-6);
        const randomSalt = Math.floor(100 + Math.random() * 900);
        uidInput.value = `SL-${timestampToken}${randomSalt}`;
    }

    generateAutocompleteUID();

    if (formElement) {
        formElement.addEventListener("submit", () => {
            setTimeout(generateAutocompleteUID, 500); 
        });
    }

    // ==========================================
    // 3. REGISTRY FILTER FIELD (REAL-TIME SEARCH)
    // ==========================================
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const queryValue = e.target.value.toLowerCase().trim();
            const entries = document.querySelectorAll("#savedSailorsList .sailor-row-item");

            entries.forEach(row => {
                const searchHaystack = row.textContent.toLowerCase();
                if (searchHaystack.includes(queryValue)) {
                    row.style.display = "flex"; 
                } else {
                    row.style.display = "none";  
                }
            });
        });
    }

    // ==========================================
    // 4. NATIVE KANBAN DRAG & DROP ENGINE
    // ==========================================
    const tileContainers = document.querySelectorAll(".tile-container");
    const competitorTiles = document.querySelectorAll(".competitor-tile");

    competitorTiles.forEach(tile => {
        tile.addEventListener("dragstart", () => {
            tile.classList.add("dragging");
        });

        tile.addEventListener("dragend", () => {
            tile.classList.remove("dragging");
            // Automatically execute synchronization loop when elements settle
            saveKanbanState(tile.parentElement);
        });
    });

    tileContainers.forEach(container => {
        container.addEventListener("dragover", (e) => {
            e.preventDefault();
            const draggingTile = document.querySelector(".dragging");
            if (!draggingTile) return;
            const afterElement = getDragAfterElement(container, e.clientY);
            if (afterElement == null) {
                container.appendChild(draggingTile);
            } else {
                container.insertBefore(draggingTile, afterElement);
            }
        });
    });

    function getDragAfterElement(container, y) {
        const dragElements = [...container.querySelectorAll(".competitor-tile:not(.dragging)")];
        return dragElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    function saveKanbanState(container) {
        if (!container) return;
        const laneElement = container.closest(".kanban-lane");
        if (!laneElement) return;
        
        const laneName = laneElement.getAttribute("data-lane");
        const tiles = container.querySelectorAll(".competitor-tile");
        let orderedUids = [];
        
        tiles.forEach(tile => {
            const uid = tile.getAttribute("data-uid");
            if (uid) orderedUids.push(uid);
        });

        // REPAIRED: Payload standard key updated directly from box: to body:
        fetch("/update-kanban", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lane: laneName, ordered_uids: orderedUids })
        }).then(res => {
            if (res.ok) window.location.reload(); 
        });
    }
});

// ==========================================
// 5. GLOBAL FLEET MANAGEMENT CONTEXTS
// ==========================================
window.toggleRacingToday = function(uid, isChecked) {
    fetch("/toggle-racing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uid: uid, racing_today: isChecked })
    }).then(res => {
        if (res.ok) window.location.reload();
    });
};