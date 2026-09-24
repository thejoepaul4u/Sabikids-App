from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.core.window import Window


class UpdateNotificationPopup(Popup):
    def __init__(self, on_confirm_callback=None, update_type="class", game_title=None, **kwargs):
        super().__init__(**kwargs)
        self.auto_dismiss = False
        self.on_confirm_callback = on_confirm_callback

        # 1. Dynamic Responsive Popup Sizing
        # Use wider width on mobile and adapt height dynamically based on screen width
        if Window.width < dp(400):
            self.size_hint = (0.9, 0.48)
        elif Window.width < dp(600):
            self.size_hint = (0.85, 0.42)
        else:
            self.size_hint = (0.6, 0.38)

        # Scale fonts smoothly based on window size
        scale = max(0.95, min(1.2, Window.width / dp(400)))
        
        title_font_size = f"{int(15 * scale)}sp"
        body_font_size = f"{int(13.5 * scale)}sp"
        btn_font_size = f"{int(13.5 * scale)}sp"

        self.title_size = title_font_size

        if update_type == "global":
            self.title = "Syllabus Update Available!"
            message_text = "New syllabus structure or general level updates are available.\n\nWould you like to download them now?"
        elif update_type == "isabi":
            self.title = "Challenge Quiz Update Available!"
            message_text = "New quiz subjects or questions are available.\n\nWould you like to download them now?"
        elif update_type == "sabi_games":
            self.title = f"{game_title or 'Game'} Update Available!"
            message_text = f"New game content updates are available for {game_title or 'this game'}.\n\nWould you like to download them now?"
        else:
            self.title = "Class Content Update Available!"
            message_text = "New subjects, topics, or notes update are available for this class.\n\nWould you like to download them now?"

        # Main Layout Container
        main_layout = BoxLayout(
            orientation='vertical',
            padding=[dp(12), dp(12), dp(12), dp(12)],
            spacing=dp(10)
        )

        # 2. Scrollable Body Area to prevent text overflow
        scroll_view = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True
        )

        msg_label = Label(
            text=message_text,
            halign='center',
            valign='middle',
            font_size=body_font_size,
            bold=True,
            color=(0.95, 0.95, 0.98, 1),
            size_hint_y=None
        )
        
        # Ensure text wraps seamlessly to the scroll area width
        msg_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(8)), None))
        )
        msg_label.bind(
            texture_size=lambda inst, val: setattr(inst, 'height', max(dp(40), val[1] + dp(10)))
        )
        
        scroll_view.add_widget(msg_label)
        main_layout.add_widget(scroll_view)

        # 3. Responsive Action Button Bar
        # Switches to vertical layout on very small screens so text never gets squished
        is_narrow = Window.width < dp(340)
        
        btn_box = BoxLayout(
            orientation='vertical' if is_narrow else 'horizontal',
            spacing=dp(8),
            size_hint_y=None,
            height=dp(84) if is_narrow else dp(44)
        )

        later_btn = Button(
            text="Later",
            font_size=btn_font_size,
            bold=True,
            background_color=(0.4, 0.45, 0.5, 1),
            background_normal='',
            halign='center',
            valign='middle'
        )
        later_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(4)), None)))
        later_btn.bind(on_release=self.dismiss)

        update_btn = Button(
            text="Update Now",
            font_size=btn_font_size,
            bold=True,
            background_color=(0.15, 0.65, 0.36, 1),
            background_normal='',
            halign='center',
            valign='middle'
        )
        update_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(4)), None)))
        update_btn.bind(on_release=self.on_update_pressed)

        btn_box.add_widget(later_btn)
        btn_box.add_widget(update_btn)

        main_layout.add_widget(btn_box)
        self.content = main_layout

    def on_update_pressed(self, instance):
        if self.on_confirm_callback:
            self.on_confirm_callback()
        self.dismiss()