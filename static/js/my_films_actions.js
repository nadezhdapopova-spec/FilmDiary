document.addEventListener('DOMContentLoaded', function() {
    // Кнопка "Запланировать просмотр"
    document.querySelectorAll('.btn-add-film[data-action="plan"]').forEach(button => {
        button.addEventListener('click', handlePlanClick);
    });

    // Кнопка "Добавить в любимое"
    document.querySelectorAll('.btn-add-film[data-action="favorite"]').forEach(button => {
        button.addEventListener('click', handleFavoriteClick);
    });
});

async function handlePlanClick(e) {
    e.preventDefault();
    const button = e.currentTarget;
    const filmId = button.dataset.id;
    const title = button.dataset.title;

    await updateFilmStatus(button, filmId, 'plan');
}

async function handleFavoriteClick(e) {
    e.preventDefault();
    const button = e.currentTarget;
    const filmId = button.dataset.id;
    const title = button.dataset.title;

    await updateFilmStatus(button, filmId, 'favorite');
}

async function updateFilmStatus(button, filmId, action) {
    const originalContent = button.innerHTML;
    button.innerHTML = '<span>Обновляем...</span>';
    button.disabled = true;

    try {
        const response = await fetch('/films/update-status/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: `film_id=${filmId}&action=${action}`
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            if (action === 'plan') {
                // Меняем статус на "Просмотрено"
                button.closest('.movie-card__footer').innerHTML = `
                    <span class="movie-card__footer-label">Мой статус:</span>
                    <span class="status-badge">
                        <span class="status-badge__text">Просмотрено</span>
                    </span>
                    <button class="glass-btn btn-add-film" data-id="${filmId}" data-title="${title}" data-action="favorite">
                        <span class="btn-add-film__text">Добавить в любимое</span>
                        <span class="status-badge__icon">🔥</span>
                    </button>
                `;
                showToast('✅ Фильм отмечен как просмотренный');
            } else if (action === 'favorite') {
                // Добавляем иконку 🔥 в статус
                const statusBadge = button.closest('.movie-card__footer').querySelector('.status-badge');
                statusBadge.innerHTML += '<span class="status-badge__icon">🔥</span>';
                button.remove(); // убираем кнопку
                showToast('❤️ Фильм добавлен в любимые');
            }
        } else {
            throw new Error(data.message || 'Неизвестная ошибка');
        }
    } catch (error) {
        console.error('Update status error:', error);
        button.innerHTML = originalContent;
        showToast('❌ Ошибка: ' + error.message);
    } finally {
        button.disabled = false;
    }
}

// CSRF токен
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

// Toast уведомления
function showToast(message) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed; top: 20px; right: 20px; 
        background: rgba(0,0,0,0.9); color: white; 
        padding: 1rem 1.5rem; border-radius: 12px; 
        backdrop-filter: blur(10px); z-index: 9999;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        font-family: Poppins, sans-serif;
        font-weight: 500;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
