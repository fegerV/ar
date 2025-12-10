-- PostgreSQL Migration for Vertex AR (ARV) - Clean Database Setup
-- Version: 1.0.0
-- Description: Complete database schema for Vertex AR application with all required tables
-- Compatible with PostgreSQL 12+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop all tables in correct order (for clean re-run)
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS email_queue CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS notification_history CASCADE;
DROP TABLE IF EXISTS email_templates CASCADE;
DROP TABLE IF EXISTS video_schedule_history CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS portraits CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS folders CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS storage_connections CASCADE;
DROP TABLE IF EXISTS admin_settings CASCADE;
DROP TABLE IF EXISTS notification_settings CASCADE;
DROP TABLE IF EXISTS monitoring_settings CASCADE;
DROP TABLE IF EXISTS admin_sessions CASCADE;
DROP TABLE IF EXISTS ar_content CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- 1. BASIC TABLES
-- ============================================

-- Users table with email-based authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Indexes for users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Companies table with comprehensive fields
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT,
    description TEXT,
    storage_type TEXT NOT NULL DEFAULT 'local_disk' CHECK (storage_type IN ('local', 'local_disk', 'minio', 'yandex_disk')),
    yandex_disk_folder_id TEXT,
    content_types TEXT DEFAULT 'portraits:Portraits',
    backup_provider TEXT DEFAULT 'local' CHECK (backup_provider IN ('local', 'yandex_disk', 'google_drive')),
    backup_remote_path TEXT,
    storage_connection_id UUID REFERENCES storage_connections(id),
    storage_folder_path TEXT DEFAULT 'content',
    email TEXT,
    city TEXT,
    phone TEXT,
    website TEXT,
    manager_name TEXT,
    manager_phone TEXT,
    manager_email TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for companies
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_slug ON companies(slug);
CREATE INDEX idx_companies_storage_type ON companies(storage_type);
CREATE INDEX idx_companies_created_at ON companies(created_at);
CREATE UNIQUE INDEX idx_companies_name_unique ON companies(name);

-- ============================================
-- 2. CONTENT HIERARCHY
-- ============================================

-- Projects table with lifecycle management
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    subscription_end TIMESTAMP WITH TIME ZONE,
    lifecycle_status TEXT DEFAULT 'active' CHECK (lifecycle_status IN ('active', 'expiring', 'archived')),
    notified_7d BOOLEAN NOT NULL DEFAULT false,
    notified_24h BOOLEAN NOT NULL DEFAULT false,
    notified_expired BOOLEAN NOT NULL DEFAULT false,
    last_status_change TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for projects
CREATE INDEX idx_projects_company_id ON projects(company_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_lifecycle_status ON projects(lifecycle_status);
CREATE INDEX idx_projects_subscription_end ON projects(subscription_end);
CREATE INDEX idx_projects_created_at ON projects(created_at);
CREATE UNIQUE INDEX idx_projects_company_name ON projects(company_id, name);
CREATE UNIQUE INDEX idx_projects_company_slug ON projects(company_id, slug) WHERE slug IS NOT NULL;

-- Folders table for content organization
CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for folders
CREATE INDEX idx_folders_project_id ON folders(project_id);
CREATE INDEX idx_folders_name ON folders(name);
CREATE UNIQUE INDEX idx_folders_project_name ON folders(project_id, name);

-- Clients table with email support
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for clients
CREATE INDEX idx_clients_company_id ON clients(company_id);
CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_email ON clients(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX idx_clients_company_phone ON clients(company_id, phone);
CREATE UNIQUE INDEX idx_clients_company_email ON clients(company_id, email) WHERE email IS NOT NULL;

-- Portraits table with lifecycle management
CREATE TABLE portraits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    file_path TEXT NOT NULL,
    public_url TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    subscription_end TIMESTAMP WITH TIME ZONE,
    lifecycle_status TEXT DEFAULT 'active' CHECK (lifecycle_status IN ('active', 'expiring', 'archived')),
    notified_7d BOOLEAN NOT NULL DEFAULT false,
    notified_24h BOOLEAN NOT NULL DEFAULT false,
    notified_expired BOOLEAN NOT NULL DEFAULT false,
    last_status_change TIMESTAMP WITH TIME ZONE,
    image_preview_path TEXT,
    marker_fset TEXT,
    marker_fset3 TEXT,
    marker_iset TEXT,
    permanent_link TEXT UNIQUE,
    qr_code TEXT,
    view_count INTEGER NOT NULL DEFAULT 0,
    click_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for portraits
CREATE INDEX idx_portraits_company_id ON portraits(company_id);
CREATE INDEX idx_portraits_client_id ON portraits(client_id);
CREATE INDEX idx_portraits_folder_id ON portraits(folder_id) WHERE folder_id IS NOT NULL;
CREATE INDEX idx_portraits_status ON portraits(status);
CREATE INDEX idx_portraits_lifecycle_status ON portraits(lifecycle_status);
CREATE INDEX idx_portraits_subscription_end ON portraits(subscription_end);
CREATE INDEX idx_portraits_permanent_link ON portraits(permanent_link) WHERE permanent_link IS NOT NULL;
CREATE INDEX idx_portraits_created_at ON portraits(created_at);

-- Videos table with scheduling support
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portrait_id UUID NOT NULL REFERENCES portraits(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    public_url TEXT,
    status TEXT NOT NULL DEFAULT 'inactive' CHECK (status IN ('active', 'inactive', 'archived')),
    schedule_start TIMESTAMP WITH TIME ZONE,
    schedule_end TIMESTAMP WITH TIME ZONE,
    rotation_type TEXT DEFAULT 'none' CHECK (rotation_type IN ('none', 'sequential', 'cyclic')),
    is_active BOOLEAN NOT NULL DEFAULT false,
    video_preview_path TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for videos
CREATE INDEX idx_videos_portrait_id ON videos(portrait_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_is_active ON videos(is_active);
CREATE INDEX idx_videos_schedule_start ON videos(schedule_start) WHERE schedule_start IS NOT NULL;
CREATE INDEX idx_videos_schedule_end ON videos(schedule_end) WHERE schedule_end IS NOT NULL;
CREATE INDEX idx_videos_rotation_type ON videos(rotation_type);
CREATE INDEX idx_videos_created_at ON videos(created_at);

-- ============================================
-- 3. ORDERS AND CLIENTS
-- ============================================

-- Orders table for order management
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL DEFAULT 'portraits',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'cancelled', 'failed')),
    amount DECIMAL(10, 2),
    subscription_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for orders
CREATE INDEX idx_orders_company_id ON orders(company_id);
CREATE INDEX idx_orders_client_id ON orders(client_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_content_type ON orders(content_type);
CREATE INDEX idx_orders_subscription_end ON orders(subscription_end) WHERE subscription_end IS NOT NULL;
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ============================================
-- 4. STORAGE AND CONFIGURATION
-- ============================================

-- Storage connections table
CREATE TABLE storage_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('local', 'minio', 'yandex_disk')),
    config TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_tested BOOLEAN NOT NULL DEFAULT false,
    test_result TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for storage_connections
CREATE INDEX idx_storage_connections_name ON storage_connections(name);
CREATE INDEX idx_storage_connections_type ON storage_connections(type);
CREATE INDEX idx_storage_connections_is_active ON storage_connections(is_active);
CREATE INDEX idx_storage_connections_is_tested ON storage_connections(is_tested);

-- ============================================
-- 5. EMAIL AND NOTIFICATIONS
-- ============================================

-- Email queue table for persistent email processing
CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_to TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    html TEXT,
    template_id TEXT,
    variables TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sending', 'sent', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for email_queue
CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_created_at ON email_queue(created_at);
CREATE INDEX idx_email_queue_status_created ON email_queue(status, created_at);
CREATE INDEX idx_email_queue_attempts ON email_queue(attempts) WHERE attempts > 0;

-- Notifications table with comprehensive fields
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'info' CHECK (type IN ('info', 'success', 'warning', 'error')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('ignore', 'low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'read', 'processed', 'archived')),
    source TEXT,
    service_name TEXT,
    event_data TEXT,
    group_id TEXT,
    user_id TEXT,
    is_read BOOLEAN NOT NULL DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for notifications
CREATE INDEX idx_notifications_company_id ON notifications(company_id) WHERE company_id IS NOT NULL;
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_priority ON notifications(priority);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_source ON notifications(source) WHERE source IS NOT NULL;
CREATE INDEX idx_notifications_group_id ON notifications(group_id) WHERE group_id IS NOT NULL;
CREATE INDEX idx_notifications_user_id ON notifications(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_group_id_status ON notifications(group_id, status) WHERE group_id IS NOT NULL;
CREATE INDEX idx_notifications_source_created ON notifications(source, created_at) WHERE source IS NOT NULL;

-- ============================================
-- 6. AUDIT
-- ============================================

-- Audit log table for tracking changes
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL,
    entity_id UUID,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'view', 'login', 'logout')),
    changes TEXT,
    actor_id UUID REFERENCES users(id),
    actor_email TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit_log
CREATE INDEX idx_audit_log_entity_type ON audit_log(entity_type);
CREATE INDEX idx_audit_log_entity_id ON audit_log(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_actor_id ON audit_log(actor_id) WHERE actor_id IS NOT NULL;
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_entity_action ON audit_log(entity_type, entity_id, action);

-- ============================================
-- 7. LEGACY AND ADDITIONAL TABLES
-- ============================================

-- Legacy AR content table (for backward compatibility)
CREATE TABLE ar_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    image_path TEXT NOT NULL,
    video_path TEXT NOT NULL,
    image_preview_path TEXT,
    video_preview_path TEXT,
    marker_fset TEXT NOT NULL,
    marker_fset3 TEXT NOT NULL,
    marker_iset TEXT NOT NULL,
    ar_url TEXT NOT NULL,
    qr_code TEXT,
    view_count INTEGER NOT NULL DEFAULT 0,
    click_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for ar_content
CREATE INDEX idx_ar_content_user_id ON ar_content(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_ar_content_created_at ON ar_content(created_at);

-- Video schedule history for tracking schedule changes
CREATE TABLE video_schedule_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    previous_status TEXT,
    new_status TEXT,
    previous_schedule_start TIMESTAMP WITH TIME ZONE,
    new_schedule_start TIMESTAMP WITH TIME ZONE,
    previous_schedule_end TIMESTAMP WITH TIME ZONE,
    new_schedule_end TIMESTAMP WITH TIME ZONE,
    previous_rotation_type TEXT,
    new_rotation_type TEXT,
    actor_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for video_schedule_history
CREATE INDEX idx_video_schedule_history_video_id ON video_schedule_history(video_id);
CREATE INDEX idx_video_schedule_history_created_at ON video_schedule_history(created_at);

-- Admin settings for system configuration
CREATE TABLE admin_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    yandex_client_id TEXT,
    yandex_client_secret_encrypted TEXT,
    yandex_redirect_uri TEXT,
    yandex_smtp_email TEXT,
    yandex_smtp_password_encrypted TEXT,
    yandex_connection_status TEXT DEFAULT 'disconnected' CHECK (yandex_connection_status IN ('connected', 'disconnected', 'reconnect_needed')),
    yandex_smtp_status TEXT DEFAULT 'disconnected' CHECK (yandex_smtp_status IN ('connected', 'disconnected', 'reconnect_needed')),
    last_tested_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Notification settings
CREATE TABLE notification_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    email_enabled BOOLEAN NOT NULL DEFAULT true,
    telegram_enabled BOOLEAN NOT NULL DEFAULT false,
    telegram_bot_token TEXT,
    telegram_chat_id TEXT,
    smtp_host TEXT,
    smtp_port INTEGER,
    smtp_username TEXT,
    smtp_password_encrypted TEXT,
    smtp_use_tls BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Notification history
CREATE TABLE notification_history (
    id TEXT PRIMARY KEY,
    notification_type TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Email templates
CREATE TABLE email_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    html_template TEXT,
    variables_used TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring settings
CREATE TABLE monitoring_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cpu_threshold REAL NOT NULL DEFAULT 80.0,
    memory_threshold REAL NOT NULL DEFAULT 85.0,
    disk_threshold REAL NOT NULL DEFAULT 90.0,
    health_check_interval INTEGER NOT NULL DEFAULT 60,
    consecutive_failures INTEGER NOT NULL DEFAULT 3,
    dedup_window_seconds INTEGER NOT NULL DEFAULT 300,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Admin sessions
CREATE TABLE admin_sessions (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Indexes for admin_sessions
CREATE INDEX idx_admin_sessions_user_id ON admin_sessions(user_id);
CREATE INDEX idx_admin_sessions_username ON admin_sessions(username);
CREATE INDEX idx_admin_sessions_expires_at ON admin_sessions(expires_at);
CREATE INDEX idx_admin_sessions_is_active ON admin_sessions(is_active);

-- ============================================
-- 8. TRIGGERS AND FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_folders_updated_at BEFORE UPDATE ON folders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_portraits_updated_at BEFORE UPDATE ON portraits FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_storage_connections_updated_at BEFORE UPDATE ON storage_connections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_email_queue_updated_at BEFORE UPDATE ON email_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_admin_settings_updated_at BEFORE UPDATE ON admin_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notification_settings_updated_at BEFORE UPDATE ON notification_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_monitoring_settings_updated_at BEFORE UPDATE ON monitoring_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 9. DEFAULT DATA
-- ============================================

-- Insert default admin user (password: admin123 - should be changed in production)
INSERT INTO users (email, password, full_name, role, is_active) 
VALUES ('admin@vertex-ar.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/V3SA0zHVe', 'System Administrator', 'admin', true);

-- Insert default company
INSERT INTO companies (id, name, slug, description, storage_type, content_types, email, city, phone, website, manager_name, manager_phone, manager_email)
VALUES (
    uuid_generate_v4(),
    'Vertex AR',
    'vertex-ar',
    'Default company for Vertex AR platform',
    'local_disk',
    'portraits:Portraits',
    'contact@vertex-ar.com',
    'Moscow',
    '+7 (495) 000-00-00',
    'https://vertex-ar.com',
    'System Administrator',
    '+7 (495) 000-00-00',
    'admin@vertex-ar.com'
) ON CONFLICT (name) DO NOTHING;

-- Insert default notification settings
INSERT INTO notification_settings (id, email_enabled) VALUES ('default', true) ON CONFLICT (id) DO NOTHING;

-- Insert default monitoring settings
INSERT INTO monitoring_settings (id) VALUES ('default') ON CONFLICT (id) DO NOTHING;

-- Insert default admin settings
INSERT INTO admin_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 10. VIEWS FOR COMMON QUERIES
-- ============================================

-- View for active users with company info
CREATE VIEW active_users AS
SELECT 
    u.id,
    u.email,
    u.full_name,
    u.role,
    u.last_login,
    c.name as company_name
FROM users u
LEFT JOIN companies c ON true  -- This would need actual company association in a real implementation
WHERE u.is_active = true;

-- View for company statistics
CREATE VIEW company_statistics AS
SELECT 
    c.id,
    c.name,
    c.storage_type,
    COUNT(DISTINCT p.id) as project_count,
    COUNT(DISTINCT f.id) as folder_count,
    COUNT(DISTINCT cl.id) as client_count,
    COUNT(DISTINCT pt.id) as portrait_count,
    COUNT(DISTINCT v.id) as video_count,
    COUNT(DISTINCT o.id) as order_count
FROM companies c
LEFT JOIN projects p ON c.id = p.company_id
LEFT JOIN folders f ON p.id = f.project_id
LEFT JOIN clients cl ON c.id = cl.company_id
LEFT JOIN portraits pt ON c.id = pt.company_id
LEFT JOIN videos v ON pt.id = v.portrait_id
LEFT JOIN orders o ON c.id = o.company_id
GROUP BY c.id, c.name, c.storage_type;

-- View for pending email queue
CREATE VIEW pending_emails AS
SELECT 
    eq.id,
    eq.recipient_to,
    eq.subject,
    eq.status,
    eq.attempts,
    eq.created_at,
    eq.updated_at
FROM email_queue eq
WHERE eq.status IN ('pending', 'sending')
ORDER BY eq.created_at ASC;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Vertex AR PostgreSQL migration completed successfully';
    RAISE NOTICE 'Database version: %', version();
    RAISE NOTICE 'Migration timestamp: %', CURRENT_TIMESTAMP;
END $$;