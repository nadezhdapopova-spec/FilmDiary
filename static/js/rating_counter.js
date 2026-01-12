document.addEventListener('DOMContentLoaded', function() {
    const ratings = ['plot_rating', 'acting_rating', 'directing_rating',
                    'visuals_rating', 'soundtrack_rating'];
    const avgDisplay = document.getElementById('avg-rating');

    ratings.forEach(field => {
        const input = document.querySelector(`input[name="${field}"]`);
        input.addEventListener('input', updateAverage);
    });

    function updateAverage() {
        let sum = 0, count = 0;
        ratings.forEach(field => {
            const val = parseFloat(document.querySelector(`input[name="${field}"]`).value) || 0;
            if (val) { sum += val; count++; }
        });
        avgDisplay.textContent = count ? (sum/count).toFixed(1) : '-';
    }
});