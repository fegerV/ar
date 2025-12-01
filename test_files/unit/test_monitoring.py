"""
Unit tests for monitoring system web server health checks.

Tests verify:
- Fallback from public URL to localhost when BASE_URL fails
- Structured error reporting for each attempted URL
- Process and port diagnostics using psutil
- Proper handling of SSL, connection, and timeout errors
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import requests
import socket

# Ensure app module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWebServerHealthCheck(unittest.TestCase):
    """Test web server health check with fallback and diagnostics."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.BASE_URL = "https://example.com"
        self.mock_settings.INTERNAL_HEALTH_URL = ""
        self.mock_settings.APP_PORT = 8000
        
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_public_url_success(self, mock_port, mock_process, mock_get, mock_settings):
        """Test successful health check on public URL (no fallback needed)."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        self.assertTrue(result["healthy"])
        self.assertEqual(result["status"], "operational")
        self.assertEqual(result["status_code"], 200)
        self.assertIn("successful_url", result)
        self.assertEqual(len(result["attempts"]), 1)
        self.assertTrue(result["attempts"][0]["success"])
        
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_fallback_to_localhost(self, mock_port, mock_process, mock_get, mock_settings):
        """Test fallback to localhost when public URL fails."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # First call (public URL) fails with SSL error, second call (localhost) succeeds
        mock_response_fail = Mock()
        mock_response_fail.side_effect = requests.exceptions.SSLError("SSL certificate verification failed")
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        
        mock_get.side_effect = [
            requests.exceptions.SSLError("SSL certificate verification failed"),  # public URL fails
            mock_response_success,  # localhost succeeds
        ]
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        self.assertTrue(result["healthy"])
        self.assertEqual(result["status"], "operational")
        self.assertEqual(result["successful_url_type"], "localhost")
        self.assertGreaterEqual(len(result["attempts"]), 2)
        
        # First attempt should have failed with SSL error
        self.assertFalse(result["attempts"][0]["success"])
        self.assertIn("SSL", result["attempts"][0]["error"])
        
        # Second attempt should have succeeded
        self.assertTrue(result["attempts"][1]["success"])
        
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_all_attempts_fail_with_diagnostics(self, mock_port, mock_process, mock_get, mock_settings):
        """Test all URL attempts fail but process/port diagnostics show service is running."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # All HTTP requests fail
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # But process is running and port is open
        mock_process.return_value = {
            "running": True,
            "pid": 12345,
            "name": "uvicorn",
            "cpu_percent": 5.2,
            "memory_mb": 150.5,
            "num_threads": 4,
        }
        
        mock_port.return_value = {
            "port": 8000,
            "accepting_connections": True,
            "status": "open",
        }
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        # Should be degraded (not failed) because process is running and port is open
        self.assertFalse(result["healthy"])
        self.assertEqual(result["status"], "degraded")
        self.assertIn("status_message", result)
        
        # All attempts should have failed
        for attempt in result["attempts"]:
            self.assertFalse(attempt["success"])
            self.assertIsNotNone(attempt["error"])
        
        # Process info should show service is running
        self.assertTrue(result["process_info"]["running"])
        self.assertEqual(result["process_info"]["pid"], 12345)
        
        # Port info should show port is open
        self.assertTrue(result["port_info"]["accepting_connections"])
        self.assertEqual(result["port_info"]["status"], "open")
        
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_all_attempts_fail_service_down(self, mock_port, mock_process, mock_get, mock_settings):
        """Test all attempts fail and diagnostics confirm service is down."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # All HTTP requests fail
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Process is not running
        mock_process.return_value = {
            "running": False,
            "error": "No uvicorn/gunicorn process found"
        }
        
        # Port is closed
        mock_port.return_value = {
            "port": 8000,
            "accepting_connections": False,
            "status": "closed",
        }
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        # Should be failed
        self.assertFalse(result["healthy"])
        self.assertEqual(result["status"], "failed")
        
        # All attempts should have failed
        for attempt in result["attempts"]:
            self.assertFalse(attempt["success"])
            self.assertIsNotNone(attempt["error"])
        
        # Process info should show service is not running
        self.assertFalse(result["process_info"]["running"])
        
        # Port info should show port is closed
        self.assertFalse(result["port_info"]["accepting_connections"])
        
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_internal_health_url_priority(self, mock_port, mock_process, mock_get, mock_settings):
        """Test INTERNAL_HEALTH_URL is tried first when configured."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings with internal URL
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = "http://localhost:8000"
        mock_settings.APP_PORT = 8000
        
        # Mock successful response on first try
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        self.assertTrue(result["healthy"])
        self.assertEqual(result["successful_url_type"], "internal")
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["attempts"][0]["type"], "internal")
        
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_timeout_error_recorded(self, mock_port, mock_process, mock_get, mock_settings):
        """Test timeout errors are properly recorded in diagnostics."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # All requests timeout
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out after 5 seconds")
        
        mock_process.return_value = {"running": False}
        mock_port.return_value = {"accepting_connections": False, "status": "closed"}
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        self.assertFalse(result["healthy"])
        
        # All attempts should have timeout errors
        for attempt in result["attempts"]:
            self.assertFalse(attempt["success"])
            self.assertIn("Timeout", attempt["error"])
            
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_http_error_status_code_recorded(self, mock_port, mock_process, mock_get, mock_settings):
        """Test non-200 HTTP status codes are properly recorded."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # Return 503 Service Unavailable
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        mock_process.return_value = {"running": True}
        mock_port.return_value = {"accepting_connections": True, "status": "open"}
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        self.assertFalse(result["healthy"])
        
        # All attempts should have HTTP error
        for attempt in result["attempts"]:
            self.assertFalse(attempt["success"])
            self.assertEqual(attempt["status_code"], 503)
            self.assertIn("HTTP 503", attempt["error"])


class TestProcessAndPortDiagnostics(unittest.TestCase):
    """Test process and port status checking functions."""
    
    @patch('app.monitoring.psutil.Process')
    @patch('app.monitoring.psutil.process_iter')
    def test_check_web_process_current_process(self, mock_process_iter, mock_process_class):
        """Test detecting uvicorn/gunicorn from current process."""
        from app.monitoring import SystemMonitor
        
        # Mock current process as uvicorn
        mock_process = Mock()
        mock_process.name.return_value = "uvicorn"
        mock_process.pid = 12345
        mock_process.cpu_percent.return_value = 5.2
        mock_process.memory_info.return_value = Mock(rss=150 * 1024 * 1024)
        mock_process.num_threads.return_value = 4
        mock_process.create_time.return_value = 1234567890.0
        
        mock_process_class.return_value = mock_process
        
        monitor = SystemMonitor()
        result = monitor._check_web_process()
        
        self.assertTrue(result["running"])
        self.assertEqual(result["pid"], 12345)
        self.assertEqual(result["name"], "uvicorn")
        
    @patch('app.monitoring.psutil.Process')
    @patch('app.monitoring.psutil.process_iter')
    def test_check_web_process_not_found(self, mock_process_iter, mock_process_class):
        """Test when no uvicorn/gunicorn process is found."""
        from app.monitoring import SystemMonitor
        
        # Mock current process as something else
        mock_process = Mock()
        mock_process.name.return_value = "bash"
        mock_process_class.return_value = mock_process
        
        # Mock process_iter returns no matching processes
        mock_process_iter.return_value = []
        
        monitor = SystemMonitor()
        result = monitor._check_web_process()
        
        self.assertFalse(result["running"])
        self.assertIn("error", result)
        
    @patch('socket.socket')
    def test_check_port_status_open(self, mock_socket_class):
        """Test port status check when port is open."""
        from app.monitoring import SystemMonitor
        
        # Mock successful connection (port is open)
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 0  # 0 means success
        mock_socket_class.return_value = mock_socket
        
        monitor = SystemMonitor()
        result = monitor._check_port_status(8000)
        
        self.assertEqual(result["port"], 8000)
        self.assertTrue(result["accepting_connections"])
        self.assertEqual(result["status"], "open")
        
    @patch('socket.socket')
    def test_check_port_status_closed(self, mock_socket_class):
        """Test port status check when port is closed."""
        from app.monitoring import SystemMonitor
        
        # Mock failed connection (port is closed)
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 111  # Connection refused
        mock_socket_class.return_value = mock_socket
        
        monitor = SystemMonitor()
        result = monitor._check_port_status(8000)
        
        self.assertEqual(result["port"], 8000)
        self.assertFalse(result["accepting_connections"])
        self.assertEqual(result["status"], "closed")


class TestMultipleURLAttempts(unittest.TestCase):
    """Test various URL attempt scenarios."""
    
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_structured_error_output(self, mock_port, mock_process, mock_get, mock_settings):
        """Test that each attempt has structured error information."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.BASE_URL = "https://example.com"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # Each URL fails with a different error
        mock_get.side_effect = [
            requests.exceptions.SSLError("SSL cert verification failed"),
            requests.exceptions.ConnectionError("Connection refused"),
            requests.exceptions.Timeout("Timeout"),
        ]
        
        mock_process.return_value = {"running": False}
        mock_port.return_value = {"accepting_connections": False, "status": "closed"}
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        # Verify each attempt has proper structure
        self.assertGreaterEqual(len(result["attempts"]), 3)
        
        for attempt in result["attempts"]:
            self.assertIn("type", attempt)
            self.assertIn("url", attempt)
            self.assertIn("success", attempt)
            self.assertIn("error", attempt)
            self.assertIn("response_time_ms", attempt)
            self.assertIn("status_code", attempt)
            self.assertFalse(attempt["success"])
            self.assertIsNotNone(attempt["error"])
            
    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_no_duplicate_localhost_urls(self, mock_port, mock_process, mock_get, mock_settings):
        """Test that localhost URLs are not duplicated in attempts list."""
        from app.monitoring import SystemMonitor
        
        # Configure BASE_URL as localhost
        mock_settings.BASE_URL = "http://localhost:8000"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        
        # First attempt succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        self.assertTrue(result["healthy"])
        
        # Should only have one attempt (no duplicate localhost URLs)
        self.assertEqual(len(result["attempts"]), 1)


class TestMonitoringPersistence(unittest.TestCase):
    """Test persistent monitoring settings and concurrency guards."""
    
    @patch('app.monitoring.settings')
    def test_load_persisted_settings_no_database(self, mock_settings):
        """Test initialization when database is not available."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.ALERTING_ENABLED = True
        mock_settings.HEALTH_CHECK_INTERVAL = 60
        mock_settings.CPU_THRESHOLD = 80.0
        mock_settings.MEMORY_THRESHOLD = 85.0
        mock_settings.DISK_THRESHOLD = 90.0
        mock_settings.MONITORING_CONSECUTIVE_FAILURES = 3
        mock_settings.MONITORING_DEDUP_WINDOW = 300
        mock_settings.NOTIFICATION_DEDUP_WINDOW = 300
        mock_settings.HEALTH_CHECK_COOLDOWN = 30
        mock_settings.MONITORING_MAX_RUNTIME = None
        mock_settings.ALERT_RECOVERY_MINUTES = 60
        
        monitor = SystemMonitor()
        
        # Verify defaults are loaded from settings
        self.assertEqual(monitor.alert_thresholds["cpu"], 80.0)
        self.assertEqual(monitor.alert_thresholds["memory"], 85.0)
        self.assertEqual(monitor.alert_thresholds["disk"], 90.0)
        self.assertEqual(monitor.check_interval, 60)
        self.assertEqual(monitor.consecutive_failure_threshold, 3)
        self.assertEqual(monitor.dedup_window, 300)
        self.assertEqual(monitor.health_check_cooldown, 30)
        self.assertIsNone(monitor.max_runtime_seconds)
        self.assertEqual(monitor.alert_recovery_minutes, 60)
    
    @patch('app.monitoring.settings')
    @patch('app.main.database')
    def test_load_persisted_settings_from_database(self, mock_db, mock_settings):
        """Test loading settings from database."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.ALERTING_ENABLED = True
        mock_settings.HEALTH_CHECK_INTERVAL = 60
        mock_settings.CPU_THRESHOLD = 80.0
        mock_settings.MEMORY_THRESHOLD = 85.0
        mock_settings.DISK_THRESHOLD = 90.0
        mock_settings.MONITORING_CONSECUTIVE_FAILURES = 3
        mock_settings.MONITORING_DEDUP_WINDOW = 300
        mock_settings.NOTIFICATION_DEDUP_WINDOW = 300
        
        # Mock database with persisted settings
        mock_db.get_monitoring_settings.return_value = {
            'cpu_threshold': 75.0,
            'memory_threshold': 80.0,
            'disk_threshold': 85.0,
            'health_check_interval': 90,
            'consecutive_failures': 5,
            'dedup_window_seconds': 600,
            'max_runtime_seconds': 120,
            'health_check_cooldown_seconds': 45,
            'alert_recovery_minutes': 90
        }
        
        monitor = SystemMonitor()
        
        # Verify persisted settings are loaded
        self.assertEqual(monitor.alert_thresholds["cpu"], 75.0)
        self.assertEqual(monitor.alert_thresholds["memory"], 80.0)
        self.assertEqual(monitor.alert_thresholds["disk"], 85.0)
        self.assertEqual(monitor.check_interval, 90)
        self.assertEqual(monitor.consecutive_failure_threshold, 5)
        self.assertEqual(monitor.dedup_window, 600)
        self.assertEqual(monitor.max_runtime_seconds, 120)
        self.assertEqual(monitor.health_check_cooldown, 45)
        self.assertEqual(monitor.alert_recovery_minutes, 90)
    
    @patch('app.monitoring.settings')
    def test_lock_initialization(self, mock_settings):
        """Test that monitoring lock is properly initialized."""
        import asyncio
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.ALERTING_ENABLED = True
        mock_settings.HEALTH_CHECK_INTERVAL = 60
        mock_settings.CPU_THRESHOLD = 80.0
        mock_settings.MEMORY_THRESHOLD = 85.0
        mock_settings.DISK_THRESHOLD = 90.0
        mock_settings.MONITORING_CONSECUTIVE_FAILURES = 3
        mock_settings.MONITORING_DEDUP_WINDOW = 300
        mock_settings.NOTIFICATION_DEDUP_WINDOW = 300
        
        monitor = SystemMonitor()
        
        # Verify lock exists and is not locked initially
        self.assertIsInstance(monitor._monitoring_lock, asyncio.Lock)
        self.assertFalse(monitor._monitoring_lock.locked())
        self.assertIsNone(monitor._last_check_start)
        self.assertIsNone(monitor._last_check_end)
    
    @patch('app.monitoring.settings')
    @patch('app.main.database')
    def test_reload_settings(self, mock_db, mock_settings):
        """Test reloading settings from database."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.ALERTING_ENABLED = True
        mock_settings.HEALTH_CHECK_INTERVAL = 60
        mock_settings.CPU_THRESHOLD = 80.0
        mock_settings.MEMORY_THRESHOLD = 85.0
        mock_settings.DISK_THRESHOLD = 90.0
        mock_settings.MONITORING_CONSECUTIVE_FAILURES = 3
        mock_settings.MONITORING_DEDUP_WINDOW = 300
        mock_settings.NOTIFICATION_DEDUP_WINDOW = 300
        
        # Initial database state
        mock_db.get_monitoring_settings.return_value = {
            'cpu_threshold': 80.0,
            'memory_threshold': 85.0,
            'disk_threshold': 90.0,
            'health_check_interval': 60,
            'consecutive_failures': 3,
            'dedup_window_seconds': 300,
            'max_runtime_seconds': None,
            'health_check_cooldown_seconds': 30,
            'alert_recovery_minutes': 60
        }
        
        monitor = SystemMonitor()
        
        # Update database settings
        mock_db.get_monitoring_settings.return_value = {
            'cpu_threshold': 85.0,
            'memory_threshold': 90.0,
            'disk_threshold': 95.0,
            'health_check_interval': 120,
            'consecutive_failures': 5,
            'dedup_window_seconds': 600,
            'max_runtime_seconds': 180,
            'health_check_cooldown_seconds': 60,
            'alert_recovery_minutes': 120
        }
        
        # Reload settings
        success = monitor.reload_settings()
        
        # Verify settings were updated
        self.assertTrue(success)
        self.assertEqual(monitor.alert_thresholds["cpu"], 85.0)
        self.assertEqual(monitor.alert_thresholds["memory"], 90.0)
        self.assertEqual(monitor.alert_thresholds["disk"], 95.0)
        self.assertEqual(monitor.check_interval, 120)
        self.assertEqual(monitor.consecutive_failure_threshold, 5)
        self.assertEqual(monitor.dedup_window, 600)
        self.assertEqual(monitor.max_runtime_seconds, 180)
        self.assertEqual(monitor.health_check_cooldown, 60)
        self.assertEqual(monitor.alert_recovery_minutes, 120)
    
    @patch('app.monitoring.settings')
    @patch('app.main.database', None)
    def test_reload_settings_no_database(self, mock_settings):
        """Test reload_settings when database is not available."""
        from app.monitoring import SystemMonitor
        
        # Configure mock settings
        mock_settings.ALERTING_ENABLED = True
        mock_settings.HEALTH_CHECK_INTERVAL = 60
        mock_settings.CPU_THRESHOLD = 80.0
        mock_settings.MEMORY_THRESHOLD = 85.0
        mock_settings.DISK_THRESHOLD = 90.0
        mock_settings.MONITORING_CONSECUTIVE_FAILURES = 3
        mock_settings.MONITORING_DEDUP_WINDOW = 300
        mock_settings.NOTIFICATION_DEDUP_WINDOW = 300
        
        monitor = SystemMonitor()
        
        # Try to reload (should fail gracefully)
        success = monitor.reload_settings()
        
        # Verify failure is handled
        self.assertFalse(success)


class TestDeepDiagnostics(unittest.TestCase):
    """Test deep diagnostics functionality (hotspots)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.ALERTING_ENABLED = True
        self.mock_settings.HEALTH_CHECK_INTERVAL = 60
        self.mock_settings.CPU_THRESHOLD = 80.0
        self.mock_settings.MEMORY_THRESHOLD = 85.0
        self.mock_settings.DISK_THRESHOLD = 90.0
        self.mock_settings.MONITORING_CONSECUTIVE_FAILURES = 3
        self.mock_settings.MONITORING_DEDUP_WINDOW = 300
        self.mock_settings.NOTIFICATION_DEDUP_WINDOW = 300
        self.mock_settings.MONITORING_PROCESS_HISTORY_SIZE = 100
        self.mock_settings.MONITORING_SLOW_QUERY_THRESHOLD_MS = 100.0
        self.mock_settings.MONITORING_SLOW_QUERY_RING_SIZE = 50
        self.mock_settings.MONITORING_SLOW_ENDPOINT_THRESHOLD_MS = 1000.0
        self.mock_settings.MONITORING_SLOW_ENDPOINT_RING_SIZE = 50
        self.mock_settings.MONITORING_TRACEMALLOC_ENABLED = False
        self.mock_settings.MONITORING_TRACEMALLOC_THRESHOLD_MB = 100.0
        self.mock_settings.MONITORING_TRACEMALLOC_TOP_N = 10
    
    @patch('app.monitoring.settings')
    def test_track_process_snapshot(self, mock_settings):
        """Test tracking process snapshots."""
        from app.monitoring import SystemMonitor
        
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Track some snapshots
        monitor.track_process_snapshot(1234, 45.5, 512.3)
        monitor.track_process_snapshot(1234, 50.2, 520.1)
        monitor.track_process_snapshot(5678, 25.0, 128.5)
        
        # Verify snapshots were stored
        self.assertIn(1234, monitor.process_history)
        self.assertIn(5678, monitor.process_history)
        self.assertEqual(len(monitor.process_history[1234]), 2)
        self.assertEqual(len(monitor.process_history[5678]), 1)
        
        # Verify snapshot data
        snapshot = monitor.process_history[1234][0]
        self.assertIn('timestamp', snapshot)
        self.assertEqual(snapshot['cpu_percent'], 45.5)
        self.assertEqual(snapshot['rss_mb'], 512.3)
    
    @patch('app.monitoring.settings')
    def test_track_slow_query(self, mock_settings):
        """Test tracking slow queries."""
        from app.monitoring import SystemMonitor
        
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Track queries
        monitor.track_slow_query("SELECT * FROM users", 150.0, ("param1",))
        monitor.track_slow_query("SELECT * FROM orders WHERE id = ?", 250.0, (123,))
        monitor.track_slow_query("UPDATE settings SET value = ?", 180.0, ("new_value",))
        
        # Verify queries were stored and sorted by duration
        self.assertEqual(len(monitor.slow_queries), 3)
        self.assertEqual(monitor.slow_queries[0]['duration_ms'], 250.0)  # Slowest first
        self.assertEqual(monitor.slow_queries[1]['duration_ms'], 180.0)
        self.assertEqual(monitor.slow_queries[2]['duration_ms'], 150.0)
        
        # Verify query data
        query = monitor.slow_queries[0]
        self.assertIn('timestamp', query)
        self.assertIn('SELECT * FROM orders', query['query'])
        self.assertEqual(query['duration_ms'], 250.0)
        self.assertIn('params', query)
    
    @patch('app.monitoring.settings')
    def test_slow_query_threshold(self, mock_settings):
        """Test slow query threshold filtering."""
        from app.monitoring import SystemMonitor
        
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Track queries below threshold
        monitor.track_slow_query("SELECT 1", 50.0)
        monitor.track_slow_query("SELECT 2", 99.0)
        
        # Track queries above threshold
        monitor.track_slow_query("SELECT 3", 100.0)
        monitor.track_slow_query("SELECT 4", 150.0)
        
        # Only queries >= threshold should be stored
        self.assertEqual(len(monitor.slow_queries), 2)
        self.assertTrue(all(q['duration_ms'] >= 100.0 for q in monitor.slow_queries))
    
    @patch('app.monitoring.settings')
    def test_track_slow_endpoint(self, mock_settings):
        """Test tracking slow HTTP endpoints."""
        from app.monitoring import SystemMonitor
        
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Track endpoints
        monitor.track_slow_endpoint("GET", "/api/users", 1500.0, 200)
        monitor.track_slow_endpoint("POST", "/api/orders", 2500.0, 201)
        monitor.track_slow_endpoint("GET", "/api/reports", 1800.0, 200)
        
        # Verify endpoints were stored and sorted by duration
        self.assertEqual(len(monitor.slow_endpoints), 3)
        self.assertEqual(monitor.slow_endpoints[0]['duration_ms'], 2500.0)  # Slowest first
        self.assertEqual(monitor.slow_endpoints[1]['duration_ms'], 1800.0)
        self.assertEqual(monitor.slow_endpoints[2]['duration_ms'], 1500.0)
        
        # Verify endpoint data
        endpoint = monitor.slow_endpoints[0]
        self.assertEqual(endpoint['method'], 'POST')
        self.assertEqual(endpoint['path'], '/api/orders')
        self.assertEqual(endpoint['status_code'], 201)
    
    @patch('app.monitoring.settings')
    def test_slow_endpoint_threshold(self, mock_settings):
        """Test slow endpoint threshold filtering."""
        from app.monitoring import SystemMonitor
        
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Track endpoints below threshold
        monitor.track_slow_endpoint("GET", "/fast", 500.0, 200)
        monitor.track_slow_endpoint("GET", "/medium", 999.0, 200)
        
        # Track endpoints above threshold
        monitor.track_slow_endpoint("GET", "/slow", 1000.0, 200)
        monitor.track_slow_endpoint("GET", "/slower", 2000.0, 200)
        
        # Only endpoints >= threshold should be stored
        self.assertEqual(len(monitor.slow_endpoints), 2)
        self.assertTrue(all(e['duration_ms'] >= 1000.0 for e in monitor.slow_endpoints))
    
    @patch('app.monitoring.settings')
    def test_ring_buffer_size_limit(self, mock_settings):
        """Test ring buffer size limits."""
        from app.monitoring import SystemMonitor
        
        # Set small ring size for testing
        self.mock_settings.MONITORING_SLOW_QUERY_RING_SIZE = 3
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Track more queries than ring size
        for i in range(5):
            monitor.track_slow_query(f"SELECT {i}", 100.0 + i * 10)
        
        # Should keep only top N slowest
        self.assertEqual(len(monitor.slow_queries), 3)
        self.assertEqual(monitor.slow_queries[0]['duration_ms'], 140.0)  # Slowest
        self.assertEqual(monitor.slow_queries[2]['duration_ms'], 120.0)  # Third slowest
    
    @patch('app.monitoring.settings')
    def test_get_hotspots(self, mock_settings):
        """Test get_hotspots aggregation."""
        from app.monitoring import SystemMonitor
        
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        monitor = SystemMonitor()
        
        # Add some diagnostic data
        monitor.track_process_snapshot(1234, 45.0, 512.0)
        monitor.track_process_snapshot(1234, 50.0, 520.0)
        monitor.track_slow_query("SELECT * FROM users", 150.0)
        monitor.track_slow_endpoint("GET", "/api/users", 1500.0, 200)
        
        # Get hotspots
        hotspots = monitor.get_hotspots()
        
        # Verify structure
        self.assertIn('process_trends', hotspots)
        self.assertIn('slow_queries', hotspots)
        self.assertIn('slow_endpoints', hotspots)
        self.assertIn('memory_snapshots', hotspots)
        
        # Verify process trends
        self.assertIn(1234, hotspots['process_trends'])
        trend = hotspots['process_trends'][1234]
        self.assertEqual(trend['sample_count'], 2)
        self.assertEqual(trend['cpu_avg'], 47.5)
        self.assertEqual(trend['cpu_max'], 50.0)
        self.assertEqual(trend['cpu_min'], 45.0)
        
        # Verify slow queries
        self.assertEqual(hotspots['slow_queries']['count'], 1)
        self.assertEqual(hotspots['slow_queries']['threshold_ms'], 100.0)
        
        # Verify slow endpoints
        self.assertEqual(hotspots['slow_endpoints']['count'], 1)
        self.assertEqual(hotspots['slow_endpoints']['threshold_ms'], 1000.0)
    
    @patch('app.monitoring.settings')
    @patch('app.monitoring.psutil.Process')
    @patch('tracemalloc.take_snapshot')
    @patch('tracemalloc.is_tracing')
    @patch('tracemalloc.start')
    def test_memory_snapshot_with_tracemalloc(self, mock_start, mock_is_tracing, 
                                             mock_take_snapshot, mock_process, mock_settings):
        """Test memory snapshot with tracemalloc enabled."""
        from app.monitoring import SystemMonitor
        
        # Enable tracemalloc in settings
        self.mock_settings.MONITORING_TRACEMALLOC_ENABLED = True
        self.mock_settings.MONITORING_TRACEMALLOC_THRESHOLD_MB = 50.0
        mock_settings.__dict__.update(self.mock_settings.__dict__)
        mock_is_tracing.return_value = False
        
        # Mock process memory
        mock_mem_info = Mock()
        mock_mem_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.return_value.memory_info.return_value = mock_mem_info
        
        # Mock tracemalloc snapshot
        mock_stat = Mock()
        mock_stat.traceback = Mock()
        mock_stat.traceback.format.return_value = ["test.py:10"]
        mock_stat.size = 1024 * 1024  # 1 MB
        mock_stat.count = 100
        
        mock_snapshot = Mock()
        mock_snapshot.statistics.return_value = [mock_stat]
        mock_take_snapshot.return_value = mock_snapshot
        
        monitor = SystemMonitor()
        
        # Take snapshot (should succeed because memory > threshold)
        snapshot = monitor.check_and_snapshot_memory()
        
        # Verify snapshot was taken
        self.assertIsNotNone(snapshot)
        self.assertIn('timestamp', snapshot)
        self.assertIn('memory_mb', snapshot)
        self.assertIn('top_allocations', snapshot)
        self.assertEqual(len(snapshot['top_allocations']), 1)
        
        # Verify it was stored
        self.assertEqual(len(monitor.tracemalloc_snapshots), 1)


if __name__ == '__main__':
    unittest.main()
