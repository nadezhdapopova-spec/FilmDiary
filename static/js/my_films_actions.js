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

    e.preventDefault();

    switch (action) {
      case 'plan':
        openPlanForm(filmId, title);
        break;

      case 'watch':
        openReviewForm(filmId, title);
        break;

      case 'favorite':
        await updateFilmStatus(button, filmId, action, title)
          .then(() => showToast(`🔥 Фильм "${title}" добавлен в Любимое`));
        break;

      case 'delete':
        const confirmed = await confirmDelete(filmId, title);
        if (confirmed) {
          await updateFilmStatus(button, filmId, action, title);
          showToast(`Фильм "${title}" удалён`, true);
        }
        break;

      default:
        console.warn('Неизвестное действие:', action);
    }
  });
});

// ------------------ Actions ------------------
function openReviewForm(filmId, title) {
  window.location.href = `/films/${filmId}/review/`;
}

function openPlanForm(filmId, title) {
  showToast(`📅 Фильм "${title}" добавлен в Запланированные`, true);
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

    const card = button.closest('.movie-card');
    if (card) applyStatusChanges(card, action, data);

  } catch (error) {
    console.error('Update status error:', error);
    showToast('❌ Ошибка: ' + error.message, false);
  } finally {
    button.innerHTML = originalContent;
    button.disabled = false;
  }
}

// ------------------ Toast ------------------
function showToast(message, success = true) {
  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    top: 20px; right: 20px;
    background: ${success ? 'linear-gradient(135deg, #4caf50, #81c784)' : 'linear-gradient(135deg, #f44336, #e57373)'};
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    backdrop-filter: blur(10px);
    z-index: 9999;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    font-family: Poppins, sans-serif;
    font-weight: 500;
    opacity: 0; transform: translateY(-20px);
    transition: transform 0.4s ease, opacity 0.4s ease;
  `;
  document.body.appendChild(toast);

  // Появление
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  // Исчезновение через 3 секунды
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-20px)';
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

// ------------------ Confirm Delete ------------------
async function confirmDelete(filmId, title) {
  return new Promise((resolve) => {
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed; top:0; left:0; width:100%; height:100%;
      background: rgba(0,0,0,0.6);
      display: flex; justify-content: center; align-items: center;
      z-index: 10000;
    `;

    modal.innerHTML = `
      <div style="
        background: #fff; padding: 2rem; border-radius: 12px;
        max-width: 400px; width: 90%; text-align: center;
        font-family: Poppins, sans-serif;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transform: scale(0.8);
        opacity: 0;
        transition: transform 0.3s ease, opacity 0.3s ease;
      ">
        <p style="font-size:1rem;">❌ Вы действительно хотите удалить фильм <strong>${title}</strong>?</p>
        <div style="margin-top: 1.5rem;">
          <button id="confirm-yes" style="
            margin-right:1rem; padding:0.5rem 1rem; border:none;
            background:#f44336; color:white; border-radius:6px; cursor:pointer;
          ">Да</button>
          <button id="confirm-no" style="
            padding:0.5rem 1rem; border:none; background:#9e9e9e;
            color:white; border-radius:6px; cursor:pointer;
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
    // WATCHED
    if (data.is_watched) {
      let watchedBadge = badgesGroup.querySelector('.movie-badge--watched');
      if (!watchedBadge) {
        const span = document.createElement('span');
        span.className = 'movie-badge movie-badge--watched';
        span.title = 'Просмотрено';
        span.textContent = '🍿';
        badgesGroup.prepend(span);
      }
    }

    // PLANNED
    if (data.is_planned) {
      let plannedBadge = badgesGroup.querySelector('.movie-badge--planned');
      if (!plannedBadge) {
        const span = document.createElement('span');
        span.className = 'movie-badge movie-badge--planned';
        span.title = 'Запланировано';
        span.textContent = '📅';
        badgesGroup.prepend(span);
      }
    }

    // FAVORITE
    if (data.is_favorite) {
      let favoriteBadge = badgesGroup.querySelector('.movie-badge--favorite');
      if (!favoriteBadge) {
        const span = document.createElement('span');
        span.className = 'movie-badge movie-badge--favorite';
        span.title = 'Любимое';
        span.textContent = '🔥';
        badgesGroup.append(span);
      }
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