document.addEventListener('DOMContentLoaded', () => {
  const ratingBlocks = document.querySelectorAll('.stars');
  const avgEl = document.getElementById('avg-rating');

  function updateAverage() {
    let sum = 0;
    let count = 0;

    document.querySelectorAll('.rating-row input[type="hidden"]').forEach(input => {
      if (input.value) {
        sum += parseFloat(input.value);
        count++;
      }
    });

    avgEl.textContent = count ? (sum / count).toFixed(1) : '—';
  }

  function initStarsFromInputs() {
    ratingBlocks.forEach(block => {
      const inputId = block.dataset.inputId;
      const input = document.getElementById(inputId);
      const stars = block.querySelectorAll('.star');

      if (!input || !input.value) return;

      const value = parseFloat(input.value);

      stars.forEach(star => {
        const starValue = parseInt(star.dataset.value, 10);
        star.classList.toggle('active', starValue <= Math.round(value));
      });
    });

    updateAverage();
  }

  ratingBlocks.forEach(block => {
    const inputId = block.dataset.inputId;
    const input = document.getElementById(inputId);
    const stars = block.querySelectorAll('.star');

    stars.forEach(star => {
      star.addEventListener('click', () => {
        const value = parseInt(star.dataset.value, 10);
        input.value = value;

        stars.forEach(s => {
          s.classList.toggle('active', s.dataset.value <= value);
        });

        updateAverage();
      });
    });
  });

  initStarsFromInputs();
});
