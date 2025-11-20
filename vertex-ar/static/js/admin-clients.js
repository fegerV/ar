/**
 * Admin Clients Page JavaScript
 * Client management functionality with state management
 */

// Client management state
const ClientManager = {
    state: {
        clients: [],
        currentPage: 1,
        recordsPerPage: 25,
        selectedClients: new Set(),
        searchTerm: '',
        statusFilter: 'all',
        sortBy: 'created_at',
        sortOrder: 'desc',
        isLoading: false
    },
    
    // State persistence
    saveState() {
        try {
            const stateToSave = {
                currentPage: this.state.currentPage,
                recordsPerPage: this.state.recordsPerPage,
                statusFilter: this.state.statusFilter,
                sortBy: this.state.sortBy,
                sortOrder: this.state.sortOrder
            };
            localStorage.setItem('admin-clients-state', JSON.stringify(stateToSave));
        } catch (error) {
            console.warn('Failed to save clients state:', error);
        }
    },
    
    loadState() {
        try {
            const savedState = localStorage.getItem('admin-clients-state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                this.state = { ...this.state, ...parsedState };
            }
        } catch (error) {
            console.warn('Failed to load clients state:', error);
        }
    },
    
    setState(updates) {
        this.state = { ...this.state, ...updates };
        this.saveState();
    }
};

// Initialize clients page
function initializeClientsPage() {
    ClientManager.loadState();
    
    // Apply saved filters
    applyFilters();
    
    // Load initial data
    loadClients();
    loadClientStats();
    
    // Initialize event listeners
    initializeEventListeners();
    
    addLog('Страница управления клиентами загружена', 'info');
}

// Event listeners
function initializeEventListeners() {
    // Search
    const searchInput = document.getElementById('clientSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            ClientManager.setState({ 
                searchTerm: e.target.value.trim(),
                currentPage: 1 
            });
            loadClients();
        }, 300));
    }
    
    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function(e) {
            ClientManager.setState({ 
                statusFilter: e.target.value,
                currentPage: 1 
            });
            loadClients();
        });
    }
    
    // Sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', function(e) {
            const [sortBy, sortOrder] = e.target.value.split('-');
            ClientManager.setState({ 
                sortBy,
                sortOrder,
                currentPage: 1 
            });
            loadClients();
        });
    }
    
    // Records per page
    const recordsPerPage = document.getElementById('recordsPerPage');
    if (recordsPerPage) {
        recordsPerPage.addEventListener('change', function(e) {
            ClientManager.setState({ 
                recordsPerPage: parseInt(e.target.value),
                currentPage: 1 
            });
            loadClients();
        });
    }
    
    // Client form
    const clientForm = document.getElementById('clientForm');
    if (clientForm) {
        clientForm.addEventListener('submit', handleClientSubmit);
    }
    
    // Select all checkbox
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', handleSelectAll);
    }
    
    // Bulk actions
    const bulkDelete = document.getElementById('bulkDelete');
    if (bulkDelete) {
        bulkDelete.addEventListener('click', handleBulkDelete);
    }
    
    const bulkExport = document.getElementById('bulkExport');
    if (bulkExport) {
        bulkExport.addEventListener('click', handleBulkExport);
    }
    
    // Export buttons
    document.querySelectorAll('.export-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const format = this.dataset.format;
            exportClients(format);
        });
    });
}

// Load clients from server
async function loadClients() {
    try {
        ClientManager.setState({ isLoading: true });
        showLoading();
        
        const params = new URLSearchParams({
            page: ClientManager.state.currentPage,
            limit: ClientManager.state.recordsPerPage,
            search: ClientManager.state.searchTerm,
            status: ClientManager.state.statusFilter,
            sort_by: ClientManager.state.sortBy,
            sort_order: ClientManager.state.sortOrder
        });
        
        const response = await fetch(`/clients?${params}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            ClientManager.setState({ 
                clients: data.clients || [],
                totalCount: data.total_count || 0
            });
            displayClients();
            updatePagination();
        } else {
            throw new Error('Failed to load clients');
        }
    } catch (error) {
        console.error('Error loading clients:', error);
        showToast('Ошибка загрузки клиентов', 'error');
        addLog('Ошибка загрузки клиентов: ' + error.message, 'error');
    } finally {
        ClientManager.setState({ isLoading: false });
        hideLoading();
    }
}

// Load client statistics
async function loadClientStats() {
    try {
        const response = await fetch('/clients/stats', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateClientStats(data);
        }
    } catch (error) {
        console.error('Error loading client stats:', error);
        addLog('Ошибка загрузки статистики клиентов: ' + error.message, 'error');
    }
}

// Update client statistics display
function updateClientStats(stats) {
    const elements = {
        'totalClients': stats.total_clients || 0,
        'activeClients': stats.active_clients || 0,
        'newClients': stats.new_clients || 0,
        'inactiveClients': stats.inactive_clients || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// Display clients in table
function displayClients() {
    const tbody = document.querySelector('.clients-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (ClientManager.state.clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Клиенты не найдены</td></tr>';
        return;
    }
    
    ClientManager.state.clients.forEach(client => {
        const row = createClientRow(client);
        tbody.appendChild(row);
    });
    
    updateBulkActions();
}

// Create client row
function createClientRow(client) {
    const row = document.createElement('tr');
    const isSelected = ClientManager.state.selectedClients.has(client.id);
    
    row.innerHTML = `
        <td>
            <input type="checkbox" 
                   class="client-checkbox" 
                   data-client-id="${client.id}"
                   ${isSelected ? 'checked' : ''}>
        </td>
        <td>
            <img src="${client.avatar || '/static/default-avatar.png'}" 
                 alt="${client.name}" 
                 class="client-avatar"
                 onerror="this.src='/static/default-avatar.png'">
        </td>
        <td>
            <strong>${client.name || ''}</strong>
            ${client.email ? `<br><small style="color: var(--secondary-color)">${client.email}</small>` : ''}
        </td>
        <td>${client.phone || ''}</td>
        <td>
            <span class="status-badge ${client.status || 'active'}">
                ${getStatusText(client.status)}
            </span>
        </td>
        <td>${client.portraits_count || 0}</td>
        <td>${formatDate(client.created_at)}</td>
        <td>
            <div class="client-actions">
                <button class="action-btn view-btn" onclick="viewClient('${client.id}')" title="Просмотр">👁️</button>
                <button class="action-btn edit-btn" onclick="editClient('${client.id}')" title="Редактировать">✏️</button>
                <button class="action-btn delete-btn" onclick="deleteClient('${client.id}')" title="Удалить">🗑️</button>
            </div>
        </td>
    `;
    
    // Add checkbox event listener
    const checkbox = row.querySelector('.client-checkbox');
    checkbox.addEventListener('change', function() {
        handleClientSelection(client.id, this.checked);
    });
    
    return row;
}

// Handle client selection
function handleClientSelection(clientId, isSelected) {
    const selectedClients = new Set(ClientManager.state.selectedClients);
    
    if (isSelected) {
        selectedClients.add(clientId);
    } else {
        selectedClients.delete(clientId);
    }
    
    ClientManager.setState({ selectedClients });
    updateBulkActions();
    updateSelectAllCheckbox();
}

// Handle select all
function handleSelectAll(e) {
    const isChecked = e.target.checked;
    const selectedClients = isChecked 
        ? new Set(ClientManager.state.clients.map(c => c.id))
        : new Set();
    
    ClientManager.setState({ selectedClients });
    
    // Update all checkboxes
    document.querySelectorAll('.client-checkbox').forEach(checkbox => {
        checkbox.checked = isChecked;
    });
    
    updateBulkActions();
}

// Update select all checkbox
function updateSelectAllCheckbox() {
    const selectAll = document.getElementById('selectAll');
    if (!selectAll) return;
    
    const totalClients = ClientManager.state.clients.length;
    const selectedCount = ClientManager.state.selectedClients.size;
    
    selectAll.checked = totalClients > 0 && selectedCount === totalClients;
    selectAll.indeterminate = selectedCount > 0 && selectedCount < totalClients;
}

// Update bulk actions visibility
function updateBulkActions() {
    const bulkActions = document.querySelector('.bulk-actions');
    const selectedCount = document.querySelector('.selected-count');
    
    if (bulkActions) {
        bulkActions.classList.toggle('hidden', ClientManager.state.selectedClients.size === 0);
    }
    
    if (selectedCount) {
        selectedCount.textContent = `Выбрано: ${ClientManager.state.selectedClients.size}`;
    }
}

// Handle client form submission
async function handleClientSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Сохранение...';
    }
    
    try {
        const response = await fetch('/clients', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast('Клиент успешно создан', 'success');
            addLog(`Создан новый клиент: ${result.client.name}`, 'success');
            
            e.target.reset();
            loadClients();
            loadClientStats();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось создать клиента'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при создании клиента: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Создать клиента';
        }
    }
}

// View client details
async function viewClient(clientId) {
    try {
        showLoading();
        
        const response = await fetch(`/clients/${clientId}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const client = await response.json();
            showClientModal(client);
        } else {
            throw new Error('Client not found');
        }
    } catch (error) {
        console.error('Error loading client:', error);
        showToast('Ошибка загрузки данных клиента', 'error');
    } finally {
        hideLoading();
    }
}

// Show client details modal
function showClientModal(client) {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Детали клиента</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <div class="client-details">
                    <div class="detail-row">
                        <span class="detail-label">ID:</span>
                        <span class="detail-value">${client.id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Имя:</span>
                        <span class="detail-value">${client.name}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Email:</span>
                        <span class="detail-value">${client.email || 'Не указан'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Телефон:</span>
                        <span class="detail-value">${client.phone}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Статус:</span>
                        <span class="detail-value">
                            <span class="status-badge ${client.status}">${getStatusText(client.status)}</span>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Портретов:</span>
                        <span class="detail-value">${client.portraits_count || 0}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Создан:</span>
                        <span class="detail-value">${formatDate(client.created_at)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Последнее обновление:</span>
                        <span class="detail-value">${formatDate(client.updated_at)}</span>
                    </div>
                    ${client.notes ? `
                    <div class="detail-row">
                        <span class="detail-label">Примечания:</span>
                        <div class="client-notes">${client.notes}</div>
                    </div>
                    ` : ''}
                    ${client.portraits && client.portraits.length > 0 ? `
                    <div class="detail-row">
                        <span class="detail-label">Портреты:</span>
                        <div class="client-portraits">
                            ${client.portraits.map(portrait => `
                                <img src="${portrait.thumbnail || portrait.path}" 
                                     alt="Portrait" 
                                     class="portrait-thumb"
                                     onclick="showLightbox('${portrait.path}')"
                                     onerror="this.src='/static/default-portrait.png'">
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn cancel" onclick="this.closest('.modal').remove()">Закрыть</button>
                <button class="modal-btn confirm" onclick="editClient('${client.id}')">Редактировать</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Event listeners
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// Edit client
function editClient(clientId) {
    // Close modal if open
    const modal = document.querySelector('.modal.active');
    if (modal) modal.remove();
    
    // Redirect to edit page or open edit modal
    showToast(`Редактирование клиента ${clientId}`, 'info');
    addLog(`Начато редактирование клиента: ${clientId}`, 'info');
    
    // For now, just show a message
    // In a real implementation, this would open an edit form
}

// Delete client
async function deleteClient(clientId) {
    if (!confirm('Вы уверены, что хотите удалить этого клиента? Все связанные данные также будут удалены.')) {
        return;
    }
    
    try {
        const response = await fetch(`/clients/${clientId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            showToast('Клиент удален', 'success');
            addLog(`Удален клиент: ${clientId}`, 'success');
            
            loadClients();
            loadClientStats();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось удалить клиента'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при удалении клиента: ${error.message}`, 'error');
    }
}

// Handle bulk delete
async function handleBulkDelete() {
    const selectedCount = ClientManager.state.selectedClients.size;
    
    if (selectedCount === 0) {
        showToast('Нет выбранных клиентов', 'warning');
        return;
    }
    
    if (!confirm(`Вы уверены, что хотите удалить ${selectedCount} клиентов? Все связанные данные также будут удалены.`)) {
        return;
    }
    
    try {
        const response = await fetch('/clients/bulk-delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                client_ids: Array.from(ClientManager.state.selectedClients)
            }),
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showToast(`Удалено клиентов: ${result.deleted_count}`, 'success');
            addLog(`Массово удалено клиентов: ${result.deleted_count}`, 'success');
            
            ClientManager.setState({ selectedClients: new Set() });
            loadClients();
            loadClientStats();
        } else {
            const error = await response.json();
            showToast(`Ошибка: ${error.detail || 'Не удалось удалить клиентов'}`, 'error');
        }
    } catch (error) {
        showToast('Ошибка сети', 'error');
        addLog(`Ошибка сети при массовом удалении: ${error.message}`, 'error');
    }
}

// Handle bulk export
async function handleBulkExport() {
    const selectedCount = ClientManager.state.selectedClients.size;
    
    if (selectedCount === 0) {
        showToast('Нет выбранных клиентов', 'warning');
        return;
    }
    
    exportClients('csv', Array.from(ClientManager.state.selectedClients));
}

// Export clients
async function exportClients(format = 'csv', clientIds = null) {
    try {
        showLoading();
        
        const params = new URLSearchParams({
            format: format,
            include_portraits: 'true'
        });
        
        if (clientIds) {
            params.append('client_ids', clientIds.join(','));
        }
        
        const response = await fetch(`/clients/export?${params}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `clients-export-${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showToast('Данные экспортированы успешно', 'success');
            addLog(`Экспортированы клиенты в формате ${format}`, 'success');
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Ошибка экспорта данных', 'error');
        addLog(`Ошибка экспорта: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Update pagination
function updatePagination() {
    const { currentPage, recordsPerPage, totalCount } = ClientManager.state;
    const totalPages = Math.ceil(totalCount / recordsPerPage);
    
    const pagination = document.querySelector('.pagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    // Previous button
    const prevBtn = createPaginationButton('←', currentPage - 1, currentPage === 1);
    pagination.appendChild(prevBtn);
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        const btn = createPaginationButton(i, i, i === currentPage);
        pagination.appendChild(btn);
    }
    
    // Next button
    const nextBtn = createPaginationButton('→', currentPage + 1, currentPage === totalPages);
    pagination.appendChild(nextBtn);
    
    // Info
    const info = document.createElement('div');
    info.style.marginLeft = '1rem';
    info.style.color = 'var(--secondary-color)';
    info.textContent = `Страница ${currentPage} из ${totalPages} (${totalCount} записей)`;
    pagination.appendChild(info);
}

// Create pagination button
function createPaginationButton(text, page, isDisabled) {
    const button = document.createElement('button');
    button.textContent = text;
    button.className = 'pagination-btn';
    button.disabled = isDisabled;
    
    if (!isDisabled) {
        button.addEventListener('click', () => {
            ClientManager.setState({ currentPage: page });
            loadClients();
        });
    }
    
    return button;
}

// Apply saved filters
function applyFilters() {
    const statusFilter = document.getElementById('statusFilter');
    const sortSelect = document.getElementById('sortSelect');
    const recordsPerPage = document.getElementById('recordsPerPage');
    
    if (statusFilter) statusFilter.value = ClientManager.state.statusFilter;
    if (sortSelect) sortSelect.value = `${ClientManager.state.sortBy}-${ClientManager.state.sortOrder}`;
    if (recordsPerPage) recordsPerPage.value = ClientManager.state.recordsPerPage;
}

// Utility functions
function getStatusText(status) {
    const statusMap = {
        'active': 'Активен',
        'inactive': 'Неактивен',
        'pending': 'Ожидает',
        'suspended': 'Приостановлен'
    };
    return statusMap[status] || status;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('ru-RU');
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

// Show lightbox for portraits
function showLightbox(imageSrc) {
    const lightbox = document.querySelector('.lightbox');
    const lightboxContent = document.querySelector('.lightbox-content');
    
    if (lightbox && lightboxContent) {
        lightboxContent.src = imageSrc;
        lightbox.classList.add('active');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeClientsPage();
    
    // Performance monitoring
    if (window.performance) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`Clients page load time: ${loadTime}ms`);
        addLog(`Страница клиентов загружена за ${loadTime}ms`, 'info');
    }
});