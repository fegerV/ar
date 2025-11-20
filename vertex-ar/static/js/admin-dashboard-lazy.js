/**
 * Admin Dashboard Lazy-Loaded Features
 * Non-critical functionality that can be loaded after initial page render
 */

// Advanced charts and analytics
const loadAdvancedAnalytics = async () => {
    try {
        // Dynamic import of charting library
        const { Chart } = await import('https://cdn.jsdelivr.net/npm/chart.js');
        
        // Initialize charts if containers exist
        initializeCharts(Chart);
    } catch (error) {
        console.warn('Failed to load charting library:', error);
    }
};

const initializeCharts = (Chart) => {
    // Client growth chart
    const clientChartCtx = document.getElementById('clientGrowthChart');
    if (clientChartCtx) {
        new Chart(clientChartCtx, {
            type: 'line',
            data: {
                labels: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн'],
                datasets: [{
                    label: 'Новые клиенты',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-color')
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-color')
                        },
                        grid: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--border-color')
                        }
                    },
                    x: {
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-color')
                        },
                        grid: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--border-color')
                        }
                    }
                }
            }
        });
    }
    
    // Storage usage chart
    const storageChartCtx = document.getElementById('storageUsageChart');
    if (storageChartCtx) {
        new Chart(storageChartCtx, {
            type: 'doughnut',
            data: {
                labels: ['Изображения', 'Видео', 'Превью', 'Другое'],
                datasets: [{
                    data: [30, 50, 15, 5],
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-color')
                        }
                    }
                }
            }
        });
    }
};

// Advanced search and filtering
const initializeAdvancedSearch = () => {
    const searchInput = document.getElementById('advancedSearch');
    if (!searchInput) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            displayRecords(); // Show all records
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
};

const performSearch = async (query) => {
    try {
        const response = await fetch(`/admin/search?q=${encodeURIComponent(query)}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            AdminDashboard.setState({ allRecords: data.results || [] });
            AdminDashboard.setState({ currentPage: 1 });
            displayRecords();
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast('Ошибка поиска', 'error');
    }
};

// Real-time notifications
const initializeRealTimeNotifications = () => {
    if (!window.EventSource) return;
    
    const eventSource = new EventSource('/admin/notifications');
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleRealTimeNotification(data);
    };
    
    eventSource.onerror = function(error) {
        console.warn('EventSource failed:', error);
        eventSource.close();
    };
};

const handleRealTimeNotification = (notification) => {
    showToast(notification.message, notification.type || 'info');
    addLog(`Уведомление: ${notification.message}`, notification.type || 'info');
    
    // Update relevant UI sections
    switch (notification.type) {
        case 'new_order':
            loadRecords();
            loadStatistics();
            break;
        case 'system_alert':
            loadSystemInfo();
            break;
        case 'backup_complete':
            loadBackupStats();
            break;
    }
};

// Export functionality
const initializeExportFeatures = () => {
    const exportBtn = document.getElementById('exportDataBtn');
    if (!exportBtn) return;
    
    exportBtn.addEventListener('click', async () => {
        try {
            showLoading();
            
            const response = await fetch('/admin/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    format: 'csv',
                    include: ['clients', 'portraits', 'orders']
                }),
                credentials: 'include'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `admin-export-${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showToast('Данные экспортированы успешно', 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            showToast('Ошибка экспорта данных', 'error');
        } finally {
            hideLoading();
        }
    });
};

// Advanced user preferences
const initializeUserPreferences = () => {
    const preferencesBtn = document.getElementById('preferencesBtn');
    if (!preferencesBtn) return;
    
    preferencesBtn.addEventListener('click', () => {
        showPreferencesModal();
    });
};

const showPreferencesModal = () => {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Настройки панели</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="autoRefreshToggle" ${AdminDashboard.state.autoRefresh ? 'checked' : ''}>
                        Автообновление (${AdminDashboard.state.refreshInterval / 1000} сек)
                    </label>
                </div>
                <div class="form-group">
                    <label for="refreshInterval">Интервал обновления (сек):</label>
                    <input type="number" id="refreshInterval" min="10" max="300" value="${AdminDashboard.state.refreshInterval / 1000}">
                </div>
                <div class="form-group">
                    <label for="recordsPerPage">Записей на странице:</label>
                    <select id="recordsPerPage">
                        <option value="10" ${AdminDashboard.state.recordsPerPage === 10 ? 'selected' : ''}>10</option>
                        <option value="25" ${AdminDashboard.state.recordsPerPage === 25 ? 'selected' : ''}>25</option>
                        <option value="50" ${AdminDashboard.state.recordsPerPage === 50 ? 'selected' : ''}>50</option>
                        <option value="100" ${AdminDashboard.state.recordsPerPage === 100 ? 'selected' : ''}>100</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="compactMode">
                        Компактный режим
                    </label>
                </div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn cancel">Отмена</button>
                <button class="modal-btn confirm">Сохранить</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Event listeners
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.querySelector('.modal-btn.cancel').addEventListener('click', () => modal.remove());
    modal.querySelector('.modal-btn.confirm').addEventListener('click', saveUserPreferences);
    
    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
};

const saveUserPreferences = () => {
    const autoRefresh = document.getElementById('autoRefreshToggle').checked;
    const refreshInterval = parseInt(document.getElementById('refreshInterval').value) * 1000;
    const recordsPerPage = parseInt(document.getElementById('recordsPerPage').value);
    const compactMode = document.getElementById('compactMode').checked;
    
    AdminDashboard.setState({
        autoRefresh,
        refreshInterval,
        recordsPerPage
    });
    
    if (compactMode) {
        document.body.classList.add('compact-mode');
    } else {
        document.body.classList.remove('compact-mode');
    }
    
    // Close modal
    document.querySelector('.modal.active').remove();
    
    // Apply changes
    displayRecords();
    
    showToast('Настройки сохранены', 'success');
    addLog('Пользовательские настройки обновлены', 'info');
};

// Performance monitoring
const initializePerformanceMonitoring = () => {
    // Monitor page performance
    if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.entryType === 'measure') {
                    console.log(`${entry.name}: ${entry.duration}ms`);
                }
            }
        });
        
        observer.observe({ entryTypes: ['measure'] });
    }
    
    // Monitor memory usage (if available)
    if ('memory' in performance) {
        setInterval(() => {
            const memory = performance.memory;
            const used = (memory.usedJSHeapSize / 1048576).toFixed(2);
            const total = (memory.totalJSHeapSize / 1048576).toFixed(2);
            
            // Update memory display if element exists
            const memoryElement = document.getElementById('memoryUsage');
            if (memoryElement) {
                memoryElement.textContent = `${used}MB / ${total}MB`;
            }
        }, 5000);
    }
};

// Keyboard shortcuts enhancement
const initializeAdvancedKeyboardShortcuts = () => {
    const shortcuts = {
        'Ctrl+K': () => {
            const searchInput = document.getElementById('advancedSearch');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        },
        'Ctrl+E': () => {
            const exportBtn = document.getElementById('exportDataBtn');
            if (exportBtn) exportBtn.click();
        },
        'Ctrl+P': () => {
            showPreferencesModal();
        },
        'Ctrl+/': () => {
            showKeyboardShortcutsHelp();
        }
    };
    
    document.addEventListener('keydown', function(e) {
        const key = [];
        if (e.ctrlKey) key.push('Ctrl');
        if (e.altKey) key.push('Alt');
        if (e.shiftKey) key.push('Shift');
        key.push(e.key);
        
        const shortcut = key.join('+');
        if (shortcuts[shortcut]) {
            e.preventDefault();
            shortcuts[shortcut]();
        }
    });
};

const showKeyboardShortcutsHelp = () => {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Горячие клавиши</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <div class="shortcuts-list">
                    <div class="shortcut-item">
                        <kbd>Ctrl</kbd> + <kbd>R</kbd>
                        <span>Обновить данные</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Ctrl</kbd> + <kbd>T</kbd>
                        <span>Переключить тему</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Ctrl</kbd> + <kbd>K</kbd>
                        <span>Фокус поиска</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Ctrl</kbd> + <kbd>E</kbd>
                        <span>Экспорт данных</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Ctrl</kbd> + <kbd>P</kbd>
                        <span>Настройки</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Ctrl</kbd> + <kbd>/</kbd>
                        <span>Помощь по горячим клавишам</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Esc</kbd>
                        <span>Закрыть модальные окна</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn confirm">Закрыть</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Event listeners
    const closeModal = () => modal.remove();
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.querySelector('.modal-btn.confirm').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
};

// Initialize all lazy features
const initializeLazyFeatures = () => {
    // Use requestIdleCallback if available, otherwise setTimeout
    const initWhenIdle = () => {
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                loadAdvancedAnalytics();
                initializeAdvancedSearch();
                initializeExportFeatures();
                initializeUserPreferences();
                initializePerformanceMonitoring();
                initializeAdvancedKeyboardShortcuts();
            }, { timeout: 2000 });
        } else {
            setTimeout(() => {
                loadAdvancedAnalytics();
                initializeAdvancedSearch();
                initializeExportFeatures();
                initializeUserPreferences();
                initializePerformanceMonitoring();
                initializeAdvancedKeyboardShortcuts();
            }, 1000);
        }
        
        // Initialize real-time features separately
        setTimeout(() => {
            initializeRealTimeNotifications();
        }, 3000);
    };
    
    // Start initialization
    initWhenIdle();
};

// CSS for lazy-loaded features
const lazyStyles = `
    .shortcuts-list {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    
    .shortcut-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem;
        background-color: var(--bg-color);
        border-radius: var(--border-radius);
    }
    
    .shortcut-item kbd {
        background-color: var(--border-color);
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    
    .compact-mode .stat-card {
        padding: 1rem;
    }
    
    .compact-mode .system-item {
        padding: 0.75rem;
    }
    
    .compact-mode .content-records {
        padding: 1rem;
    }
    
    .tooltip {
        position: absolute;
        background-color: var(--dark-color);
        color: var(--text-color);
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.85rem;
        z-index: 10001;
        pointer-events: none;
        opacity: 0.9;
    }
    
    @media (max-width: 768px) {
        .shortcut-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
    }
`;

// Inject lazy styles
const injectLazyStyles = () => {
    const style = document.createElement('style');
    style.textContent = lazyStyles;
    document.head.appendChild(style);
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        injectLazyStyles();
        setTimeout(initializeLazyFeatures, 500);
    });
} else {
    injectLazyStyles();
    setTimeout(initializeLazyFeatures, 500);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeLazyFeatures,
        loadAdvancedAnalytics,
        initializeAdvancedSearch,
        initializeRealTimeNotifications
    };
}