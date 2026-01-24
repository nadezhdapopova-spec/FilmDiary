document.addEventListener('DOMContentLoaded', () => {
  const grid = document.querySelector('.movie-search-grid');
  if (!grid) return;

  const page = grid.dataset.page; // 'my-films', 'favorites' и т.д.

  grid.addEventListener('click', async (e) => {
    const button = e.target.closest('.btn-icon');
    if (!button) return;

    e.preventDefault();

    const action = button.dataset.action;
    const filmId = button.dataset.id;  // tmdb_id
    const filmDbId = button.dataset.filmDbId;  // Film.id
    const title = button.dataset.title;
    if (!action || !filmId) return;

    const card = button.closest('.glass-card');

    switch (action) {
      case 'plan': {
          if (!filmDbId) {
              showToast('❌ Ошибка: не найден ID фильма', 'error');
              return;
          }
          if (card.querySelector('.movie-badge--planned')) {
              showToast(`📅 Фильм "${title}" уже запланирован`, 'info');
              return;
          }

          // Открыть модальное окно с выбором даты и заметкой
          createPlanModal(filmDbId, title);
          break;
      }

      case 'watch': {
        const data = await updateFilmStatus(button, filmId, action);
        if (!data || data.status !== 'success') return;
        break;
      }
      case 'favorite': {
        // ⛔ Уже в Любимом — не шлём запрос
        if (card.querySelector('.movie-badge--favorite')) {
          showToast(`🔥 Фильм "${title}" уже в Любимом`, 'info');
          return;
        }

        const data = await updateFilmStatus(button, filmId, action);
        if (!data || data.status !== 'success') return;

        showToast(`🔥 Фильм "${title}" добавлен в Любимое`, 'favorite');
        break;
      }
      case 'unfavorite': {
        const data = await updateFilmStatus(button, filmId, action);
        if (!data || data.status !== 'success') return;

        showToast(`💔 Фильм "${title}" убран из Любимого`, 'info');
        if (page === 'favorites') card.remove();
        break;
      }

      case 'edit-review': {
        const reviewId = button.dataset.reviewId;
        if (reviewId) {
          window.location.href = `/reviews/reviews/${reviewId}/`;
        }
        break;
      }

      case 'delete': {
        const confirmed = await confirmDelete('delete', title);
        if (!confirmed) return;

        const response = await fetch(`/films/${filmId}/delete/`, {
           method: 'POST',
           headers: {
               'X-CSRFToken': getCookie('csrftoken'),
               'X-Requested-With': 'XMLHttpRequest'
           }
        });

        if (response.ok) {
          showToast(`❌ Фильм "${title}" удалён`, 'error');
          card.remove();
        }
        break;
      }

      case 'delete-watched': {
        const reviewId = button.dataset.reviewId;

        const confirmed = await confirmDelete('delete-watched', title);
        if (!confirmed) return;

        const response = await fetch(`/reviews/${reviewId}/delete/`, {
           method: 'POST',
           headers: {
              'X-CSRFToken': getCookie('csrftoken'),
              'X-Requested-With': 'XMLHttpRequest'
           }
        });

        if (response.ok) {
            showToast(`➖ Фильм "${title}" убран из просмотренного`, 'info');
            card.remove();
        }
        break;
      }

    }
  });
});

// ------------------ Actions ------------------
function createPlanModal(filmDbId, title) {
  // if (!filmDbId || card.querySelector('.plan-form')) return null;

  const modal = document.createElement('div');
  modal.className = 'plan-modal';

  modal.innerHTML = `
    <div class="plan-modal__overlay"></div>
    <div class="plan-modal__content">
      <h3>📅 Запланировать просмотр</h3>
      <p class="plan-title">${title}</p>

      <input type="date" class="planned-date"
             value="${new Date().toISOString().slice(0, 10)}">

      <input type="text" class="planned-note"
             placeholder="Комментарий (необязательно)">

      <div class="plan-actions">
        <button class="save-plan-btn">Сохранить</button>
        <button class="cancel-plan-btn">Отмена</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // закрытие
  modal.querySelector('.plan-modal__overlay').onclick =
  modal.querySelector('.cancel-plan-btn').onclick = () => modal.remove();

  modal.querySelector('.save-plan-btn').onclick = async () => {
    const date = modal.querySelector('.planned-date').value;
    const note = modal.querySelector('.planned-note').value;

    const success = await addPlannedFilmAPI(filmDbId, date, note);
    if (!success) return;

    showToast(`📅 Фильм "${title}" добавлен в Запланированные`, 'plan');
    modal.remove();

    if (window.loadCalendarEvents) window.loadCalendarEvents();
  };
}

async function addPlannedFilmAPI(filmDbId, plannedDate, note = '') {
  try {
    const response = await fetch('/api/calendar_events/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({
        film: filmDbId,
        planned_date: plannedDate,
        note: note,
      })
    });

    const data = await response.json();

    if (!response.ok) {
      const msg =
        data?.non_field_errors?.[0] ||
        'Не удалось запланировать фильм';

      showToast(`📅 ${msg}`, 'info');
      return false;
    }

    return true;

  } catch (e) {
    console.error('Ошибка планирования:', e);
    showToast('❌ Не удалось запланировать фильм', 'error');
    return false;
  }
}

// ------------------ Update Film Status ------------------
async function updateFilmStatus(button, filmId, action) {
  const original = button.innerHTML;
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
      body: `tmdb_id=${encodeURIComponent(filmId)}&action=${encodeURIComponent(action)}`
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    // Редирект для "watch"
    if (data.status === 'redirect' && data.url) {
      window.location.href = data.url;
      return;
    }

    // Ошибка
    if (data.status !== 'success') throw new Error(data.message);

    // Применяем изменения статусов для карточки
    const card = button.closest('.glass-card');
    if (card) applyStatusChanges(card, data);

    return data; // возвращаем JSON, чтобы можно было использовать в switch-case

  } catch (e) {
    console.error(e);
    showToast('❌ Ошибка: ' + e.message, 'error');
  } finally {
    // Снимаем затемнение и восстанавливаем кнопку
    button.innerHTML = original;
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
function applyStatusChanges(card, data) {
  const badges = card.querySelector('.movie-badge-group');
  const overlay = card.querySelector('.movie-card__overlay');
  if (!badges || !overlay) return;

  // 1. Очистка (UI ← сервер)
  badges.innerHTML = '';
  overlay.querySelector('.movie-rating')?.remove();

  if (data.has_review) {
    badges.insertAdjacentHTML(
      'beforeend',
      `<span class="movie-badge movie-badge--watched" title="Просмотрено">🍿</span>`
    );
  }

  if (data.is_planned) {
    badges.insertAdjacentHTML(
      'beforeend',
      `<span class="movie-badge movie-badge--planned" title="Запланировано">📅</span>`
    );
  }

  if (data.is_favorite) {
    badges.insertAdjacentHTML(
      'beforeend',
      `<span class="movie-badge movie-badge--favorite" title="Любимое">🔥</span>`
    );
  }

  if (data.user_rating) {
    const rating = document.createElement('span');
    rating.className = 'movie-rating movie-badge movie-badge--rating';
    rating.textContent = data.user_rating;
    overlay.appendChild(rating);
  }

}

function getCookie(name) {
  return document.cookie
    .split('; ')
    .find(c => c.startsWith(name + '='))
    ?.split('=')[1];
}