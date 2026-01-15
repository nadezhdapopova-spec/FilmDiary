// Инициализация после загрузки DOM
document.addEventListener('DOMContentLoaded', function () {
  // контейнер с карточками
  const grid = document.querySelector('.movie-search-grid');
  if (!grid) return;

  // Делегирование кликов по иконкам
  grid.addEventListener('click', async function (e) {
    const button = e.target.closest('.btn-icon');
    if (!button) return;

    const action = button.dataset.action;
    const filmId = button.dataset.id;
    const title = button.dataset.title;

    if (!action || !filmId) return;

    e.preventDefault();

    switch (action) {
      case 'plan':
      case 'watch':
      case 'unwatch':
      case 'favorite':
      case 'unfavorite':
      case 'delete':
        await updateFilmStatus(button, filmId, action, title);
        break;

      case 'edit-review':
        // Здесь можно открыть модалку или перейти на страницу редактирования
        // openReviewModal(filmId);
        showToast('✍️ Редактирование отзыва пока не реализовано');
        break;

      default:
        console.warn('Неизвестное действие:', action);
    }
  });
});

/**
 * Обновление статуса фильма на сервере и частичное обновление UI.
 * Ожидается, что сервер вернёт JSON с флагами вида:
 * { status: "success", message: "...", is_watched: true/false, is_planned: ..., is_favorite: ... }
 */
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

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (data.status !== 'success') {
      throw new Error(data.message || 'Неизвестная ошибка');
    }

    const card = button.closest('.movie-card');
    if (card) {
      applyStatusChanges(card, action, data);
    }

    showToast(data.message || '✅ Статус обновлён');
  } catch (error) {
    console.error('Update status error:', error);
    showToast('❌ Ошибка: ' + error.message);
  } finally {
    button.innerHTML = originalContent;
    button.disabled = false;
  }
}

/**
 * Применяем изменения в интерфейсе в зависимости от действия и нового состояния.
 * card — элемент .movie-card (article), data — JSON от сервера.
 */
function applyStatusChanges(card, action, data) {
  const badgesGroup = card.querySelector('.movie-badge-group');
  const footer = card.querySelector('.movie-card__footer--compact');
  if (!footer) return;

  // 1. Обновляем бейджи над постером
  if (badgesGroup) {
    updateBadges(badgesGroup, data);
  }

  // 2. Обновляем иконки в футере (data-action и title)
  const actionsRow = footer.querySelector('.movie-card__actions-row');
  if (!actionsRow) return;

  const buttons = actionsRow.querySelectorAll('.btn-icon');

  buttons.forEach(btn => {
    const btnAction = btn.dataset.action;

    if (btnAction === 'plan' || btnAction === 'watch' || btnAction === 'unwatch') {
      // Кнопка, связанная с просмотром / планами
      if (data.is_watched) {
        // Фильм в просмотренных: показываем "unwatch"
        btn.dataset.action = 'unwatch';
        btn.title = 'Убрать из просмотренного';
        btn.innerHTML = `
          <span class="btn-remove-watched__icon">👁️</span>
          <span class="btn-remove-watched__cross">✕</span>
        `;
      } else if (data.is_planned) {
        // Фильм запланирован: кнопка "watch"
        btn.dataset.action = 'watch';
        btn.title = 'Добавить в Просмотрено';
        btn.textContent = '🍿';
      } else {
        // Ничего не запланировано: кнопка "plan"
        btn.dataset.action = 'plan';
        btn.title = 'Запланировать';
        btn.textContent = '📅';
      }
    }

    if (btnAction === 'favorite' || btnAction === 'unfavorite') {
      if (data.is_favorite) {
        btn.dataset.action = 'unfavorite';
        btn.title = 'Убрать из Любимого';
        btn.textContent = '⛔';
      } else {
        btn.dataset.action = 'favorite';
        btn.title = 'Добавить в Любимое';
        btn.textContent = '🔥';
      }
    }

    if (btnAction === 'delete') {
      // Поведение удаления карты зависит от логики на бэке:
      // здесь предположим, что delete просто убирает фильм из списка.
      if (action === 'delete' && data.removed) {
        const outerCard = card.closest('.movie-card.glass-card') || card;
        outerCard.remove();
      }
    }
  });
}

/**
 * Обновление бейджей над постером (просмотрено, запланировано, избранное).
 */
function updateBadges(badgesGroup, data) {
  const watchedBadge = badgesGroup.querySelector('.movie-badge--watched');
  const plannedBadge = badgesGroup.querySelector('.movie-badge--planned');
  const favoriteBadge = badgesGroup.querySelector('.movie-badge--favorite');

  // Просмотрено
  if (data.is_watched) {
    if (!watchedBadge) {
      const span = document.createElement('span');
      span.className = 'movie-badge movie-badge--watched';
      span.title = 'Просмотрено';
      span.textContent = '🍿';
      badgesGroup.prepend(span);
    }
  } else if (watchedBadge) {
    watchedBadge.remove();
  }

  // Запланировано
  if (data.is_planned && !data.is_watched) {
    if (!plannedBadge) {
      const span = document.createElement('span');
      span.className = 'movie-badge movie-badge--planned';
      span.title = 'Запланировано';
      span.textContent = '📅';
      badgesGroup.prepend(span);
    }
  } else if (plannedBadge) {
    plannedBadge.remove();
  }

  // Любимое
  if (data.is_favorite) {
    if (!favoriteBadge) {
      const span = document.createElement('span');
      span.className = 'movie-badge movie-badge--favorite';
      span.title = 'Любимое';
      span.textContent = '🔥';
      badgesGroup.append(span);
    }
  } else if (favoriteBadge) {
    favoriteBadge.remove();
  }
}

/**
 * Получение CSRF токена из cookie.
 */
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

/**
 * Простейший toast.
 */
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