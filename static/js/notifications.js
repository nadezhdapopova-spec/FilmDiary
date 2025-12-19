document.addEventListener("DOMContentLoaded", () => {
    if (!window.djangoMessages) return;

    const notyf = new Notyf({
        duration: 4000,
        position: {
            x: "right",
            y: "top",
        },
        dismissible: true,
        ripple: false,
        types: [
            {
                type: "success",
                background: "#000",
                icon: {
                    className: "bi bi-check-circle-fill",
                    tagName: "i",
                    color: "#fff",
                },
            },
            {
                type: "error",
                background: "#000",
                icon: {
                    className: "bi bi-exclamation-circle-fill",
                    tagName: "i",
                    color: "#fff",
                },
            },
            {
                type: "info",
                background: "#000",
                icon: {
                    className: "bi bi-info-circle-fill",
                    tagName: "i",
                    color: "#fff",
                },
            },
            {
                type: "warning",
                background: "#000",
                icon: {
                    className: "bi bi-exclamation-triangle-fill",
                    tagName: "i",
                    color: "#fff",
                },
            },
        ],
    });

    window.djangoMessages.forEach((msg) => {
        notyf.open({
            type: msg.level || "info",
            message: msg.text,
        });
    });
});

document.addEventListener('DOMContentLoaded', function () {
  var offcanvasEl = document.getElementById('sideMenu');
  if (!offcanvasEl) return;

  offcanvasEl.addEventListener('show.bs.offcanvas', function () {
    document.body.classList.add('sidebar-open');
  });

  offcanvasEl.addEventListener('hidden.bs.offcanvas', function () {
    document.body.classList.remove('sidebar-open');
  });
});
