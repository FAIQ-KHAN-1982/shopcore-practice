import pytest
from unittest.mock import patch, MagicMock
from App.Services.email_service import (
    send_email_template,
    send_verification_email,
    send_reset_password_email,
    send_new_device_login_alert,
    send_lockout_alert_email
)
from App.Security import MAX_LOGIN_ATTEMPTS

@patch("smtplib.SMTP")
def test_send_email_template_smtp_success(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    send_email_template("test@example.com", "Test Subject", "Test Body Content")

    mock_smtp.assert_called_once()
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once()
    mock_server.send_message.assert_called_once()


@patch("smtplib.SMTP", side_effect=Exception("SMTP Connection Error"))
def test_send_email_template_smtp_failure_fallback(mock_smtp, capsys):
    # Should handle Exception gracefully and print mock email to stdout
    send_email_template("test@example.com", "Test Subject", "Test Body Content")

    captured = capsys.readouterr()
    assert "Failed to send email 'Test Subject'" in captured.out
    assert "--- MOCK EMAIL [Subject: Test Subject] ---" in captured.out
    assert "To: test@example.com" in captured.out


@patch("App.Services.email_service.send_email_template")
def test_send_verification_email(mock_send):
    token = "test_verification_token_123"
    send_verification_email("user@example.com", token)

    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert args[0] == "user@example.com"
    assert args[1] == "Verify your ShopCore Account"
    assert token in args[2]


@patch("App.Services.email_service.send_email_template")
def test_send_reset_password_email(mock_send):
    token = "test_reset_token_456"
    send_reset_password_email("user@example.com", token)

    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert args[0] == "user@example.com"
    assert args[1] == "Reset your ShopCore Password"
    assert token in args[2]


@patch("App.Services.email_service.send_email_template")
def test_send_new_device_login_alert(mock_send):
    ip_address = "192.168.1.100"
    send_new_device_login_alert("user@example.com", ip_address)

    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert args[0] == "user@example.com"
    assert args[1] == "Security Alert: Login from New Device/Location"
    assert ip_address in args[2]


@patch("App.Services.email_service.send_email_template")
def test_send_lockout_alert_email(mock_send):
    send_lockout_alert_email("user@example.com")

    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert args[0] == "user@example.com"
    assert args[1] == "Security Alert: Account Locked"
    assert str(MAX_LOGIN_ATTEMPTS) in args[2]
