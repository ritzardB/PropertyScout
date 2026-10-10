
import os
from typing import Any

import requests


class PropertyAPIClient:
    """Small HTTP client for an authorized JSON property API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("PROPERTYSCOUT_API_BASE_URL", "")
        ).rstrip("/")
        self.api_key = os.getenv("PROPERTYSCOUT_API_KEY", "")
        self.timeout = timeout

        if not self.base_url:
            raise ValueError(
                "Set PROPERTYSCOUT_API_BASE_URL before using the API."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PropertyScout/0.1",
        })

        # Generic bearer-token example only.
        # Change this to match your provider's authentication scheme.
        if self.api_key:
            self.session.headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

    def get_json(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Fetch one JSON response from a relative API endpoint."""
        if endpoint.startswith(("http://", "https://")):
            raise ValueError("Endpoint must be a relative API path.")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, (dict, list)):
            raise ValueError("Expected a JSON object or array.")

        return data
