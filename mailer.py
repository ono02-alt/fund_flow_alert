"""
mailer.py
Gmail SMTPを使ってHTMLメールを送信する
"""

import logging
import os
import smtplib
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


def send_report(
    html_body: str,
    subject: Optional[str] = None,
    to_addr: Optional[str] = None,
) -> bool:
    """
    Gmail SMTPでHTMLメールを送信する

    環境変数:
        GMAIL_ADDRESS : 送信元Gmailアドレス
        GMAIL_APP_PASSWORD : Googleアカウントのアプリパスワード（16文字）
        NOTIFY_EMAIL : 送信先メールアドレス（未設定時はGMAIL_ADDRESSと同じ）
    """
    from_addr  = os.environ.get("GMAIL_ADDRESS", "")
    app_pw     = os.environ.get("GMAIL_APP_PASSWORD", "")
    notify_to  = to_addr or os.environ.get("NOTIFY_EMAIL", from_addr)

    if not from_addr or not app_pw:
        logger.error("GMAIL_ADDRESS または GMAIL_APP_PASSWORD が未設定です")
        return False

    if not notify_to:
        logger.error("送信先メールアドレスが設定されていません")
        return False

    date_str = datetime.now().strftime("%Y/%m/%d")
    if subject is None:
        subject = f"【資金流入レポート】{date_str} 大口・機関投資家動向"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = notify_to

    # プレーンテキスト（フォールバック）
    plain = "HTMLメール非対応の環境です。HTMLビューアでご確認ください。"
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, app_pw)
            server.sendmail(from_addr, notify_to, msg.as_string())
        logger.info(f"メール送信完了 → {notify_to}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail認証失敗。アプリパスワードを確認してください")
        return False
    except Exception as e:
        logger.error(f"メール送信エラー: {e}")
        return False


