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

    document.getElementById('avg-rating').textContent =
      count ? (sum / count).toFixed(1) : '—';
  }

  ratingBlocks.forEach(block => {
    const inputId = block.dataset.inputId;
    const input = document.getElementById(inputId);
    const stars = block.querySelectorAll('.star');

    stars.forEach(star => {
      star.addEventListener('click', () => {
        const value = parseInt(star.dataset.value);
        input.value = value;

        stars.forEach(s => {
          s.classList.toggle('active', s.dataset.value <= value);
        });

        updateAverage();
      });
    });
  });
});
