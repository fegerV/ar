/**
 * Admin Dashboard JavaScript - Enhanced with State Management and Performance Optimizations
 * Main dashboard functionality with lazy loading support
 */

// Global state management - replacing cookies
const AdminDashboard = {
    state: {
        currentPage: 1,
        recordsPerPage: 10,
        allRecords: [],
        currentCompany: {
            id: 'vertex-ar-default',
            name: 'Vertex AR'
        },
        selectedCompanyToDelete: null,
        theme: localStorage.getItem('admin-theme') || 'dark',
        autoRefresh: true,
        refreshInterval: 30000,
        isLoading: false,
        lastUpdate: null,
        statusFilter: null,
        companyConfigs: {},
        yandexFolders: [],
        storageConfig: null,
        storageFolders: [],
        storageLoading: false
    },
    
    // State persistence using localStorage instead of cookies
    saveState() {
        try {
            const stateToSave = {
                currentPage: this.state.currentPage,
                currentCompany: this.state.currentCompany,
                theme: this.state.theme,
                autoRefresh: this.state.autoRefresh,
                lastUpdate: new Date().toISOString()
            };
            localStorage.setItem('admin-dashboard-state', JSON.stringify(stateToSave));
        } catch (error) {
            console.warn('Failed to save state to localStorage:', error);
        }
    },
    
    loadState() {
        try {
            const savedState = localStorage.getItem('admin-dashboard-state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                this.state = { ...this.state, ...parsedState };
                
                // Apply saved theme
                if (this.state.theme) {
                    document.documentElement.setAttribute('data-theme', this.state.theme);
                }
            }
        } catch (error) {
            console.warn('Failed to load state from localStorage:', error);
        }
    },
    
    // Update state and save
    setState(updates) {
        this.state = { ...this.state, ...updates };
        this.saveState();
    }
};

// Initialize dashboard
function initializeDashboard() {
    // Load saved state
    AdminDashboard.loadState();
    
    // Apply theme
    applyTheme();
    
    // Update current company name in UI
    const currentNameElement = document.getElementById('currentCompanyName');
    if (currentNameElement && AdminDashboard.state.currentCompany) {
        currentNameElement.textContent = AdminDashboard.state.currentCompany.name || 'Vertex AR';
    }
    
    // Load initial data
    loadStatistics();
    loadSystemInfo();
    loadRecords();
    loadCompanies();
    loadStorageOptions();
    loadBackupStats();
    loadNotifications();
    
    // Load config for current company
    const currentCompanyId = AdminDashboard.state.currentCompany?.id;
    if (currentCompanyId) {
        loadCompanyConfig(currentCompanyId);
    }
    
    addLog('Админ панель загружена', 'info');
    
    // Auto-refresh data if enabled
    if (AdminDashboard.state.autoRefresh) {
        startAutoRefresh();
    }
    
    // Initialize event listeners
    initializeEventListeners();
}

// Theme management
function applyTheme() {
    const theme = AdminDashboard.state.theme;
    document.documentElement.setAttribute('data-theme', theme);
    
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.textContent = theme === 'light' ? '🌙' : '☀️';
    }
}

function toggleTheme() {
    const currentTheme = AdminDashboard.state.theme;
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    AdminDashboard.setState({ theme: newTheme });
    applyTheme();
    
    addLog(`Тема изменена на: ${newTheme}`, 'info');
}

// Auto-refresh management
function startAutoRefresh() {
    if (AdminDashboard.refreshInterval) {
        setInterval(() => {
            if (!AdminDashboard.state.isLoading) {
                refreshData();
            }
        }, AdminDashboard.state.refreshInterval);
    }
}

function refreshData() {
    loadStatistics();
    loadSystemInfo();
    loadCompanies();
    loadBackupStats();
    loadRecords(); // Also reload records with current company context
    
    // Refresh storage config and folders for current company
    const currentCompanyId = AdminDashboard.state.currentCompany?.id;
    if (currentCompanyId) {
        loadCompanyStorageConfig(currentCompanyId);
        loadStorageFolders(currentCompanyId);
    }
    
    addLog('Данные обновлены автоматически', 'info');
}

// Event listeners initialization
function initializeEventListeners() {
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Form submissions
    const orderForm = document.getElementById('orderForm');
    if (orderForm) {
        orderForm.addEventListener('submit', handleOrderSubmit);
    }
    
    // File upload preview
    const imageInput = document.getElementById('clientPhoto');
    if (imageInput) {
        imageInput.addEventListener('change', handleImagePreview);
    }
    
    // Company management
    const companyInput = document.getElementById('companyNameInput');
    if (companyInput) {
        companyInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                createCompany();
            }
        });
    }
    
    // Yandex folder select change listener
    const yandexFolderSelect = document.getElementById('yandexFolderSelect');
    const saveYandexFolderBtn = document.getElementById('saveYandexFolderBtn');
    if (yandexFolderSelect && saveYandexFolderBtn) {
        yandexFolderSelect.addEventListener('change', function() {
            saveYandexFolderBtn.disabled = !this.value;
        });
    }
    
    // Content type input listeners
    const newContentTypeInput = document.getElementById('newContentTypeInput');
    const addContentTypeBtn = document.getElementById('addContentTypeBtn');
    if (newContentTypeInput && addContentTypeBtn) {
        newContentTypeInput.addEventListener('input', function() {
            addContentTypeBtn.disabled = !this.value.trim();
        });
        newContentTypeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addContentType();
            }
        });
    }
    
    // Storage folder input listeners
    const newStorageFolderInput = document.getElementById('newStorageFolderInput');
    const addStorageFolderBtn = document.getElementById('addStorageFolderBtn');
    if (newStorageFolderInput && addStorageFolderBtn) {
        newStorageFolderInput.addEventListener('input', function() {
            addStorageFolderBtn.disabled = !this.value.trim();
        });
        newStorageFolderInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                createStorageFolder();
            }
        });
    }
    
    // Notifications toggle
    const notificationToggle = document.getElementById('notificationToggle');
    if (notificationToggle) {
        notificationToggle.addEventListener('click', function() {
            const dropdown = document.getElementById('notificationDropdown');
            if (dropdown) {
                dropdown.classList.toggle('active');
                loadNotifications();
            }
        });
    }
    
    // Search functionality
    const searchInput = document.getElementById('advancedSearch');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 300);
        });
    }
    
    // Clear logs button
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', clearLogs);
    }
    
    // Clear notifications button
    const markNotificationsRead = document.getElementById('markNotificationsRead');
    if (markNotificationsRead) {
        markNotificationsRead.addEventListener('click', function() {
            updateNotifications([]);
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                badge.classList.add('hidden');
                badge.textContent = '0';
            }
            addLog('Уведомления очищены', 'info');
        });
    }
    
    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Lightbox close
    const lightboxClose = document.querySelector('.lightbox-close');
    if (lightboxClose) {
        lightboxClose.addEventListener('click', closeLightbox);
    }
    
    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });
    
    // Click outside lightbox to close
    const lightbox = document.querySelector('.lightbox');
    if (lightbox) {
        lightbox.addEventListener('click', function(e) {
            if (e.target === this) {
                closeLightbox();
            }
        });
    }
    
    // Advanced search with debounce
    const advancedSearch = document.getElementById('advancedSearch');
    if (advancedSearch) {
        const debouncedSearch = debounce((query) => {
            performSearch(query);
        }, 500);
        
        advancedSearch.addEventListener('input', (e) => {
            debouncedSearch(e.target.value);
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Escape to close modals/lightbox
        if (e.key === 'Escape') {
            closeAllModals();
            closeLightbox();
        }
        
        // Ctrl+R to refresh data
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            refreshData();
        }
        
        // Ctrl+T to toggle theme
        if (e.ctrlKey && e.key === 't') {
            e.preventDefault();
            toggleTheme();
        }
    });
}

// Statistics loading
async function loadStatistics() {
    try {
        showLoading();
        
        // Include current company ID in the request
        const companyId = AdminDashboard.state.currentCompany?.id;
        const url = companyId ? `/admin/stats?company_id=${encodeURIComponent(companyId)}` : '/admin/stats';
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateStatistics(data);
            AdminDashboard.setState({ lastUpdate: new Date().toISOString() });
        } else {
            let errorDetail = `HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorDetail = typeof errorData.detail === 'string' 
                        ? errorData.detail 
                        : JSON.stringify(errorData.detail);
                }
            } catch (e) {
                // If response is not JSON, use default error message
            }
            throw new Error(errorDetail);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
        showToast('Ошибка загрузки статистики: ' + error.message, 'error');
        addLog('Ошибка загрузки статистики: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function updateStatistics(data) {
    const elements = {
        'totalClients': data.total_clients || 0,
        'totalPortraits': data.total_portraits || 0,
        'totalVideos': data.total_videos || 0,
        'totalOrders': data.total_orders || 0,
        'activePortraits': data.active_portraits || 0,
        'totalViews': data.total_views || 0,
        'storageUsed': data.storage_used || '0 B',
        'storageAvailable': data.storage_available || '0 B'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Update lifecycle status counts if available
    if (data.status_counts) {
        const statusElements = {
            'statusActive': data.status_counts.active || 0,
            'statusExpiring': data.status_counts.expiring || 0,
            'statusArchived': data.status_counts.archived || 0
        };
        
        Object.entries(statusElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }
    
    // Update storage progress bars
    updateStorageProgress(data.storage_usage_percent || 0);
}

function updateStorageProgress(percentage) {
    const progressFills = document.querySelectorAll('.progress-fill-small');
    progressFills.forEach(fill => {
        fill.style.width = `${Math.min(percentage, 100)}%`;
    });
}

// System information loading
async function loadSystemInfo() {
    try {
        const response = await fetch('/admin/system-info', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateSystemInfo(data);
        }
    } catch (error) {
        console.error('Error loading system info:', error);
        addLog('Ошибка загрузки системной информации: ' + error.message, 'error');
    }
}

function updateSystemInfo(data) {
    const elements = {
        'systemVersion': data.version || 'N/A',
        'systemUptime': data.uptime || 'N/A',
        'systemMemory': data.memory_usage || 'N/A',
        'systemDisk': data.disk_usage || 'N/A',
        'systemCPU': data.cpu_usage || 'N/A',
        'systemHost': data.hostname || 'N/A'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Update platform info
    const platformElement = document.getElementById('systemPlatform');
    if (platformElement && data.platform) {
        platformElement.textContent = data.platform;
    }
    
    // Update progress bars
    if (data.memory_percent !== undefined && data.memory_percent !== null) {
        const memoryBar = document.getElementById('memoryUsageBar');
        if (memoryBar) {
            memoryBar.style.width = `${Math.min(data.memory_percent, 100)}%`;
            memoryBar.style.backgroundColor = data.memory_percent > 80 ? '#dc3545' : 
                                           data.memory_percent > 60 ? '#ffc107' : '#28a745';
        }
    }
    
    if (data.disk_percent !== undefined && data.disk_percent !== null) {
        const diskBar = document.getElementById('diskUsageBar');
        if (diskBar) {
            diskBar.style.width = `${Math.min(data.disk_percent, 100)}%`;
            diskBar.style.backgroundColor = data.disk_percent > 80 ? '#dc3545' : 
                                          data.disk_percent > 60 ? '#ffc107' : '#28a745';
        }
    }
    
    if (data.cpu_percent !== undefined && data.cpu_percent !== null) {
        const cpuBar = document.getElementById('cpuUsageBar');
        if (cpuBar) {
            cpuBar.style.width = `${Math.min(data.cpu_percent, 100)}%`;
            cpuBar.style.backgroundColor = data.cpu_percent > 80 ? '#dc3545' : 
                                         data.cpu_percent > 60 ? '#ffc107' : '#28a745';
        }
    }
}

// Records management
async function loadRecords() {
    try {
        AdminDashboard.setState({ isLoading: true });
        
        // Build URL with filters
        const companyId = AdminDashboard.state.currentCompany?.id;
        const statusFilter = AdminDashboard.state.statusFilter;
        
        let url = '/admin/records';
        const params = [];
        if (companyId) {
            params.push(`company_id=${encodeURIComponent(companyId)}`);
        }
        
        // If status filter is active, use search endpoint instead
        if (statusFilter) {
            url = '/admin/search';
            params.push(`status=${encodeURIComponent(statusFilter)}`);
        }
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            const records = statusFilter ? (data.results || []) : (data.records || []);
            AdminDashboard.setState({ allRecords: records });
            displayRecords();
        } else {
            let errorDetail = `HTTP ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorDetail = typeof errorData.detail === 'string' 
                        ? errorData.detail 
                        : JSON.stringify(errorData.detail);
                }
            } catch (e) {
                // If response is not JSON, use default error message
            }
            throw new Error(errorDetail);
        }
    } catch (error) {
        console.error('Error loading records:', error);
        showToast('Ошибка загрузки записей: ' + error.message, 'error');
        addLog('Ошибка загрузки записей: ' + error.message, 'error');
    } finally {
        AdminDashboard.setState({ isLoading: false });
    }
}

// Filter records by lifecycle status
function filterByStatus(status) {
    AdminDashboard.setState({ 
        statusFilter: status === AdminDashboard.state.statusFilter ? null : status,
        currentPage: 1 
    });
    loadRecords();
    addLog(`Фильтр по статусу: ${status || 'все'}`, 'info');
}

function displayRecords(records = null) {
    const recordsToDisplay = records || AdminDashboard.state.allRecords;
    const { currentPage, recordsPerPage } = AdminDashboard.state;
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = startIndex + recordsPerPage;
    const pageRecords = recordsToDisplay.slice(startIndex, endIndex);
    
    const tbody = document.querySelector('.records-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (pageRecords.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">Нет записей</td></tr>';
        return;
    }
    
    pageRecords.forEach(record => {
        const row = createRecordRow(record);
        tbody.appendChild(row);
    });
    
    if (!records) {
        updatePagination();
    }
}

function createRecordRow(record) {
    const row = document.createElement('tr');
    const placeholderImage = '/static/images/placeholder.svg';
    const noImageText = 'Нет фото';
    
    // Generate status indicator with tooltip
    const statusInfo = getStatusIndicator(record.status, record.days_remaining);
    
    row.innerHTML = `
        <td>
            ${record.id ? 
                `<a href="/admin/order/${record.id}" class="order-link" title="Открыть детальную информацию">${record.order_number || ''}</a>` : 
                `${record.order_number || ''}`
            }
        </td>
        <td>
            <span class="status-indicator" title="${statusInfo.tooltip}">
                ${statusInfo.icon}
            </span>
        </td>
        <td>
            ${record.portrait_path ? 
                `<img src="${record.portrait_path}" 
                     alt="Portrait" 
                     class="portrait-preview"
                     onclick="showLightbox('${record.portrait_path}')"
                     onerror="this.src='${placeholderImage}'; this.onerror=null;"
                     style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; cursor: pointer;">` : 
                `<div style="width: 50px; height: 50px; background: var(--border-color); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--secondary-color); font-size: 0.7rem;">${noImageText}</div>`
            }
        </td>
        <td>
            ${record.active_video_url ? 
                `<video src="${record.active_video_url}" 
                       class="video-preview" 
                       style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; cursor: pointer;"
                       onclick="showVideoLightbox('${record.active_video_url}')"
                       muted
                       preload="metadata"></video>` : 
                '<div style="width: 50px; height: 50px; background: var(--border-color); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--secondary-color); font-size: 0.7rem;">Нет видео</div>'
            }
        </td>
        <td>${record.client_name || ''}</td>
        <td>${record.client_phone || ''}</td>
        <td>${record.views || 0}</td>
        <td>
            ${record.permanent_url ? 
                `<div style="display: flex; gap: 0.25rem;">
                    <button class="link-button small" onclick="window.open('${record.permanent_url}', '_blank')" title="Открыть в новой вкладке">Открыть</button>
                    <button class="link-button small" onclick="copyToClipboard('${record.permanent_url}')" title="Скопировать ссылку">Копировать</button>
                </div>` : 
                'Нет ссылки'
            }
        </td>
        <td>
            ${record.qr_code ? 
                `<img src="${record.qr_code}" 
                     alt="QR Code" 
                     class="qr-preview"
                     onclick="showLightbox('${record.qr_code}')"
                     style="width: 30px; height: 30px; cursor: pointer;">` : 
                '<div style="width: 30px; height: 30px; background: var(--border-color); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--secondary-color); font-size: 0.6rem;">Нет QR</div>'
            }
        </td>
        <td>${record.created_at ? new Date(record.created_at).toLocaleString('ru-RU') : ''}</td>
        <td>
            <button class="action-btn edit-btn" onclick="editRecord('${record.id}')" title="Редактировать">✏️</button>
            <button class="action-btn delete-btn" onclick="deleteRecord('${record.id}')" title="Удалить">🗑️</button>
        </td>
    `;
    return row;
}

// Helper function to get status indicator with tooltip
function getStatusIndicator(status, daysRemaining) {
    const statusMap = {
        'active': { icon: '🟢', text: 'Активен', color: '#28a745' },
        'expiring': { icon: '🔴', text: 'Истекает', color: '#dc3545' },
        'archived': { icon: '⚫️', text: 'Архив', color: '#6c757d' }
    };
    
    const statusInfo = statusMap[status] || statusMap['active'];
    let tooltip = statusInfo.text;
    
    if (status === 'expiring' && daysRemaining !== null && daysRemaining !== undefined) {
        tooltip = `${statusInfo.text}: ${daysRemaining} ${getDaysText(daysRemaining)}`;
    } else if (status === 'archived' && daysRemaining !== null && daysRemaining < 0) {
        tooltip = `${statusInfo.text}: истек ${Math.abs(daysRemaining)} ${getDaysText(Math.abs(daysRemaining))} назад`;
    }
    
    return { icon: statusInfo.icon, tooltip, color: statusInfo.color };
}

function getDaysText(days) {
    const absDays = Math.abs(days);
    if (absDays % 10 === 1 && absDays % 100 !== 11) {
        return 'день';
    } else if ([2, 3, 4].includes(absDays % 10) && ![12, 13, 14].includes(absDays % 100)) {
        return 'дня';
    }
    return 'дней';
}

function updatePagination() {
    const { allRecords, currentPage, recordsPerPage } = AdminDashboard.state;
    const totalPages = Math.ceil(allRecords.length / recordsPerPage);
    
    const pagination = document.querySelector('.pagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    // Previous button
    const prevBtn = createPaginationButton('←', currentPage - 1, currentPage === 1);
    pagination.appendChild(prevBtn);
    
    // Page numbers
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        const btn = createPaginationButton(i, i, i === currentPage);
        pagination.appendChild(btn);
    }
    
    // Next button
    const nextBtn = createPaginationButton('→', currentPage + 1, currentPage === totalPages);
    pagination.appendChild(nextBtn);
}

function createPaginationButton(text, page, isDisabled) {
    const button = document.createElement('button');
    button.textContent = text;
    button.className = 'pagination-btn';
    button.disabled = isDisabled;
    
    if (!isDisabled) {
        button.addEventListener('click', () => {
            AdminDashboard.setState({ currentPage: page });
            displayRecords();
        });
    }
    
    return button;
}

// Image preview functionality
function handleImagePreview(e) {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('imagePreview');
            if (preview) {
                preview.src = e.target.result;
                preview.classList.add('active');
            }
        };
        reader.readAsDataURL(file);
    } else {
        hideImagePreview();
    }
}

function hideImagePreview() {
    const preview = document.getElementById('imagePreview');
    if (preview) {
        preview.src = '';
        preview.classList.remove('active');
    }
}

// Company management
async function loadCompanies() {
    try {
        const response = await fetch('/companies', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateCompanySelect(data.items || data.companies || []);
        }
    } catch (error) {
        console.error('Error loading companies:', error);
        addLog('Ошибка загрузки компаний: ' + error.message, 'error');
    }
}

function updateCompanySelect(companies) {
    const select = document.getElementById('companySelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Выберите компанию</option>';
    
    companies.forEach(company => {
        const option = document.createElement('option');
        option.value = company.id;
        option.textContent = `${company.name} (${company.client_count || 0} клиентов)`;
        select.appendChild(option);
    });
}

// Load storage options for company creation
async function loadStorageOptions() {
    const select = document.getElementById('companyStorageSelect');
    if (!select) return;
    
    try {
        const response = await fetch('/storage-options', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const options = await response.json();
            
            select.innerHTML = '';
            options.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option.id;
                optionElement.textContent = option.name;
                
                // Add connection ID as data attribute for remote storage
                if (option.connection_id) {
                    optionElement.setAttribute('data-connection-id', option.connection_id);
                }
                
                select.appendChild(optionElement);
            });
        }
    } catch (error) {
        console.error('Error loading storage options:', error);
        addLog('Ошибка загрузки вариантов хранилищ: ' + error.message, 'error');
    }
}

async function createCompany() {
    const nameInput = document.getElementById('companyNameInput');
    const storageSelect = document.getElementById('companyStorageSelect');
    const name = nameInput?.value?.trim();
    const storageType = storageSelect?.value || 'local';
    let storageConnectionId = null;
    
    if (!name) {
        showToast('Введите название компании', 'warning');
        return;
    }
    
    // Get storage connection ID if not local
    if (storageType !== 'local') {
        const selectedOption = storageSelect.options[storageSelect.selectedIndex];
        storageConnectionId = selectedOption?.getAttribute('data-connection-id');
    }
    
    try {
        const companyData = { 
            name,
            storage_type: storageType,
            storage_connection_id: storageConnectionId
        };
        
        const response = await fetch('/companies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(companyData),
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast('Компания создана успешно', 'success');
            addLog(`Создана компания: ${name}`, 'success');
            
            if (nameInput) nameInput.value = '';
            loadCompanies();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось создать компанию'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при создании компании: ${error.message}`, 'error');
    }
}

async function switchCompany() {
    const select = document.getElementById('companySelect');
    const companyId = select?.value;
    
    if (!companyId) {
        showToast('Выберите компанию', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/companies/${companyId}/select`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            const companyName = result.name || 'Unknown';
            
            AdminDashboard.setState({ 
                currentCompany: { 
                    id: companyId, 
                    name: companyName 
                }
            });
            
            const currentNameElement = document.getElementById('currentCompanyName');
            if (currentNameElement) {
                currentNameElement.textContent = companyName;
            }
            
            if (select) select.value = '';
            
            showToast(`Переключились на компанию: ${companyName}`, 'success');
            addLog(`Выбрана компания: ${companyName}`, 'info');
            
            // Load company config (Yandex folder and content types)
            await loadCompanyConfig(companyId);
            
            // Reload data for new company
            loadRecords();
            loadStatistics();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось переключить компанию'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при переключении компании: ${error.message}`, 'error');
    }
}

// Delete company functionality
function showDeleteCompanyModal() {
    const select = document.getElementById('companySelect');
    const companyId = select?.value;
    
    if (!companyId) {
        showToast('Выберите компанию для удаления', 'warning');
        return;
    }
    
    const companyOption = select.querySelector(`option[value="${companyId}"]`);
    const companyName = companyOption ? companyOption.textContent.replace(/ \([^)]*\)/, '') : 'Unknown';
    
    AdminDashboard.setState({ selectedCompanyToDelete: { id: companyId, name: companyName } });
    
    const messageElement = document.getElementById('deleteCompanyMessage');
    if (messageElement) {
        messageElement.textContent = `Вы уверены, что хотите удалить компанию "${companyName}"? Все данные будут удалены без возможности восстановления.`;
    }
    
    const modal = document.getElementById('deleteCompanyModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function hideDeleteCompanyModal() {
    const modal = document.getElementById('deleteCompanyModal');
    if (modal) {
        modal.classList.remove('active');
    }
    AdminDashboard.setState({ selectedCompanyToDelete: null });
}

async function confirmDeleteCompany() {
    const { selectedCompanyToDelete } = AdminDashboard.state;
    
    if (!selectedCompanyToDelete) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch(`/companies/${selectedCompanyToDelete.id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            showToast(`Компания "${selectedCompanyToDelete.name}" удалена`, 'success');
            addLog(`Удалена компания: ${selectedCompanyToDelete.name}`, 'success');
            
            hideDeleteCompanyModal();
            loadCompanies();
            loadRecords();
            loadStatistics();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось удалить компанию'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при удалении компании: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Yandex Disk Folder Management
async function loadYandexFolders() {
    const select = document.getElementById('yandexFolderSelect');
    if (!select) return;
    
    try {
        showLoading('Загрузка папок Yandex Disk...');
        
        const response = await fetch('/api/yandex-disk/folders', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const folders = await response.json();
            AdminDashboard.state.yandexFolders = folders;
            
            select.innerHTML = '<option value="">Выберите папку...</option>';
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.path || folder.name;
                option.textContent = folder.name;
                select.appendChild(option);
            });
            
            showToast('Папки загружены успешно', 'success');
            addLog('Загружены папки Yandex Disk', 'info');
        } else {
            const error = await response.json();
            showToast(`Ошибка загрузки папок: ${error.detail || 'Неизвестная ошибка'}`, 'error');
            addLog(`Ошибка загрузки папок Yandex Disk: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error loading Yandex folders:', error);
        showToast('Ошибка сети при загрузке папок', 'error');
        addLog(`Ошибка сети при загрузке папок: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function saveYandexFolder() {
    const select = document.getElementById('yandexFolderSelect');
    const saveBtn = document.getElementById('saveYandexFolderBtn');
    const selectedFolder = select?.value;
    
    if (!selectedFolder) {
        showToast('Выберите папку для сохранения', 'warning');
        return;
    }
    
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    try {
        if (saveBtn) saveBtn.disabled = true;
        
        const response = await fetch(`/api/companies/${companyId}/yandex-disk-folder`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ folder_path: selectedFolder }),
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (!AdminDashboard.state.companyConfigs[companyId]) {
                AdminDashboard.state.companyConfigs[companyId] = {};
            }
            AdminDashboard.state.companyConfigs[companyId].yandex_folder = selectedFolder;
            
            const currentFolderElement = document.getElementById('currentYandexFolder');
            if (currentFolderElement) {
                currentFolderElement.textContent = selectedFolder;
            }
            
            showToast('Папка сохранена успешно', 'success');
            addLog(`Сохранена папка Yandex Disk: ${selectedFolder}`, 'success');
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось сохранить папку'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving Yandex folder:', error);
        showToast('Ошибка сети при сохранении папки', 'error');
        addLog(`Ошибка сети при сохранении папки: ${error.message}`, 'error');
    } finally {
        if (saveBtn) saveBtn.disabled = false;
    }
}

async function loadCompanyConfig(companyId) {
    if (!companyId) return;
    
    try {
        const response = await fetch(`/api/companies/${companyId}/yandex-disk-folder`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (!AdminDashboard.state.companyConfigs[companyId]) {
                AdminDashboard.state.companyConfigs[companyId] = {};
            }
            AdminDashboard.state.companyConfigs[companyId].yandex_folder = data.folder_path;
            
            const currentFolderElement = document.getElementById('currentYandexFolder');
            if (currentFolderElement) {
                currentFolderElement.textContent = data.folder_path || 'Не выбрана';
            }
        }
    } catch (error) {
        console.error('Error loading company config:', error);
    }
    
    try {
        const response = await fetch(`/api/companies/${companyId}/content-types`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (!AdminDashboard.state.companyConfigs[companyId]) {
                AdminDashboard.state.companyConfigs[companyId] = {};
            }
            AdminDashboard.state.companyConfigs[companyId].content_types = data.content_types || [];
            
            updateContentTypesList(data.content_types || []);
            updateContentTypeSelect(data.content_types || []);
        }
    } catch (error) {
        console.error('Error loading content types:', error);
    }
    
    // Load storage configuration
    await loadCompanyStorageConfig(companyId);
    
    // Load storage folders if applicable
    await loadStorageFolders(companyId);
}

// Content Types Management
function updateContentTypesList(contentTypes) {
    const listElement = document.getElementById('contentTypesList');
    if (!listElement) return;
    
    if (!contentTypes || contentTypes.length === 0) {
        listElement.innerHTML = '<p style="text-align: center; opacity: 0.6; padding: 1rem;">Типы контента отсутствуют</p>';
        return;
    }
    
    listElement.innerHTML = '';
    contentTypes.forEach(type => {
        const item = document.createElement('div');
        item.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: var(--bg-color); border-radius: var(--border-radius); border: 1px solid var(--border-color);';
        item.innerHTML = `
            <span style="flex: 1;">${type}</span>
            <button onclick="removeContentType('${type}')" class="company-btn danger" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">🗑️ Удалить</button>
        `;
        listElement.appendChild(item);
    });
}

function updateContentTypeSelect(contentTypes) {
    const select = document.getElementById('contentType');
    if (!select) return;
    
    select.innerHTML = '<option value="">Выберите тип контента...</option>';
    
    if (contentTypes && contentTypes.length > 0) {
        contentTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            select.appendChild(option);
        });
        
        select.value = contentTypes[0];
    }
}

async function addContentType() {
    const input = document.getElementById('newContentTypeInput');
    const addBtn = document.getElementById('addContentTypeBtn');
    const newType = input?.value?.trim();
    
    if (!newType) {
        showToast('Введите тип контента', 'warning');
        return;
    }
    
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    const currentConfig = AdminDashboard.state.companyConfigs[companyId] || {};
    const currentTypes = currentConfig.content_types || [];
    
    if (currentTypes.includes(newType)) {
        showToast('Такой тип контента уже существует', 'warning');
        return;
    }
    
    const updatedTypes = [...currentTypes, newType];
    
    try {
        if (addBtn) addBtn.disabled = true;
        
        const response = await fetch(`/api/companies/${companyId}/content-types`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content_types: updatedTypes }),
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (!AdminDashboard.state.companyConfigs[companyId]) {
                AdminDashboard.state.companyConfigs[companyId] = {};
            }
            AdminDashboard.state.companyConfigs[companyId].content_types = updatedTypes;
            
            updateContentTypesList(updatedTypes);
            updateContentTypeSelect(updatedTypes);
            
            if (input) input.value = '';
            
            showToast('Тип контента добавлен', 'success');
            addLog(`Добавлен тип контента: ${newType}`, 'success');
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось добавить тип'}`, 'error');
        }
    } catch (error) {
        console.error('Error adding content type:', error);
        showToast('Ошибка сети при добавлении типа', 'error');
        addLog(`Ошибка сети при добавлении типа: ${error.message}`, 'error');
    } finally {
        if (addBtn) addBtn.disabled = false;
    }
}

async function removeContentType(typeToRemove) {
    if (!confirm(`Удалить тип контента "${typeToRemove}"?`)) {
        return;
    }
    
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    const currentConfig = AdminDashboard.state.companyConfigs[companyId] || {};
    const currentTypes = currentConfig.content_types || [];
    const updatedTypes = currentTypes.filter(t => t !== typeToRemove);
    
    try {
        const response = await fetch(`/api/companies/${companyId}/content-types`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content_types: updatedTypes }),
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (!AdminDashboard.state.companyConfigs[companyId]) {
                AdminDashboard.state.companyConfigs[companyId] = {};
            }
            AdminDashboard.state.companyConfigs[companyId].content_types = updatedTypes;
            
            updateContentTypesList(updatedTypes);
            updateContentTypeSelect(updatedTypes);
            
            showToast('Тип контента удалён', 'success');
            addLog(`Удалён тип контента: ${typeToRemove}`, 'success');
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось удалить тип'}`, 'error');
        }
    } catch (error) {
        console.error('Error removing content type:', error);
        showToast('Ошибка сети при удалении типа', 'error');
        addLog(`Ошибка сети при удалении типа: ${error.message}`, 'error');
    }
}

// Storage Folder Management
async function loadCompanyStorageConfig(companyId) {
    if (!companyId) {
        console.warn('No company ID provided for storage config');
        return;
    }
    
    try {
        AdminDashboard.state.storageLoading = true;
        
        const response = await fetch(`/api/companies/${companyId}/storage-info`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            AdminDashboard.state.storageConfig = data;
            
            // Update UI elements if they exist
            updateStorageConfigDisplay(data);
            
            addLog(`Загружена конфигурация хранилища для компании: ${data.company_name}`, 'info');
        } else {
            const error = await response.json();
            console.error('Error loading storage config:', error);
            addLog(`Ошибка загрузки конфигурации хранилища: ${error.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error loading storage config:', error);
        addLog(`Ошибка сети при загрузке конфигурации хранилища: ${error.message}`, 'error');
    } finally {
        AdminDashboard.state.storageLoading = false;
    }
}

function updateStorageConfigDisplay(config) {
    // Update storage type indicator
    const storageTypeElement = document.getElementById('storageTypeIndicator');
    if (storageTypeElement) {
        storageTypeElement.textContent = config.storage_type || 'local';
    }
    
    // Update storage status
    const storageStatusElement = document.getElementById('storageStatus');
    if (storageStatusElement) {
        storageStatusElement.textContent = config.status_message || 'Не настроено';
        storageStatusElement.className = config.is_configured ? 'status-configured' : 'status-unconfigured';
    }
    
    // Update folder path if available
    const folderPathElement = document.getElementById('storageFolderPath');
    if (folderPathElement && config.storage_folder_path) {
        folderPathElement.textContent = config.storage_folder_path;
    }
}

async function loadStorageFolders(companyId) {
    if (!companyId) {
        console.warn('No company ID provided for loading folders');
        return;
    }
    
    const company = AdminDashboard.state.storageConfig;
    if (!company) {
        await loadCompanyStorageConfig(companyId);
    }
    
    // Only load folders for remote storage types
    const storageType = AdminDashboard.state.storageConfig?.storage_type;
    if (storageType === 'local') {
        AdminDashboard.state.storageFolders = [];
        updateStorageFoldersList([]);
        return;
    }
    
    if (storageType === 'yandex_disk') {
        await loadYandexDiskFolders(companyId);
    } else {
        // For other storage types (MinIO, etc.), implement similar logic
        console.log('Storage type not yet supported for folder listing:', storageType);
        AdminDashboard.state.storageFolders = [];
        updateStorageFoldersList([]);
    }
}

async function loadYandexDiskFolders(companyId) {
    try {
        AdminDashboard.state.storageLoading = true;
        
        const response = await fetch(`/api/yandex-disk/folders?company_id=${encodeURIComponent(companyId)}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            AdminDashboard.state.storageFolders = data.items || [];
            updateStorageFoldersList(data.items || []);
            
            addLog(`Загружено папок: ${data.items?.length || 0}`, 'info');
        } else {
            const error = await response.json();
            showToast(`Ошибка загрузки папок: ${error.detail || 'Неизвестная ошибка'}`, 'error');
            addLog(`Ошибка загрузки папок: ${error.detail}`, 'error');
            AdminDashboard.state.storageFolders = [];
            updateStorageFoldersList([]);
        }
    } catch (error) {
        console.error('Error loading storage folders:', error);
        showToast('Ошибка сети при загрузке папок', 'error');
        addLog(`Ошибка сети при загрузке папок: ${error.message}`, 'error');
        AdminDashboard.state.storageFolders = [];
        updateStorageFoldersList([]);
    } finally {
        AdminDashboard.state.storageLoading = false;
    }
}

function updateStorageFoldersList(folders) {
    const foldersListElement = document.getElementById('storageFoldersList');
    if (!foldersListElement) return;
    
    if (!folders || folders.length === 0) {
        foldersListElement.innerHTML = '<p style="text-align: center; opacity: 0.6; padding: 1rem;">Папки отсутствуют или не применимы для данного типа хранилища</p>';
        return;
    }
    
    foldersListElement.innerHTML = '';
    folders.forEach(folder => {
        const item = document.createElement('div');
        item.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: var(--bg-color); border-radius: var(--border-radius); border: 1px solid var(--border-color); margin-bottom: 0.5rem;';
        item.innerHTML = `
            <div style="flex: 1;">
                <strong>📁 ${folder.name}</strong>
                <div style="font-size: 0.85rem; opacity: 0.7; margin-top: 0.25rem;">${folder.path || ''}</div>
            </div>
            <button onclick="deleteStorageFolder('${folder.path || folder.name}')" class="company-btn danger" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">🗑️ Удалить</button>
        `;
        foldersListElement.appendChild(item);
    });
}

function validateFolderName(folderName) {
    // Validate folder name: letters, digits, dash, underscore only
    const pattern = /^[a-zA-Z0-9_-]+$/;
    return pattern.test(folderName);
}

async function createStorageFolder() {
    const input = document.getElementById('newStorageFolderInput');
    const addBtn = document.getElementById('addStorageFolderBtn');
    const folderName = input?.value?.trim();
    
    if (!folderName) {
        showToast('Введите название папки', 'warning');
        return;
    }
    
    // Client-side validation
    if (!validateFolderName(folderName)) {
        showToast('Название папки может содержать только буквы, цифры, дефис и подчёркивание', 'error');
        return;
    }
    
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    const storageType = AdminDashboard.state.storageConfig?.storage_type;
    
    try {
        if (addBtn) addBtn.disabled = true;
        
        // Optimistic UI update
        const optimisticFolder = { name: folderName, path: folderName };
        const currentFolders = [...AdminDashboard.state.storageFolders];
        AdminDashboard.state.storageFolders = [...currentFolders, optimisticFolder];
        updateStorageFoldersList(AdminDashboard.state.storageFolders);
        
        let response;
        if (storageType === 'local') {
            // For local storage, use the storage folder endpoint
            response = await fetch(`/api/companies/${companyId}/storage-folder`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ folder_path: folderName }),
                credentials: 'include'
            });
        } else {
            // For remote storage (Yandex, MinIO), we would need folder creation endpoints
            // For now, show a message that manual creation is needed
            showToast('Для удалённого хранилища создавайте папки в интерфейсе хранилища', 'warning');
            // Revert optimistic update
            AdminDashboard.state.storageFolders = currentFolders;
            updateStorageFoldersList(currentFolders);
            return;
        }
        
        if (response.ok) {
            const result = await response.json();
            
            if (input) input.value = '';
            
            // Reload folders to get actual state
            await loadStorageFolders(companyId);
            await loadCompanyStorageConfig(companyId);
            
            showToast('Папка создана успешно', 'success');
            addLog(`Создана папка хранилища: ${folderName}`, 'success');
        } else {
            // Revert optimistic update on error
            AdminDashboard.state.storageFolders = currentFolders;
            updateStorageFoldersList(currentFolders);
            
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось создать папку'}`, 'error');
            addLog(`Ошибка создания папки: ${error.detail}`, 'error');
        }
    } catch (error) {
        // Revert optimistic update on error
        const currentFolders = AdminDashboard.state.storageFolders.filter(f => f.name !== folderName);
        AdminDashboard.state.storageFolders = currentFolders;
        updateStorageFoldersList(currentFolders);
        
        console.error('Error creating storage folder:', error);
        showToast('Ошибка сети при создании папки', 'error');
        addLog(`Ошибка сети при создании папки: ${error.message}`, 'error');
    } finally {
        if (addBtn) addBtn.disabled = false;
    }
}

async function deleteStorageFolder(folderPath) {
    if (!confirm(`Удалить папку "${folderPath}"?`)) {
        return;
    }
    
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    const storageType = AdminDashboard.state.storageConfig?.storage_type;
    
    // Optimistic UI update
    const currentFolders = [...AdminDashboard.state.storageFolders];
    AdminDashboard.state.storageFolders = currentFolders.filter(f => f.path !== folderPath && f.name !== folderPath);
    updateStorageFoldersList(AdminDashboard.state.storageFolders);
    
    try {
        if (storageType === 'local') {
            // For local storage, we might not have a delete endpoint
            // Show warning that manual deletion might be needed
            showToast('Для локального хранилища удаляйте папки вручную через файловую систему', 'warning');
            // Revert optimistic update
            AdminDashboard.state.storageFolders = currentFolders;
            updateStorageFoldersList(currentFolders);
            return;
        } else if (storageType === 'yandex_disk') {
            // For Yandex Disk, we would need a delete endpoint
            showToast('Для Яндекс Диска удаляйте папки через интерфейс Яндекс Диска', 'warning');
            // Revert optimistic update
            AdminDashboard.state.storageFolders = currentFolders;
            updateStorageFoldersList(currentFolders);
            return;
        }
        
        showToast('Папка удалена успешно', 'success');
        addLog(`Удалена папка хранилища: ${folderPath}`, 'success');
        
        // Reload folders to get actual state
        await loadStorageFolders(companyId);
        await loadCompanyStorageConfig(companyId);
        
    } catch (error) {
        // Revert optimistic update on error
        AdminDashboard.state.storageFolders = currentFolders;
        updateStorageFoldersList(currentFolders);
        
        console.error('Error deleting storage folder:', error);
        
        // Handle specific error cases
        if (error.message && error.message.includes('permission')) {
            showToast('Ошибка: Недостаточно прав для удаления папки', 'error');
        } else if (error.message && error.message.includes('not empty')) {
            showToast('Ошибка: Папка не пуста. Удалите содержимое перед удалением папки', 'error');
        } else {
            showToast('Ошибка при удалении папки', 'error');
        }
        
        addLog(`Ошибка удаления папки: ${error.message}`, 'error');
    }
}

// Image preview handling
function handleImagePreview(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        showImagePreview(e.target.result);
    };
    reader.readAsDataURL(file);
}

function showImagePreview(src) {
    const preview = document.querySelector('.image-preview');
    if (preview) {
        preview.src = src;
        preview.classList.add('active');
    }
}

function hideImagePreview() {
    const preview = document.querySelector('.image-preview');
    if (preview) {
        preview.classList.remove('active');
        preview.src = '';
    }
}

// Lightbox functionality
function showLightbox(imageSrc) {
    const lightbox = document.querySelector('.lightbox');
    const lightboxContent = document.querySelector('.lightbox-content');
    
    if (lightbox && lightboxContent) {
        // Remove any existing video element
        const existingVideo = lightbox.querySelector('.lightbox-video');
        if (existingVideo) {
            existingVideo.remove();
        }
        
        // Show image
        lightboxContent.style.display = 'block';
        lightboxContent.src = imageSrc;
        lightbox.classList.add('active');
        addLog('Открыт просмотр изображения', 'info');
    }
}

function showVideoLightbox(videoSrc) {
    const lightbox = document.querySelector('.lightbox');
    const lightboxContent = document.querySelector('.lightbox-content');
    
    if (lightbox && lightboxContent) {
        // Hide image
        lightboxContent.style.display = 'none';
        
        // Remove existing video if any
        const existingVideo = lightbox.querySelector('.lightbox-video');
        if (existingVideo) {
            existingVideo.remove();
        }
        
        // Create video element
        const videoElement = document.createElement('video');
        videoElement.src = videoSrc;
        videoElement.className = 'lightbox-video';
        videoElement.controls = true;
        videoElement.autoplay = true;
        videoElement.style.maxWidth = '90%';
        videoElement.style.maxHeight = '90%';
        videoElement.style.display = 'block';
        videoElement.style.margin = 'auto';
        
        // Insert video after the image content
        lightboxContent.parentNode.insertBefore(videoElement, lightboxContent.nextSibling);
        
        lightbox.classList.add('active');
        addLog('Открыт просмотр видео', 'info');
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Ссылка скопирована в буфер обмена', 'success');
            addLog('Ссылка скопирована в буфер обмена', 'info');
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            fallbackCopyTextToClipboard(text);
        });
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showToast('Ссылка скопирована в буфер обмена', 'success');
            addLog('Ссылка скопирована в буфер обмена', 'info');
        } else {
            showToast('Не удалось скопировать ссылку', 'error');
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        showToast('Не удалось скопировать ссылку', 'error');
    }
    
    document.body.removeChild(textArea);
}

function closeLightbox() {
    const lightbox = document.querySelector('.lightbox');
    if (lightbox) {
        // Remove any video element
        const existingVideo = lightbox.querySelector('.lightbox-video');
        if (existingVideo) {
            existingVideo.pause();
            existingVideo.remove();
        }
        
        // Show image content again
        const lightboxContent = lightbox.querySelector('.lightbox-content');
        if (lightboxContent) {
            lightboxContent.style.display = 'block';
        }
        
        lightbox.classList.remove('active');
    }
}

// Modal functionality
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        addLog(`Открыто модальное окно: ${modalId}`, 'info');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal.active').forEach(modal => {
        modal.classList.remove('active');
    });
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.querySelector('.toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Loading states
function showLoading(text = 'Загрузка...', status = '') {
    const overlay = document.querySelector('.loading-overlay');
    const loadingText = document.getElementById('loadingText');
    const loadingStatus = document.getElementById('loadingStatus');
    
    if (overlay) {
        overlay.classList.add('active');
    }
    if (loadingText) {
        loadingText.textContent = text;
    }
    if (loadingStatus) {
        loadingStatus.textContent = status;
    }
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

function updateLoadingStatus(status) {
    const loadingStatus = document.getElementById('loadingStatus');
    if (loadingStatus) {
        loadingStatus.textContent = status;
    }
}

// Logging
function addLog(message, type = 'info') {
    // This would typically send logs to a logging endpoint
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // For debugging, you could also display logs in the UI
    const logContainer = document.getElementById('logContainer');
    if (logContainer) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Limit log entries
        while (logContainer.children.length > 100) {
            logContainer.removeChild(logContainer.firstChild);
        }
    }
}

// Backup statistics loading
async function loadBackupStats() {
    try {
        const response = await fetch('/backups/stats', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateBackupStats(data);
        }
    } catch (error) {
        console.error('Error loading backup stats:', error);
        addLog('Ошибка загрузки статистики бэкапов: ' + error.message, 'error');
    }
}

function updateBackupStats(data) {
    const elements = {
        'totalBackups': data.total_backups || 0,
        'databaseBackups': data.database_backups || 0,
        'storageBackups': data.storage_backups || 0,
        'fullBackups': data.full_backups || 0,
        'backupSize': data.total_size_mb ? formatBytes(data.total_size_mb * 1024 * 1024) : '0 B',
        'lastBackup': data.last_backup ? new Date(data.last_backup).toLocaleString('ru-RU') : 'N/A'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// Record operations
async function editRecord(recordId) {
    // Navigate to the detail page for editing
    window.location.href = `/admin/order/${recordId}`;
}

async function deleteRecord(recordId) {
    if (!confirm('Вы уверены, что хотите удалить эту запись?')) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/records/${recordId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            showToast('Запись удалена', 'success');
            addLog(`Удалена запись: ${recordId}`, 'success');
            loadRecords();
            loadStatistics();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось удалить запись'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при удалении записи: ${error.message}`, 'error');
    }
}

// Utility functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

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

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Performance optimization - lazy load non-critical features
const lazyLoadFeatures = () => {
    // Load features that are not immediately needed
    setTimeout(() => {
        // Initialize tooltips
        initializeTooltips();
        
        // Load charts if needed
        if (document.querySelector('.chart-container')) {
            loadCharts();
        }
        
        // Initialize keyboard shortcuts help
        initializeKeyboardHelp();
    }, 1000);
};

// Initialize tooltips
function initializeTooltips() {
    // Simple tooltip implementation
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.getAttribute('data-tooltip');
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = document.querySelector('.tooltip');
            if (tooltip) tooltip.remove();
        });
    });
}

// Load charts (placeholder for charting library integration)
function loadCharts() {
    // This would integrate with a charting library like Chart.js
    console.log('Charts would be loaded here');
}

// Initialize keyboard shortcuts help
function initializeKeyboardHelp() {
    // Show keyboard shortcuts help
    const helpText = `
        Горячие клавиши:
        Ctrl+R - Обновить данные
        Ctrl+T - Переключить тему
        Escape - Закрыть модальные окна
    `;
    
    // You could display this in a help modal or tooltip
    console.log(helpText);
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    lazyLoadFeatures();
    
    // Performance monitoring
    if (window.performance && window.performance.now) {
        const loadTime = Math.round(performance.now());
        console.log(`Page load time: ${loadTime}ms`);
        addLog(`Страница загружена за ${loadTime}ms`, 'info');
    }
});

// Toast notification system
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        console.warn('Toast container not found');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Add icon based on type
    const icon = document.createElement('span');
    icon.className = 'toast-icon';
    switch (type) {
        case 'success':
            icon.textContent = '✅';
            break;
        case 'error':
            icon.textContent = '❌';
            break;
        case 'warning':
            icon.textContent = '⚠️';
            break;
        default:
            icon.textContent = 'ℹ️';
    }
    toast.insertBefore(icon, toast.firstChild);
    
    toastContainer.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Lightbox functionality
function showLightbox(imageSrc) {
    const lightbox = document.getElementById('lightbox');
    const lightboxContent = document.getElementById('lightboxContent');
    
    if (lightbox && lightboxContent) {
        lightboxContent.src = imageSrc;
        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal.active').forEach(modal => {
        modal.classList.remove('active');
    });
}

// Toggle order form visibility
function toggleOrderForm() {
    const formElement = document.getElementById('orderForm');
    const btn = document.querySelector('.create-ar-btn');
    
    if (!formElement || !btn) return;
    
    const isActive = formElement.classList.contains('active');
    
    if (isActive) {
        formElement.classList.remove('active');
        btn.textContent = '+ Создать AR контент';
    } else {
        formElement.classList.add('active');
        btn.textContent = '− Скрыть форму';
        
        const companyId = AdminDashboard.state.currentCompany?.id;
        const currentConfig = AdminDashboard.state.companyConfigs[companyId] || {};
        const contentTypes = currentConfig.content_types || [];
        
        if (contentTypes.length === 0) {
            showToast('Предупреждение: Типы контента не настроены. Настройте их в секции управления компаниями.', 'warning');
        }
    }
}

// Order form submission
async function handleOrderSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData();
    
    // Get form values
    const clientName = document.getElementById('clientName').value.trim();
    const clientPhone = document.getElementById('clientPhone').value.trim();
    const clientEmail = document.getElementById('clientEmail').value.trim();
    const contentType = document.getElementById('contentType').value.trim();
    const clientPhoto = document.getElementById('clientPhoto').files[0];
    const clientVideo = document.getElementById('clientVideo').files[0];
    const clientNotes = document.getElementById('clientNotes').value.trim();
    
    // Validation
    if (!clientName) {
        showToast('Имя клиента обязательно', 'error');
        return;
    }
    
    if (!clientPhone) {
        showToast('Телефон клиента обязателен', 'error');
        return;
    }
    
    if (!contentType) {
        const companyId = AdminDashboard.state.currentCompany?.id;
        const currentConfig = AdminDashboard.state.companyConfigs[companyId] || {};
        const contentTypes = currentConfig.content_types || [];
        
        if (contentTypes.length === 0) {
            showToast('Предупреждение: Типы контента не настроены для этой компании. Добавьте типы контента в секции управления компаниями.', 'warning');
        } else {
            showToast('Выберите тип контента', 'error');
        }
        return;
    }
    
    // Validate email format if provided
    if (clientEmail) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(clientEmail)) {
            showToast('Неверный формат email', 'error');
            return;
        }
    }
    
    if (!clientPhoto) {
        showToast('Фото клиента обязательно', 'error');
        return;
    }
    
    if (!clientVideo) {
        showToast('Видео клиента обязательно', 'error');
        return;
    }
    
    // Validate file types
    if (!clientPhoto.type.startsWith('image/')) {
        showToast('Выберите файл изображения', 'error');
        return;
    }
    
    if (!clientVideo.type.startsWith('video/')) {
        showToast('Выберите видеофайл', 'error');
        return;
    }
    
    // Append data with correct field names for API
    formData.append('name', clientName);
    formData.append('phone', clientPhone);
    if (clientEmail) {
        formData.append('email', clientEmail);
    }
    formData.append('content_type', contentType);
    formData.append('image', clientPhoto);
    formData.append('video', clientVideo);
    if (clientNotes) {
        formData.append('description', clientNotes);
    }
    
    // Add current company_id from state
    const companyId = AdminDashboard.state.currentCompany?.id || 'vertex-ar-default';
    formData.append('company_id', companyId);
    
    try {
        showLoading('Создание AR контента', 'Загрузка файлов...');
        
        // Simulate progress updates
        setTimeout(() => updateLoadingStatus('Обработка изображения...'), 500);
        setTimeout(() => updateLoadingStatus('Обработка видео...'), 1500);
        setTimeout(() => updateLoadingStatus('Генерация AR портрета...'), 3000);
        
        const response = await fetch('/orders/create', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        if (response.ok) {
            updateLoadingStatus('Завершение...');
            const result = await response.json();
            showToast('AR контент создан успешно', 'success');
            addLog(`Создан заказ для клиента: ${clientName}`, 'success');
            
            // Reset form
            form.reset();
            hideImagePreview();
            
            // Toggle form visibility
            const formElement = document.getElementById('orderForm');
            const btn = document.querySelector('.create-ar-btn');
            if (formElement && btn) {
                formElement.classList.remove('active');
                btn.textContent = '+ Создать AR контент';
            }
            
            // Reload data
            loadRecords();
            loadStatistics();
            
        } else {
            let errorMessage = 'Ошибка при создании заказа';
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    if (Array.isArray(errorData.detail)) {
                        errorMessage = errorData.detail.map(err => err.msg || err).join(', ');
                    } else {
                        errorMessage = errorData.detail;
                    }
                }
            } catch (e) {
                // If response is not JSON, use status text
                errorMessage = `Ошибка ${response.status}: ${response.statusText}`;
            }
            
            showToast(errorMessage, 'error');
            addLog(`Ошибка при создании заказа: ${errorMessage}`, 'error');
        }
    } catch (error) {
        console.error('Error creating order:', error);
        showToast('Ошибка сети при создании заказа', 'error');
        addLog(`Ошибка сети при создании заказа: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Logging functionality
function addLog(message, type = 'info') {
    const logContainer = document.getElementById('logContainer');
    if (!logContainer) return;
    
    // Remove empty message if exists
    const emptyMessage = logContainer.querySelector('.log-empty');
    if (emptyMessage) {
        emptyMessage.remove();
    }
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type}`;
    
    const timestamp = new Date().toLocaleTimeString('ru-RU');
    logEntry.innerHTML = `
        <span class="log-time">${timestamp}</span>
        <span class="log-message">${message}</span>
        <span class="log-type">${type}</span>
    `;
    
    logContainer.appendChild(logEntry);
    
    // Keep only last 50 log entries
    const entries = logContainer.querySelectorAll('.log-entry');
    if (entries.length > 50) {
        entries[0].remove();
    }
    
    // Scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Clear logs functionality
function clearLogs() {
    const logContainer = document.getElementById('logContainer');
    if (!logContainer) return;
    
    logContainer.innerHTML = '<p class="log-empty">Логи появятся во время работы системы</p>';
    addLog('Логи очищены', 'info');
}

// Initialize tooltips
function initializeTooltips() {
    // Basic tooltip implementation
    document.querySelectorAll('[title]').forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            // Could implement tooltip display here
        });
    });
}

// Load charts (placeholder)
function loadCharts() {
    // Chart loading would be implemented here
    console.log('Charts loaded');
}

// Notifications functionality
async function loadNotifications() {
    try {
        const response = await fetch('/notifications?limit=10', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateNotifications(data || []);
        } else {
            console.error('Failed to load notifications:', response.status);
            updateNotifications([]);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        updateNotifications([]);
    }
}

function updateNotifications(notifications) {
    const notificationList = document.getElementById('notificationList');
    const notificationBadge = document.getElementById('notificationBadge');
    
    if (!notificationList || !notificationBadge) return;
    
    if (notifications.length === 0) {
        notificationList.innerHTML = '<p class="notification-empty">Новых уведомлений нет</p>';
        notificationBadge.classList.add('hidden');
        notificationBadge.textContent = '0';
        return;
    }
    
    notificationBadge.textContent = notifications.length;
    notificationBadge.classList.remove('hidden');
    
    notificationList.innerHTML = '';
    notifications.forEach(notification => {
        const notifElement = document.createElement('div');
        notifElement.className = 'notification-item';
        notifElement.innerHTML = `
            <div class="notification-title">${notification.title || 'Уведомление'}</div>
            <div class="notification-message">${notification.message || ''}</div>
            <div class="notification-time">${notification.created_at ? new Date(notification.created_at).toLocaleString('ru-RU') : ''}</div>
        `;
        notificationList.appendChild(notifElement);
    });
}

// Search functionality with advanced filters
async function performSearch(query = '', filters = {}) {
    try {
        let url = '/admin/search?';
        const params = [];
        
        if (query && query.trim()) {
            params.push(`q=${encodeURIComponent(query.trim())}`);
        }
        
        if (filters.dateFrom) {
            params.push(`date_from=${encodeURIComponent(filters.dateFrom)}`);
        }
        
        if (filters.dateTo) {
            params.push(`date_to=${encodeURIComponent(filters.dateTo)}`);
        }
        
        if (filters.minViews !== undefined && filters.minViews !== '') {
            params.push(`min_views=${filters.minViews}`);
        }
        
        if (filters.maxViews !== undefined && filters.maxViews !== '') {
            params.push(`max_views=${filters.maxViews}`);
        }
        
        const companyId = AdminDashboard.state.currentCompany?.id;
        if (companyId) {
            params.push(`company_id=${encodeURIComponent(companyId)}`);
        }
        
        url += params.join('&');
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayRecords(data.results || []);
            if (data.total_filtered !== undefined) {
                showToast(`Найдено записей: ${data.total_filtered}`, 'info');
            }
        } else {
            showToast('Ошибка поиска', 'error');
        }
    } catch (error) {
        console.error('Error searching:', error);
        showToast('Ошибка сети при поиске', 'error');
    }
}

// Apply filters from filter panel
window.applyFilters = function() {
    const dateFrom = document.getElementById('filterDateFrom')?.value;
    const dateTo = document.getElementById('filterDateTo')?.value;
    const minViews = document.getElementById('filterMinViews')?.value;
    const maxViews = document.getElementById('filterMaxViews')?.value;
    const searchQuery = document.getElementById('advancedSearch')?.value;
    
    const filters = {};
    if (dateFrom) filters.dateFrom = dateFrom;
    if (dateTo) filters.dateTo = dateTo;
    if (minViews) filters.minViews = parseInt(minViews);
    if (maxViews) filters.maxViews = parseInt(maxViews);
    
    performSearch(searchQuery || '', filters);
};

// Clear filters
window.clearFilters = function() {
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    document.getElementById('filterMinViews').value = '';
    document.getElementById('filterMaxViews').value = '';
    loadRecords();
    showToast('Фильтры сброшены', 'info');
};

// Toggle filters panel
window.toggleFiltersPanel = function() {
    const panel = document.getElementById('filtersPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
};

// ============================================================
// Storage Management Functions
// ============================================================

/**
 * Initialize storage management UI based on current company
 */
async function initializeStorageManagement() {
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showStorageEmptyState('Компания не выбрана');
        return;
    }
    
    try {
        // Fetch storage configuration for current company
        const response = await fetch(`/api/companies/${encodeURIComponent(companyId)}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const company = await response.json();
            updateStorageUI(company);
            
            // Load folders if local storage
            if (company.storage_type === 'local') {
                await loadStorageFolders();
            }
        } else {
            showStorageEmptyState('Не удалось загрузить настройки хранилища');
        }
    } catch (error) {
        console.error('Error initializing storage management:', error);
        showStorageEmptyState('Ошибка при загрузке настроек хранилища');
    }
}

/**
 * Update storage UI with company configuration
 */
function updateStorageUI(company) {
    const storageType = company.storage_type || 'local';
    const basePath = company.base_path || '/uploads';
    
    // Update storage type and path
    const storageTypeEl = document.getElementById('storageType');
    const storageBasePathEl = document.getElementById('storageBasePath');
    
    if (storageTypeEl) {
        storageTypeEl.textContent = getStorageTypeLabel(storageType);
    }
    
    if (storageBasePathEl) {
        storageBasePathEl.textContent = basePath;
    }
    
    // Update status badge
    updateStorageStatusBadge('ready');
    
    // Show/hide management UI based on storage type
    const emptyState = document.getElementById('storageEmptyState');
    const managementUI = document.getElementById('storageFolderManagement');
    
    if (storageType === 'local') {
        if (emptyState) emptyState.style.display = 'none';
        if (managementUI) managementUI.style.display = 'flex';
    } else {
        if (emptyState) emptyState.style.display = 'block';
        if (managementUI) managementUI.style.display = 'none';
    }
    
    // Populate content type selector
    populateContentTypeSelector(company.content_types || []);
}

/**
 * Get human-readable storage type label
 */
function getStorageTypeLabel(storageType) {
    const labels = {
        'local': 'Локальный диск',
        'yandex': 'Yandex Disk',
        's3': 'Amazon S3',
        'minio': 'MinIO'
    };
    return labels[storageType] || storageType;
}

/**
 * Update storage status badge
 */
function updateStorageStatusBadge(status) {
    const badge = document.getElementById('storageStatus');
    if (!badge) return;
    
    badge.setAttribute('data-status', status);
    
    const statusConfig = {
        'ready': { text: '✅ Готово', bg: 'var(--success-color)', color: 'white' },
        'warning': { text: '⚠️ Внимание', bg: 'var(--warning-color)', color: '#000' },
        'error': { text: '❌ Ошибка', bg: 'var(--danger-color)', color: 'white' }
    };
    
    const config = statusConfig[status] || statusConfig.ready;
    badge.textContent = config.text;
    badge.style.background = config.bg;
    badge.style.color = config.color;
}

/**
 * Show empty state message
 */
function showStorageEmptyState(message) {
    const emptyState = document.getElementById('storageEmptyState');
    const managementUI = document.getElementById('storageFolderManagement');
    
    if (emptyState) {
        emptyState.style.display = 'block';
        if (message) {
            const messageEl = emptyState.querySelector('p:last-child');
            if (messageEl) messageEl.textContent = message;
        }
    }
    
    if (managementUI) {
        managementUI.style.display = 'none';
    }
}

/**
 * Populate content type selector
 */
function populateContentTypeSelector(contentTypes) {
    const selector = document.getElementById('storageFolderContentType');
    if (!selector) return;
    
    // Clear existing options except first (placeholder)
    selector.innerHTML = '<option value="">Не указан</option>';
    
    // Add content types
    if (Array.isArray(contentTypes) && contentTypes.length > 0) {
        contentTypes.forEach(ct => {
            const option = document.createElement('option');
            option.value = ct.slug || ct;
            option.textContent = ct.label || ct;
            selector.appendChild(option);
        });
    }
}

/**
 * Load storage folders for current company
 */
async function loadStorageFolders() {
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) return;
    
    AdminDashboard.setState({ storageLoading: true });
    
    try {
        // TODO: Replace with actual API endpoint when backend is ready
        // For now, show empty state
        const folders = [];
        
        displayStorageFolders(folders);
    } catch (error) {
        console.error('Error loading storage folders:', error);
        showToast('Ошибка при загрузке списка папок', 'error');
    } finally {
        AdminDashboard.setState({ storageLoading: false });
    }
}

/**
 * Display storage folders in the list
 */
function displayStorageFolders(folders) {
    const listContainer = document.getElementById('storageFolderList');
    const countEl = document.getElementById('storageFolderCount');
    
    if (!listContainer) return;
    
    // Update count
    if (countEl) {
        countEl.textContent = `${folders.length} ${folders.length === 1 ? 'папка' : 'папок'}`;
    }
    
    // Clear list
    listContainer.innerHTML = '';
    
    if (folders.length === 0) {
        listContainer.innerHTML = `
            <div class="storage-empty-list" style="padding: 2rem 1rem; text-align: center; color: var(--secondary-color); font-size: 0.9rem;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem; opacity: 0.5;">📂</div>
                <p>Папки появятся здесь после создания</p>
            </div>
        `;
        return;
    }
    
    // Render folders
    folders.forEach(folder => {
        const folderItem = createFolderItemElement(folder);
        listContainer.appendChild(folderItem);
    });
}

/**
 * Create folder item element
 */
function createFolderItemElement(folder) {
    const item = document.createElement('div');
    item.className = 'storage-folder-item';
    item.dataset.folderId = folder.id || folder.name;
    
    const folderInfo = document.createElement('div');
    folderInfo.className = 'storage-folder-info';
    
    const folderName = document.createElement('div');
    folderName.className = 'storage-folder-name';
    folderName.innerHTML = `📁 ${escapeHtml(folder.name)}`;
    
    const folderMeta = document.createElement('div');
    folderMeta.className = 'storage-folder-meta';
    
    // Add metadata
    if (folder.content_type) {
        const metaItem = document.createElement('span');
        metaItem.className = 'storage-folder-meta-item';
        metaItem.innerHTML = `🏷️ ${escapeHtml(folder.content_type)}`;
        folderMeta.appendChild(metaItem);
    }
    
    if (folder.created_at) {
        const metaItem = document.createElement('span');
        metaItem.className = 'storage-folder-meta-item';
        metaItem.innerHTML = `📅 ${new Date(folder.created_at).toLocaleDateString('ru-RU')}`;
        folderMeta.appendChild(metaItem);
    }
    
    if (folder.file_count !== undefined) {
        const metaItem = document.createElement('span');
        metaItem.className = 'storage-folder-meta-item';
        metaItem.innerHTML = `📄 ${folder.file_count} файлов`;
        folderMeta.appendChild(metaItem);
    }
    
    folderInfo.appendChild(folderName);
    folderInfo.appendChild(folderMeta);
    
    const actions = document.createElement('div');
    actions.className = 'storage-folder-actions';
    
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'storage-folder-delete-btn';
    deleteBtn.textContent = '🗑️ Удалить';
    deleteBtn.onclick = () => deleteStorageFolder(folder.id || folder.name);
    
    actions.appendChild(deleteBtn);
    
    item.appendChild(folderInfo);
    item.appendChild(actions);
    
    return item;
}

/**
 * Validate folder name input
 */
function validateFolderInput() {
    const input = document.getElementById('storageFolderInput');
    const errorEl = document.getElementById('storageFolderInputError');
    const createBtn = document.getElementById('createFolderBtn');
    
    if (!input || !createBtn) return false;
    
    const value = input.value.trim();
    const pattern = /^[a-zA-Z0-9_-]+$/;
    
    if (!value) {
        input.classList.remove('error');
        if (errorEl) {
            errorEl.style.display = 'none';
            errorEl.textContent = '';
        }
        createBtn.disabled = true;
        return false;
    }
    
    if (!pattern.test(value)) {
        input.classList.add('error');
        if (errorEl) {
            errorEl.style.display = 'block';
            errorEl.textContent = 'Только буквы, цифры, дефисы и подчёркивания';
            errorEl.classList.add('visible');
        }
        createBtn.disabled = true;
        return false;
    }
    
    input.classList.remove('error');
    if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
        errorEl.classList.remove('visible');
    }
    createBtn.disabled = false;
    return true;
}

/**
 * Create new storage folder
 */
window.createStorageFolder = async function() {
    const input = document.getElementById('storageFolderInput');
    const contentTypeSelect = document.getElementById('storageFolderContentType');
    
    if (!validateFolderInput()) {
        return;
    }
    
    const folderName = input.value.trim();
    const contentType = contentTypeSelect?.value || '';
    const companyId = AdminDashboard.state.currentCompany?.id;
    
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    try {
        showLoading('Создание папки...');
        
        // TODO: Replace with actual API endpoint when backend is ready
        // const response = await fetch('/api/storage/folders', {
        //     method: 'POST',
        //     credentials: 'include',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({
        //         company_id: companyId,
        //         folder_name: folderName,
        //         content_type: contentType
        //     })
        // });
        
        // Simulated success for now
        await new Promise(resolve => setTimeout(resolve, 500));
        
        showToast(`Папка "${folderName}" создана (функция в разработке)`, 'info');
        input.value = '';
        if (contentTypeSelect) contentTypeSelect.value = '';
        
        // Refresh folder list
        await refreshStorageFolderList();
        
    } catch (error) {
        console.error('Error creating folder:', error);
        showToast('Ошибка при создании папки', 'error');
    } finally {
        hideLoading();
    }
};

/**
 * Refresh storage folder list
 */
window.refreshStorageFolderList = async function() {
    try {
        showLoading('Обновление списка...');
        await loadStorageFolders();
        showToast('Список папок обновлён', 'success');
    } catch (error) {
        console.error('Error refreshing folder list:', error);
        showToast('Ошибка при обновлении списка', 'error');
    } finally {
        hideLoading();
    }
};

/**
 * Delete storage folder
 */
async function deleteStorageFolder(folderId) {
    if (!confirm('Вы уверены, что хотите удалить эту папку? Это действие нельзя отменить.')) {
        return;
    }
    
    const companyId = AdminDashboard.state.currentCompany?.id;
    if (!companyId) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    try {
        showLoading('Удаление папки...');
        
        // TODO: Replace with actual API endpoint when backend is ready
        // const response = await fetch(`/api/storage/folders/${encodeURIComponent(folderId)}`, {
        //     method: 'DELETE',
        //     credentials: 'include',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({ company_id: companyId })
        // });
        
        // Simulated success for now
        await new Promise(resolve => setTimeout(resolve, 500));
        
        showToast('Папка удалена (функция в разработке)', 'info');
        
        // Refresh folder list
        await refreshStorageFolderList();
        
    } catch (error) {
        console.error('Error deleting folder:', error);
        showToast('Ошибка при удалении папки', 'error');
    } finally {
        hideLoading();
    }
}

// Add input validation listener
document.addEventListener('DOMContentLoaded', () => {
    const folderInput = document.getElementById('storageFolderInput');
    if (folderInput) {
        folderInput.addEventListener('input', validateFolderInput);
        folderInput.addEventListener('blur', validateFolderInput);
    }
    
    // Initialize storage management on page load
    initializeStorageManagement();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AdminDashboard };
}