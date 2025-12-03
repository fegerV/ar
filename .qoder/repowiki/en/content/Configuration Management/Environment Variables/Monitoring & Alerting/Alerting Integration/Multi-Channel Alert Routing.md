# Multi-Channel Alert Routing

<cite>
**Referenced Files in This Document**   
- [alertmanager.yml](file://monitoring/alertmanager.yml)
- [alerting.py](file://vertex-ar/app/alerting.py)
- [config.py](file://vertex-ar/app/config.py)
- [notification_config.py](file://vertex-ar/app/notification_config.py)
- [notification_integrations.py](file://vertex-ar/notification_integrations.py)
- [notifications.py](file://vertex-ar/notifications.py)
- [notification_sync.py](file://vertex-ar/notification_sync.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Alerting Components](#core-alerting-components)
3. [send_alert Method Implementation](#send_alert-method-implementation)
4. [Notification Routing Configuration](#notification-routing-configuration)
5. [Alertmanager Integration](#alertmanager-integration)
6. [Testing and Validation](#testing-and-validation)
7. [Configuration Examples](#configuration-examples)
8. [Conclusion](#conclusion)

## Introduction

The multi-channel alert routing system in Vertex AR provides a comprehensive notification framework that delivers alerts through multiple channels including Telegram, email, and database-stored notifications. This system ensures critical information reaches stakeholders through redundant channels based on severity levels, with sophisticated routing logic that considers feature flags and priority-based configurations.

The architecture integrates both internal application-level alerting and external monitoring systems, creating a cohesive notification ecosystem. At its core, the system uses severity-based formatting with emoji indicators to quickly convey the urgency of alerts, while implementing intelligent routing that respects business hours and suppresses redundant notifications.

This documentation details the implementation of the `send_alert` method, the `_get_routes_for_priority` routing logic, integration with Prometheus Alertmanager, and provides guidance on configuration and testing of the alert routing system.

## Core Alerting Components

The multi-channel alert routing system comprises several interconnected components that work together to deliver notifications across multiple channels. The primary components include the AlertManager class, NotificationIntegrator, and the underlying notification storage system.

```mermaid
classDiagram
class AlertManager {
+enabled : bool
+last_alerts : Dict[str, datetime]
+alert_cooldown : int
+send_alert(alert_type, subject, message, severity) bool
+send_telegram_alert(message) bool
+send_email_alert(subject, message) bool
+_get_routes_for_priority(priority) List[str]
+test_alert_system() Dict[str, bool]
}
class NotificationIntegrator {
+enabled : bool
+webhook_queue : List[WebhookEvent]
+integration_handlers : Dict[str, Callable]
+webhook_timeout : int
+max_retries : int
+route_notification(notification_data, integrations, priority) Dict[str, bool]
+_handle_telegram(notification_data, priority) bool
+_handle_email(notification_data, priority) bool
+_handle_webhook(notification_data, priority) bool
+_format_message(notification_data, priority) str
}
class NotificationConfig {
+db_path : str
+_cached_settings : Dict[str, Any]
+get_settings() Dict[str, Any]
+get_smtp_config(actor) Dict[str, Any]
+get_telegram_config() Dict[str, Any]
+get_event_settings() Dict[str, bool]
+get_thresholds() Dict[str, int]
}
class Notification {
+id : int
+title : str
+message : str
+user_id : str
+notification_type : str
+priority : NotificationPriority
+status : NotificationStatus
+is_read : bool
+source : str
+service_name : str
+event_data : str
+group_id : str
+created_at : datetime
+expires_at : datetime
+processed_at : datetime
}
AlertManager --> NotificationIntegrator : "uses"
AlertManager --> NotificationConfig : "retrieves config"
AlertManager --> Notification : "creates"
NotificationIntegrator --> AlertManager : "handles integrations"
```

**Diagram sources**
- [alerting.py](file://vertex-ar/app/alerting.py#L15-L382)
- [notification_integrations.py](file://vertex-ar/notification_integrations.py#L48-L355)
- [notification_config.py](file://vertex-ar/app/notification_config.py#L40-L221)
- [notifications.py](file://vertex-ar/notifications.py#L63-L87)

**Section sources**
- [alerting.py](file://vertex-ar/app/alerting.py#L1-L382)
- [notification_integrations.py](file://vertex-ar/notification_integrations.py#L1-L355)
- [notification_config.py](file://vertex-ar/app/notification_config.py#L1-L221)
- [notifications.py](file://vertex-ar/notifications.py#L1-L689)

## send_alert Method Implementation

The `send_alert` method in the AlertManager class coordinates the delivery of alerts across multiple channels with severity-based formatting. This method serves as the central entry point for the alerting system, handling the entire workflow from alert creation to multi-channel delivery.

The implementation follows a comprehensive process that begins with validation of the alerting system's enabled status and cooldown period checks to prevent alert flooding. When an alert is triggered, the method formats the message with emoji indicators based on severity level: red circle (🔴) for high severity, yellow circle (🟡) for medium, and green circle (🟢) for low severity alerts.

```mermaid
flowchart TD
Start([send_alert invoked]) --> ValidateEnabled["Validate Alerting Enabled"]
ValidateEnabled --> |Disabled| ReturnFalse["Return False"]
ValidateEnabled --> |Enabled| CheckCooldown["Check Cooldown Period"]
CheckCooldown --> |Within Cooldown| ReturnFalse
CheckCooldown --> |Beyond Cooldown| FormatMessage["Format Message with Emoji"]
FormatMessage --> SendTelegram["Send to Telegram"]
SendTelegram --> SendEmail["Send to Email"]
SendEmail --> StoreDatabase["Store in Database"]
StoreDatabase --> DetermineRoutes["Determine Active Routes"]
DetermineRoutes --> RouteIntegrations["Route to Integrations"]
RouteIntegrations --> Fallback["Execute Fallback if Needed"]
Fallback --> End([Alert Processing Complete])
style Start fill:#4CAF50,stroke:#388E3C
style End fill:#4CAF50,stroke:#388E3C
style ReturnFalse fill:#f44336,stroke:#d32f2f
```

The method implements a fallback mechanism that ensures alert delivery even when the enhanced notification system encounters issues. If the primary enhanced notification path fails, the system falls back to the original notification storage method, ensuring reliability and message delivery.

The alert processing includes several key steps:
1. Cooldown validation to prevent alert storms
2. Message formatting with severity-based emoji indicators
3. Parallel delivery to Telegram and email channels
4. Storage in the database with enhanced metadata
5. Routing through configured integration channels
6. Fallback mechanisms for system resilience

**Section sources**
- [alerting.py](file://vertex-ar/app/alerting.py#L229-L328)

## Notification Routing Configuration

The notification routing system in Vertex AR uses a priority-based configuration model that determines active channels for different alert severities. The `_get_routes_for_priority` method implements this logic by mapping priority levels to specific notification routes based on configuration settings and feature flags.

The routing configuration is defined through environment variables that specify the channels for each priority level:
- CRITICAL_NOTIFICATION_ROUTES: Channels for critical alerts
- HIGH_NOTIFICATION_ROUTES: Channels for high severity alerts
- MEDIUM_NOTIFICATION_ROUTES: Channels for medium severity alerts
- LOW_NOTIFICATION_ROUTES: Channels for low severity alerts

```mermaid
graph TD
Priority[Alert Priority] --> Critical{"Critical?"}
Critical --> |Yes| GetCriticalRoutes["Get CRITICAL_NOTIFICATION_ROUTES"]
Critical --> |No| High{"High?"}
High --> |Yes| GetHighRoutes["Get HIGH_NOTIFICATION_ROUTES"]
High --> |No| Medium{"Medium?"}
Medium --> |Yes| GetMediumRoutes["Get MEDIUM_NOTIFICATION_ROUTES"]
Medium --> |No| Low{"Low?"}
Low --> |Yes| GetLowRoutes["Get LOW_NOTIFICATION_ROUTES"]
Low --> |No| Default["Use Default Routes"]
GetCriticalRoutes --> FilterEnabled["Filter by Enabled Integrations"]
GetHighRoutes --> FilterEnabled
GetMediumRoutes --> FilterEnabled
GetLowRoutes --> FilterEnabled
Default --> FilterEnabled
FilterEnabled --> TelegramEnabled{"Telegram Enabled?"}
TelegramEnabled --> |Yes| IncludeTelegram["Include Telegram"]
TelegramEnabled --> |No| ExcludeTelegram["Exclude Telegram"]
FilterEnabled --> EmailEnabled{"Email Enabled?"}
EmailEnabled --> |Yes| IncludeEmail["Include Email"]
EmailEnabled --> |No| ExcludeEmail["Exclude Email"]
FilterEnabled --> WebhookEnabled{"Webhook Enabled?"}
WebhookEnabled --> |Yes| IncludeWebhook["Include Webhook"]
WebhookEnabled --> |No| ExcludeWebhook["Exclude Webhook"]
IncludeTelegram --> FinalRoutes["Final Route List"]
ExcludeTelegram --> FinalRoutes
IncludeEmail --> FinalRoutes
ExcludeEmail --> FinalRoutes
IncludeWebhook --> FinalRoutes
ExcludeWebhook --> FinalRoutes
FinalRoutes --> ReturnRoutes["Return Active Routes"]
```

Feature flags control the availability of each notification channel:
- NOTIFICATION_TELEGRAM_ENABLED: Enables/disables Telegram notifications
- NOTIFICATION_EMAIL_ENABLED: Enables/disables email notifications
- NOTIFICATION_WEBHOOK_ENABLED: Enables/disables webhook notifications

The routing method filters the configured routes based on these feature flags, ensuring that only enabled channels are included in the final route list. This allows administrators to temporarily disable specific channels without modifying the route configurations.

**Section sources**
- [alerting.py](file://vertex-ar/app/alerting.py#L329-L353)
- [config.py](file://vertex-ar/app/config.py#L151-L160)

## Alertmanager Integration

The Vertex AR system integrates with Prometheus Alertmanager through the alertmanager.yml configuration file, which defines a sophisticated routing and notification system for monitoring alerts. This integration enables the system to handle alerts from Prometheus and route them appropriately based on severity and service type.

```mermaid
graph TB
subgraph "Alertmanager Configuration"
Route[Route Configuration] --> Grouping["Group By: alertname, service"]
Route --> Timing["Group Wait: 10s<br/>Group Interval: 10s<br/>Repeat Interval: 1h"]
Route --> CriticalRoute["Critical Alerts Route"]
Route --> WarningRoute["Warning Alerts Route"]
Route --> ServiceRoute["Vertex-AR Service Route"]
CriticalRoute --> MatchCritical["Match: severity=critical"]
CriticalRoute --> ReceiverCritical["Receiver: critical-alerts"]
CriticalRoute --> CriticalTiming["Group Wait: 5s<br/>Repeat Interval: 30m"]
WarningRoute --> MatchWarning["Match: severity=warning"]
WarningRoute --> ReceiverWarning["Receiver: warning-alerts"]
WarningRoute --> WarningTiming["Repeat Interval: 2h"]
ServiceRoute --> MatchService["Match: service=vertex-ar"]
ServiceRoute --> ReceiverService["Receiver: vertex-ar-team"]
end
subgraph "Receivers"
WebHookReceiver["Receiver: web.hook"] --> WebHookConfig["Webhook Config"]
WebHookConfig --> WebHookURL["URL: http://localhost:8000/admin/monitoring/webhook/alert"]
CriticalReceiver["Receiver: critical-alerts"] --> CriticalEmail["Email Config"]
CriticalEmail --> CriticalEmailTo["To: admin@vertex-ar.example.com"]
CriticalEmail --> CriticalSubject["Subject: [CRITICAL] Vertex AR Alert"]
CriticalReceiver --> CriticalWebhook["Webhook Config"]
WarningReceiver["Receiver: warning-alerts"] --> WarningEmail["Email Config"]
WarningEmail --> WarningEmailTo["To: team@vertex-ar.example.com"]
WarningEmail --> WarningSubject["Subject: [WARNING] Vertex AR Alert"]
WarningReceiver --> WarningWebhook["Webhook Config"]
SlackReceiver["Receiver: vertex-ar-team"] --> SlackConfig["Slack Config"]
SlackConfig --> SlackWebhook["API URL: YOUR_SLACK_WEBHOOK_URL"]
SlackConfig --> SlackChannel["Channel: #vertex-ar-alerts"]
end
subgraph "Advanced Rules"
InhibitRules["Inhibition Rules"] --> InhibitSource["Source: severity=critical"]
InhibitRules --> InhibitTarget["Target: severity=warning"]
InhibitRules --> InhibitEqual["Equal: alertname, service"]
TimeIntervals["Time Intervals"] --> BusinessHours["Business Hours"]
BusinessHours --> BusinessTimes["09:00-17:00"]
BusinessHours --> BusinessDays["Monday-Friday"]
TimeIntervals --> Weekends["Weekends"]
Weekends --> WeekendDays["Saturday, Sunday"]
end
Route --> Receivers
Receivers --> AdvancedRules
```

**Diagram sources**
- [alertmanager.yml](file://monitoring/alertmanager.yml#L1-L97)

The Alertmanager configuration includes several key components:

### Route Configuration
The route configuration defines how alerts are grouped and routed based on their labels. Alerts are grouped by alertname and service, with specific routes for different severity levels:
- Critical alerts (severity=critical) are routed to the critical-alerts receiver
- Warning alerts (severity=warning) are routed to the warning-alerts receiver
- Alerts for the vertex-ar service are routed to the vertex-ar-team receiver

### Receivers Configuration
The system defines multiple receivers for different notification channels:
- **web.hook**: A webhook receiver that forwards alerts to the Vertex AR application at http://localhost:8000/admin/monitoring/webhook/alert
- **critical-alerts**: Sends email notifications to admin@vertex-ar.example.com with a [CRITICAL] subject prefix
- **warning-alerts**: Sends email notifications to team@vertex-ar.example.com with a [WARNING] subject prefix
- **vertex-ar-team**: Sends notifications to a Slack channel (#vertex-ar-alerts) using a webhook

### Inhibition Rules
The system implements inhibition rules to prevent alert noise by suppressing less severe alerts when more critical alerts exist. Specifically, warning alerts are suppressed when critical alerts exist for the same service and alert name. This prevents teams from being overwhelmed with warning notifications when a critical issue is already being addressed.

### Time Intervals
The configuration defines time intervals for different operational periods:
- Business hours: 09:00 to 17:00 on weekdays (Monday through Friday)
- Weekends: Saturday and Sunday

These time intervals can be used to implement different notification policies during business hours versus after hours, though the specific routing based on these intervals is not shown in the current configuration.

**Section sources**
- [alertmanager.yml](file://monitoring/alertmanager.yml#L1-L97)

## Testing and Validation

The alert routing system includes comprehensive testing and validation capabilities to ensure proper configuration and functionality. These testing mechanisms allow administrators to verify that alerts are properly routed through the configured channels.

The AlertManager class includes a `test_alert_system` method that tests all configured alert channels. This method sends test messages through Telegram and email channels, returning a dictionary with the success status of each channel. The test process follows these steps:

```mermaid
sequenceDiagram
participant Admin as Administrator
participant AlertManager as AlertManager
participant Telegram as Telegram
participant Email as Email Service
participant Database as Notification Database
Admin->>AlertManager : test_alert_system()
AlertManager->>AlertManager : Log test initiation
alt Telegram Configured
AlertManager->>Telegram : send_telegram_alert("Test message")
Telegram-->>AlertManager : Success/Failure
else Telegram Not Configured
AlertManager-->>AlertManager : Set telegram : false
end
alt Email Configuration Valid
AlertManager->>Email : send_email_alert("Test Alert", "Test message")
Email-->>AlertManager : Success/Failure
else Email Configuration Invalid
AlertManager-->>AlertManager : Set email : false
end
AlertManager->>AlertManager : Compile results
AlertManager->>Database : Log test results
AlertManager-->>Admin : Return results dictionary
```

**Diagram sources**
- [alerting.py](file://vertex-ar/app/alerting.py#L355-L378)

Additionally, the system provides an API endpoint for testing notification routing through the integrations layer. The `/test-routing` endpoint in notifications_management.py allows administrators to test specific notification configurations with custom data, priority levels, and integration channels.

The testing process includes:
1. Verification of Telegram configuration (bot token and chat ID)
2. Validation of email service connectivity and SMTP configuration
3. Testing of webhook delivery (if configured)
4. Verification of database notification storage
5. Validation of integration routing logic

These testing capabilities ensure that administrators can validate the entire alert routing pipeline before relying on it for production alerts.

**Section sources**
- [alerting.py](file://vertex-ar/app/alerting.py#L355-L378)
- [notifications_management.py](file://vertex-ar/app/api/notifications_management.py#L270-L304)

## Configuration Examples

The multi-channel alert routing system supports various configuration strategies through environment variables and the alertmanager.yml file. Below are examples of different routing configurations:

### Basic Configuration
```env
# Enable alerting system
ALERTING_ENABLED=true

# Notification channel feature flags
NOTIFICATION_TELEGRAM_ENABLED=true
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_WEBHOOK_ENABLED=false

# Priority-based routing
CRITICAL_NOTIFICATION_ROUTES=telegram,email
HIGH_NOTIFICATION_ROUTES=telegram,email
MEDIUM_NOTIFICATION_ROUTES=email
LOW_NOTIFICATION_ROUTES=
```

### Production Configuration with Webhooks
```env
# Enable all notification channels
NOTIFICATION_TELEGRAM_ENABLED=true
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_WEBHOOK_ENABLED=true

# Webhook configuration
WEBHOOK_URLS=https://webhook.example.com/alerts,https://backup-webhook.example.com/alerts
WEBHOOK_TIMEOUT=30
WEBHOOK_MAX_RETRIES=3

# Enhanced routing for critical situations
CRITICAL_NOTIFICATION_ROUTES=telegram,email,webhook
HIGH_NOTIFICATION_ROUTES=telegram,email,webhook
MEDIUM_NOTIFICATION_ROUTES=email,webhook
LOW_NOTIFICATION_ROUTES=webhook
```

### Development Configuration
```env
# Disable external notifications in development
NOTIFICATION_TELEGRAM_ENABLED=false
NOTIFICATION_EMAIL_ENABLED=false
NOTIFICATION_WEBHOOK_ENABLED=false

# Route all notifications to database only
CRITICAL_NOTIFICATION_ROUTES=
HIGH_NOTIFICATION_ROUTES=
MEDIUM_NOTIFICATION_ROUTES=
LOW_NOTIFICATION_ROUTES=
```

### Business Hours Configuration
```yaml
# alertmanager.yml - Business hours routing
time_intervals:
  - name: 'business-hours'
    time_intervals:
      - times:
          - start_time: '09:00'
            end_time: '17:00'
        weekdays: ['monday:friday']
  
  - name: 'weekends'
    time_intervals:
      - weekdays: ['saturday', 'sunday']

# Route critical alerts to on-call team during business hours
routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
    active_time_intervals: ['business-hours', 'weekends']
  
  - match:
      severity: warning
    receiver: 'warning-alerts'
    active_time_intervals: ['business-hours']
```

### Alertmanager Configuration with Inhibition
```yaml
# alertmanager.yml - Complete configuration
route:
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 5s
      repeat_interval: 30m
    - match:
        severity: warning
      receiver: 'warning-alerts'
      repeat_interval: 2h
    - match:
        service: vertex-ar
      receiver: 'vertex-ar-team'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:8000/admin/monitoring/webhook/alert'
        send_resolved: true

  - name: 'critical-alerts'
    email_configs:
      - to: 'admin@vertex-ar.example.com'
        subject: '[CRITICAL] Vertex AR Alert: {{ .GroupLabels.alertname }}'
    webhook_configs:
      - url: 'http://localhost:8000/admin/monitoring/webhook/alert'
        send_resolved: true

  - name: 'warning-alerts'
    email_configs:
      - to: 'team@vertex-ar.example.com'
        subject: '[WARNING] Vertex AR Alert: {{ .GroupLabels.alertname }}'
    webhook_configs:
      - url: 'http://localhost:8000/admin/monitoring/webhook/alert'
        send_resolved: true

  - name: 'vertex-ar-team'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#vertex-ar-alerts'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'service']
```

These configuration examples demonstrate the flexibility of the alert routing system, allowing administrators to tailor notification strategies to their specific operational requirements.

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L151-L160)
- [alertmanager.yml](file://monitoring/alertmanager.yml#L1-L97)

## Conclusion

The multi-channel alert routing system in Vertex AR provides a robust and flexible framework for delivering critical notifications through multiple channels. The system's architecture combines application-level alerting with external monitoring integration, creating a comprehensive notification ecosystem that ensures important alerts reach the appropriate stakeholders.

Key features of the system include:
- Multi-channel delivery through Telegram, email, and database notifications
- Severity-based formatting with emoji indicators for quick visual recognition
- Priority-based routing controlled by configuration settings and feature flags
- Integration with Prometheus Alertmanager for monitoring alerts
- Inhibition rules that suppress warning alerts when critical alerts exist
- Comprehensive testing and validation capabilities

The system's design emphasizes reliability and flexibility, with fallback mechanisms that ensure alert delivery even when components fail. The configuration model allows administrators to tailor notification strategies to their specific operational requirements, from development environments with minimal notifications to production systems with redundant alerting channels.

By implementing this sophisticated alert routing system, Vertex AR ensures that critical information is delivered promptly and reliably, enabling rapid response to system issues and maintaining high availability.