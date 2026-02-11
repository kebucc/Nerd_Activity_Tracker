document.addEventListener("DOMContentLoaded", () => {
    const cfg = window.DASH_CONFIG || {};
    const viewMode = cfg.viewMode || "day";
    const dateStr = cfg.dateStr;
    const startDate = cfg.startDate;
    const endDate = cfg.endDate;

    if (viewMode === "day") {
        loadTimeline(dateStr, "mouse", "timeline-mouse", "session-segment-mouse");
        loadTimeline(dateStr, "keyboard", "timeline-keyboard", "session-segment-keyboard");
        loadTimeline(dateStr, null, "timeline-cumulative", "session-segment-cumulative");
        loadSessionsTable(dateStr);
    } else if (viewMode === "week") {
        loadWeekChart(startDate, endDate);
        loadSessionsTableRange(startDate, endDate);
    } else if (viewMode === "month") {
        loadMonthChart(startDate, endDate);
        loadSessionsTableRange(startDate, endDate);
    }

    document.getElementById("nav-prev").addEventListener("click", () => navigate(viewMode, dateStr, -1));
    document.getElementById("nav-next").addEventListener("click", () => navigate(viewMode, dateStr, +1));
});

function navigate(viewMode, dateStr, offset) {
    const current = new Date(dateStr + "T12:00:00");
    if (viewMode === "day") {
        current.setDate(current.getDate() + offset);
    } else if (viewMode === "week") {
        current.setDate(current.getDate() + offset * 7);
    } else if (viewMode === "month") {
        current.setMonth(current.getMonth() + offset);
    }
    const y = current.getFullYear();
    const m = String(current.getMonth() + 1).padStart(2, "0");
    const d = String(current.getDate()).padStart(2, "0");
    window.location.href = `/${viewMode}/${y}-${m}-${d}`;
}

// --- Day view ---

async function loadTimeline(dateStr, type, barId, segmentClass) {
    let url = `/api/sessions/${dateStr}`;
    if (type) url += `?type=${type}`;
    const resp = await fetch(url);
    const sessions = await resp.json();
    const bar = document.getElementById(barId);
    if (!bar) return;
    bar.innerHTML = "";

    const MINUTES_IN_DAY = 1440;
    sessions.forEach(s => {
        const startMin = parseTimeToMinutes(s.start_time);
        const endMin = parseTimeToMinutes(s.end_time);
        const seg = document.createElement("div");
        seg.className = `session-segment ${segmentClass}`;
        seg.style.left = `${(startMin / MINUTES_IN_DAY) * 100}%`;
        seg.style.width = `${(Math.max(endMin - startMin, 0.2) / MINUTES_IN_DAY) * 100}%`;
        seg.title = `${formatTimeFromISO(s.start_time)} - ${formatTimeFromISO(s.end_time)}  (${formatDuration(s.duration)})`;
        bar.appendChild(seg);
    });
}

async function loadSessionsTable(dateStr) {
    const resp = await fetch(`/api/sessions/${dateStr}`);
    const sessions = await resp.json();
    const tbody = document.querySelector("#sessions-table tbody");
    const noSessions = document.getElementById("no-sessions");
    tbody.innerHTML = "";

    if (sessions.length === 0) {
        noSessions.classList.remove("hidden");
        document.getElementById("sessions-table").classList.add("hidden");
        return;
    }

    noSessions.classList.add("hidden");
    document.getElementById("sessions-table").classList.remove("hidden");

    sessions.forEach((s, i) => {
        const tr = document.createElement("tr");
        const typeLabel = s.type === "mouse" ? "Mouse" : "Keyboard";
        const typeClass = s.type === "mouse" ? "mouse-color" : "keyboard-color";
        tr.innerHTML = `
            <td>${i + 1}</td>
            <td><span class="${typeClass}">${typeLabel}</span></td>
            <td>${formatTimeFromISO(s.start_time)}</td>
            <td>${formatTimeFromISO(s.end_time)}</td>
            <td>${formatDuration(s.duration)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Week view ---

async function loadWeekChart(startDate, endDate) {
    const container = document.getElementById("week-chart");
    if (!container) return;
    container.innerHTML = "";

    const resp = await fetch(`/api/sessions/${startDate}/${endDate}`);
    const sessions = await resp.json();

    // Group sessions by date
    const byDate = {};
    sessions.forEach(s => {
        const d = s.start_time.split("T")[0];
        if (!byDate[d]) byDate[d] = { mouse: 0, keyboard: 0 };
        byDate[d][s.type] = (byDate[d][s.type] || 0) + s.duration;
    });

    // Find max daily total for scaling
    let maxTotal = 0;
    Object.values(byDate).forEach(v => {
        const total = v.mouse + v.keyboard;
        if (total > maxTotal) maxTotal = total;
    });
    if (maxTotal === 0) maxTotal = 1;

    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const start = new Date(startDate + "T12:00:00");

    for (let i = 0; i < 7; i++) {
        const d = new Date(start);
        d.setDate(d.getDate() + i);
        const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
        const data = byDate[iso] || { mouse: 0, keyboard: 0 };

        const row = document.createElement("div");
        row.className = "week-row";

        const label = document.createElement("span");
        label.className = "week-label";
        label.textContent = `${dayNames[i]}  ${iso.slice(5)}`;

        const barTrack = document.createElement("div");
        barTrack.className = "week-bar-track";

        const mouseSeg = document.createElement("div");
        mouseSeg.className = "week-bar-seg mouse-bg";
        mouseSeg.style.width = `${(data.mouse / maxTotal) * 100}%`;
        mouseSeg.title = `Mouse: ${formatDuration(data.mouse)}`;

        const kbSeg = document.createElement("div");
        kbSeg.className = "week-bar-seg keyboard-bg";
        kbSeg.style.width = `${(data.keyboard / maxTotal) * 100}%`;
        kbSeg.title = `Keyboard: ${formatDuration(data.keyboard)}`;

        const totalLabel = document.createElement("span");
        totalLabel.className = "week-total";
        totalLabel.textContent = formatDuration(data.mouse + data.keyboard);

        barTrack.appendChild(mouseSeg);
        barTrack.appendChild(kbSeg);
        row.appendChild(label);
        row.appendChild(barTrack);
        row.appendChild(totalLabel);
        container.appendChild(row);
    }
}

// --- Month view ---

async function loadMonthChart(startDate, endDate) {
    const container = document.getElementById("month-chart");
    if (!container) return;
    container.innerHTML = "";

    const resp = await fetch(`/api/sessions/${startDate}/${endDate}`);
    const sessions = await resp.json();

    // Group total duration by date
    const byDate = {};
    sessions.forEach(s => {
        const d = s.start_time.split("T")[0];
        byDate[d] = (byDate[d] || 0) + s.duration;
    });

    let maxDuration = 0;
    Object.values(byDate).forEach(v => { if (v > maxDuration) maxDuration = v; });
    if (maxDuration === 0) maxDuration = 1;

    // Day-of-week headers
    const dayHeaders = document.createElement("div");
    dayHeaders.className = "month-header";
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach(name => {
        const span = document.createElement("span");
        span.textContent = name;
        dayHeaders.appendChild(span);
    });
    container.appendChild(dayHeaders);

    // Build calendar grid
    const grid = document.createElement("div");
    grid.className = "month-grid";

    const firstDay = new Date(startDate + "T12:00:00");
    const startDow = (firstDay.getDay() + 6) % 7; // Mon=0

    // Empty cells before first day
    for (let i = 0; i < startDow; i++) {
        const empty = document.createElement("div");
        empty.className = "month-cell empty";
        grid.appendChild(empty);
    }

    // Each day of the month
    const endD = new Date(endDate + "T12:00:00");
    for (let d = new Date(firstDay); d <= endD; d.setDate(d.getDate() + 1)) {
        const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
        const duration = byDate[iso] || 0;
        const intensity = duration / maxDuration;

        const cell = document.createElement("div");
        cell.className = "month-cell";
        cell.style.opacity = duration > 0 ? (0.2 + intensity * 0.8) : 0.1;
        cell.style.backgroundColor = duration > 0 ? "var(--color-cumulative)" : "#1a1a1a";
        cell.textContent = d.getDate();
        cell.title = `${iso}: ${formatDuration(duration)}`;
        grid.appendChild(cell);
    }

    container.appendChild(grid);
}

// --- Range session table (week/month) ---

async function loadSessionsTableRange(startDate, endDate) {
    const resp = await fetch(`/api/sessions/${startDate}/${endDate}`);
    const sessions = await resp.json();
    const tbody = document.querySelector("#sessions-table tbody");
    const noSessions = document.getElementById("no-sessions");
    tbody.innerHTML = "";

    if (sessions.length === 0) {
        noSessions.classList.remove("hidden");
        document.getElementById("sessions-table").classList.add("hidden");
        return;
    }

    noSessions.classList.add("hidden");
    document.getElementById("sessions-table").classList.remove("hidden");

    sessions.forEach((s, i) => {
        const tr = document.createElement("tr");
        const typeLabel = s.type === "mouse" ? "Mouse" : "Keyboard";
        const typeClass = s.type === "mouse" ? "mouse-color" : "keyboard-color";
        const sessionDate = s.start_time.split("T")[0];
        tr.innerHTML = `
            <td>${i + 1}</td>
            <td>${sessionDate}</td>
            <td><span class="${typeClass}">${typeLabel}</span></td>
            <td>${formatTimeFromISO(s.start_time)}</td>
            <td>${formatTimeFromISO(s.end_time)}</td>
            <td>${formatDuration(s.duration)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Helpers ---

function parseTimeToMinutes(isoString) {
    const timePart = isoString.split("T")[1];
    if (!timePart) return 0;
    const parts = timePart.split(":");
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    const s = parseFloat(parts[2]) || 0;
    return h * 60 + m + s / 60;
}

function formatTimeFromISO(isoString) {
    const timePart = isoString.split("T")[1];
    if (!timePart) return "";
    return timePart.substring(0, 8);
}

function formatDuration(seconds) {
    seconds = Math.round(seconds);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}
