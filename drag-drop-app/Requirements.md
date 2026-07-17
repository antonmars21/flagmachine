Here is the updated requirements document. I have translated your specifications into formal functional and non-functional requirements (`FR-3.x` and `NFR-4.x`), maintaining the same design philosophy, precise terminology, and structural hierarchy as your original starting sequence module.

Since you requested the Python script to be completely independent, these have been structured as a standalone **Results & Roster Management Module**.

---

# Sailing Race Regatta Module ("Flag Machine") - Functional Specifications

## 1. Functional Requirements

### 1.1 Race Configuration & Planning Phase

* **FR-1.1**: The application main controller must accept an editable configuration input string to serve as the global `master_start_time`, formatted exactly to the 24-hour time constraint (HH:MM).
* **FR-1.2**: The application must include an automated dynamic asset scanner that automatically inspects the local directory workspace (`static/flags/`) on startup and refresh to extract available regatta signal images.
* **FR-1.3**: The left-hand asset palette sidebar must dynamically loop through and output these discovered flag assets as draggable card templates containing matching identity properties: Class Label, Flag Filename Asset Image path, and default race intervals.
* **FR-1.4**: Users must be able to drag card components directly from the left palette library into a single-column vertical grid container to generate an ordered active event plan.
* **FR-1.5**: The interface must allow users to visually reorder items directly inside the active sequence list via vertical mouse or touch drag actions.
* **FR-1.6**: Modifications to row layouts, deletion events, or manual adjustments of class duration value text fields must trigger asynchronous, non-reloading payload posts (`fetch()`) to reconcile server memory arrays instantly.

### 1.2 Race Execution Phase

* **FR-1.7**: The header control layer must render persistent visual global action buttons mapped to the execution lifecycle: Start, Override Stop, and Override Reset.
* **FR-1.8**: The application must compute and output a running live clock layout matching local system time precisely down to the second (HH:MM:SS).
* **FR-1.9**: Upon receiving a Start trigger, the live timing routine must synchronize against the `master_start_time` value and initiate the automatic time waterfall cascade.
* **FR-1.10**: The active sequence column must maintain a strict sequential daisy-chain execution schedule. Only the first row item is activated initially.
* **FR-1.11**: As the active item counts down, its localized text field must transform to show a live ticking countdown display format (MM:SS).
* **FR-1.12**: When an active row's local timer counts down to exactly 00:00, its state property must instantly toggle to a cleared status flag, sound a start alert trigger, and immediately wake up the next pending row card below it to start its own localized countdown sequence.
* **FR-1.13**: The interface wrapper must dynamically bind visual layouts to individual card rows using precise, real-time context CSS state identifiers:
* `state-pending`: Rendered as a neutral, stationary placeholder state.
* `state-active`: Rendered as an intense, highlighted operational visual mode, indicating live clock ticks are currently executing inside that row container.
* `state-clear`: Rendered as a muted, greyed out or struck-through appearance, indicating the class sequence has successfully concluded its starting window.


* **FR-1.14**: Handlers for global control state buttons must be able to intercept runtime scripts instantaneously:
* **Override Stop**: Freezes all active clock timers in place, retaining countdown states while switching the interface badge to an administrative pause alert status.
* **Override Reset**: Instantly terminates executing clocks, flushes the runtime loop, and resets all row components back to their default configuration states.



### 1.3 Results & Roster Management Module (Independent Script)

* **FR-3.1**: The system must utilize a persistent relational database schema to register and maintain global sailor profiles. Each record must explicitly capture the following structural attributes:
* `uid` (Unique Identifier, Primary Key)
* `sailor_name`
* `short_name`
* `sail_no`
* `boat_class`
* `handicap`
* `seed`


* **FR-3.2**: The roster management interface must present a complete operational listing of all saved sailors with a persistent state toggle interaction ("Racing Today" checkbox) assigned to each profile.
* **FR-3.3**: Committing the "Racing Today" state configuration must dynamically populate an active race tracking interface without modifying or deleting the master global sailor registry database.
* **FR-3.4**: The race tracking interface must be rendered as a multi-column Kanban board configuration comprising at least two primary layout vectors: a **"Racing" (Pending Finish)** column and a **"Finished"** column.
* **FR-3.5**: The "Racing" column must automatically group active competitor tiles by their respective `boat_class` attribute, sorting each sub-group container sequentially by its designated `seed` value.
* **FR-3.6**: Competitor tiles rendered within the Kanban lanes must explicitly display a concise layout containing only the individual's `short_name` and `sail_no`.
* **FR-3.7**: The Race Officer must be able to drag competitor tiles interactively from the "Racing" column directly into the "Finished" column via mouse or touch mechanics to register a completed race.
* **FR-3.8**: The application must record the precise sequence order in which tiles are dropped into the "Finished" column to establish the definitive, uncorrected finishing order results.
* **FR-3.9**: The Kanban workflow engine must permit arbitrary visual reordering within *any* lane container, allowing the Race Officer to manually manipulate and override tile arrays to correct finishing placements on the fly.
* **FR-3.10**: All drag-and-drop operations, structural lane migrations, and column sequence modifications must trigger immediate asynchronous background payloads (`fetch()`) to synchronize the local client configuration state with the backend database seamlessly.

---

## 2. Technical & Non-Functional Constraints

* **NFR-2.1**: The application workspace must execute cleanly on local Windows 11 system hardware utilizing explicit Anaconda base terminal environments via target python paths.
* **NFR-2.2**: State alterations across the client layout canvas must process without invoking full browser reload cycles or structural interface flicker.
* **NFR-4.1**: The Results & Roster Management codebase must exist as an entirely self-contained, independent execution routine (`.py` script and related layout files) completely segregated from the core startup timer workflow.

---

### Ready for Next Steps?

Would you like me to generate the foundational database schema and the independent Python script (using Flask or your preferred framework) to build this Kanban results dashboard next?