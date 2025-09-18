"""Module to read manual inserted data."""

from http import HTTPStatus
from pathlib import Path

import requests
from msal import ConfidentialClientApplication

from app.logger import get_logger

logger = get_logger()


class SharePointClient:
    """Client to interact with SharePoint for downloading and uploading files."""

    class Constants:
        """Constant values for SharePointClient."""

        authority_url = "https://login.microsoftonline.com/"
        scope = "https://graph.microsoft.com/.default"
        graph_url = "https://graph.microsoft.com/v1.0/sites/"

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        sharepoint_host: str,
        site_name: str,
    ) -> None:
        """Initialize the SharePoint client.

        :param tenant_id: Azure AD tenant ID
        :type tenant_id: str
        :param client_id: Azure AD client ID
        :type client_id: str
        :param client_secret: Azure AD client secret
        :type client_secret: str
        :param sharepoint_host: SharePoint host URL (e.g., 'yourdomain.sharepoint.com')
        :type sharepoint_host: str
        :param site_name: SharePoint site name
        :type site_name: str
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.sharepoint_host = sharepoint_host
        self.site_name = site_name

    @classmethod
    def from_config(cls, config: dict) -> "SharePointClient":
        """Create a SharePointClient instance from a configuration dictionary.

        :param config: Dictionary containing SharePoint configuration
        :type config: dict
        :return: SharePointClient instance
        :rtype: SharePointClient
        """
        return cls(
            tenant_id=config["tenant_id"],
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            sharepoint_host=config["sharepoint_host"],
            site_name=config["site_name"],
        )

    def _authenticate(self) -> str:
        logger.info("Authenticating to SharePoint %s", self.sharepoint_host)

        app = ConfidentialClientApplication(
            self.client_id,
            authority=f"{self.Constants.authority_url}{self.tenant_id}",
            client_credential=self.client_secret,
        )

        result = app.acquire_token_for_client(scopes=[self.Constants.scope])
        if "access_token" not in result:
            msg = f"Failed to get token: {result}"
            raise Exception(msg)

        return result["access_token"]

    def _create_folder(self, folder_name: str) -> None:
        logger.info("Creating local directory for folder %s", folder_name)

        local_dir = Path.cwd() / folder_name
        local_dir.mkdir(parents=True, exist_ok=True)

    def _download_all(
        self, site_id: str, token: str, files: list[str], local_dir: str
    ) -> None:
        for file in files:
            file_name = file["name"]
            file_id = file["id"]

            headers = {"Authorization": f"Bearer {token}"}
            download_url = (
                f"{self.Constants.graph_url}/{site_id}/drive/items/{file_id}/content"
            )
            response = requests.get(download_url, headers=headers, timeout=10)

            if response.status_code == HTTPStatus.OK:
                output_file = local_dir / file_name

                with Path.open(output_file, "wb") as f:
                    f.write(response.content)
                logger.info("Downloading file %s", file_name)
            else:
                logger.error("Failed to download file %s: %S", file_name, response.text)

    def search_file(self, remote_folder: str, expression: str) -> list[dict]:
        """Search for files in the `remote_folder` that contain the expression.

        This searches within the SharePoint folder for files whose names include the
        given expression.

        :param remote_folder: The remote folder to search in
        :type remote_folder: str
        :param expression: The expression to search for in filenames
        :type expression: str
        :return: List of matching files
        :rtype: list[dict]
        """
        token = self._authenticate()

        headers = {"Authorization": f"Bearer {token}"}
        site_url = (
            f"{self.Constants.graph_url}{self.sharepoint_host}:/sites/{self.site_name}"
        )
        site = requests.get(site_url, headers=headers, timeout=10).json()
        site_id = site["id"]

        folder_url = (
            f"{self.Constants.graph_url}/{site_id}/drive/root:/"
            f"{remote_folder}:/children"
        )
        response = requests.get(folder_url, headers=headers, timeout=10)

        if response.status_code != HTTPStatus.OK:
            msg = f"Failed to list files: {response.text}"
            raise Exception(msg)

        files = response.json().get("value", [])

        return [f for f in files if expression in f["name"]]

    def download_file(self, file: dict, local_path: str) -> str:
        """Download a specific file from SharePoint to a local path.

        :param file: The file metadata dictionary containing 'id' and 'name'
        :type file: dict
        :param local_path: The local directory path to save the downloaded file
        :type local_path: str
        :return: The filename of the downloaded file or None if failed
        :rtype: str
        """
        token = self._authenticate()

        headers = {"Authorization": f"Bearer {token}"}
        site_url = (
            f"{self.Constants.graph_url}{self.sharepoint_host}:/sites/{self.site_name}"
        )
        site = requests.get(site_url, headers=headers, timeout=10).json()
        site_id = site["id"]
        file_id = file["id"]

        download_url = (
            f"{self.Constants.graph_url}/{site_id}/drive/items/{file_id}/content"
        )
        response = requests.get(download_url, headers=headers, timeout=10)

        output_filename = local_path / file["name"]
        if response.status_code == HTTPStatus.OK:
            with Path.open(output_filename, "wb") as f:
                f.write(response.content)

            logger.info("Downloaded file %s", file["name"])
            return output_filename

        logger.error("Failed to download file %s", file["name"])
        return None

    def download_folder(
        self, remote_folder: str, local_folder: str, local_path: str
    ) -> None:
        """Download all files from a SharePoint folder to a local folder.

        :param remote_folder: The remote SharePoint folder to download from
        :type remote_folder: str
        :param local_folder: The local folder name to save files into
        :type local_folder: str
        :param local_path: The base local path where the local_folder will be created
        :type local_path: str
        """
        token = self._authenticate()

        headers = {"Authorization": f"Bearer {token}"}
        site_url = (
            f"{self.Constants.graph_url}{self.sharepoint_host}:/sites/{self.site_name}"
        )
        site = requests.get(site_url, headers=headers, timeout=10).json()
        site_id = site["id"]

        folder_url = (
            f"{self.Constants.graph_url}/{site_id}/drive/root:/"
            f"{remote_folder}:/children"
        )
        response = requests.get(folder_url, headers=headers, timeout=10)

        if response.status_code != HTTPStatus.OK:
            msg = f"Failed to get files: {response.text}"
            raise Exception(msg)

        files = response.json().get("value", [])

        logger.info("Found %s files in the folder %s", len(files), remote_folder)

        local_path = local_path / local_folder
        self._create_folder(local_path)
        self._download_all(site_id, token, files, local_path)

        logger.info("Download completed from SharePoint %s", self.sharepoint_host)

    def _upload_all(
        self,
        site_id: str,
        token: str,
        remote_folder: str,
        local_folder: str,
    ) -> None:
        files = Path.iterdir(local_folder)
        logger.info("Found %s files in the folder %s", len(files), local_folder)

        for file in files:
            filename = file
            local_path = local_folder / filename

            with Path.open(local_path, "rb") as file_data:
                headers = {"Authorization": f"Bearer {token}"}

                upload_url = (
                    f"{self.Constants.graph_url}/{site_id}/drive/root:/"
                    f"{remote_folder}/{filename}:/content"
                )
                upload_resp = requests.put(
                    upload_url,
                    headers=headers,
                    data=file_data,
                    timeout=30,
                )
                if upload_resp.status_code in [200, 201]:
                    logger.info("Uploaded file %s", filename)
                else:
                    logger.error("Failed to upload file %s", filename)

    def upload(self, remote_folder: str, local_folder: str) -> None:
        """Upload all files from a local folder to a SharePoint folder.

        :param remote_folder: The remote SharePoint folder to upload to
        :type remote_folder: str
        :param local_folder: The local folder path containing files to upload
        :type local_folder: str
        """
        token = self._authenticate()

        headers = {"Authorization": f"Bearer {token}"}
        site_url = (
            f"{self.Constants.graph_url}{self.sharepoint_host}:/sites/{self.site_name}"
        )
        site = requests.get(site_url, headers=headers, timeout=10).json()
        site_id = site["id"]

        self._upload_all(site_id, token, remote_folder, local_folder)

        logger.info("Upload completed to SharePoint %s", self.sharepoint_host)
