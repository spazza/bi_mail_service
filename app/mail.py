"""Module to send emails with attachments using SMTP."""

from __future__ import annotations

import base64
import configparser
import re
from datetime import datetime, timezone
from pathlib import Path

from app.graph_api import GraphAPIClient
from app.logger import get_logger

logger = get_logger()


def send_mail(report_type: str, subject: str, date: datetime | None = None) -> None:
    """Send an email with the report as an attachment.

    :param report_type: Type of report to send
    :type report_type: str
    :param subject: Subject of the email
    :type subject: str
    :param date: Date of the report to send, defaults to None
    :type date: datetime | None, optional
    """
    config = configparser.ConfigParser()
    config.read("config.ini")

    local_path = config["Generic"]["local_path"]
    microsoft_config = config["Microsoft"]
    sender = config["Email"]["username"]

    report_type_path = Path(local_path) / report_type.lower().replace(" ", "_")

    email = _create_message(report_type_path, subject, date)

    microsoft_client = GraphAPIClient.from_config(microsoft_config)
    microsoft_client.send_email(email, sender)


def _create_message(report_type_path: str, subject: str, date: datetime) -> dict:
    return {
        "message": {
            "subject": subject,
            "toRecipients": _get_recipients(report_type_path),
            "body": {"contentType": "HTML", "content": _get_body(report_type_path)},
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": "report.pdf",
                    "contentType": "application/pdf",
                    "contentBytes": _get_pdf(report_type_path, date),
                },
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": "report.png",
                    "contentType": "image/png",
                    "contentBytes": _get_image(report_type_path, date),
                    "isInline": True,
                    "contentId": "inline_image",
                },
            ],
        },
        "saveToSentItems": "true",
    }


def _get_recipients(report_type_path: str) -> list[str]:
    recipients_path = Path.cwd() / report_type_path / "recipients.txt"

    with Path.open(recipients_path) as f:
        raw_recipients = [line.strip() for line in f if line.strip()]
        if raw_recipients:
            return [{"emailAddress": {"address": email}} for email in raw_recipients]

    logger.warning("No recipients found in recipients.txt. Please check the file.")
    return []


def _get_body(report_type_path: str) -> str | None:
    html_content_path = Path.cwd() / report_type_path / "body.html"

    with Path.open(html_content_path) as f:
        return f.read()

    logger.error("HTML content file not found. Please check the path.")
    return None


def _get_image(report_type_path: str, date: datetime | None) -> str:
    image_path = Path.cwd() / report_type_path / "image"
    image_file = _get_file(image_path, date)

    with Path.open(image_file, "rb") as f:
        image_data = f.read()

        return base64.b64encode(image_data).decode("utf-8")

    msg = "Image path is not set. Please provide a valid image path."
    raise ValueError(msg)


def _get_pdf(report_type_path: str, date: datetime | None) -> str:
    pdf_path = Path.cwd() / report_type_path / "pdf"
    pdf_file = _get_file(pdf_path, date)

    with Path.open(pdf_file, "rb") as f:
        pdf_data = f.read()

        return base64.b64encode(pdf_data).decode("utf-8")

    msg = "PDF path is not set. Please provide a valid PDF path."
    raise ValueError(msg)


def _get_file(path: str, date: datetime | None) -> str:
    if date is None:
        date = datetime.now(tz=timezone.utc)

    files = [f for f in Path(path).iterdir() if f.is_file()]

    for file in files:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", file.name)
        if match:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            if file_date.date() == date.date():
                logger.info("Found file for today: %s", file)
                return file
    return None
