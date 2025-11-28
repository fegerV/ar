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


if __name__ == '__main__':
    unittest.main()
