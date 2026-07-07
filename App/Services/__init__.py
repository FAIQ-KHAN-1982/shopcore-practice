from App.Services.auth_service import get_user_by_email, create_user
from App.Services.email_service import (
    send_email_template,
    send_verification_email,
    send_reset_password_email,
    send_new_device_login_alert,
    send_lockout_alert_email
)
