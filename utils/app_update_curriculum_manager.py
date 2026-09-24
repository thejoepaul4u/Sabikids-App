import json
import threading
import time
import urllib.request

CURRENT_APP_VERSION = "1.0.0"
GITHUB_UPDATE_URL = "https://raw.githubusercontent.com/thejoepaul4u/Sabikids-App/refs/heads/main/app_update_curriculum.json"


class AppUpdateManager:

    def __init__(
        self,
        current_version=CURRENT_APP_VERSION,
        github_url=GITHUB_UPDATE_URL,
    ):
        self.current_version = current_version
        self.github_url = github_url

    def check_for_updates(self, on_update_found_callback):
        """Fetches update data asynchronously to keep the UI smooth and responsive."""

        def fetch():
            try:
                # Bypass GitHub CDN caching by appending a timestamp parameter
                cache_bust_url = f"{self.github_url}?nocache={int(time.time())}"

                headers = {
                    "User-Agent": "SabiLearnersApp",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                }

                req = urllib.request.Request(cache_bust_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        remote_version = data.get(
                            "app_version", self.current_version
                        )
                        changelog = data.get(
                            "changelog", "New updates and improvements!"
                        )
                        is_mandatory = data.get("mandatory_update", False)

                        if self._is_newer_version(
                            remote_version, self.current_version
                        ):
                            # Pass details including mandatory flag to callback
                            on_update_found_callback(
                                remote_version, changelog, is_mandatory
                            )
            except Exception as e:
                print(f"[APP UPDATE CHECK SKIPPED]: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _is_newer_version(self, remote, current):
        """Compares semantic version strings (e.g. '1.1.0' > '1.0.0')."""
        try:
            remote_parts = [int(x) for x in remote.split(".")]
            current_parts = [int(x) for x in current.split(".")]
            return remote_parts > current_parts
        except Exception:
            return False