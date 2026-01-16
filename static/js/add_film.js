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

            let data = null;  // ← ИНИЦИАЛИЗИРУЕМ

            try {
                const csrfToken = getCookie('csrftoken');
                console.log('CSRF token:', csrfToken);  // ОТЛАДКА
                console.log('tmdbId:', tmdbId);         // ОТЛАДКА

                const response = await fetch('/films/add_film/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: `tmdb_id=${tmdbId}`
                });

                console.log('Response status:', response.status);  // ОТЛАДКА

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                data = await response.json();
                console.log('Response data:', data);  // ОТЛАДКА

                if (data.status === 'added') {
                    this.outerHTML = `
                        <span class="status-badge">
                            <span class="status-badge__text">В моей библиотеке</span>
                        </span>
                    `;
                    showToast('✅ Фильм добавлен!');
                } else if (data.status === 'exists') {
                    this.outerHTML = `
                        <span class="status-badge">
                            <span class="status-badge__text">Уже в библиотеке</span>
                        </span>
                    `;
                    showToast('ℹ️ Фильм уже есть');
                } else {
                    throw new Error(data.message || 'Неизвестная ошибка');
                }
            } catch (error) {
                console.error('Add film error:', error);
                this.innerHTML = originalText;
                showToast('❌ Ошибка: ' + error.message);
            } finally {
                this.disabled = false;
            }
        });
    });
});

// функция для CSRF токена
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

// уведомления (простая версия)
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
