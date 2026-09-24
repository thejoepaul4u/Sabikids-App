import sys
import os

# Apply ANGLE backend ONLY on Windows machines to fix OpenGL 2.0 errors
if sys.platform == 'win32':
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.config import Config

# Default window dimensions for desktop environments
if sys.platform in ('win32', 'darwin', 'linux'):
    Config.set('graphics', 'width', '900')
    Config.set('graphics', 'height', '680')
    Config.set('graphics', 'resizable', True)
    Config.set('graphics', 'multisamples', '0') #prevents black-screen glitches on old GPUs

from kivy.core.window import Window

# Minimum window limits for desktop environments
if sys.platform in ('win32', 'darwin', 'linux'):
    Window.minimum_width = 320    #360
    Window.minimum_height = 568  #550


import threading
import time
from datetime import datetime

os.environ['KIVY_VIDEO'] = 'ffpyplayer'
os.environ['KIVY_AUDIO'] = 'sdl2'
from kivy.utils import platform
from kivy.app import App

if platform == 'win':
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")

from kivy.config import Config
if os.path.exists(ICON_PATH):
    Config.set('graphics', 'window_icon', ICON_PATH)

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock

# --- GLOBAL BUTTON CLICK SOUND IMPLEMENTATION ---
from kivy.core.audio import SoundLoader
from kivy.uix.button import Button

CLICK_SOUND_PATH = os.path.join(os.path.dirname(__file__), "assets", "audio", "click.mp3")
click_sound = SoundLoader.load(CLICK_SOUND_PATH) if os.path.exists(CLICK_SOUND_PATH) else None

original_on_release = Button.on_release

def play_sound_and_release(self, *args, **kwargs):
    """Triggers button audio playback unless the button is explicitly muted."""
    if not getattr(self, 'mute_sound', False) and click_sound:
        try:
            if click_sound.state == 'play':
                click_sound.stop()
            click_sound.play()
        except Exception as e:
            print(f"[AUDIO PLAYBACK ERROR]: {e}")

    return original_on_release(self, *args, **kwargs)

Button.on_release = play_sound_and_release
# ------------------------------------------------

import database
database.init_secure_db()

# Safe import for Offline Notification Manager
try:
    import notification_manager
except ImportError:
    notification_manager = None

from kivy.utils import platform
from kivy.core.window import Window


def safe_import_screen(module_path, class_name):
    try:
        mod = __import__(module_path, fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception as e:
        print(f"[IMPORT WARNING]: Could not load {class_name} from {module_path}: {e}")
        class DummyScreen(Screen):
            pass
        return DummyScreen

ReceivingPageScreen = safe_import_screen('screens.receiving_page', 'ReceivingPageScreen')
AuthPageScreen = safe_import_screen('screens.auth_page', 'AuthPageScreen')
PlansPageScreen = safe_import_screen('screens.plans_page', 'PlansPageScreen')
HomePageScreen = safe_import_screen('screens.home_page', 'HomePageScreen')
ClassroomHomeScreen = safe_import_screen('screens.classroom_home', 'ClassroomHomeScreen')
TopicListScreen = safe_import_screen('screens.topic_list_page', 'TopicListScreen')
ContentViewerScreen = safe_import_screen('screens.content_viewer_page', 'ContentViewerScreen')
TopicPathScreen = safe_import_screen('screens.topic_path_page', 'TopicPathScreen')
SettingsPageScreen = safe_import_screen('screens.settings_page', 'SettingsPageScreen')
ISabiLevelScreen = safe_import_screen('screens.isabi_level_page', 'ISabiLevelScreen')
ISabiSubjectScreen = safe_import_screen('screens.isabi_subject_page', 'ISabiSubjectScreen')
ISabiMCQScreen = safe_import_screen('screens.isabi_mcq_page', 'ISabiMCQScreen')
SabiGamesHubScreen = safe_import_screen('screens.sabi_games_hub_page', 'SabiGamesHubScreen')
WordBuilderPageScreen = safe_import_screen('screens.word_builder_page', 'WordBuilderPageScreen')
MathBalloonPopPageScreen = safe_import_screen('screens.math_balloon_pop_page', 'MathBalloonPopPageScreen')
MemoryFlashMatchPageScreen = safe_import_screen('screens.memory_flash_match_page', 'MemoryFlashMatchPageScreen')
SentenceCatcherPageScreen = safe_import_screen('screens.sentence_catcher_page', 'SentenceCatcherPageScreen')
ShapeColorSorterPageScreen = safe_import_screen('screens.shape_color_sorter_page', 'ShapeColorSorterPageScreen')
VocabularyWordlePageScreen = safe_import_screen('screens.vocabulary_wordle_page', 'VocabularyWordlePageScreen')
SpeedMathChallengePageScreen = safe_import_screen('screens.speed_math_challenge_page', 'SpeedMathChallengePageScreen')
#WordCrossPageScreen = safe_import_screen('screens.word_cross_page', 'WordCrossPageScreen')
WordSearchPageScreen = safe_import_screen('screens.word_search_page', 'WordSearchPageScreen')
KnowledgeHuntPageScreen = safe_import_screen('screens.knowledge_hunt_game_page', 'KnowledgeHuntPageScreen')



Window.softinput_mode = 'below_target'

class SabiLearnersApp(App):
    def get_media_cache_dir(self):
        """Returns the isolated folder where media is stored."""
        cache_dir = os.path.join(self.user_data_dir, "media_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def build(self):
        self.title = "Sabi Learners"
        if os.path.exists(ICON_PATH):
            self.icon = ICON_PATH

        self.sm = ScreenManager()
        
        self.sm.otp_timestamp = 0.0
        self.sm.temp_user_data = {}
        self.sm.generated_otp = ""
        
        screens = [
            ReceivingPageScreen(name='receiving_page'),
            AuthPageScreen(name='auth_page'),
            PlansPageScreen(name='plans_page'),
            HomePageScreen(name='home_page'),
            ClassroomHomeScreen(name='classroom_home'),
            TopicListScreen(name='topic_list'),
            ContentViewerScreen(name='content_viewer'),
            TopicPathScreen(name='topic_path'),
            SettingsPageScreen(name='settings_page'),
            ISabiLevelScreen(name='isabi_level'),
            ISabiSubjectScreen(name='isabi_subject'),
            ISabiMCQScreen(name='isabi_mcq'),
            SabiGamesHubScreen(name='sabi_games_hub_page'),
            WordBuilderPageScreen(name='word_builder_page'),
            MathBalloonPopPageScreen(name='math_balloon_pop_page'),
            MemoryFlashMatchPageScreen(name='memory_flash_match_page'),
            SentenceCatcherPageScreen(name='sentence_catcher_page'),
            ShapeColorSorterPageScreen(name='shape_color_sorter_page'),
            VocabularyWordlePageScreen(name='vocabulary_wordle_page'),
            SpeedMathChallengePageScreen(name='speed_math_challenge_page'),
            #WordCrossPageScreen(name='word_cross_page'),
            WordSearchPageScreen(name='word_search_page'),
            KnowledgeHuntPageScreen(name='knowledge_hunt_game_page')
        ]
        
        for scr in screens:
            self.sm.add_widget(scr)
        
        Window.bind(on_hardware_button=self.on_hardware_back_press)
        self.sm.current = 'receiving_page'
        return self.sm

    def on_start(self):
        self.db_sync_counter = 0

        # --- INITIALIZE OFFLINE NOTIFICATION REMINDERS ---
        if notification_manager:
            try:
                notification_manager.init_offline_notifications()
                print("[APP START]: Offline Notification Manager initialized.")
            except Exception as e:
                print(f"[APP START NOTIFICATION ERROR]: {e}")

        # --- DUAL REVENUECAT SDK INITIALIZATION (ANDROID & IOS) ---
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Purchases = autoclass('com.revenuecat.purchases.Purchases')
                PurchasesConfigurationBuilder = autoclass('com.revenuecat.purchases.PurchasesConfiguration$Builder')
                
                api_key = "goog_YOUR_REVENUECAT_ANDROID_PUBLIC_API_KEY"
                context = PythonActivity.mActivity
                
                builder = PurchasesConfigurationBuilder(context, api_key)
                Purchases.configure(builder.build())
                print("[REVENUECAT ANDROID]: SDK initialized successfully.")
            except Exception as e:
                print(f"[REVENUECAT ANDROID INIT ERROR]: {e}")

        elif platform == 'ios':
            try:
                from pyobjus import autoclass
                RCPurchases = autoclass('RCPurchases')
                api_key = "appl_YOUR_REVENUECAT_IOS_PUBLIC_API_KEY"
                
                RCPurchases.configureWithAPIKey_(api_key)
                print("[REVENUECAT IOS]: SDK initialized successfully.")
            except Exception as e:
                print(f"[REVENUECAT IOS INIT ERROR]: {e}")

        profile = database.get_user_profile()
        self.rem_sec = float(profile.get("free_seconds_remaining", database.DEFAULT_FREE_SECONDS))
        self.subscription_status = profile.get("subscription_status", "ACTIVE")
        self.chosen_plan_type = profile.get("chosen_plan_type", "Demo")

        self.start_metered_timer()

    def sync_from_database(self):
        """Forces runtime variables to sync directly with database values."""
        profile = database.get_user_profile()
        self.rem_sec = float(profile.get("free_seconds_remaining", database.DEFAULT_FREE_SECONDS))
        self.subscription_status = profile.get("subscription_status", "ACTIVE")
        self.chosen_plan_type = profile.get("chosen_plan_type", "Demo")

    def start_metered_timer(self):
        Clock.unschedule(self.global_metered_timer_pulse)
        self.last_monotonic_tick = time.monotonic()
        Clock.schedule_interval(self.global_metered_timer_pulse, 1.0)

    def global_metered_timer_pulse(self, dt):
        now_monotonic = time.monotonic()
        elapsed_monotonic = max(0.0, now_monotonic - self.last_monotonic_tick)
        self.last_monotonic_tick = now_monotonic

        if self.subscription_status == "EXPIRED":
            return

        if self.rem_sec > 0:
            self.rem_sec = max(0.0, self.rem_sec - elapsed_monotonic)
            
            self.db_sync_counter += 1
            if self.db_sync_counter >= 30 or self.rem_sec <= 0:
                self.async_db_checkpoint(self.rem_sec)
                self.db_sync_counter = 0

            if self.sm.has_screen('home_page'):
                home_screen = self.sm.get_screen('home_page')
                if hasattr(home_screen, 'update_tracker_display'):
                    home_screen.update_tracker_display(self.rem_sec)

        if self.rem_sec <= 0 and self.subscription_status != "EXPIRED":
            self.subscription_status = "EXPIRED"
            is_demo = 1 if self.chosen_plan_type == "Demo" else int(database.get_user_profile().get("is_demo_used", 0))
            
            update_data = {"subscription_status": "EXPIRED", "is_demo_used": is_demo}
            if self.chosen_plan_type == "Demo":
                update_data["demo_seconds_remaining"] = 0.0

            database.update_user_profile(update_data)
            
            if self.sm.has_screen('home_page'):
                home_screen = self.sm.get_screen('home_page')
                if hasattr(home_screen, 'update_tracker_display'):
                    home_screen.update_tracker_display(0.0)

            self.evict_if_locked("Access Expired", "Your active usage time has ended. Please choose a pass to continue!")

    def async_db_checkpoint(self, seconds_remaining):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_used = 1 if (seconds_remaining <= 0 and self.chosen_plan_type == "Demo") else int(database.get_user_profile().get("is_demo_used", 0))
        status = "EXPIRED" if seconds_remaining <= 0 else self.subscription_status
        
        checkpoint_data = {
            "free_seconds_remaining": seconds_remaining, 
            "last_active_timestamp": now_str, 
            "is_demo_used": is_used, 
            "subscription_status": status
        }
        
        if self.chosen_plan_type == "Demo":
            checkpoint_data["demo_seconds_remaining"] = seconds_remaining

        threading.Thread(
            target=database.update_user_profile,
            args=(checkpoint_data,),
            daemon=True
        ).start()

    def evict_if_locked(self, title, message):
        current_screen = self.sm.current
        protected_learning_screens = [
            'classroom_home', 'topic_list', 'content_viewer', 'topic_path',
            'isabi_level', 'isabi_subject', 'isabi_mcq', 'sabi_games_hub_page',
            'word_builder_page', 'math_balloon_pop_page', 'memory_flash_match_page',
            'sentence_catcher_page', 'shape_color_sorter_page', 'vocabulary_wordle_page',
            'speed_math_challenge_page', 'word_cross_page', 'word_search_page',
            'knowledge_hunt_game_page'
        ]
        
        if current_screen in protected_learning_screens:
            self.sm.current = 'home_page'
            if self.sm.has_screen('home_page'):
                home_screen = self.sm.get_screen('home_page')
                if hasattr(home_screen, 'show_subscription_access_dialog'):
                    home_screen.show_subscription_access_dialog(title, message)

    def on_pause(self):
        Clock.unschedule(self.global_metered_timer_pulse)
        self.async_db_checkpoint(self.rem_sec)
        return True

    def on_stop(self):
        Clock.unschedule(self.global_metered_timer_pulse)
        is_demo = 1 if (self.rem_sec <= 0 and self.chosen_plan_type == "Demo") else int(database.get_user_profile().get("is_demo_used", 0))
        
        stop_data = {
            "free_seconds_remaining": self.rem_sec,
            "last_active_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_demo_used": is_demo,
            "subscription_status": "EXPIRED" if self.rem_sec <= 0 else self.subscription_status
        }
        if self.chosen_plan_type == "Demo":
            stop_data["demo_seconds_remaining"] = self.rem_sec

        database.update_user_profile(stop_data)

    def on_hardware_back_press(self, window, key, *args):
        if key == 27:
            current = self.sm.current
            
            if current == 'settings_page':
                self.sm.current = 'home_page'
                return True
            elif current == 'plans_page':
                plans_screen = self.sm.get_screen('plans_page')
                if hasattr(plans_screen, 'from_settings') and plans_screen.from_settings:
                    self.sm.current = 'settings_page'
                else:
                    self.sm.current = 'home_page'
                return True
            elif current == 'content_viewer':
                self.sm.current = 'topic_path'
                return True
            elif current == 'topic_path':
                self.sm.current = 'topic_list'
                return True
            elif current == 'topic_list':
                self.sm.current = 'classroom_home'
                return True
            elif current == 'classroom_home':
                self.sm.current = 'home_page'
                return True

        return False

if __name__ == '__main__':
    SabiLearnersApp().run()