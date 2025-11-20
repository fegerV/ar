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
        lastUpdate: null
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
    
    // Load initial data
    loadStatistics();
    loadSystemInfo();
    loadRecords();
    loadCompanies();
    loadBackupStats();
    loadNotifications();
    
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
        const response = await fetch('/admin/stats', {
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
        const response = await fetch('/admin/records', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            AdminDashboard.setState({ allRecords: data.records || [] });
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
    
    row.innerHTML = `
        <td>${record.order_number || ''}</td>
        <td>
            ${record.portrait_path ? 
                `<img src="${record.portrait_path}" 
                     alt="Portrait" 
                     class="portrait-preview"
                     onclick="showLightbox('${record.portrait_path}')"
                     onerror="this.src='${placeholderImage}'; this.onerror=null;"
                     style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">` : 
                `<div style="width: 50px; height: 50px; background: var(--border-color); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--secondary-color); font-size: 0.7rem;">${noImageText}</div>`
            }
        </td>
        <td>
            ${record.active_video_url ? 
                `<video src="${record.active_video_url}" 
                       class="video-preview" 
                       style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;"
                       onclick="window.open('${record.active_video_url}', '_blank')"></video>` : 
                '<div style="width: 50px; height: 50px; background: var(--border-color); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--secondary-color); font-size: 0.7rem;">Нет видео</div>'
            }
        </td>
        <td>${record.client_name || ''}</td>
        <td>${record.client_phone || ''}</td>
        <td>${record.views || 0}</td>
        <td>
            ${record.permanent_url ? 
                `<a href="${record.permanent_url}" target="_blank" class="link-button">Открыть</a>` : 
                'Нет ссылки'
            }
        </td>
        <td>
            ${record.qr_code ? 
                `<img src="${record.qr_code}" 
                     alt="QR Code" 
                     class="qr-preview"
                     onclick="showLightbox('${record.qr_code}')"
                     style="width: 30px; height: 30px;">` : 
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

async function createCompany() {
    const nameInput = document.getElementById('companyNameInput');
    const name = nameInput?.value?.trim();
    
    if (!name) {
        showToast('Введите название компании', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/companies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name }),
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
    
    showModal('deleteCompanyModal');
}

function hideDeleteCompanyModal() {
    hideModal('deleteCompanyModal');
    AdminDashboard.setState({ selectedCompanyToDelete: null });
}

async function confirmDeleteCompany() {
    const { selectedCompanyToDelete } = AdminDashboard.state;
    
    if (!selectedCompanyToDelete) {
        showToast('Компания не выбрана', 'error');
        return;
    }
    
    try {
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
    }
}

// Order form handling
async function handleOrderSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const submitBtn = e.target.querySelector('.upload-btn');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Загрузка...';
    }
    
    try {
        const response = await fetch('/admin/upload', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast('Заказ успешно создан!', 'success');
            addLog(`Создан новый заказ: ${result.order_id || 'unknown'}`, 'success');
            
            e.target.reset();
            hideImagePreview();
            loadRecords();
            loadStatistics();
        } else {
            const error = await response.json();
            let errorMessage = 'Не удалось создать заказ';
            
            if (error.detail) {
                if (typeof error.detail === 'string') {
                    errorMessage = error.detail;
                } else if (Array.isArray(error.detail)) {
                    errorMessage = error.detail.map(e => 
                        typeof e === 'string' ? e : (e.msg || 'Ошибка')
                    ).join(', ');
                } else if (typeof error.detail === 'object') {
                    errorMessage = Object.values(error.detail).map(v => 
                        typeof v === 'string' ? v : JSON.stringify(v)
                    ).join(', ');
                }
            }
            
            showToast(`Ошибка: ${errorMessage}`, 'error');
            addLog(`Ошибка при создании заказа: ${errorMessage}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при создании заказа: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Создать AR контент';
        }
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
        lightboxContent.src = imageSrc;
        lightbox.classList.add('active');
        addLog('Открыт просмотр изображения', 'info');
    }
}

function closeLightbox() {
    const lightbox = document.querySelector('.lightbox');
    if (lightbox) {
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
function showLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
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
    // This would open an edit modal or navigate to edit page
    showToast(`Редактирование записи ${recordId}`, 'info');
    addLog(`Начато редактирование записи: ${recordId}`, 'info');
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
    if (window.performance) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`Page load time: ${loadTime}ms`);
        addLog(`Страница загружена за ${loadTime}ms`, 'info');
    }
});

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

// Search functionality
async function performSearch(query) {
    if (!query.trim()) {
        loadRecords();
        return;
    }
    
    try {
        const response = await fetch(`/admin/search?q=${encodeURIComponent(query)}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayRecords(data.results || []);
        } else {
            showToast('Ошибка поиска', 'error');
        }
    } catch (error) {
        console.error('Error searching:', error);
        showToast('Ошибка сети при поиске', 'error');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AdminDashboard };
}