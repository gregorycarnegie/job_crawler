# =============================================================================
# Configuration
# =============================================================================

import os


class MonitoringConfig:
    # Health check intervals
    HEALTH_CHECK_INTERVAL = 300  # 5 minutes
    API_CHECK_INTERVAL = 600     # 10 minutes
    DB_CHECK_INTERVAL = 900      # 15 minutes
    
    # Alert thresholds
    MAX_RESPONSE_TIME = 10       # seconds
    MAX_ERROR_RATE = 0.05        # 5%
    MIN_SUCCESS_RATE = 0.95      # 95%
    
    # Retention periods
    LOG_RETENTION_DAYS = 30
    METRICS_RETENTION_DAYS = 90
    BACKUP_RETENTION_DAYS = 7
    
    def __init__(self):
        # Email alerts (optional) - read at instance creation
        self.ENABLE_EMAIL_ALERTS = os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true"
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.EMAIL_USER = os.getenv("EMAIL_USER")
        self.EMAIL_PASS = os.getenv("EMAIL_PASS")
        self.ALERT_EMAIL = os.getenv("ALERT_EMAIL")
