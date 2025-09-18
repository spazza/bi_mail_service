"""Module to send emails with attachments using SMTP."""

import configparser
import mimetypes
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from app.logger import get_logger

logger = get_logger()


def send_mail(report_type: str, subject: str) -> None:
    """Send an email with the report as an attachment.

    :param report_type: Type of report to send
    :type report_type: str
    :param subject: Subject of the email
    :type subject: str
    """
    config = configparser.ConfigParser()
    config.read("config.ini")

    smtp_server = "smtp.office365.com"
    smtp_port = 587
    sender_email = config.get("Email", "username")
    password = config.get("Email", "password")
    local_path = config["SharePoint"]["local_path"]

    report_type_path = Path(local_path) / report_type.lower().replace(" ", "_")

    recipients = _get_recipients(report_type_path)

    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    _add_content(msg, report_type_path)
    _add_image(msg, report_type_path)
    _add_pdf(msg, report_type_path)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        logger.info("Email sent successfully")


def _get_recipients(report_type_path: str) -> list[str]:
    recipients_path = Path.cwd() / report_type_path / "recipients.txt"

    with Path.open(recipients_path) as f:
        return [line.strip() for line in f if line.strip()]

    logger.warning("No recipients found in emails.txt. Please check the file.")
    return []


def _add_image(msg: EmailMessage, report_type_path: str) -> None:
    image_path = Path.cwd() / report_type_path / "image"
    image_file = _get_daily_file(image_path)

    with Path.open(image_file, "rb") as img:
        img_data = img.read()
        maintype, subtype = mimetypes.guess_type(image_file)[0].split("/")
        msg.get_payload()[1].add_related(
            img_data, maintype=maintype, subtype=subtype, cid="inline_image"
        )
        return

    msg = "Image path is not set. Please provide a valid image path."
    raise ValueError(msg)


def _add_pdf(msg: EmailMessage, report_type_path: str) -> None:
    pdf_path = Path.cwd() / report_type_path / "pdf"
    pdf_file = _get_daily_file(pdf_path)

    file = Path(pdf_file)
    mime_type, _ = mimetypes.guess_type(file)
    maintype, subtype = mime_type.split("/")

    with Path.open(file, "rb") as f:
        msg.add_attachment(
            f.read(), maintype=maintype, subtype=subtype, filename=file.name
        )
        return

    msg = "PDF path is not set. Please provide a valid PDF path."
    raise ValueError(msg)


def _add_content(msg: EmailMessage, report_type_path: str) -> None:
    html_content_path = Path.cwd() / report_type_path / "body.html"

    with Path.open(html_content_path) as f:
        html_body = f.read()

        msg.set_content("Report Content")
        msg.add_alternative(html_body, subtype="html")
        return

    logger.error("HTML content file not found. Please check the path.")


def _get_daily_file(path: str) -> str:
    now = datetime.now(tz=timezone.utc)
    files = [f for f in Path(path).iterdir() if f.is_file()]

    for file in files:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", file.name)
        if match:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            if file_date.date() == now.date():
                logger.info("Found file for today: %s", file)
                return file
    return None
