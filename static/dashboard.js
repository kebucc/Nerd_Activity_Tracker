document.addEventListener("DOMContentLoaded", () => {
    const dateStr = document.getElementById("current-date").textContent.trim();
    loadTimeline(dateStr, "mouse", "timeline-mouse", "session-segment-mouse");
    loadTimeline(dateStr, "keyboard", "timeline-keyboard", "session-segment-keyboard");
    loadTimeline(dateStr, null, "timeline-cumulative", "session-segment-cumulative");
    loadSessionsTable(dateStr);

    document.getElementById("prev-day").addEventListener("click", () => navigateDay(-1));
    document.getElementById("next-day").addEventListener("click", () => navigateDay(+1));
});

async function loadTimeline(dateStr, type, barId, segmentClass) {
    let url = `/api/sessions/${dateStr}`;
    if (type) url += `?type=${type}`;
    const resp = await fetch(url);
    const sessions = await resp.json();
    const bar = document.getElementById(barId);
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

function navigateDay(offset) {
    const current = new Date(document.getElementById("current-date").textContent.trim());
    current.setDate(current.getDate() + offset);
    const y = current.getFullYear();
    const m = String(current.getMonth() + 1).padStart(2, "0");
    const d = String(current.getDate()).padStart(2, "0");
    window.location.href = `/day/${y}-${m}-${d}`;
}

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
