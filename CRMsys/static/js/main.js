// Основной JavaScript файл

// Глобальные переменные
let autoRefreshInterval = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Инициализация popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Настройка автообновления
    setupAutoRefresh();

    // Настройка обработчиков событий
    setupEventListeners();

    // Загрузка начальных данных
    loadInitialData();
});

// Настройка автообновления
function setupAutoRefresh() {
    const refreshToggle = document.getElementById('autoRefreshToggle');
    if (refreshToggle) {
        refreshToggle.addEventListener('change', function() {
            if (this.checked) {
                autoRefreshInterval = setInterval(function() {
                    if (!document.hidden) {
                        refreshDashboard();
                    }
                }, 30000); // 30 секунд
                showToast('Автообновление включено', 'success');
            } else {
                clearInterval(autoRefreshInterval);
                showToast('Автообновление выключено', 'info');
            }
        });
    }
}

// Обновление дашборда
function refreshDashboard() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        refreshBtn.disabled = true;
    }

    fetch('/api/dashboard/stats')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
            
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Обновить';
                refreshBtn.disabled = false;
            }
            
            showToast('Дашборд обновлен', 'success');
        })
        .catch(error => {
            console.error('Ошибка обновления:', error);
            showToast('Ошибка обновления', 'error');
            
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Обновить';
                refreshBtn.disabled = false;
            }
        });
}

// Обновление статистики на дашборде
function updateDashboardStats(stats) {
    // Обновление счетчиков
    for (const [key, value] of Object.entries(stats)) {
        const element = document.getElementById(`stat-${key}`);
        if (element) {
            animateCounter(element, value);
        }
    }

    // Обновление графиков (если есть)
    if (window.updateCharts) {
        window.updateCharts(stats);
    }
}

// Анимация счетчика
function animateCounter(element, targetValue) {
    const currentValue = parseInt(element.textContent) || 0;
    const duration = 500; // мс
    const step = (targetValue - currentValue) / (duration / 16);
    
    let current = currentValue;
    const timer = setInterval(() => {
        current += step;
        if ((step > 0 && current >= targetValue) || (step < 0 && current <= targetValue)) {
            element.textContent = targetValue;
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, 16);
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Поиск
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            performSearch(this.value);
        }, 300));
    }

    // Фильтры
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            applyFilter(filter);
        });
    });

    // Экспорт данных
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportData);
    }

    // Уведомления
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', markAllNotificationsAsRead);
    }
}

// Выполнение поиска
function performSearch(query) {
    if (query.length < 2) {
        clearSearchResults();
        return;
    }

    fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data);
        })
        .catch(error => {
            console.error('Ошибка поиска:', error);
        });
}

// Отображение результатов поиска
function displaySearchResults(results) {
    const resultsContainer = document.getElementById('searchResults');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = '';
    
    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="text-center py-3 text-muted">Ничего не найдено</div>';
        return;
    }

    results.forEach(result => {
        const item = document.createElement('a');
        item.href = result.url;
        item.className = 'list-group-item list-group-item-action';
        item.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">${result.title}</h6>
                <small>${result.type}</small>
            </div>
            <p class="mb-1">${result.description}</p>
            <small>${result.date}</small>
        `;
        resultsContainer.appendChild(item);
    });
}

// Применение фильтра
function applyFilter(filter) {
    const url = new URL(window.location);
    url.searchParams.set('filter', filter);
    window.location.href = url.toString();
}

// Экспорт данных
function exportData() {
    const format = document.getElementById('exportFormat').value;
    const url = `/api/export?format=${format}`;
    
    showToast('Экспорт начат...', 'info');
    
    fetch(url)
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `export_${new Date().toISOString().slice(0,10)}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('Экспорт завершен', 'success');
        })
        .catch(error => {
            console.error('Ошибка экспорта:', error);
            showToast('Ошибка экспорта', 'error');
        });
}

// Пометить все уведомления как прочитанные
function markAllNotificationsAsRead() {
    fetch('/api/notifications/mark-all-read', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.querySelectorAll('.notification-unread').forEach(el => {
                el.classList.remove('notification-unread');
                el.classList.add('notification-read');
            });
            
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                badge.remove();
            }
            
            showToast('Все уведомления прочитаны', 'success');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showToast('Ошибка обновления уведомлений', 'error');
    });
}

// Вспомогательные функции
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        // Создать контейнер для тостов
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    document.getElementById('toastContainer').appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', function () {
        this.remove();
    });
}

// Загрузка начальных данных
function loadInitialData() {
    // Загрузка уведомлений
    loadNotifications();

    // Загрузка статистики
    loadStats();
}

function loadNotifications() {
    fetch('/api/notifications/unread-count')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadge(data.count);
        })
        .catch(console.error);
}

function loadStats() {
    fetch('/api/dashboard/quick-stats')
        .then(response => response.json())
        .then(data => {
            // Обновление мини-виджетов
            Object.entries(data).forEach(([key, value]) => {
                const element = document.getElementById(`quick-stat-${key}`);
                if (element) {
                    element.textContent = value;
                }
            });
        })
        .catch(console.error);
}

function updateNotificationBadge(count) {
    let badge = document.querySelector('.notification-badge');
    if (count > 0) {
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'notification-badge badge bg-danger rounded-pill';
            const bell = document.querySelector('.fa-bell').parentElement;
            bell.appendChild(badge);
        }
        badge.textContent = count;
    } else if (badge) {
        badge.remove();
    }
}

// API функции
window.api = {
    updateTaskStatus: function(taskId, status) {
        return fetch(`/api/tasks/${taskId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: status })
        });
    },

    addComment: function(requestId, comment, isInternal) {
        return fetch(`/api/requests/${requestId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: comment,
                is_internal: isInternal
            })
        });
    },

    getRequestStatus: function(requestId) {
        return fetch(`/api/requests/${requestId}/status`)
            .then(response => response.json());
    }
};