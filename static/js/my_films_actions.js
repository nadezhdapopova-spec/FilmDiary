document.addEventListener('DOMContentLoaded', function () {
  const grid = document.querySelector('.movie-search-grid');
  if (!grid) return;

  const page = grid.dataset.page; // 'my-films', 'favorites' и т.д.

  grid.addEventListener('click', async function (e) {
    const button = e.target.closest('.btn-icon');
    if (!button) return;

    const action = button.dataset.action;
    const filmId = button.dataset.id;
    const title = button.dataset.title;
    if (!action || !filmId) return;

    const card = button.closest('.glass-card');

    e.preventDefault();

    switch (action) {
      case 'plan':
        if (card.querySelector('.movie-badge--planned')) {
          showToast(`📅 Фильм "${title}" уже в Запланированных`, 'plan');
          return;
        }
        // Иначе переход на страницу планирования
        window.location.href = `/plans/create/${filmId}/`; // изменить путь
        break;

      case 'watch': {
        const response = await updateFilmStatus(button, filmId, action, title);
        if (response && response.status === 'redirect') {
           window.location.href = response.url;
        }
        break;
      }

      case 'favorite': {
        if (card.querySelector('.movie-badge--favorite')) {
          showToast(`🔥 Фильм "${title}" уже в Любимых`, 'info');
          return;
        }
        const data = await updateFilmStatus(button, filmId, action, title);
        // await updateFilmStatus(button, filmId, action, title);
        // если сервер не ответил success — ничего не делаем
        if (!data || data.status !== 'success') return;
        showToast(`🔥 Фильм "${title}" добавлен в Любимое`, 'favorite');
        break;
      }

      case 'unfavorite': {
        const confirmedUnfav = await confirmDelete('unfavorite', title);
        if (!confirmedUnfav) return;

        const data = await updateFilmStatus(button, filmId, action, title);
        showToast(`🔥 Фильм "${title}" убран из Любимого`, 'info');

        // Убираем карточку сразу на странице Любимое
        if (page === 'favorites') card.remove();
        break;
      }

      case 'delete': {
        const confirmedDelete = await confirmDelete('delete', title);
        if (!confirmedDelete) return;

        const response = await fetch(`/films/${filmId}/delete/`, {
           method: 'POST',
           headers: {
               'X-CSRFToken': getCookie('csrftoken'),
               'X-Requested-With': 'XMLHttpRequest'
           }
        });

        if (!response.ok) {
           showToast('❌ Ошибка при удалении фильма', 'error');
           return;
        }

        showToast(`❌ Фильм "${title}" удалён`, 'error');
        if (page === 'my-films') card.remove(); // удаляем с Мои фильмы
        break;
      }

      case 'delete-watched': {
        const confirmedWatched = await confirmDelete('delete-watched', title);
        if (!confirmedWatched) return;

        const response = await fetch(`/reviews/${filmId}/delete/`, {
           method: 'POST',
           headers: {
              'X-CSRFToken': getCookie('csrftoken'),
              'X-Requested-With': 'XMLHttpRequest'
           }
        });

        if (!response.ok) {
          showToast('❌ Ошибка при удалении отзыва', 'error');
          return;
        }

        showToast(`➖ Фильм "${title}" убран из просмотренного`, 'info');
        card.remove();
        break;
      }

      default:
        console.warn('Неизвестное действие:', action);
    }
  });
});

// ------------------ Actions ------------------
function openReviewForm(filmId, title) {
  window.location.href = `/reviews/create/${filmId}/`;
}

function openPlanForm(filmId, title, button) {
  const card = button.closest('.glass-card');
  if (card.querySelector('.movie-badge--planned')) {
    showToast(`📅 Фильм "${title}" уже в Запланированных`, 'plan');
    return;
  }
  updateFilmStatus(button, filmId, 'plan', title).then(() => {
    showToast(`📅 Фильм "${title}" добавлен в Запланированные`, 'plan');
  });
}

// ------------------ Update Film Status ------------------
async function updateFilmStatus(button, filmId, action, title) {
  const originalContent = button.innerHTML;
  button.innerHTML = '...';
  button.disabled = true;

  try {
    const response = await fetch('/films/update-status/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: `film_id=${encodeURIComponent(filmId)}&action=${encodeURIComponent(action)}`
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    // Редирект для "watch"
    if (data.status === 'redirect' && data.url) {
      window.location.href = data.url;
      return;
    }

    // Ошибка
    if (data.status !== 'success') throw new Error(data.message || 'Неизвестная ошибка');

    // Применяем изменения статусов для карточки
    const card = button.closest('.glass-card');
    if (card) applyStatusChanges(card, action, data);

    return data; // возвращаем JSON, чтобы можно было использовать в switch-case

  } catch (error) {
    console.error('Update status error:', error);
    showToast('❌ Ошибка: ' + error.message, 'error');
  } finally {
    // Снимаем затемнение и восстанавливаем кнопку
    button.innerHTML = originalContent;
    button.disabled = false;
  }
}

// ------------------ Neon Toast ------------------
const neonColors = {
  favorite: 'rgba(182,94,101,0.75)',   // Мягкий кораллово-розовый
  success: 'rgba(94,151,134,0.75)',     // Бирюзовый, приглушённый
  plan: 'rgba(255, 190, 80, 0.75)',        // Тёплый янтарно-оранжевый
  info: 'rgba(92,116,156,0.87)',       // Спокойный голубовато-фиолетовый
  error: 'rgba(156,92,96,0.8)'        // Мягкий розово-красный
};

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.textContent = message;
  const color = neonColors[type] || neonColors.success;

  toast.style.cssText = `
    position: fixed;
    top: 20px; right: 20px;
    background: ${color};
    color: #fff;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    z-index: 9999;
    backdrop-filter: blur(10px);
    box-shadow: 0 0 12px ${color}, 0 0 25px ${color};
    font-family: Poppins, sans-serif;
    font-weight: 500;
    letter-spacing: 0.3px;
    opacity: 0; transform: translateY(-20px);
    transition: transform 0.4s ease, opacity 0.4s ease;
  `;

  document.body.appendChild(toast);
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-20px)';
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

// ------------------ Confirm Delete Modal ------------------
async function confirmDelete(action, title) {
  return new Promise((resolve) => {

    const isUnfavorite = action === 'unfavorite';

    const questionText = isUnfavorite
      ? `💔 Убрать фильм <strong style='color:#ffa07a;'>${title}</strong> из Любимого?`
      : action === 'delete-watched'
        ? `❗ Убрав фильм <strong style='color:#ffa07a;'>${title}</strong> из просмотренного, вы удалите отзыв и оценку. Продолжить удаление?`
        : `❌ Удалив фильм <strong style='color:#ffa07a;'>${title}</strong>, вы также удалите отзыв и оценку. Продолжить удаление?`;

    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed; inset: 0;
      background: rgba(10, 10, 25, 0.8);
      backdrop-filter: blur(4px);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    modal.innerHTML = `
      <div style="
        background: rgba(20,20,40,0.95);
        padding: 2rem;
        border-radius: 14px;
        max-width: 420px;
        width: 90%;
        text-align: center;
        font-family: Poppins, sans-serif;
        box-shadow: 0 0 25px rgba(255,120,80,0.3),
                    0 0 40px rgba(80,160,255,0.3);
        color: #f5f5f5;
        transform: scale(0.8);
        opacity: 0;
        transition: transform 0.3s ease, opacity 0.3s ease;
      ">
        <p style="font-size:1rem;">${questionText}</p>

        <div style="margin-top: 1.5rem;">
          <button id="confirm-yes" style="
            margin-right:1rem;
            padding:0.5rem 1.2rem;
            border:none;
            background: linear-gradient(90deg, #ff6b6b, #ff4757);
            color:white;
            border-radius:8px;
            cursor:pointer;
          ">Да</button>

          <button id="confirm-no" style="
            padding:0.5rem 1.2rem;
            border:none;
            background: rgba(140,140,160,0.4);
            color:white;
            border-radius:8px;
            cursor:pointer;
          ">Отмена</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const dialog = modal.querySelector('div');
    requestAnimationFrame(() => {
      dialog.style.transform = 'scale(1)';
      dialog.style.opacity = '1';
    });

    modal.querySelector('#confirm-yes').onclick = () => {
      modal.remove();
      resolve(true);
    };

    modal.querySelector('#confirm-no').onclick = () => {
      modal.remove();
      resolve(false);
    };
  });
}

// ------------------ Status Changes ------------------
function applyStatusChanges(card, action, data) {
  const overlay = card.querySelector('.movie-card__overlay');
  const badgesGroup = card.querySelector('.movie-badge-group');

  if (!overlay || !badgesGroup) return;

  // 1. Очистка (UI ← сервер)
  badgesGroup.innerHTML = '';
  overlay.querySelector('.movie-badge--rating')?.remove();

  if (data.has_review) {
    badgesGroup.innerHTML += `<span class="movie-badge movie-badge--watched">🍿</span>`;
  }

  if (data.is_planned) {
    badgesGroup.innerHTML += `<span class="movie-badge movie-badge--planned">📅</span>`;
  }

  if (data.is_favorite) {
    badgesGroup.innerHTML += `<span class="movie-badge movie-badge--favorite">🔥</span>`;
  }

  if (data.user_rating) {
    const rating = document.createElement('div');
    rating.className = 'movie-badge movie-badge--rating';
    rating.textContent = data.user_rating;
    overlay.prepend(rating);
  }

  if (action === 'delete') card.remove();
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    document.cookie.split(';').forEach(c => {
      const cookie = c.trim();
      if (cookie.startsWith(name + '=')) cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
    });
  }
  return cookieValue;
}