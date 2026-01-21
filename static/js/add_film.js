document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.btn-add-film').forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();

            const tmdbId = this.dataset.tmdbId;
            const title = this.dataset.title;

            // визуальная обратная связь
            const originalText = this.innerHTML;
            this.innerHTML = '<span>Добавляем...</span>';
            this.disabled = true;

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

                if (data.status === 'added') {
                    this.outerHTML = `
                        <span class="status-badge">
                            <span class="status-badge__text">В моей библиотеке</span>
                        </span>
                    `;
                    showToast(`✅ Фильм "${title}" добавлен!`);
                } else if (data.status === 'exists') {
                    this.outerHTML = `
                        <span class="status-badge">
                            <span class="status-badge__text">Уже в библиотеке</span>
                        </span>
                    `;
                    showToast(`ℹ️ Фильм "${title}" уже есть`);
                } else if (data.status === 'error') {
                    throw new Error(data.message || 'Неизвестная ошибка');
                } else {
                    throw new Error('Неизвестный ответ сервера');
                }

            } catch (error) {
                console.error('Add film error:', error);
                if (document.body.contains(this)) {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }
                showToast('❌ Ошибка: ' + error.message);
            }
        });
    });
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