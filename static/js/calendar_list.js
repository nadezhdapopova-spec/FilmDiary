document.addEventListener("DOMContentLoaded", () => {
    loadCalendarEvents();
});

window.loadCalendarEvents = loadCalendarEvents;

function loadCalendarEvents() {
    fetch("/api/calendar_events/", {
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        }
    })
        .then(response => {
            if (response.status === 401 || response.status === 403) {
                window.location.href = "/login/";
            return;
            }
            if (!response.ok) {
                throw new Error("Ошибка загрузки данных");
            }
            return response.json();
        })
        .then(data => {
            const events = data.results || data;
            renderEvents(events);
        })
        .catch(error => {
            console.error(error);
            showError();
        });
}


function renderEvents(events) {
    const container = document.getElementById("calendar-events-list");
    if (!container) return;

    const loader = container.querySelector(".loader");
    if (loader) loader.remove();

    container.innerHTML = "";

    if (!events.length) {
        container.innerHTML = "<p class='empty-state'>Пока ничего не запланировано</p>";
        return;
    }

    events.sort((a, b) =>
        new Date(a.planned_date) - new Date(b.planned_date)
    );

    const grouped = groupEventsByDate(events);

    Object.entries(grouped).forEach(([date, dateEvents]) => {
        const group = document.createElement("div");
        group.className = "date-group";

        group.innerHTML = `
            <h2 class="date-title">${formatDate(date)}</h2>
            <div class="events-list"></div>
        `;

        const list = group.querySelector(".events-list");

        dateEvents.forEach(event => {
            const card = document.createElement("div");
            card.className = "event-card";

            card.innerHTML = `
                <div class="event-main">
                    <div class="event-title">${event.film_title}</div>
                    ${event.note ? `<div class="event-note">${event.note}</div>` : ""}
                    }
                </div>
            `;

            list.appendChild(card);
        });

        container.appendChild(group);
    });
}

function groupEventsByDate(events) {
    return events.reduce((groups, event) => {
        const date = event.planned_date;
        if (!groups[date]) {
            groups[date] = [];
        }
        groups[date].push(event);
        return groups;
    }, {});
}


function formatDate(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();

    const dateMidnight = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    const diffDays = (dateMidnight - todayMidnight) / (1000 * 60 * 60 * 24);

    if (diffDays === 0) return "Сегодня";
    if (diffDays === 1) return "Завтра";

    return date.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long"
    });
}

function showError() {
    const container = document.getElementById("calendar-events-list");
    if (!container) return;

    container.innerHTML =
        "<p class='error'>Не удалось загрузить события</p>";
}
