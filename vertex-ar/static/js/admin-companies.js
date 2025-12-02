/**
 * Admin Companies Management
 * Handles company CRUD operations, storage configuration, folder management, and backup settings
 */

const CompanyManager = {
    state: {
        companies: [],
        storageConnections: [],
        currentCompany: null,
        currentFolders: [],
        currentPath: '/',
        selectedFolder: null,
        backupProviders: [],
        isLoading: false
    },

    init() {
        this.setupEventListeners();
        this.applyTheme();
        this.loadInitialData();
    },

    setupEventListeners() {
        document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());
        document.getElementById('createCompanyBtn').addEventListener('click', () => this.openCreateCompanyModal());
        document.getElementById('refreshCompaniesBtn').addEventListener('click', () => this.loadCompanies());
        document.getElementById('saveCompanyBtn').addEventListener('click', () => this.saveCompany());
        document.getElementById('storageType').addEventListener('change', (e) => this.handleStorageTypeChange(e));
        document.getElementById('selectFolderBtn').addEventListener('click', () => this.openFolderModal());
        document.getElementById('createFolderBtn').addEventListener('click', () => this.createFolder());
        document.getElementById('selectFolderConfirmBtn').addEventListener('click', () => this.confirmFolderSelection());
        document.getElementById('saveBackupConfigBtn').addEventListener('click', () => this.saveBackupConfig());
    },

    applyTheme() {
        const theme = localStorage.getItem('admin-theme') || 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        const themeToggle = document.getElementById('themeToggle');
        themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('admin-theme', newTheme);
        const themeToggle = document.getElementById('themeToggle');
        themeToggle.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    },

    async loadInitialData() {
        this.showLoading('Загрузка данных...');
        try {
            await Promise.all([
                this.loadCompanies(),
                this.loadStorageConnections(),
                this.loadBackupProviders(),
                this.loadStatistics()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showToast('Ошибка загрузки данных', 'error');
        } finally {
            this.hideLoading();
        }
    },

    async loadCompanies() {
        try {
            const response = await fetch('/api/companies', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.state.companies = data.items || [];
            this.renderCompaniesTable();
        } catch (error) {
            console.error('Error loading companies:', error);
            this.showToast('Ошибка загрузки компаний', 'error');
            this.renderCompaniesTable();
        }
    },

    async loadStorageConnections() {
        try {
            const response = await fetch('/api/storage/connections', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.state.storageConnections = data.connections || [];
            }
        } catch (error) {
            console.error('Error loading storage connections:', error);
        }
    },

    async loadBackupProviders() {
        try {
            const response = await fetch('/api/remote-storage/providers', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.state.backupProviders = data.providers || [];
            }
        } catch (error) {
            console.error('Error loading backup providers:', error);
        }
    },

    async loadStatistics() {
        try {
            const response = await fetch('/admin/stats', {
                credentials: 'include'
            });

            if (response.ok) {
                const stats = await response.json();
                document.getElementById('totalCompanies').textContent = stats.companies || 0;
                document.getElementById('totalClients').textContent = stats.clients || 0;
                document.getElementById('totalPortraits').textContent = stats.portraits || 0;
                document.getElementById('totalStorageConnections').textContent = this.state.storageConnections.length || 0;
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    },

    renderCompaniesTable() {
        const tbody = document.getElementById('companiesTableBody');

        if (this.state.companies.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        <div class="empty-state-icon">🏢</div>
                        <div class="empty-state-text">Нет компаний</div>
                        <button class="btn btn-primary" onclick="CompanyManager.openCreateCompanyModal()">
                            Создать первую компанию
                        </button>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.state.companies.map(company => {
            const isDefault = company.id === 'vertex-ar-default';
            const storageTypeBadge = this.getStorageTypeBadge(company.storage_type);
            const backupStatus = this.getBackupStatus(company);
            const createdDate = new Date(company.created_at).toLocaleDateString('ru-RU');

            return `
                <tr>
                    <td>
                        <strong>${company.name}</strong>
                        ${isDefault ? '<span class="badge badge-info" style="margin-left: 0.5rem;">DEFAULT</span>' : ''}
                    </td>
                    <td>${storageTypeBadge}</td>
                    <td>
                        ${company.storage_folder_path || company.yandex_disk_folder_id || '-'}
                    </td>
                    <td>${company.client_count || 0}</td>
                    <td>${backupStatus}</td>
                    <td>${createdDate}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn btn-secondary btn-sm" onclick="CompanyManager.editCompany('${company.id}')">
                                ✏️ Редактировать
                            </button>
                            <button class="btn btn-secondary btn-sm" onclick="CompanyManager.configureBackup('${company.id}')">
                                🔒 Backup
                            </button>
                            ${!isDefault ? `
                                <button class="btn btn-danger btn-sm" onclick="CompanyManager.deleteCompany('${company.id}', '${company.name}')">
                                    🗑️ Удалить
                                </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    getStorageTypeBadge(storageType) {
        const badges = {
            'local': '<span class="badge badge-local">Локальный диск</span>',
            'local_disk': '<span class="badge badge-local">Локальное хранилище</span>',
            'yandex_disk': '<span class="badge badge-yandex">Yandex Disk</span>',
            's3': '<span class="badge badge-s3">S3</span>'
        };
        return badges[storageType] || '<span class="badge badge-secondary">Неизвестно</span>';
    },

    getBackupStatus(company) {
        if (!company.backup_provider) {
            return '<div class="backup-status"><span class="status-indicator danger"></span> Не настроено</div>';
        }
        return `<div class="backup-status"><span class="status-indicator success"></span> ${company.backup_provider}</div>`;
    },

    openCreateCompanyModal() {
        this.state.currentCompany = null;
        
        document.getElementById('companyModalTitle').textContent = 'Создать компанию';
        document.getElementById('companyName').value = '';
        document.getElementById('storageType').value = '';
        document.getElementById('storageConnection').value = '';
        document.getElementById('storageFolder').value = '';
        document.getElementById('storageConnectionGroup').style.display = 'none';
        document.getElementById('storageFolderGroup').style.display = 'none';
        
        this.showModal('companyModal');
    },

    async editCompany(companyId) {
        try {
            const company = this.state.companies.find(c => c.id === companyId);
            if (!company) {
                this.showToast('Компания не найдена', 'error');
                return;
            }

            this.state.currentCompany = company;
            
            document.getElementById('companyModalTitle').textContent = 'Редактировать компанию';
            document.getElementById('companyName').value = company.name;
            document.getElementById('companyName').disabled = true;
            document.getElementById('storageType').value = company.storage_type || 'local';
            document.getElementById('storageType').disabled = true;
            
            if (company.storage_connection_id) {
                await this.populateStorageConnections(company.storage_type);
                document.getElementById('storageConnection').value = company.storage_connection_id;
                document.getElementById('storageConnectionGroup').style.display = 'block';
            }

            if (company.storage_folder_path || company.yandex_disk_folder_id) {
                document.getElementById('storageFolder').value = company.storage_folder_path || company.yandex_disk_folder_id;
                document.getElementById('storageFolderGroup').style.display = 'block';
            }
            
            this.showModal('companyModal');
        } catch (error) {
            console.error('Error editing company:', error);
            this.showToast('Ошибка при загрузке компании', 'error');
        }
    },

    async deleteCompany(companyId, companyName) {
        if (companyId === 'vertex-ar-default') {
            this.showToast('Нельзя удалить компанию по умолчанию', 'error');
            return;
        }

        if (!confirm(`Вы уверены, что хотите удалить компанию "${companyName}"?\n\nБудут удалены:\n- Все клиенты компании\n- Все портреты\n- Все связанные данные\n\nЭто действие необратимо!`)) {
            return;
        }

        this.showLoading('Удаление компании...');
        try {
            const response = await fetch(`/api/companies/${companyId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                this.showToast('Компания успешно удалена', 'success');
                await this.loadCompanies();
                await this.loadStatistics();
            } else {
                const error = await response.json();
                this.showToast(error.detail || 'Ошибка при удалении компании', 'error');
            }
        } catch (error) {
            console.error('Error deleting company:', error);
            this.showToast('Ошибка сети при удалении компании', 'error');
        } finally {
            this.hideLoading();
        }
    },

    async saveCompany() {
        const companyName = document.getElementById('companyName').value.trim();
        const storageType = document.getElementById('storageType').value;
        const storageConnectionId = document.getElementById('storageConnection').value;
        const storageFolder = document.getElementById('storageFolder').value.trim();

        if (!companyName) {
            this.showToast('Введите название компании', 'error');
            return;
        }

        if (!storageType) {
            this.showToast('Выберите тип хранилища', 'error');
            return;
        }

        if (storageType !== 'local' && storageType !== 'local_disk' && !storageConnectionId) {
            this.showToast('Выберите подключение к хранилищу', 'error');
            return;
        }

        const payload = {
            name: companyName,
            storage_type: storageType,
            storage_connection_id: storageConnectionId || null
        };

        if (storageType === 'yandex_disk' && storageFolder) {
            payload.yandex_disk_folder_id = storageFolder;
        } else if ((storageType === 'local' || storageType === 'local_disk') && storageFolder) {
            payload.storage_folder_path = storageFolder;
        }

        this.showLoading(this.state.currentCompany ? 'Обновление компании...' : 'Создание компании...');
        
        try {
            let response;
            if (this.state.currentCompany) {
                if (storageFolder && storageType === 'yandex_disk') {
                    const folderResponse = await fetch(`/api/companies/${this.state.currentCompany.id}/yandex-disk-folder`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ folder_path: storageFolder })
                    });

                    if (!folderResponse.ok) {
                        const error = await folderResponse.json();
                        throw new Error(error.detail || 'Ошибка обновления папки');
                    }
                }

                this.showToast('Компания успешно обновлена', 'success');
            } else {
                response = await fetch('/api/companies', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка создания компании');
                }

                const newCompany = await response.json();
                this.showToast('Компания успешно создана', 'success');

                if (storageType !== 'local' && storageType !== 'local_disk' && !storageFolder) {
                    this.showToast('Не забудьте выбрать папку для хранения файлов', 'info');
                }
            }

            this.closeCompanyModal();
            await this.loadCompanies();
            await this.loadStatistics();
        } catch (error) {
            console.error('Error saving company:', error);
            this.showToast(error.message || 'Ошибка при сохранении компании', 'error');
        } finally {
            this.hideLoading();
        }
    },

    async handleStorageTypeChange(event) {
        const storageType = event.target.value;
        const storageConnectionGroup = document.getElementById('storageConnectionGroup');
        const storageFolderGroup = document.getElementById('storageFolderGroup');

        if (storageType === 'local' || storageType === 'local_disk') {
            storageConnectionGroup.style.display = 'none';
            storageFolderGroup.style.display = 'block';
            document.getElementById('storageConnection').required = false;
        } else if (storageType === 'yandex_disk') {
            storageConnectionGroup.style.display = 'block';
            storageFolderGroup.style.display = 'block';
            document.getElementById('storageConnection').required = true;
            await this.populateStorageConnections(storageType);
        } else {
            storageConnectionGroup.style.display = 'none';
            storageFolderGroup.style.display = 'none';
        }
    },

    async populateStorageConnections(storageType) {
        const select = document.getElementById('storageConnection');
        select.innerHTML = '<option value="">Выберите подключение</option>';

        const connections = this.state.storageConnections.filter(conn => {
            return conn.storage_type === storageType && conn.is_active && conn.is_tested;
        });

        if (connections.length === 0) {
            select.innerHTML += '<option value="" disabled>Нет активных подключений. Создайте в разделе "Хранилища"</option>';
            return;
        }

        connections.forEach(conn => {
            const option = document.createElement('option');
            option.value = conn.id;
            option.textContent = conn.name;
            select.appendChild(option);
        });
    },

    async openFolderModal() {
        const storageType = document.getElementById('storageType').value;
        const storageConnectionId = document.getElementById('storageConnection').value;

        if (storageType === 'yandex_disk' && !storageConnectionId) {
            this.showToast('Сначала выберите подключение к хранилищу', 'error');
            return;
        }

        this.state.currentPath = '/';
        this.state.selectedFolder = null;
        document.getElementById('currentPath').value = '/';
        
        this.showModal('folderModal');
        await this.loadFolders();
    },

    async loadFolders() {
        const storageType = document.getElementById('storageType').value;
        const folderList = document.getElementById('folderList');

        folderList.innerHTML = '<div class="empty-state"><div class="empty-state-text">Загрузка папок...</div></div>';

        try {
            let folders = [];

            if (storageType === 'yandex_disk') {
                const storageConnectionId = document.getElementById('storageConnection').value;
                const companyId = this.state.currentCompany?.id;
                
                let url = `/api/yandex-disk/folders?path=${encodeURIComponent(this.state.currentPath)}`;
                if (companyId) {
                    url += `&company_id=${companyId}`;
                } else if (storageConnectionId) {
                    url += `&storage_connection_id=${storageConnectionId}`;
                }

                const response = await fetch(url, {
                    credentials: 'include'
                });

                if (response.ok) {
                    const data = await response.json();
                    folders = data.items || [];
                }
            } else {
                folders = [
                    { name: 'portraits', path: '/portraits' },
                    { name: 'certificates', path: '/certificates' },
                    { name: 'diplomas', path: '/diplomas' }
                ];
            }

            this.state.currentFolders = folders;
            this.renderFolders();
        } catch (error) {
            console.error('Error loading folders:', error);
            folderList.innerHTML = '<div class="empty-state"><div class="empty-state-text">Ошибка загрузки папок</div></div>';
        }
    },

    renderFolders() {
        const folderList = document.getElementById('folderList');

        if (this.state.currentFolders.length === 0) {
            folderList.innerHTML = '<div class="empty-state"><div class="empty-state-text">Папок не найдено</div></div>';
            return;
        }

        folderList.innerHTML = this.state.currentFolders.map(folder => `
            <div class="folder-item" onclick="CompanyManager.selectFolder('${folder.path}', '${folder.name}')">
                📁 ${folder.name}
            </div>
        `).join('');
    },

    selectFolder(path, name) {
        this.state.selectedFolder = { path, name };
        
        document.querySelectorAll('.folder-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        event.target.closest('.folder-item').classList.add('selected');
    },

    async createFolder() {
        const folderName = document.getElementById('newFolderName').value.trim();
        if (!folderName) {
            this.showToast('Введите имя папки', 'error');
            return;
        }

        const storageType = document.getElementById('storageType').value;
        
        if (storageType === 'yandex_disk') {
            this.showToast('Создание папок на Яндекс.Диске пока не поддерживается через интерфейс', 'warning');
            return;
        }

        const newPath = `${this.state.currentPath}/${folderName}`.replace('//', '/');
        this.state.currentFolders.push({ name: folderName, path: newPath });
        this.renderFolders();
        document.getElementById('newFolderName').value = '';
        this.showToast(`Папка "${folderName}" будет создана при сохранении`, 'info');
    },

    confirmFolderSelection() {
        if (!this.state.selectedFolder) {
            this.showToast('Выберите папку из списка', 'error');
            return;
        }

        document.getElementById('storageFolder').value = this.state.selectedFolder.path;
        this.closeFolderModal();
        this.showToast(`Выбрана папка: ${this.state.selectedFolder.name}`, 'success');
    },

    async configureBackup(companyId) {
        const company = this.state.companies.find(c => c.id === companyId);
        if (!company) {
            this.showToast('Компания не найдена', 'error');
            return;
        }

        this.state.currentCompany = company;

        try {
            const response = await fetch(`/api/remote-storage/companies/${companyId}/backup-config`, {
                credentials: 'include'
            });

            if (response.ok) {
                const config = await response.json();
                document.getElementById('backupProvider').value = config.backup_provider || '';
                document.getElementById('backupRemotePath').value = config.backup_remote_path || '';
            } else {
                document.getElementById('backupProvider').value = '';
                document.getElementById('backupRemotePath').value = '';
            }
        } catch (error) {
            console.error('Error loading backup config:', error);
            document.getElementById('backupProvider').value = '';
            document.getElementById('backupRemotePath').value = '';
        }

        this.showModal('backupModal');
    },

    async saveBackupConfig() {
        if (!this.state.currentCompany) {
            this.showToast('Компания не выбрана', 'error');
            return;
        }

        const backupProvider = document.getElementById('backupProvider').value;
        const backupRemotePath = document.getElementById('backupRemotePath').value.trim();

        if (!backupProvider) {
            this.showToast('Выберите провайдер резервного копирования', 'error');
            return;
        }

        this.showLoading('Сохранение настроек резервного копирования...');
        
        try {
            const response = await fetch(`/api/remote-storage/companies/${this.state.currentCompany.id}/backup-config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    backup_provider: backupProvider,
                    backup_remote_path: backupRemotePath || null
                })
            });

            if (response.ok) {
                this.showToast('Настройки резервного копирования сохранены', 'success');
                this.closeBackupModal();
                await this.loadCompanies();
            } else {
                const error = await response.json();
                this.showToast(error.detail || 'Ошибка при сохранении настроек', 'error');
            }
        } catch (error) {
            console.error('Error saving backup config:', error);
            this.showToast('Ошибка сети при сохранении настроек', 'error');
        } finally {
            this.hideLoading();
        }
    },

    showModal(modalId) {
        document.getElementById(modalId).classList.add('active');
    },

    closeCompanyModal() {
        document.getElementById('companyModal').classList.remove('active');
        document.getElementById('companyName').disabled = false;
        document.getElementById('storageType').disabled = false;
    },

    closeFolderModal() {
        document.getElementById('folderModal').classList.remove('active');
    },

    closeBackupModal() {
        document.getElementById('backupModal').classList.remove('active');
    },

    showLoading(text = 'Загрузка...') {
        this.state.isLoading = true;
        document.getElementById('loadingText').textContent = text;
        document.getElementById('loadingOverlay').classList.add('active');
    },

    hideLoading() {
        this.state.isLoading = false;
        document.getElementById('loadingOverlay').classList.remove('active');
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }[type] || 'ℹ️';
        
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);
        
        setTimeout(() => toast.classList.add('show'), 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

window.CompanyManager = CompanyManager;

window.closeCompanyModal = () => CompanyManager.closeCompanyModal();
window.closeFolderModal = () => CompanyManager.closeFolderModal();
window.closeBackupModal = () => CompanyManager.closeBackupModal();

document.addEventListener('DOMContentLoaded', () => {
    CompanyManager.init();
});
