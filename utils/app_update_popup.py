from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView


class AppUpdatePopup:

    @staticmethod
    def show(new_version, changelog, is_mandatory=False):
        """Schedules popup presentation on the main thread safely."""

        def _build_and_open(dt):
            # Dynamic Responsive Popup Sizing (giving it enough breathing room)
            if Window.width < dp(400):
                popup_size_hint = (0.9, 0.55)
            elif Window.width < dp(600):
                popup_size_hint = (0.85, 0.5)
            else:
                popup_size_hint = (0.55, 0.45)

            scale = max(0.95, min(1.2, Window.width / dp(400)))

            title_font_size = f"{int(15 * scale)}sp"
            body_font_size = f"{int(13 * scale)}sp"

            # Main Layout Container
            layout = BoxLayout(
                orientation="vertical",
                padding=[dp(12), dp(12), dp(12), dp(12)],
                spacing=dp(10),
            )

            # Message Content
            if is_mandatory:
                message_text = (
                    f"A new version ({new_version}) of Sabi Learners is available!\n\n"
                    f"What's New:\n{changelog}\n\n"
                    f"Please update to continue learning."
                )
            else:
                message_text = (
                    f"A new version ({new_version}) of Sabi Learners is available!\n\n"
                    f"What's New:\n{changelog}"
                )

            # ScrollView safely wraps the label so long changelogs never collide
            scroll_view = ScrollView(
                size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True
            )

            info_label = Label(
                text=message_text,
                halign="center",
                valign="middle",
                font_size=body_font_size,
                bold=True,
                color=(0.95, 0.95, 0.98, 1),
                size_hint_y=None,  # Crucial for letting the height expand with text
            )

            # Automatically adjust text width and compute height based on text amount
            info_label.bind(
                width=lambda inst, val: setattr(
                    inst, "text_size", (max(dp(10), val - dp(16)), None)
                )
            )
            info_label.bind(
                texture_size=lambda inst, val: setattr(
                    inst, "height", max(dp(80), val[1] + dp(20))
                )
            )

            scroll_view.add_widget(info_label)
            layout.add_widget(scroll_view)

            popup = Popup(
                title="Update Available " if is_mandatory else "Update Available",
                content=layout,
                size_hint=popup_size_hint,
                title_size=title_font_size,
                auto_dismiss=not is_mandatory,  # True for optional, False for mandatory
            )

            popup.open()

        Clock.schedule_once(_build_and_open, 0)