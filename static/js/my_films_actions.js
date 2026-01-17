document.addEventListener('DOMContentLoaded', function () {
  const grid = document.querySelector('.movie-search-grid');
  if (!grid) return;

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
        openPlanForm(filmId, title, button);
        break;

      case 'watch':
        openReviewForm(filmId);
        break;

      case 'favorite':
        if (card.querySelector('.movie-badge--favorite')) {
          showToast(`🔥 Фильм "${title}" уже в Любимых`, 'info');
          return;
        }
        await updateFilmStatus(button, filmId, action, title);
        showToast(`🔥 Фильм "${title}" добавлен в Любимое`, 'favorite');
        button.disabled = true;
        button.style.opacity = '0.5';
        button.title = 'Уже в Любимых';
        break;

      case 'unfavorite': {
        const confirmedUnfav = await confirmDelete(filmId, title);
        if (!confirmedUnfav) return;

        await updateFilmStatus(button, filmId, action, title);
        showToast(`🔥 Фильм "${title}" убран из Любимого`, 'info');
        break;
      }

      case 'delete':
        const confirmed = await confirmDelete(filmId, title);
        if (confirmed) {
          await updateFilmStatus(button, filmId, action, title);
          showToast(`❌ Фильм "${title}" удалён`, 'error');
        }
        break;

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
  updateFilmStatus(button, filmId, 'plan', title).then(() => {
    showToast(`📅 Фильм "${title}" добавлен в Запланированные`, 'plan');
    button.disabled = true;
    button.style.opacity = '0.5';
    button.title = 'Уже в Запланированных';
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
    if (data.status !== 'success') throw new Error(data.message || 'Неизвестная ошибка');

    const card = button.closest('.glass-card');
    if (card) applyStatusChanges(card, action, data);

  } catch (error) {
    console.error('Update status error:', error);
    showToast('❌ Ошибка: ' + error.message, 'error');
  } finally {
    button.innerHTML = originalContent;
    if (action !== 'favorite' && action !== 'plan') button.disabled = false;
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
async function confirmDelete(filmId, title) {
  return new Promise((resolve) => {
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed; top:0; left:0; width:100%; height:100%;
      background: rgba(10, 10, 25, 0.8);
      backdrop-filter: blur(4px);
      display: flex; justify-content: center; align-items: center;
      z-index: 10000;
    `;

    modal.innerHTML = `
      <div style="
        background: rgba(20,20,40,0.95);
        padding: 2rem; border-radius: 14px;
        max-width: 420px; width: 90%; text-align: center;
        font-family: Poppins, sans-serif;
        box-shadow: 0 0 25px rgba(255,120,80,0.3), 0 0 40px rgba(80,160,255,0.3);
        color: #f5f5f5;
        transform: scale(0.8);
        opacity: 0;
        transition: transform 0.3s ease, opacity 0.3s ease;
      ">
        <p style="font-size:1rem;">❌ Удалить фильм <strong style='color:#ffa07a;'>${title}</strong>?</p>
        <div style="margin-top: 1.5rem;">
          <button id="confirm-yes" style="
            margin-right:1rem; padding:0.5rem 1.2rem; border:none;
            background: linear-gradient(90deg, #ff6b6b, #ff4757);
            color:white; border-radius:8px; cursor:pointer;
            box-shadow: 0 0 10px #ff6b6b, 0 0 20px #ff7f7f;
          ">Да</button>
          <button id="confirm-no" style="
            padding:0.5rem 1.2rem; border:none;
            background: rgba(140,140,160,0.4);
            color:white; border-radius:8px; cursor:pointer;
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

    modal.querySelector('#confirm-yes').addEventListener('click', () => {
      modal.remove();
      resolve(true);
    });

    modal.querySelector('#confirm-no').addEventListener('click', () => {
      modal.remove();
      resolve(false);
    });
  });
}

// ------------------ Status Changes ------------------
function applyStatusChanges(card, action, data) {
  const badgesGroup = card.querySelector('.movie-badge-group');

  if (badgesGroup) {

    // PLANNED
    if (data.is_planned && !badgesGroup.querySelector('.movie-badge--planned')) {
      const span = document.createElement('span');
      span.className = 'movie-badge movie-badge--planned';
      span.title = 'Запланировано';
      span.textContent = '📅';
      badgesGroup.prepend(span);
    }

    // FAVORITE
    if (action === 'favorite' && data.is_favorite) {
      if (!badgesGroup.querySelector('.movie-badge--favorite')) {
        const span = document.createElement('span');
        span.className = 'movie-badge movie-badge--favorite';
        span.title = 'Любимое';
        span.textContent = '🔥';
        badgesGroup.append(span);
      }
    }

    // UNFAVORITE
    if (action === 'unfavorite') {
      const favBadge = badgesGroup.querySelector('.movie-badge--favorite');
      if (favBadge) favBadge.remove();

      // если это страница Любимое — удаляем карточку
      card.remove();
    }
  }

  // DELETE
  if (action === 'delete') {
    const outerCard = card.closest('.glass-card');
    if (outerCard) outerCard.remove();
  }
}

// ------------------ Get CSRF ------------------
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
      const cookie = c.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}