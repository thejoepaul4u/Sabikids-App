import os
import json
from kivy.app import App
from kivy.network.urlrequest import UrlRequest
from kivy.clock import Clock

ISABI_GITHUB_JSON_URL = "https://raw.githubusercontent.com/thejoepaul4u/Sabikids-App/refs/heads/main/isabi_curriculum.json"


class ISabiCurriculumManager:
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
        return os.path.join(base_dir, 'isabi_curriculum.json')

    @classmethod
    def get_secure_media_dir(cls):
        """Returns isolated folder for i-Sabi media assets with .nomedia protection."""
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
    def load_curriculum(cls):
        """Loads local i-Sabi Challenge JSON curriculum file safely."""
        if cls._cached_data is not None:
            return cls._cached_data

        json_path = cls.get_local_json_path()
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._cached_data = json.load(f)
                    return cls._cached_data
            else:
                print(f"[i-SABI WARNING]: {json_path} not found. Creating default layout.")
                cls._cached_data = {"version": "0.0.0", "levels": []}
                return cls._cached_data
        except Exception as e:
            print(f"[i-SABI ERROR]: Failed to load curriculum JSON -> {e}")
            cls._cached_data = {"version": "0.0.0", "levels": []}
            return cls._cached_data

    @classmethod
    def get_levels(cls):
        """Returns all challenge levels for ISabiLevelScreen."""
        data = cls.load_curriculum()
        return data.get("levels", [])

    @classmethod
    def get_level_version(cls, level_id):
        """Returns version for a specific level."""
        levels = cls.get_levels()
        for lvl in levels:
            if lvl.get("level_id") == level_id:
                return lvl.get("version", "1.0.0")
        return "1.0.0"

    @classmethod
    def parse_version(cls, ver_str):
        """Converts version string into integer tuple for comparison."""
        try:
            return tuple(map(int, ver_str.split(".")))
        except Exception:
            return (1, 0, 0)

    @classmethod
    def get_subjects_for_level(cls, level_id):
        """Returns subject array for ISabiSubjectScreen."""
        levels = cls.get_levels()
        for lvl in levels:
            if lvl.get("level_id") == level_id:
                return lvl.get("subjects", [])
        return []

    @classmethod
    def get_quizzes(cls, level_id, subject_id):
        """Fetches quizzes array for ISabiMCQScreen."""
        subjects = cls.get_subjects_for_level(level_id)
        for sub in subjects:
            if sub.get("subject_id") == subject_id:
                return sub.get("quizzes", [])
        return []

    @classmethod
    def check_level_update(cls, level_id, on_update_found_callback):
        """Checks remote repository asynchronously for challenge updates."""
        def on_success(req, result):
            try:
                remote_json = result if isinstance(result, dict) else json.loads(result)
                remote_version_str = "1.0.0"

                for lvl in remote_json.get("levels", []):
                    if lvl.get("level_id") == level_id:
                        remote_version_str = lvl.get("version", "1.0.0")
                        break

                local_version_str = cls.get_level_version(level_id)
                remote_ver = cls.parse_version(remote_version_str)
                local_ver = cls.parse_version(local_version_str)

                print(f"[i-SABI SYNC]: Level '{level_id}' | Local: {local_version_str} | Remote: {remote_version_str}")

                if remote_ver > local_ver:
                    cls._pending_remote_data = remote_json
                    if callable(on_update_found_callback):
                        Clock.schedule_once(lambda dt: on_update_found_callback(level_id))
            except Exception as e:
                print(f"[i-SABI SYNC ERROR]: Failed processing update -> {e}")

        def on_error(req, error):
            print(f"[i-SABI SYNC NOTICE]: Offline or update failed -> {error}")

        UrlRequest(
            ISABI_GITHUB_JSON_URL,
            on_success=on_success,
            on_error=on_error,
            on_failure=on_error,
            timeout=5
        )

    @classmethod
    def apply_pending_update(cls, target_level_id=None):
        """Saves remote updates to disk for a specific level only."""
        if not cls._pending_remote_data:
            return False

        try:
            local_json = cls.load_curriculum()

            if target_level_id:
                remote_level_obj = None
                for lvl in cls._pending_remote_data.get("levels", []):
                    if lvl.get("level_id") == target_level_id:
                        remote_level_obj = lvl
                        break

                if remote_level_obj:
                    updated = False
                    for idx, lvl in enumerate(local_json.get("levels", [])):
                        if lvl.get("level_id") == target_level_id:
                            local_json["levels"][idx] = remote_level_obj
                            updated = True
                            break

                    if not updated:
                        local_json.setdefault("levels", []).append(remote_level_obj)

                data_to_save = local_json
            else:
                data_to_save = cls._pending_remote_data

            json_path = cls.get_local_json_path()
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)

            cls._cached_data = data_to_save
            cls._pending_remote_data = None
            print(f"[i-SABI SYNC]: Successfully updated level '{target_level_id}'!")
            return True

        except Exception as e:
            print(f"[i-SABI ERROR]: Failed writing update -> {e}")
            return False

    @classmethod
    def reload_data(cls):
        cls._cached_data = None
        return cls.load_curriculum()