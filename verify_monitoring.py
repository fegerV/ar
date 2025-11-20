#!/usr/bin/env python3
"""
Final verification script for Vertex AR monitoring system implementation.
"""
import sys
import os

# Add project root to Python path
sys.path.insert(0, '/home/engine/project/vertex-ar')

def check_implementation():
    """Check if all components are properly implemented."""
    print("🔍 Проверка реализации системы мониторинга Vertex AR")
    print("=" * 60)
    
    checks = []
    
    # 1. Check core modules
    try:
        from app.alerting import alert_manager
        from app.monitoring import system_monitor
        from app.weekly_reports import weekly_report_generator
        checks.append("✅ Основные модули мониторинга импортированы")
    except Exception as e:
        checks.append(f"❌ Ошибка импорта модулей: {e}")
    
    # 2. Check API endpoints
    try:
        from app.api.monitoring import router
        checks.append("✅ API эндпоинты мониторинга созданы")
    except Exception as e:
        checks.append(f"❌ Ошибка API модуля: {e}")
    
    # 3. Check configuration
    try:
        from app.config import settings
        required_attrs = [
            'ALERTING_ENABLED', 'CPU_THRESHOLD', 'MEMORY_THRESHOLD', 
            'DISK_THRESHOLD', 'HEALTH_CHECK_INTERVAL',
            'WEEKLY_REPORT_DAY', 'WEEKLY_REPORT_TIME',
            'SMTP_SERVER', 'SMTP_USERNAME', 'ADMIN_EMAILS',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
        ]
        
        missing_attrs = [attr for attr in required_attrs if not hasattr(settings, attr)]
        if missing_attrs:
            checks.append(f"❌ Отсутствуют настройки: {missing_attrs}")
        else:
            checks.append("✅ Все конфигурационные параметры определены")
    except Exception as e:
        checks.append(f"❌ Ошибка конфигурации: {e}")
    
    # 4. Check dependencies
    try:
        import psutil
        import aiohttp
        import aiosmtplib
        checks.append("✅ Зависимости установлены (psutil, aiohttp, aiosmtplib)")
    except ImportError as e:
        checks.append(f"❌ Отсутствуют зависимости: {e}")
    
    # 5. Check app integration
    try:
        from app.main import create_app
        app = create_app()
        
        # Check if monitoring routes are registered
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        monitoring_routes = [r for r in routes if 'monitoring' in r]
        
        if len(monitoring_routes) >= 5:
            checks.append(f"✅ API эндпоинты зарегистрированы ({len(monitoring_routes)} маршрутов)")
        else:
            checks.append(f"❌ Недостаточно маршрутов мониторинга: {len(monitoring_routes)}")
            
    except Exception as e:
        checks.append(f"❌ Ошибка интеграции с приложением: {e}")
    
    # 6. Check admin dashboard integration
    try:
        dashboard_path = '/home/engine/project/vertex-ar/templates/admin_dashboard.html'
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_elements = [
            'monitoring-section',
            'monitoring-controls', 
            'realtime-metrics',
            'loadMonitoringStatus',
            'testAlertSystem',
            'sendWeeklyReport'
        ]
        
        missing_elements = [elem for elem in required_elements if elem not in content]
        if missing_elements:
            checks.append(f"❌ Отсутствуют элементы в админке: {missing_elements}")
        else:
            checks.append("✅ Админская панель интегрирована")
            
    except Exception as e:
        checks.append(f"❌ Ошибка проверки админской панели: {e}")
    
    # 7. Check documentation
    try:
        doc_files = [
            '/home/engine/project/MONITORING_SETUP.md',
            '/home/engine/project/MONITORING_IMPLEMENTATION.md'
        ]
        
        missing_docs = [doc for doc in doc_files if not os.path.exists(doc)]
        if missing_docs:
            checks.append(f"❌ Отсутствует документация: {missing_docs}")
        else:
            checks.append("✅ Документация создана")
            
    except Exception as e:
        checks.append(f"❌ Ошибка проверки документации: {e}")
    
    # Print results
    print("\n".join(checks))
    
    # Summary
    success_count = len([c for c in checks if c.startswith("✅")])
    total_count = len(checks)
    
    print("\n" + "=" * 60)
    print(f"Итог: {success_count}/{total_count} проверок пройдено")
    
    if success_count == total_count:
        print("🎉 Система мониторинга и оповещений готова к использованию!")
        print("\nСледующие шаги:")
        print("1. Настройте SMTP/Telegram в .env файле")
        print("2. Установите ALERTING_ENABLED=true")
        print("3. Перезапустите приложение")
        print("4. Проверьте раздел мониторинга в админской панели")
        return True
    else:
        print("⚠️ Есть проблемы, которые нужно исправить")
        return False

if __name__ == "__main__":
    success = check_implementation()
    sys.exit(0 if success else 1)
