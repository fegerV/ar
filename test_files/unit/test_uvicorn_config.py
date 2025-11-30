"""
Unit tests for uvicorn runtime configuration.

Tests verify:
- Configuration parsing from environment variables
- Default worker calculation based on CPU count
- Health check timeout and method settings
- Configuration validation and edge cases
"""

import unittest
from unittest.mock import Mock, patch
import os


class TestUvicornConfig(unittest.TestCase):
    """Test uvicorn runtime configuration settings."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing env vars
        self.env_vars_to_clear = [
            'UVICORN_WORKERS',
            'UVICORN_KEEPALIVE_TIMEOUT',
            'UVICORN_TIMEOUT_KEEP_ALIVE',
            'UVICORN_LIMIT_CONCURRENCY',
            'UVICORN_BACKLOG',
            'UVICORN_PROXY_HEADERS',
            'UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN',
            'WEB_HEALTH_CHECK_TIMEOUT',
            'WEB_HEALTH_CHECK_USE_HEAD',
            'WEB_HEALTH_CHECK_COOLDOWN',
        ]
        for var in self.env_vars_to_clear:
            os.environ.pop(var, None)

    def tearDown(self):
        """Clean up after tests."""
        for var in self.env_vars_to_clear:
            os.environ.pop(var, None)

    @patch('psutil.cpu_count')
    def test_default_worker_calculation_4_cores(self, mock_cpu_count):
        """Test default worker count is (2 * cores) + 1 for 4-core system."""
        mock_cpu_count.return_value = 4
        
        from app.config import Settings
        settings = Settings()
        
        expected_workers = (2 * 4) + 1  # 9 workers
        self.assertEqual(settings.UVICORN_WORKERS, expected_workers)

    @patch('psutil.cpu_count')
    def test_default_worker_calculation_2_cores(self, mock_cpu_count):
        """Test default worker count is (2 * cores) + 1 for 2-core system."""
        mock_cpu_count.return_value = 2
        
        from app.config import Settings
        settings = Settings()
        
        expected_workers = (2 * 2) + 1  # 5 workers
        self.assertEqual(settings.UVICORN_WORKERS, expected_workers)

    @patch('psutil.cpu_count')
    def test_default_worker_calculation_1_core(self, mock_cpu_count):
        """Test default worker count is (2 * cores) + 1 for 1-core system."""
        mock_cpu_count.return_value = 1
        
        from app.config import Settings
        settings = Settings()
        
        expected_workers = (2 * 1) + 1  # 3 workers
        self.assertEqual(settings.UVICORN_WORKERS, expected_workers)

    @patch('psutil.cpu_count')
    def test_default_worker_calculation_none_cores(self, mock_cpu_count):
        """Test default worker count handles None from cpu_count."""
        mock_cpu_count.return_value = None
        
        from app.config import Settings
        settings = Settings()
        
        # Should default to 1 CPU when psutil returns None
        expected_workers = (2 * 1) + 1  # 3 workers
        self.assertEqual(settings.UVICORN_WORKERS, expected_workers)

    def test_explicit_worker_override(self):
        """Test explicit UVICORN_WORKERS env var overrides calculation."""
        os.environ['UVICORN_WORKERS'] = '12'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_WORKERS, 12)

    def test_keepalive_timeout_default(self):
        """Test default keepalive timeout is 5 seconds."""
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_KEEPALIVE_TIMEOUT, 5)
        self.assertEqual(settings.UVICORN_TIMEOUT_KEEP_ALIVE, 5)

    def test_keepalive_timeout_override(self):
        """Test keepalive timeout can be overridden."""
        os.environ['UVICORN_KEEPALIVE_TIMEOUT'] = '10'
        os.environ['UVICORN_TIMEOUT_KEEP_ALIVE'] = '15'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_KEEPALIVE_TIMEOUT, 10)
        self.assertEqual(settings.UVICORN_TIMEOUT_KEEP_ALIVE, 15)

    def test_limit_concurrency_default(self):
        """Test default limit concurrency is 0 (unlimited)."""
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_LIMIT_CONCURRENCY, 0)

    def test_limit_concurrency_override(self):
        """Test limit concurrency can be set."""
        os.environ['UVICORN_LIMIT_CONCURRENCY'] = '1000'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_LIMIT_CONCURRENCY, 1000)

    def test_backlog_default(self):
        """Test default backlog is 2048."""
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_BACKLOG, 2048)

    def test_backlog_override(self):
        """Test backlog can be customized."""
        os.environ['UVICORN_BACKLOG'] = '4096'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_BACKLOG, 4096)

    def test_proxy_headers_default_true(self):
        """Test proxy headers enabled by default."""
        from app.config import Settings
        settings = Settings()
        
        self.assertTrue(settings.UVICORN_PROXY_HEADERS)

    def test_proxy_headers_disable(self):
        """Test proxy headers can be disabled."""
        os.environ['UVICORN_PROXY_HEADERS'] = 'false'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertFalse(settings.UVICORN_PROXY_HEADERS)

    def test_proxy_headers_case_insensitive(self):
        """Test proxy headers setting is case-insensitive."""
        test_cases = [
            ('True', True),
            ('TRUE', True),
            ('true', True),
            ('False', False),
            ('FALSE', False),
            ('false', False),
            ('yes', False),  # Only 'true' should be True
            ('1', False),
        ]
        
        for value, expected in test_cases:
            os.environ['UVICORN_PROXY_HEADERS'] = value
            from importlib import reload
            import app.config
            reload(app.config)
            settings = app.config.settings
            self.assertEqual(settings.UVICORN_PROXY_HEADERS, expected, 
                           f"Failed for value: {value}")

    def test_graceful_shutdown_default(self):
        """Test default graceful shutdown timeout is 30 seconds."""
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN, 30)

    def test_graceful_shutdown_override(self):
        """Test graceful shutdown timeout can be customized."""
        os.environ['UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN'] = '60'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN, 60)

    def test_web_health_check_timeout_default(self):
        """Test default health check timeout is 5 seconds."""
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.WEB_HEALTH_CHECK_TIMEOUT, 5)

    def test_web_health_check_timeout_override(self):
        """Test health check timeout can be customized."""
        os.environ['WEB_HEALTH_CHECK_TIMEOUT'] = '10'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.WEB_HEALTH_CHECK_TIMEOUT, 10)

    def test_web_health_check_use_head_default_false(self):
        """Test HEAD requests disabled by default for health checks."""
        from app.config import Settings
        settings = Settings()
        
        self.assertFalse(settings.WEB_HEALTH_CHECK_USE_HEAD)

    def test_web_health_check_use_head_enable(self):
        """Test HEAD requests can be enabled for health checks."""
        os.environ['WEB_HEALTH_CHECK_USE_HEAD'] = 'true'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertTrue(settings.WEB_HEALTH_CHECK_USE_HEAD)

    def test_web_health_check_cooldown_default(self):
        """Test default health check cooldown is 30 seconds."""
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.WEB_HEALTH_CHECK_COOLDOWN, 30)

    def test_web_health_check_cooldown_override(self):
        """Test health check cooldown can be customized."""
        os.environ['WEB_HEALTH_CHECK_COOLDOWN'] = '60'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.WEB_HEALTH_CHECK_COOLDOWN, 60)

    def test_all_uvicorn_settings_together(self):
        """Test all uvicorn settings can be configured together."""
        os.environ['UVICORN_WORKERS'] = '8'
        os.environ['UVICORN_KEEPALIVE_TIMEOUT'] = '10'
        os.environ['UVICORN_TIMEOUT_KEEP_ALIVE'] = '10'
        os.environ['UVICORN_LIMIT_CONCURRENCY'] = '500'
        os.environ['UVICORN_BACKLOG'] = '4096'
        os.environ['UVICORN_PROXY_HEADERS'] = 'true'
        os.environ['UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN'] = '45'
        os.environ['WEB_HEALTH_CHECK_TIMEOUT'] = '8'
        os.environ['WEB_HEALTH_CHECK_USE_HEAD'] = 'true'
        os.environ['WEB_HEALTH_CHECK_COOLDOWN'] = '45'
        
        from app.config import Settings
        settings = Settings()
        
        self.assertEqual(settings.UVICORN_WORKERS, 8)
        self.assertEqual(settings.UVICORN_KEEPALIVE_TIMEOUT, 10)
        self.assertEqual(settings.UVICORN_TIMEOUT_KEEP_ALIVE, 10)
        self.assertEqual(settings.UVICORN_LIMIT_CONCURRENCY, 500)
        self.assertEqual(settings.UVICORN_BACKLOG, 4096)
        self.assertTrue(settings.UVICORN_PROXY_HEADERS)
        self.assertEqual(settings.UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN, 45)
        self.assertEqual(settings.WEB_HEALTH_CHECK_TIMEOUT, 8)
        self.assertTrue(settings.WEB_HEALTH_CHECK_USE_HEAD)
        self.assertEqual(settings.WEB_HEALTH_CHECK_COOLDOWN, 45)


class TestHealthCheckThrottling(unittest.TestCase):
    """Test health check throttling and method selection."""

    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_health_check_uses_get_by_default(self, mock_port, mock_process, mock_get, mock_settings):
        """Test health check uses GET method by default."""
        from app.monitoring import SystemMonitor
        
        mock_settings.BASE_URL = "http://localhost:8000"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        mock_settings.WEB_HEALTH_CHECK_TIMEOUT = 5
        mock_settings.WEB_HEALTH_CHECK_USE_HEAD = False
        mock_settings.WEB_HEALTH_CHECK_COOLDOWN = 30
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        # Should use GET
        self.assertTrue(mock_get.called)
        self.assertEqual(result['check_method'], 'GET')
        self.assertTrue(result['healthy'])

    @patch('app.monitoring.settings')
    @patch('requests.head')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_health_check_uses_head_when_enabled(self, mock_port, mock_process, mock_head, mock_settings):
        """Test health check uses HEAD method when enabled."""
        from app.monitoring import SystemMonitor
        
        mock_settings.BASE_URL = "http://localhost:8000"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        mock_settings.WEB_HEALTH_CHECK_TIMEOUT = 5
        mock_settings.WEB_HEALTH_CHECK_USE_HEAD = True
        mock_settings.WEB_HEALTH_CHECK_COOLDOWN = 30
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        # Should use HEAD
        self.assertTrue(mock_head.called)
        self.assertEqual(result['check_method'], 'HEAD')
        self.assertTrue(result['healthy'])

    @patch('app.monitoring.settings')
    @patch('requests.get')
    @patch('app.monitoring.SystemMonitor._check_web_process')
    @patch('app.monitoring.SystemMonitor._check_port_status')
    def test_health_check_respects_timeout(self, mock_port, mock_process, mock_get, mock_settings):
        """Test health check respects configured timeout."""
        from app.monitoring import SystemMonitor
        
        mock_settings.BASE_URL = "http://localhost:8000"
        mock_settings.INTERNAL_HEALTH_URL = ""
        mock_settings.APP_PORT = 8000
        mock_settings.WEB_HEALTH_CHECK_TIMEOUT = 10
        mock_settings.WEB_HEALTH_CHECK_USE_HEAD = False
        mock_settings.WEB_HEALTH_CHECK_COOLDOWN = 30
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor = SystemMonitor()
        result = monitor._check_web_server_health()
        
        # Should pass timeout=10 to requests.get
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 10)


if __name__ == '__main__':
    unittest.main()
