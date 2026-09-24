import os
from kivy.animation import Animation
from kivy.core.window import Window  # Tool to check keyboard keys
from kivy.graphics import Color, RoundedRectangle, Triangle
from kivy.metrics import dp
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from utils.app_update_popup import AppUpdatePopup
from utils.app_update_curriculum_manager import AppUpdateManager

SETTINGS_FILE = "sabikids_settings.json"


# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    base_scale = Window.width / dp(360)
    return max(0.85, min(1.30, base_scale))


class ColorfulLabel(Label):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True


class HandDrawnSpeechBubble(FloatLayout):
    bubble_color = ListProperty([0.05, 0.35, 0.85, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(160), dp(85))

        with self.canvas.before:
            self.canvas_color = Color(rgba=self.bubble_color)
            self.rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(15)]
            )
            self.triangle = Triangle()

        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.bind(bubble_color=self.update_color)

        self.bubble_text = Label(
            text="Tap anywhere\nto continue",
            font_size="13sp",
            bold=True,
            halign="center",
            valign="middle",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.bubble_text.bind(
            width=lambda inst, val: setattr(
                inst, "text_size", (max(dp(10), val - dp(4)), None)
            )
        )
        self.add_widget(self.bubble_text)

    def update_canvas(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        x, y = self.pos
        w, h = self.size
        self.triangle.points = [
            x + w - dp(45),
            y,
            x + w - dp(30),
            y - dp(12),
            x + w - dp(25),
            y,
        ]

    def update_color(self, *args):
        self.canvas_color.rgba = self.bubble_color

    def apply_scale(self, scale):
        self.size = (dp(160 * scale), dp(85 * scale))
        self.bubble_text.font_size = f"{int(13 * scale)}sp"


class ReceivingPageScreen(Screen):

    def on_enter(self):
        self.trigger_animations()

        # Asynchronously check GitHub for app updates when entering screen
        update_manager = AppUpdateManager()
        update_manager.check_for_updates(self.handle_update_found)

    def handle_update_found(self, new_version, changelog, is_mandatory=False):
        # Trigger update popup when a newer version tag is found on GitHub
        AppUpdatePopup.show(new_version, changelog, is_mandatory)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.main_layout = FloatLayout()

        background_tap_trigger = Button(
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0),
            background_normal="",
        )
        background_tap_trigger.bind(on_release=self.go_next)
        self.main_layout.add_widget(background_tap_trigger)

        self.custom_bubble = HandDrawnSpeechBubble(
            pos_hint={"top": 0.95, "right": 0.95}
        )
        self.main_layout.add_widget(self.custom_bubble)

        # Center Branding Container
        self.title_box = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            spacing=dp(2),
            opacity=0,
        )

        self.app_title = ColorfulLabel(
            text=(
                "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color]"
                " [color=ffffff]Learners[/color]"
            ),
            font_size="54sp",
            bold=True,
            halign="center",
            valign="middle",
            size_hint_y=None,
        )
        self.app_title.bind(
            width=lambda inst, val: setattr(
                inst, "text_size", (max(dp(20), val - dp(8)), None)
            ),
            texture_size=lambda inst, val: setattr(
                inst, "height", max(dp(40), val[1] + dp(4))
            ),
        )

        self.slogan_label = Label(
            text="   Mastery Beyond the Physical Classroom.",
            font_size="20sp",
            italic=True,
            bold=True,
            color=(0.16, 0.50, 0.28, 1),
            halign="center",
            valign="middle",
            size_hint_y=None,
        )
        self.slogan_label.bind(
            width=lambda inst, val: setattr(
                inst, "text_size", (max(dp(20), val - dp(8)), None)
            ),
            texture_size=lambda inst, val: setattr(
                inst, "height", max(dp(24), val[1] + dp(4))
            ),
        )

        self.title_box.add_widget(self.app_title)
        self.title_box.add_widget(self.slogan_label)
        self.title_box.bind(minimum_height=self.title_box.setter("height"))

        self.main_layout.add_widget(self.title_box)

        # Bottom Audience Tag
        self.subtitle_label = Label(
            text="FOR KIDS & TEENS",
            font_size="13sp",
            bold=True,
            color=(1, 1, 1, 0.45),
            size_hint=(1, None),
            height=dp(30),
            pos_hint={"center_x": 0.5, "y": 0.05},
            halign="center",
            valign="middle",
        )
        self.subtitle_label.bind(
            width=lambda inst, val: setattr(
                inst, "text_size", (max(dp(20), val - dp(4)), None)
            )
        )
        self.main_layout.add_widget(self.subtitle_label)

        self.add_widget(self.main_layout)

        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()

        # Responsive speech bubble sizing
        self.custom_bubble.apply_scale(scale)

        # Responsive title container sizing
        max_title_w = max(dp(280), Window.width * 0.90)
        self.title_box.width = max_title_w

        # Scaled typography
        title_size = int(54 * scale)
        slogan_size = int(20 * scale)
        subtitle_size = int(13 * scale)

        if Window.width < dp(340):
            title_size = int(38 * scale)
            slogan_size = int(15 * scale)

        self.app_title.font_size = f"{title_size}sp"
        self.slogan_label.font_size = f"{slogan_size}sp"
        self.subtitle_label.font_size = f"{subtitle_size}sp"
        self.subtitle_label.height = dp(30 * scale)

    def trigger_animations(self):
        Animation(opacity=1.0, duration=2.0, t="in_quad").start(self.title_box)
        bubble_loop = (
            Animation(bubble_color=[0.90, 0.49, 0.13, 1], duration=2.5, t="in_out_sine")
            + Animation(bubble_color=[0.10, 0.60, 0.60, 1], duration=2.5, t="in_out_sine")
            + Animation(bubble_color=[0.05, 0.35, 0.85, 1], duration=2.5, t="in_out_sine")
        )
        bubble_loop.repeat = True
        bubble_loop.start(self.custom_bubble)

    def go_next(self, instance):
        # 🌟 MASTER DEVELOPER BACKDOOR BYPASS SHIFT-KEY LINK
        if "shift" in Window.modifiers:
            self.manager.current = "auth_page"
            return

        # Core Relational Account Verification Routing Switch
        try:
            import database

            profile = database.get_user_profile()

            # If the database profile is completely empty, start them fresh at signup
            if not profile:
                self.manager.current = "auth_page"
                return

            # Read the exact step saved in SQLite (defaults to auth_page for brand new kids)
            saved_milestone = profile.get("registration_step", "auth_page")

            print(
                f"[SPLASH GATE]: Routing returning session straight to saved step: {saved_milestone}"
            )
            self.manager.current = saved_milestone

        except Exception as e:
            print(f"[SPLASH ENGINE ERROR]: Database state route mapping failed: {e}")
            self.manager.current = "auth_page"  # Safe safety fallback layout