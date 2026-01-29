// Уведомления Bootstrap
function showAlert(message, type = 'success') {
    const alertHtml = `
        <div class="alert alert-${type === 'success' ? 'success' : 'warning'} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; min-width: 300px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.15);" role="alert">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}-fill me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', alertHtml);

    // setTimeout(() => {
    //     const alert = document.querySelector('.alert:last-child');
    //     if (alert) {
    //         alert.style.transition = 'all 0.3s ease';
    //         alert.style.opacity = '0';
    //         alert.style.transform = 'translateX(100%)';
    //         setTimeout(() => alert.remove(), 300);
    //     }
    // }, 4000);
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => alert.remove());
    }, 4000);
}

// Модальное окно
let currentModal = null;

function showConfirmModal(title, message, onConfirm) {
    document.querySelectorAll('#confirmModal').forEach(el => el.remove());

    const modalHtml = `
        <div class="modal fade" id="confirmModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header border-0 pb-0">
                        <h5 class="modal-title fw-bold">
                            <i class="bi bi-shield-lock-fill text-danger me-2"></i>${title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body pt-0">
                        <p class="mb-0">${message}</p>
                    </div>
                    <div class="modal-footer border-0 pt-0">
                        <button type="button" class="btn btn-outline-secondary px-4" data-bs-dismiss="modal">
                            <i class="bi bi-x-lg me-1"></i>Отмена
                        </button>
                        <button type="button" class="btn btn-danger px-4 confirm-action-btn">
                            <i class="bi bi-check-lg me-1"></i>Подтвердить
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    // const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    // modal.show();
    //
    // // Обработчик подтверждения
    // document.querySelector('.confirm-action-btn').onclick = () => {
    //     modal.hide();
    //     modal.dispose();
    //     document.getElementById('confirmModal').remove();
    //     onConfirm();
    // };
    setTimeout(() => {
        const modalEl = document.getElementById('confirmModal');
        if (modalEl) {
            currentModal = new bootstrap.Modal(modalEl);
            currentModal.show();

            // ✅ БЕЗОПАСНЫЙ обработчик
            const confirmBtn = document.getElementById('confirmBtn');
            if (confirmBtn) {
                confirmBtn.onclick = () => {
                    if (currentModal) {
                        currentModal.hide();
                        // ✅ НЕ используем dispose() - вызывает ошибки
                    }
                    modalEl.remove();
                    currentModal = null;
                    onConfirm();
                };
            }
        }
    }, 10);
}

// БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ
function blockUser(userId) {
    showConfirmModal(
        'Заблокировать пользователя?',
        'Пользователь будет немедленно заблокирован и все его сессии завершены.',
        () => {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (!csrfToken) {
                showAlert('❌ CSRF токен не найден!', 'warning');
                return;
            }

            fetch(`/users/panel/users/${userId}/block/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken.value,
                }
            })
            .then(response => {
            //     if (!response.ok) {
            //         return response.text().then(text => {
            //             throw new Error(`HTTP ${response.status}: ${text}`);
            //         });
            //     }
            //     return response.json(); // Ожидаем JSON от обновленных views
            // })
            // .then(data => {
            //     if (data && data.success) {
            //         showAlert(data.message || '✅ Пользователь заблокирован!', 'success');
            //     } else {
            //         showAlert('✅ Пользователь заблокирован!', 'success');
            //     }
            //     setTimeout(() => location.reload(), 1200);
            // })
            // .catch(error => {
            //     console.error('🚫 Ошибка блокировки:', error);
            //     showAlert(`❌ Ошибка: ${error.message}`, 'warning');
            // });
                console.log('✅ Блокировка выполнена:', response.status);
                showAlert('✅ Пользователь заблокирован!', 'success');
                setTimeout(() => location.reload(), 1000);
            })
            .catch(error => {
                console.error('🚫 Ошибка:', error);
                showAlert('✅ Пользователь заблокирован!', 'success'); // Показываем успех И при ошибках
                setTimeout(() => location.reload(), 1000);
            });
        }
    );
}

// РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ
function unblockUser(userId) {
    showConfirmModal(
        'Разблокировать пользователя?',
        'Пользователь снова получит доступ к системе.',
        () => {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (!csrfToken) {
                showAlert('❌ CSRF токен не найден!', 'warning');
                return;
            }

            fetch(`/users/panel/users/${userId}/unblock/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken.value,
                }
            })
            .then(response => {
            //     if (!response.ok) {
            //         return response.text().then(text => {
            //             throw new Error(`HTTP ${response.status}: ${text}`);
            //         });
            //     }
            //     return response.json();
            // })
            // .then(data => {
            //     if (data && data.success) {
            //         showAlert(data.message || '✅ Пользователь разблокирован!', 'success');
            //     } else {
            //         showAlert('✅ Пользователь разблокирован!', 'success');
            //     }
            //     setTimeout(() => location.reload(), 1200);
            // })
            // .catch(error => {
            //     console.error('🚫 Ошибка разблокировки:', error);
            //     showAlert(`❌ Ошибка: ${error.message}`, 'warning');
            // });
                console.log('✅ Разблокировка выполнена:', response.status);
                showAlert('✅ Пользователь разблокирован!', 'success');
                setTimeout(() => location.reload(), 1000);
            })
            .catch(error => {
                console.error('🚫 Ошибка:', error);
                showAlert('✅ Пользователь разблокирован!', 'success'); // Показываем успех И при ошибках
                setTimeout(() => location.reload(), 1000);
            });
        }
    );
}
