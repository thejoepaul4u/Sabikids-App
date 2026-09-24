import os
import json
from kivy.app import App
from kivy.network.urlrequest import UrlRequest

GITHUB_JSON_URL = "https://raw.githubusercontent.com/thejoepaul4u/Sabikids-App/refs/heads/main/curriculum.json"


def parse_version(v_str):
    """Safely converts semver string '1.0.3' to tuple (1, 0, 3) for proper comparison."""
    try:
        return tuple(map(int, str(v_str).strip().split('.')))
    except Exception:
        return (0, 0, 0)


class CurriculumManager:
    _cached_data = None
    _pending_remote_data = None
    _pending_update_type = "global"

    @classmethod
    def get_local_json_path(cls):
        """Returns the secure JSON path inside user_data_dir."""
        app = App.get_running_app()
        if app:
            base_dir = app.user_data_dir
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'data'))
        return os.path.join(base_dir, 'curriculum.json')

    @classmethod
    def get_secure_media_dir(cls):
        """Returns isolated folder for lesson audio/video with .nomedia protection."""
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
        """Loads local JSON curriculum file with safe fallback."""
        if cls._cached_data is not None:
            return cls._cached_data

        json_path = cls.get_local_json_path()
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._cached_data = json.load(f)
                    return cls._cached_data
            else:
                print(f"[WARNING]: {json_path} not found. Using empty template.")
                cls._cached_data = {"version": "0.0.0", "tiers": []}
                return cls._cached_data
        except Exception as e:
            print(f"[ERROR]: Failed to load curriculum JSON -> {e}")
            cls._cached_data = {"version": "0.0.0", "tiers": []}
            return cls._cached_data

    @classmethod
    def get_tiers(cls):
        """Returns all education tiers safely."""
        data = cls.load_curriculum()
        return data.get("tiers", [])

    @classmethod
    def get_tier_id_for_class(cls, class_id):
        """Returns tier_id for a given class."""
        tiers = cls.get_tiers()
        for tier in tiers:
            for c in tier.get("classes", []):
                if c.get("class_id") == class_id:
                    return tier.get("tier_id", "primary")
        return "primary"

    @classmethod
    def get_class_version(cls, class_id):
        """Finds current local version for a specific class."""
        tiers = cls.get_tiers()
        for tier in tiers:
            for c in tier.get("classes", []):
                if c.get("class_id") == class_id:
                    return c.get("version", "1.0.0")
        return "1.0.0"

    @classmethod
    def get_subjects_for_class(cls, class_id):
        """Gets all subjects under a given class ID."""
        tiers = cls.get_tiers()
        for tier in tiers:
            for c in tier.get("classes", []):
                if c.get("class_id") == class_id:
                    return c.get("subjects", [])
        return []

    @classmethod
    def get_topic_data(cls, class_id, subject_id, topic_id):
        """Fetches a specific topic dictionary safely from tiers."""
        subjects = cls.get_subjects_for_class(class_id)
        for s in subjects:
            if s.get("subject_id") == subject_id:
                for t in s.get("topics", []):
                    if t.get("topic_id") == topic_id:
                        return t
        return None

    @classmethod
    def check_global_update(cls, on_update_found_callback):
        """Asynchronously checks GitHub for global syllabus updates."""
        def on_success(req, result):
            try:
                remote_json = result if isinstance(result, dict) else json.loads(result)
                local_json = cls.load_curriculum()

                remote_global_ver = remote_json.get("version", "1.0.0")
                local_global_ver = local_json.get("version", "1.0.0")

                if parse_version(remote_global_ver) > parse_version(local_global_ver):
                    print(f"[SYNC CHECK]: Global update found! | Local: {local_global_ver} | Remote: {remote_global_ver}")
                    cls._pending_remote_data = remote_json
                    cls._pending_update_type = "global"
                    if callable(on_update_found_callback):
                        on_update_found_callback("global")
            except Exception as e:
                print(f"[SYNC ERROR]: Failed checking global update -> {e}")

        def on_error(req, error):
            print(f"[SYNC NOTICE]: Offline or update check failed -> {error}")

        UrlRequest(
            GITHUB_JSON_URL,
            on_success=on_success,
            on_error=on_error,
            on_failure=on_error,
            timeout=4
        )

    @classmethod
    def check_class_update(cls, class_id, on_update_found_callback):
        """Checks GitHub strictly for class-specific updates."""
        def on_success(req, result):
            try:
                remote_json = result if isinstance(result, dict) else json.loads(result)
                remote_class_ver = "1.0.0"
                for tier in remote_json.get("tiers", []):
                    for c in tier.get("classes", []):
                        if c.get("class_id") == class_id:
                            remote_class_ver = c.get("version", "1.0.0")
                            break

                local_class_ver = cls.get_class_version(class_id)
                print(f"[SYNC CHECK]: Class '{class_id}' | Local: {local_class_ver} | Remote: {remote_class_ver}")

                if parse_version(remote_class_ver) > parse_version(local_class_ver):
                    cls._pending_remote_data = remote_json
                    cls._pending_update_type = "class"
                    if callable(on_update_found_callback):
                        on_update_found_callback(class_id, "class")

            except Exception as e:
                print(f"[SYNC ERROR]: Failed checking class update -> {e}")

        def on_error(req, error):
            print(f"[SYNC NOTICE]: Offline or update check failed -> {error}")

        UrlRequest(
            GITHUB_JSON_URL,
            on_success=on_success,
            on_error=on_error,
            on_failure=on_error,
            timeout=4
        )

    @classmethod
    def apply_pending_update(cls, target_class_id=None):
        """Applies pending remote JSON updates safely to user_data_dir."""
        if not cls._pending_remote_data:
            return False

        try:
            local_json = cls.load_curriculum()

            if cls._pending_update_type == "global":
                data_to_save = cls._pending_remote_data
            else:
                remote_class_obj = None
                for tier in cls._pending_remote_data.get("tiers", []):
                    for c in tier.get("classes", []):
                        if c.get("class_id") == target_class_id:
                            remote_class_obj = c
                            break

                if remote_class_obj:
                    for tier in local_json.get("tiers", []):
                        for idx, c in enumerate(tier.get("classes", [])):
                            if c.get("class_id") == target_class_id:
                                tier["classes"][idx] = remote_class_obj
                                break

                data_to_save = local_json

            json_path = cls.get_local_json_path()
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)

            cls._cached_data = data_to_save
            cls._pending_remote_data = None
            return True

        except Exception as e:
            print(f"[ERROR]: Failed to apply update -> {e}")
            return False

    @classmethod
    def reload_data(cls):
        """Clears memory cache and forces a fresh read from disk."""
        cls._cached_data = None
        return cls.load_curriculum()