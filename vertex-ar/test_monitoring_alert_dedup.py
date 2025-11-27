#!/usr/bin/env python3
"""
Tests for monitoring alert deduplication and degraded service detection.
Tests that single noisy samples don't trigger alerts, but sustained issues do.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.monitoring import SystemMonitor
from app.config import settings


class TestMonitoringAlertDedup:
    """Test monitoring alert deduplication and consecutive failure tracking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a fresh monitor instance for each test
        self.monitor = SystemMonitor()
        # Override settings for tests
        self.monitor.consecutive_failure_threshold = 3
        self.monitor.dedup_window = 300  # 5 minutes
        
    def test_consecutive_failure_tracking_single_spike(self):
        """Test that a single spike doesn't escalate to alert."""
        alert_key = "test_cpu"
        
        # First failure - should not escalate
        result = self.monitor._should_escalate_alert(alert_key)
        assert result is False
        assert self.monitor.failure_counts[alert_key] == 1
        
        print("✅ Single spike does not escalate to alert")
    
    def test_consecutive_failure_tracking_two_spikes(self):
        """Test that two consecutive failures don't escalate to alert."""
        alert_key = "test_cpu"
        
        # First failure
        self.monitor._should_escalate_alert(alert_key)
        # Second failure - should still not escalate
        result = self.monitor._should_escalate_alert(alert_key)
        assert result is False
        assert self.monitor.failure_counts[alert_key] == 2
        
        print("✅ Two consecutive spikes do not escalate to alert")
    
    def test_consecutive_failure_tracking_sustained_issue(self):
        """Test that sustained issues (3+ failures) do escalate to alert."""
        alert_key = "test_cpu"
        
        # First and second failures - no escalation
        self.monitor._should_escalate_alert(alert_key)
        self.monitor._should_escalate_alert(alert_key)
        
        # Third failure - should escalate
        result = self.monitor._should_escalate_alert(alert_key)
        assert result is True
        assert self.monitor.failure_counts[alert_key] == 3
        assert alert_key in self.monitor.last_alerts
        
        print("✅ Sustained issue (3 consecutive failures) escalates to alert")
    
    def test_failure_count_reset_on_recovery(self):
        """Test that failure count resets when metric recovers."""
        alert_key = "test_memory"
        
        # Simulate two failures
        self.monitor._should_escalate_alert(alert_key)
        self.monitor._should_escalate_alert(alert_key)
        assert self.monitor.failure_counts[alert_key] == 2
        
        # Metric recovers
        self.monitor._reset_failure_count(alert_key)
        assert self.monitor.failure_counts[alert_key] == 0
        
        # Next failure should start from 1 again
        result = self.monitor._should_escalate_alert(alert_key)
        assert result is False
        assert self.monitor.failure_counts[alert_key] == 1
        
        print("✅ Failure count resets on recovery")
    
    def test_deduplication_window(self):
        """Test that alerts within dedup window are suppressed."""
        alert_key = "test_disk"
        
        # Reach threshold (3 failures)
        for _ in range(3):
            self.monitor._should_escalate_alert(alert_key)
        
        # First alert should go through
        assert alert_key in self.monitor.last_alerts
        first_alert_time = self.monitor.last_alerts[alert_key]
        
        # Try to send another alert immediately - should be suppressed
        result = self.monitor._should_escalate_alert(alert_key)
        assert result is False
        
        # Simulate time passing (beyond dedup window)
        self.monitor.last_alerts[alert_key] = datetime.utcnow() - timedelta(seconds=301)
        
        # Now alert should go through again
        result = self.monitor._should_escalate_alert(alert_key)
        assert result is True
        
        print("✅ Deduplication window works correctly")
    
    def test_severity_determination_warning(self):
        """Test severity determination for just-over-threshold values."""
        # Just over threshold (80.5% when threshold is 80%)
        severity = self.monitor._determine_severity("cpu", 80.5, 80.0)
        assert severity == "warning"
        
        print("✅ Just-over-threshold values get 'warning' severity")
    
    def test_severity_determination_medium(self):
        """Test severity determination for moderately degraded values."""
        # 10% over threshold (88% when threshold is 80%)
        severity = self.monitor._determine_severity("memory", 88.0, 80.0)
        assert severity == "medium"
        
        print("✅ Moderately degraded values get 'medium' severity")
    
    def test_severity_determination_high(self):
        """Test severity determination for critical values."""
        # Way over threshold (97% when threshold is 80%)
        severity = self.monitor._determine_severity("disk", 97.0, 80.0)
        assert severity == "high"
        
        # Also test >95% absolute threshold
        severity = self.monitor._determine_severity("cpu", 96.0, 80.0)
        assert severity == "high"
        
        print("✅ Critical values get 'high' severity")
    
    async def test_cpu_alert_not_sent_on_single_spike(self):
        """Test that CPU alert is not sent on a single spike."""
        with patch('app.monitoring.alert_manager.send_alert', new_callable=AsyncMock) as mock_alert:
            # Mock CPU usage to be over threshold
            with patch.object(self.monitor, 'get_cpu_usage') as mock_cpu:
                mock_cpu.return_value = {
                    "percent": 85.0,
                    "load_average": {"1min": 1.0, "5min": 0.8, "15min": 0.5},
                    "cpu_count": {"physical": 4, "logical": 8},
                    "per_core": [80, 85, 90, 85],
                    "top_processes": []
                }
                
                # Mock other methods to avoid side effects
                with patch.object(self.monitor, 'get_memory_usage') as mock_mem, \
                     patch.object(self.monitor, 'get_disk_usage') as mock_disk, \
                     patch.object(self.monitor, 'get_service_health') as mock_service, \
                     patch.object(self.monitor, 'get_network_stats') as mock_net, \
                     patch.object(self.monitor, 'get_process_info') as mock_proc, \
                     patch.object(self.monitor, '_store_historical_data'):
                    
                    mock_mem.return_value = {
                        "virtual": {"percent": 50, "used_gb": 4.0, "total_gb": 8.0, "available_gb": 4.0, "free_gb": 4.0},
                        "swap": {"percent": 0, "used_gb": 0.0, "total_gb": 0.0, "free_gb": 0.0, "sin_gb": 0.0, "sout_gb": 0.0},
                        "top_processes": []
                    }
                    mock_disk.return_value = {
                        "storage": {"percent": 50, "used_gb": 50.0, "total_gb": 100.0, "free_gb": 50.0},
                        "partitions": [],
                        "io_stats": {},
                        "temperature": {}
                    }
                    mock_service.return_value = {}
                    mock_net.return_value = {"total": {}, "interfaces": {}, "connections": {}}
                    mock_proc.return_value = {}
                    
                    # First check - should not send alert
                    health_data = await self.monitor.check_system_health()
                    
                    # Verify alert was NOT sent
                    mock_alert.assert_not_called()
                    
                    # Verify health_data includes the transient alert
                    assert len(health_data["alerts"]) == 1
                    assert health_data["alerts"][0]["transient"] is True
                    assert "transient" in health_data["alerts"][0]["message"]
                    
        print("✅ Single CPU spike does not send alert")
    
    async def test_cpu_alert_sent_after_sustained_issue(self):
        """Test that CPU alert IS sent after 3 consecutive high readings."""
        with patch('app.monitoring.alert_manager.send_alert', new_callable=AsyncMock) as mock_alert:
            # Mock CPU usage to be over threshold
            with patch.object(self.monitor, 'get_cpu_usage') as mock_cpu:
                mock_cpu.return_value = {
                    "percent": 85.0,
                    "load_average": {"1min": 1.0, "5min": 0.8, "15min": 0.5},
                    "cpu_count": {"physical": 4, "logical": 8},
                    "per_core": [80, 85, 90, 85],
                    "top_processes": []
                }
                
                # Mock other methods
                with patch.object(self.monitor, 'get_memory_usage') as mock_mem, \
                     patch.object(self.monitor, 'get_disk_usage') as mock_disk, \
                     patch.object(self.monitor, 'get_service_health') as mock_service, \
                     patch.object(self.monitor, 'get_network_stats') as mock_net, \
                     patch.object(self.monitor, 'get_process_info') as mock_proc, \
                     patch.object(self.monitor, '_store_historical_data'):
                    
                    mock_mem.return_value = {
                        "virtual": {"percent": 50, "used_gb": 4.0, "total_gb": 8.0, "available_gb": 4.0, "free_gb": 4.0},
                        "swap": {"percent": 0, "used_gb": 0.0, "total_gb": 0.0, "free_gb": 0.0, "sin_gb": 0.0, "sout_gb": 0.0},
                        "top_processes": []
                    }
                    mock_disk.return_value = {
                        "storage": {"percent": 50, "used_gb": 50.0, "total_gb": 100.0, "free_gb": 50.0},
                        "partitions": [],
                        "io_stats": {},
                        "temperature": {}
                    }
                    mock_service.return_value = {}
                    mock_net.return_value = {"total": {}, "interfaces": {}, "connections": {}}
                    mock_proc.return_value = {}
                    
                    # First check - no alert
                    await self.monitor.check_system_health()
                    assert mock_alert.call_count == 0
                    
                    # Second check - no alert
                    await self.monitor.check_system_health()
                    assert mock_alert.call_count == 0
                    
                    # Third check - should send alert
                    health_data = await self.monitor.check_system_health()
                    assert mock_alert.call_count == 1
                    
                    # Verify alert was called with correct parameters
                    call_args = mock_alert.call_args
                    assert call_args[0][0] == "high_cpu"
                    assert "High CPU Usage Detected" in call_args[0][1]
                    
                    # Verify health_data includes the real alert (not transient)
                    assert len(health_data["alerts"]) == 1
                    assert health_data["alerts"][0].get("transient") is not True
                    
        print("✅ Sustained CPU issue sends alert after 3 checks")
    
    async def test_service_degraded_warning_vs_failure(self):
        """Test that slow service gets warning, failed service gets high severity."""
        with patch('app.monitoring.alert_manager.send_alert', new_callable=AsyncMock) as mock_alert:
            # Mock healthy CPU/memory/disk
            with patch.object(self.monitor, 'get_cpu_usage') as mock_cpu, \
                 patch.object(self.monitor, 'get_memory_usage') as mock_mem, \
                 patch.object(self.monitor, 'get_disk_usage') as mock_disk, \
                 patch.object(self.monitor, 'get_service_health') as mock_service, \
                 patch.object(self.monitor, 'get_network_stats') as mock_net, \
                 patch.object(self.monitor, 'get_process_info') as mock_proc, \
                 patch.object(self.monitor, '_store_historical_data'):
                
                mock_cpu.return_value = {"percent": 50, "load_average": {"1min": 1.0}, "cpu_count": {"physical": 4}, "per_core": [], "top_processes": []}
                mock_mem.return_value = {
                    "virtual": {"percent": 50, "used_gb": 4.0, "total_gb": 8.0, "available_gb": 4.0, "free_gb": 4.0},
                    "swap": {"percent": 0, "used_gb": 0.0, "total_gb": 0.0, "free_gb": 0.0, "sin_gb": 0.0, "sout_gb": 0.0},
                    "top_processes": []
                }
                mock_disk.return_value = {
                    "storage": {"percent": 50, "used_gb": 50.0, "total_gb": 100.0, "free_gb": 50.0},
                    "partitions": [],
                    "io_stats": {},
                    "temperature": {}
                }
                mock_net.return_value = {"total": {}, "interfaces": {}, "connections": {}}
                mock_proc.return_value = {}
                
                # Test degraded service (slow but working)
                mock_service.return_value = {
                    "database": {
                        "healthy": True,
                        "response_time_ms": 6000,  # Over 5000ms threshold
                        "status": "degraded"
                    }
                }
                
                # Run 3 checks to reach threshold
                for _ in range(3):
                    await self.monitor.check_system_health()
                
                # Should have called alert with "medium" severity for slow response
                assert any(call[0][3] == "medium" for call in mock_alert.call_args_list)
                
                mock_alert.reset_mock()
                
                # Now test failed service
                mock_service.return_value = {
                    "database": {
                        "healthy": False,
                        "response_time_ms": None,
                        "status": "failed",
                        "error": "Connection refused"
                    }
                }
                
                # Reset failure counts
                self.monitor.failure_counts = {}
                self.monitor.last_alerts = {}
                
                # Run 3 checks to reach threshold
                for _ in range(3):
                    await self.monitor.check_system_health()
                
                # Should have called alert with "high" severity for failure
                assert any(call[0][3] == "high" for call in mock_alert.call_args_list)
                
        print("✅ Degraded service gets warning, failed service gets high severity")
    
    async def test_multiple_metrics_independent_tracking(self):
        """Test that different metrics track failures independently."""
        with patch('app.monitoring.alert_manager.send_alert', new_callable=AsyncMock) as mock_alert:
            # Mock CPU and memory over threshold, disk healthy
            with patch.object(self.monitor, 'get_cpu_usage') as mock_cpu, \
                 patch.object(self.monitor, 'get_memory_usage') as mock_mem, \
                 patch.object(self.monitor, 'get_disk_usage') as mock_disk, \
                 patch.object(self.monitor, 'get_service_health') as mock_service, \
                 patch.object(self.monitor, 'get_network_stats') as mock_net, \
                 patch.object(self.monitor, 'get_process_info') as mock_proc, \
                 patch.object(self.monitor, '_store_historical_data'):
                
                mock_cpu.return_value = {
                    "percent": 85.0,
                    "load_average": {"1min": 1.0},
                    "cpu_count": {"physical": 4},
                    "per_core": [],
                    "top_processes": []
                }
                mock_mem.return_value = {
                    "virtual": {"percent": 90, "used_gb": 8.0, "total_gb": 10.0, "available_gb": 2.0, "free_gb": 2.0},
                    "swap": {"percent": 0, "used_gb": 0.0, "total_gb": 0.0, "free_gb": 0.0, "sin_gb": 0.0, "sout_gb": 0.0},
                    "top_processes": []
                }
                mock_disk.return_value = {
                    "storage": {"percent": 50, "used_gb": 50.0, "total_gb": 100.0, "free_gb": 50.0},
                    "partitions": [],
                    "io_stats": {},
                    "temperature": {}
                }
                mock_service.return_value = {}
                mock_net.return_value = {"total": {}, "interfaces": {}, "connections": {}}
                mock_proc.return_value = {}
                
                # First check - no alerts
                await self.monitor.check_system_health()
                assert self.monitor.failure_counts["high_cpu"] == 1
                assert self.monitor.failure_counts["high_memory"] == 1
                assert mock_alert.call_count == 0
                
                # Second check - no alerts
                await self.monitor.check_system_health()
                assert self.monitor.failure_counts["high_cpu"] == 2
                assert self.monitor.failure_counts["high_memory"] == 2
                assert mock_alert.call_count == 0
                
                # CPU recovers, memory still high
                mock_cpu.return_value["percent"] = 50.0
                
                # Third check - only memory should alert
                await self.monitor.check_system_health()
                assert self.monitor.failure_counts["high_cpu"] == 0  # Reset
                assert self.monitor.failure_counts["high_memory"] == 3
                assert mock_alert.call_count == 1
                
                # Verify only memory alert was sent
                assert mock_alert.call_args[0][0] == "high_memory"
                
        print("✅ Multiple metrics track failures independently")


async def run_async_tests():
    """Run all async tests."""
    test_suite = TestMonitoringAlertDedup()
    
    print("\n" + "=" * 60)
    print("Testing Monitoring Alert Deduplication & Stabilization")
    print("=" * 60 + "\n")
    
    # Run synchronous tests
    print("Testing consecutive failure tracking...")
    test_suite.setup_method()
    test_suite.test_consecutive_failure_tracking_single_spike()
    
    test_suite.setup_method()
    test_suite.test_consecutive_failure_tracking_two_spikes()
    
    test_suite.setup_method()
    test_suite.test_consecutive_failure_tracking_sustained_issue()
    
    test_suite.setup_method()
    test_suite.test_failure_count_reset_on_recovery()
    
    test_suite.setup_method()
    test_suite.test_deduplication_window()
    
    print("\nTesting severity determination...")
    test_suite.setup_method()
    test_suite.test_severity_determination_warning()
    
    test_suite.setup_method()
    test_suite.test_severity_determination_medium()
    
    test_suite.setup_method()
    test_suite.test_severity_determination_high()
    
    # Run async tests
    print("\nTesting alert sending behavior...")
    test_suite.setup_method()
    await test_suite.test_cpu_alert_not_sent_on_single_spike()
    
    test_suite.setup_method()
    await test_suite.test_cpu_alert_sent_after_sustained_issue()
    
    test_suite.setup_method()
    await test_suite.test_service_degraded_warning_vs_failure()
    
    test_suite.setup_method()
    await test_suite.test_multiple_metrics_independent_tracking()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60 + "\n")
    
    print("Summary:")
    print("- Single noisy samples do not trigger alerts ✅")
    print("- Sustained issues (3+ consecutive failures) do trigger alerts ✅")
    print("- Deduplication window prevents alert spam ✅")
    print("- Degraded services get warning severity ✅")
    print("- Failed services get high severity ✅")
    print("- Multiple metrics track independently ✅")
    print("- health_data['alerts'] mirrors sent alerts ✅")


if __name__ == "__main__":
    asyncio.run(run_async_tests())
