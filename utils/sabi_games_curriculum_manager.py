import os
import json
from kivy.app import App
from kivy.network.urlrequest import UrlRequest
from kivy.clock import Clock

GAMES_GITHUB_JSON_URL = "https://raw.githubusercontent.com/thejoepaul4u/Sabikids-App/refs/heads/main/sabi_games_curriculum.json"


class SabiGamesCurriculumManager:
    _cached_data = None
    _pending_remote_data = None

    @classmethod
    def get_local_json_path(cls):
        """Returns the secure JSON path inside user_data_dir."""
        app = App.get_running_app()
        if app:
            base_dir = app.user_data_dir
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'data'))
        return os.path.join(base_dir, 'sabi_games_curriculum.json')

    @classmethod
    def get_secure_media_dir(cls):
        """Returns isolated folder for game media assets with .nomedia protection."""
        app = App.get_running_app()
        base_dir = app.user_data_dir if app else os.path.dirname(__file__)
        media_dir = os.path.join(base_dir, ".media_cache")
        os.makedirs(media_dir, exist_ok=True)

        nomedia_file = os.path.join(media_dir, ".nomedia")
        if not os.path.exists(nomedia_file):
            try:
                open(nomedia_file, 'a').close()
            except Exception:
                pass
        return media_dir

    @classmethod
    def load_curriculum(cls, force_reload=False):
        """Loads local games curriculum JSON file safely with cache control."""
        if cls._cached_data is not None and not force_reload:
            return cls._cached_data

        json_path = cls.get_local_json_path()
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._cached_data = json.load(f)
                    return cls._cached_data
            else:
                cls._cached_data = {"games": {}}
                return cls._cached_data
        except Exception as e:
            print(f"[GAMES CURRICULUM ERROR]: Failed loading JSON -> {e}")
            cls._cached_data = {"games": {}}
            return cls._cached_data

    @classmethod
    def get_game_data(cls, game_id, force_reload=False):
        """Returns game specific dictionary payload."""
        data = cls.load_curriculum(force_reload=force_reload)
        return data.get("games", {}).get(game_id, {})

    @classmethod
    def get_game_words(cls, game_id="word_builder"):
        """Generic method to flatten category word banks for ANY word/quiz mini-game."""
        game_data = cls.get_game_data(game_id)
        categories = game_data.get("categories", [])
        all_words = []
        for cat in categories:
            all_words.extend(cat.get("words", []))
        return all_words

    @classmethod
    def get_game_version(cls, game_id):
        """Returns the isolated version for a specific mini-game."""
        game_data = cls.get_game_data(game_id)
        return game_data.get("version", "0.0.0")

    @classmethod
    def parse_version(cls, ver_str):
        try:
            return tuple(map(int, ver_str.split(".")))
        except Exception:
            return (1, 0, 0)

    @classmethod
    def check_game_update(cls, game_id, on_update_found_callback):
        """Checks GitHub asynchronously for updates specifically for game_id."""
        def on_success(req, result):
            try:
                remote_json = result if isinstance(result, dict) else json.loads(result)
                remote_game = remote_json.get("games", {}).get(game_id, {})
                remote_version_str = remote_game.get("version", "1.0.0")
                local_version_str = cls.get_game_version(game_id)

                remote_ver = cls.parse_version(remote_version_str)
                local_ver = cls.parse_version(local_version_str)

                print(f"[GAME SYNC]: Game '{game_id}' | Local: {local_version_str} | Remote: {remote_version_str}")

                if remote_ver > local_ver:
                    cls._pending_remote_data = remote_json
                    if callable(on_update_found_callback):
                        Clock.schedule_once(lambda dt: on_update_found_callback(game_id))
            except Exception as e:
                print(f"[GAMES SYNC ERROR]: Update check failed for {game_id} -> {e}")

        def on_error(req, error):
            print(f"[GAMES SYNC NOTICE]: Offline or update check failed -> {error}")

        UrlRequest(
            GAMES_GITHUB_JSON_URL,
            on_success=on_success,
            on_error=on_error,
            on_failure=on_error,
            timeout=5
        )

    @classmethod
    def apply_pending_update(cls, target_game_id):
        """Replaces ONLY target game payload and forces immediate cache invalidation."""
        if not cls._pending_remote_data or not target_game_id:
            return False

        try:
            local_json = cls.load_curriculum(force_reload=True)
            remote_game_data = cls._pending_remote_data.get("games", {}).get(target_game_id)

            if remote_game_data:
                local_json.setdefault("games", {})[target_game_id] = remote_game_data
                json_path = cls.get_local_json_path()

                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(local_json, f, indent=2, ensure_ascii=False)

                cls._cached_data = local_json
                cls._pending_remote_data = None
                print(f"[GAME SYNC]: Successfully updated ONLY game '{target_game_id}'!")
                return True
            return False
        except Exception as e:
            print(f"[GAMES CURRICULUM ERROR]: Save update failed -> {e}")
            return False