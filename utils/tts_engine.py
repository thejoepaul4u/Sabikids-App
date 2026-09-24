import os
import threading

try:
  import pyttsx3

  HAS_PYTTSX3 = True
except ImportError:
  HAS_PYTTSX3 = False

try:
  from kivy.core.audio import SoundLoader

  HAS_KIVY_SOUND = True
except ImportError:
  HAS_KIVY_SOUND = False

from kivy.app import App


class TTSEngine:

  _engine = None
  _current_sound = None
  _is_speaking = False

  @classmethod
  def get_secure_media_dir(cls):
    """Returns hidden, app-bound sandbox path that wipes on app uninstall."""
    app = App.get_running_app()
    if app:
      base_dir = app.user_data_dir
    else:
      base_dir = os.path.dirname(__file__)

    media_dir = os.path.join(base_dir, ".media_cache")
    os.makedirs(media_dir, exist_ok=True)

    # .nomedia blocks Android Gallery and Music Players from indexing files
    nomedia_file = os.path.join(media_dir, ".nomedia")
    if not os.path.exists(nomedia_file):
      try:
        open(nomedia_file, "a").close()
      except Exception:
        pass

    return media_dir

  @classmethod
  def _get_engine(cls):
    if HAS_PYTTSX3 and cls._engine is None:
      try:
        cls._engine = pyttsx3.init()
        cls._engine.setProperty("rate", 140)  # Friendly pacing for kids
      except Exception:
        cls._engine = None
    return cls._engine

  @classmethod
  def play_file(cls, audio_filename):
    """Plays custom recorded audio stored securely inside the app sandbox with fallback to root assets."""
    cls.stop_immediately()

    if not audio_filename:
      return

    # Check if absolute path
    if os.path.isabs(audio_filename):
      audio_path = audio_filename
    else:
      # Check sandbox first
      sandbox_path = os.path.join(cls.get_secure_media_dir(), audio_filename)
      # Fallback to local root app asset directory if sandbox copy isn't present
      if os.path.exists(sandbox_path):
        audio_path = sandbox_path
      else:
        audio_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), audio_filename
        )

    if os.path.exists(audio_path) and HAS_KIVY_SOUND:
      try:
        cls._current_sound = SoundLoader.load(audio_path)
        if cls._current_sound:
          cls._current_sound.play()
      except Exception as e:
        print(f"[TTS AUDIO ERROR]: Failed to play {audio_path} -> {e}")

  @classmethod
  def speak_text(cls, text):
    """Reads given text aloud in a background thread to prevent UI freezing."""
    cls.stop_immediately()

    if not text:
      return

    def _speak():
      engine = cls._get_engine()
      if engine:
        try:
          cls._is_speaking = True
          engine.say(text)
          engine.runAndWait()
        except Exception:
          pass
        finally:
          cls._is_speaking = False

    threading.Thread(target=_speak, daemon=True).start()

  @classmethod
  def stop_immediately(cls):
    """Stops all active playback immediately."""
    if cls._current_sound:
      try:
        cls._current_sound.stop()
        cls._current_sound.unload()
      except Exception:
        pass
      cls._current_sound = None

    if HAS_PYTTSX3 and cls._engine:
      try:
        cls._engine.stop()
      except Exception:
        pass
    cls._is_speaking = False