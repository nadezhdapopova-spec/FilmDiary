document.addEventListener("DOMContentLoaded", () => {
    loadCalendarEvents();
});

window.loadCalendarEvents = loadCalendarEvents;

let currentView = "active";

function loadCalendarEvents(page = 1) {
    let url = `/api/calendar_events/?view=${currentView}`;
    if (page > 1) url += `&page=${page}`;

    fetch(url, {
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
            // const events = data.results || data;
            // renderEvents(events);
            renderEvents(data);
        })
        .catch(error => {
            console.error(error);
            showError();
        });
}

function renderPagination(apiResponse, hasEvents) {
    const paginationContainer = document.getElementById("calendar-pagination");
    if (!paginationContainer) return;

    if (!hasEvents || !apiResponse.count || apiResponse.count <= 12) {
        paginationContainer.innerHTML = "";
        return;
    }

    const currentPage = getCurrentPage(apiResponse.next, apiResponse.previous);
    const totalPages = Math.ceil(apiResponse.count / 12); // 12 = твой PAGE_SIZE

    let paginationHTML = `
        <div class="pagination-info">
            Показаны ${currentPage === 1 ? 1 : (currentPage - 1) * 12 + 1}–${Math.min(currentPage * 12, apiResponse.count)} из ${apiResponse.count}
        </div>
    `;

    paginationHTML += `
        <div class="pagination-buttons">
            ${apiResponse.previous ? `<button class="page-btn" data-page="${currentPage - 1}">‹ Назад</button>` : ''}
            <span class="page-info">Страница ${currentPage} из ${totalPages}</span>
            ${apiResponse.next ? `<button class="page-btn" data-page="${getNextPage(apiResponse.next)}">Вперед ›</button>` : ''}
        </div>
    `;

    paginationContainer.innerHTML = paginationHTML;

    // Обработчики кнопок пагинации
    paginationContainer.querySelectorAll(".page-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const page = parseInt(e.target.dataset.page);
            loadCalendarEvents(page);
        });
    });
}

function getCurrentPage(next, previous) {
    if (next) {
        const match = next.match(/page=(\d+)/);
        return match ? parseInt(match[1]) - 1 || 1 : 1;
    }
    return previous ? 2 : 1;
}

function getNextPage(nextUrl) {
    const match = nextUrl.match(/page=(\d+)/);
    return match ? parseInt(match[1]) : 2;
}


function renderEvents(apiResponse) {
    const container = document.getElementById("calendar-events-list");
    const paginationContainer = document.getElementById("calendar-pagination");
    if (!container) return;

    const loader = container.querySelector(".loader");
    if (loader) loader.remove();

    const events = apiResponse.results || apiResponse;
    container.innerHTML = "";

    if (!events.length) {
        container.innerHTML = `
          <div class="empty-state">
            <strong>Пока ничего не запланировано</strong>
            <p>Добавь фильмы в план просмотра, чтобы они появились здесь.</p>
          </div>
        `;
        paginationContainer.innerHTML = ""; // Скрываем пагинацию
        return;
    }

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

            const filmUrl = `/films/film/${event.film_tmdb_id}/`;

            card.innerHTML = `
                <div class="event-main">
                    <div class="event-title">${event.film_title}</div>
                    ${event.note ? `<div class="event-note">${event.note}</div>` : ""}
                </div>
                <div class="event-actions">
                    <a href="${filmUrl}" title="Подробнее">🎬</a>
                    <button class="mark-watched" data-event-id="${event.id}" title="Отменить просмотр">➖</button>
                </div>
            `;

            list.appendChild(card);
        });

        container.appendChild(group);
    });
    renderPagination(apiResponse, container.children.length > 0);
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

// Делегирование кликов по кнопкам "Отменить просмотр"
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".mark-watched");
    if (!btn) return;

    e.preventDefault();

    const eventId = btn.dataset.eventId;
    if (!eventId) {
        console.error("Нет event ID");
        return;
    }

    showDeleteModal(eventId, btn);
});

// Переключение вкладок Активные / Архив
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".view-btn");
    if (!btn) return;

    e.preventDefault();

    document.querySelectorAll(".view-btn").forEach(b =>
        b.classList.remove("active")
    );
    btn.classList.add("active");

    currentView = btn.dataset.view;
    loadCalendarEvents(1);
});

function deleteEvent(eventId, buttonEl) {
    fetch(`/api/calendar_events/${eventId}/`, {
        method: "DELETE",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"), // для CSRF защиты Django
        }
    })
    .then(response => {
        if (response.status === 401 || response.status === 403) {
            window.location.href = "/login/";
            return;
        }
        if (!response.ok) {
            throw new Error("Ошибка удаления события");
        }
        return Promise.resolve();
    })
    .then(async() => {
        // УДАЛЕНИЕ ИЗ DOM - локальное удаление
        const card = buttonEl.closest(".event-card");
        if (card && card.parentNode) {
            card.parentNode.removeChild(card);
        }

        const eventsList = buttonEl.closest(".events-list");
        if (eventsList && eventsList.children.length === 0) {
            const dateGroup = eventsList.closest(".date-group");
            if (dateGroup && dateGroup.parentNode) {
                dateGroup.parentNode.removeChild(dateGroup);
            }
        }

        const container = document.getElementById("calendar-events-list");
        if (container.children.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <strong>Пока ничего не запланировано</strong>
                    <p>Добавь фильмы в план просмотра, чтобы они появились здесь</p>
                </div>
            `;
        }

        const filmTmdbId = await getFilmTmdbIdFromEventId(eventId);
        window.dispatchEvent(new CustomEvent('calendarEventDeleted', {
            detail: {
                eventId: eventId,
                filmTmdbId: filmTmdbId
            }
        }));

        showSuccessToast("✅ Просмотр отменён");
    })
    .catch(error => {
        console.error("Ошибка:", error);
        showErrorToast("❌ Ошибка удаления");
    });
}

// Вспомогательная функция — получить tmdb_id по eventId
async function getFilmTmdbIdFromEventId(eventId) {
    try {
        const response = await fetch(`/api/calendar_events/${eventId}/`);
        const event = await response.json();
        return event.film_tmdb_id;
    } catch {
        return null;
    }
}

// Функция для получения CSRF токена (Django)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Модальные окна
function showDeleteModal(eventId, buttonEl) {
    const modal = document.createElement("div");
    modal.id = "delete-modal";
    modal.className = "modal-overlay";
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Отменить просмотр?</h3>
            <p><strong>${buttonEl.closest('.event-card').querySelector('.event-title').textContent}</strong></p>
            <div class="modal-actions">
                <button class="btn-cancel">Отмена</button>
                <button class="btn-confirm" data-event-id="${eventId}">Удалить</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Закрытие по клику на фон
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    // Обработчик кнопки "Удалить"
    modal.querySelector(".btn-confirm").addEventListener("click", () => {
        deleteEvent(eventId, buttonEl);
        closeModal();
    });

    // Обработчик кнопки "Отмена"
    modal.querySelector(".btn-cancel").addEventListener("click", () => {
        closeModal();
    });
}

function closeModal() {
    const modal = document.getElementById("delete-modal");
    if (modal) modal.remove();
}

function showSuccessToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast-success";
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}


function showErrorToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast-error";
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}
