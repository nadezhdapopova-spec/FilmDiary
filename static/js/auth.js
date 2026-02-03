function togglePassword(inputId, icon) {
    const input = document.getElementById(inputId);

    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        icon.classList.replace("bi-eye", "bi-eye-slash");
    } else {
        input.type = "password";
        icon.classList.replace("bi-eye-slash", "bi-eye");
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const passwordInput = document.getElementById("id_password1");
    const strengthBar = document.getElementById("password-strength-bar");

    if (!passwordInput || !strengthBar) return;

    passwordInput.addEventListener("input", function () {
        const value = passwordInput.value;
        let strength = 0;

        if (value.length >= 8) strength++;
        if (/[A-Z]/.test(value)) strength++;
        if (/[0-9]/.test(value)) strength++;
        if (/[^A-Za-z0-9]/.test(value)) strength++;

        const percent = strength * 25;
        let color = "#dc3545"; // красный

        if (strength === 2) color = "#ffc107"; // желтый
        if (strength >= 3) color = "#198754"; // зеленый

        strengthBar.style.width = percent + "%";
        strengthBar.style.backgroundColor = color;
    });
});