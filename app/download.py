"""Module for downloading reports from SharePoint and converting PDFs to images."""

import configparser
from datetime import datetime, timezone
from pathlib import Path

from pdf2image import convert_from_path

from app.graph_api import GraphAPIClient
from app.logger import get_logger

logger = get_logger()


def download_report(report_type: str, image_page: int = 0) -> None:
    """Download report from SharePoint and convert it to an image.

    :param report_type: Type of report to download ('daily' or 'weekly')
    :type report_type: str
    """
    config = configparser.ConfigParser()
    config.read("config.ini")

    local_path = config["Generic"]["local_path"]
    site_name = config["Sharepoint"]["site_name"]
    microsoft_config = config["Microsoft"]
    microsoft_client = GraphAPIClient.from_config(microsoft_config)

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    remote_folder = f"Report/{report_type}"
    files = microsoft_client.search_file(
        site_name=site_name, remote_folder=remote_folder, expression=today
    )

    for file in files:
        filename = file["name"]

        logger.info("Found file for %s: %s", report_type, filename)

        report_type_path = report_type.lower().replace(" ", "_")
        local_path_obj = Path.cwd() / local_path / report_type_path
        local_pdf_path = local_path_obj / "pdf"

        output_filename = microsoft_client.download_file(
            site_name, file, local_pdf_path
        )
        _save_image(output_filename, local_path_obj, image_page)


def _save_image(pdf_filename: str, local_path: str, image_page: int) -> None:
    local_path_image = Path.cwd() / local_path / "image"
    local_path_image.mkdir(parents=True, exist_ok=True)

    image_pathname = local_path_image / pdf_filename
    images = convert_from_path(image_pathname, dpi=200, fmt="jpeg")

    if images:
        pdf_name = image_pathname.stem
        image_path = local_path_image / f"{pdf_name}.jpg"
        images[image_page].save(image_path, "JPEG")
        logger.info("Saved image: %s", image_path)
    else:
        logger.error("No images found in the PDF file.")
