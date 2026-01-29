document.addEventListener('click', async function (e) {
    const button = e.target.closest('.btn-add-film');
    if (!button) return;

    console.log('DELEGATED CLICK add-film', button.dataset.tmdbId);
    e.preventDefault();

    const tmdbId = button.dataset.tmdbId;
    const title = button.dataset.title;

    const originalHTML = button.innerHTML;
    button.innerHTML = '<span>Добавляем...</span>';
    button.disabled = true;

    try {
        const csrfToken = getCookie('csrftoken');

        const response = await fetch('/films/add_film/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: `tmdb_id=${encodeURIComponent(tmdbId)}`
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'added' || data.status === 'exists') {
            button.outerHTML = `
                <span class="status-badge">
                    <span class="status-badge__text">
                        ${data.status === 'added' ? 'В моей библиотеке' : 'Уже в библиотеке'}
                    </span>
                </span>
            `;
            showToast(`✅ Фильм "${title}" добавлен`);
        } else {
            throw new Error(data.message || 'Неизвестная ошибка');
        }

    } catch (error) {
        console.error('Add film error:', error);
        if (document.body.contains(button)) {
            button.innerHTML = originalHTML;
            button.disabled = false;
        }
        showToast('❌ Ошибка: ' + error.message);
    }
});

// функция для CSRF токена
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// уведомления
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
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}