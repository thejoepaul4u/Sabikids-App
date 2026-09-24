import random
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp


# --- RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    # Reduced base width divisor to dp(320) so small screens receive larger scale factor
    base_scale = Window.width / dp(320)
    return max(0.85, min(1.25, base_scale))


# 4 Dark Vibe Palette Colors in fixed repeating sequence
TOPIC_CARD_COLORS = [
    (0.05, 0.22, 0.38, 1),  # Dark Navy Blue
    (0.60, 0.20, 0.05, 1),  # Dark Orange
    (0.04, 0.22, 0.12, 1),  # Deep Forest Green
    (0.55, 0.42, 0.05, 1),  # Dark Yellow
]


class TopicCardButton(ButtonBehavior, BoxLayout):
    def __init__(self, title, subtitle, topic_data, bg_color=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = [dp(14), dp(12), dp(14), dp(12)]
        self.spacing = dp(6)
        self.topic_data = topic_data

        card_bg = bg_color if bg_color is not None else TOPIC_CARD_COLORS[0]

        with self.canvas.before:
            Color(*card_bg)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # Fallback values for text constraints
        self.display_title = title if title else "Untitled Topic"
        self.display_subtitle = subtitle if subtitle else "Tap to explore topic content"

        # Sharp, bold title label
        self.lbl_title = Label(
            text=f"[b]{self.display_title}[/b]",
            font_size='16sp',
            markup=True,
            halign='left',
            valign='top',
            size_hint_y=None
        )
        self.lbl_title.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)),
            texture_size=self._update_card_height
        )
        self.add_widget(self.lbl_title)

        # Crisp, bold subtext label
        self.lbl_sub = Label(
            text=f"[b]{self.display_subtitle}[/b]",
            font_size='12sp',
            markup=True,
            color=(0.92, 0.92, 0.92, 1),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        self.lbl_sub.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)),
            texture_size=self._update_card_height
        )
        self.add_widget(self.lbl_sub)

    def _update_card_height(self, *args):
        # Dynamically set label heights based on texture height to display full text without truncation
        self.lbl_title.height = max(dp(22), self.lbl_title.texture_size[1])
        self.lbl_sub.height = max(dp(18), self.lbl_sub.texture_size[1])
        
        # Calculate total height ensuring content fits within card bounds
        total_content = self.lbl_title.height + self.lbl_sub.height + self.padding[1] + self.padding[3] + self.spacing
        self.height = max(dp(80), total_content)

    def apply_scale(self, scale):
        # Update text size dynamically on window resize
        title_font_pt = int(17 * scale)
        sub_font_pt = int(12.5 * scale)

        self.lbl_title.font_size = f"{title_font_pt}sp"
        self.lbl_sub.font_size = f"{sub_font_pt}sp"

        # Force texture recalculation to avoid blurriness and immediately resize container
        self._update_card_height()

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class TopicListScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'topic_list')
        super().__init__(**kwargs)

        self.subject_data = {}
        self.main_container = FloatLayout()

        # --- RESPONSIVE NAVBAR ---
        self.navbar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(2), dp(4)],
            spacing=dp(2),
            pos_hint={'top': 1}
        )

        self.back_btn = Button(
            text="Subjects",
            font_size='13sp',
            bold=True,
            size_hint=(None, None),
            size=(dp(85), dp(36)),
            pos_hint={'center_y': 0.5},
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal='',
            halign='center',
            valign='middle'
        )
        self.back_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(2)), None)))
        self.back_btn.bind(on_release=self.go_back)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners[/color]",
            font_size='16sp',
            bold=True,
            markup=True,
            size_hint=(1, 1),
            halign='center',
            valign='middle'
        )
        self.brand_title.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(2)), None)))
        self.navbar.add_widget(self.brand_title)

        # Right spacer to keep brand title centered
        self.nav_spacer = Label(size_hint=(None, None), size=(dp(85), dp(36)))
        self.navbar.add_widget(self.nav_spacer)

        self.main_container.add_widget(self.navbar)

        # --- RESPONSIVE SCROLLVIEW & CONTENT CONTAINER ---
        self.scroll_view = ScrollView(
            size_hint=(1, None),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )

        self.layout = BoxLayout(
            orientation='vertical',
            spacing=dp(12),
            padding=[dp(10), dp(10), dp(10), dp(15)],
            size_hint=(1, None)
        )
        self.layout.bind(minimum_height=self.layout.setter('height'))

        # Subject Title Header Label
        self.subject_title_label = Label(
            text="[size=22sp][b]Subject Name[/b][/size]",
            markup=True,
            font_size='20sp',
            halign='left',
            valign='middle',
            size_hint_y=None
        )
        self.subject_title_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)),
            texture_size=lambda inst, val: setattr(inst, 'height', max(dp(34), val[1] + dp(4)))
        )
        self.layout.add_widget(self.subject_title_label)

        # Sub Header Note Label
        self.sub_header = Label(
            text="Select a topic to start learning:",
            font_size='14sp',
            bold=True,
            color=(0.90, 0.90, 0.90, 1),
            halign='left',
            valign='middle',
            size_hint_y=None
        )
        self.sub_header.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)),
            texture_size=lambda inst, val: setattr(inst, 'height', max(dp(22), val[1] + dp(2)))
        )
        self.layout.add_widget(self.sub_header)

        # --- STRICT SINGLE-COLUMN VERTICAL GRID ---
        self.topics_grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
        self.topics_grid.bind(minimum_height=self.topics_grid.setter('height'))
        self.layout.add_widget(self.topics_grid)

        self.scroll_view.add_widget(self.layout)
        self.main_container.add_widget(self.scroll_view)
        self.add_widget(self.main_container)

        # --- RESPONSIVE WINDOW RESIZE BINDING ---
        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _update_scroll_bounds(self, *args):
        fixed_header_height = self.navbar.height
        top_offset = fixed_header_height + dp(4)
        self.scroll_view.y = 0
        self.scroll_view.height = max(dp(80), Window.height - top_offset)

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()
        self._update_scroll_bounds()

        # ALWAYS keep 1 single column across ALL screen sizes (Desktop, Tablet, Mobile)
        self.topics_grid.cols = 1

        # Navbar responsiveness
        if Window.width < dp(360):
            btn_w = dp(55 * scale)
            self.back_btn.text = "Subjects"
            self.back_btn.font_size = f"{int(11 * scale)}sp"
            self.brand_title.font_size = f"{int(18 * scale)}sp"
        else:
            btn_w = dp(75 * scale)
            self.back_btn.text = "Subjects"
            self.back_btn.font_size = f"{int(13 * scale)}sp"
            self.brand_title.font_size = f"{int(20 * scale)}sp"

        nav_h = dp(50 * scale)
        self.navbar.height = nav_h
        btn_h = dp(38 * scale)
        self.back_btn.size = (btn_w, btn_h)
        self.nav_spacer.size = (btn_w, btn_h)

        # Page text scaling
        self.subject_title_label.font_size = f"{int(20 * scale)}sp"
        self.sub_header.font_size = f"{int(14 * scale)}sp"

        # Responsive layout padding
        if Window.width >= dp(768):
            side_padding = max(dp(30), (Window.width - dp(850)) / 2)
            self.layout.padding = [side_padding, dp(16), side_padding, dp(24)]
            self.layout.spacing = dp(14)
        else:
            side_pad = max(dp(8), Window.width * 0.03)
            self.layout.padding = [side_pad, dp(10), side_pad, dp(16)]
            self.layout.spacing = dp(12)

        # Instantly scale and update all active topic cards dynamically
        for child in self.topics_grid.children:
            if isinstance(child, TopicCardButton):
                child.apply_scale(scale)

    def on_pre_enter(self):
        self._apply_responsive_structure()

        self.topics_grid.clear_widgets()

        # Dynamic navbar branding
        selected_class_id = getattr(self.manager, 'selected_class_id', '') or ''
        cid = selected_class_id.lower()

        if any(keyword in cid for keyword in ["junior", "senior", "jss", "sss", "ss"]):
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Students[/color]"
        else:
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Pupils[/color]"

        if hasattr(self.manager, 'selected_subject_data'):
            self.subject_data = getattr(self.manager, 'selected_subject_data', {}) or {}

        subject_title = self.subject_data.get("title", "Subject Topics")
        self.subject_title_label.text = f"[size=22sp][b]{subject_title}[/b][/size]"

        topics = self.subject_data.get("topics", [])

        if not topics:
            no_topics_lbl = Label(
                text="[color=888888][b]No topics added yet for this subject.\nDownload/Update topics.[/b][/color]",
                markup=True,
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(80)
            )
            no_topics_lbl.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
            self.topics_grid.add_widget(no_topics_lbl)
            return

        for idx, topic in enumerate(topics):
            selected_color = TOPIC_CARD_COLORS[idx % len(TOPIC_CARD_COLORS)]
            btn = TopicCardButton(
                title=topic.get("title", "Untitled Topic"),
                subtitle=topic.get("subtitle", ""),
                topic_data=topic,
                bg_color=selected_color
            )
            btn.bind(on_release=self.on_topic_selected)
            self.topics_grid.add_widget(btn)

        self._apply_responsive_structure()

    def on_topic_selected(self, instance):
        topic_data = instance.topic_data
        topic_id = topic_data.get('topic_id')
        print(f"[TOPICS]: Selected Topic -> {topic_data.get('title')}")

        if self.manager:
            self.manager.selected_topic_data = topic_data
            self.manager.selected_topic_id = topic_id

        class_id = getattr(self.manager, 'selected_class_id', None)
        subject_id = getattr(self.manager, 'selected_subject_id', None)

        if self.manager and self.manager.has_screen('topic_path'):
            path_screen = self.manager.get_screen('topic_path')
            path_screen.set_topic_context(class_id, subject_id, topic_id, topic_data.get('title'))
            self.manager.current = 'topic_path'

    def go_back(self, instance):
        if self.manager and self.manager.has_screen('classroom_home'):
            self.manager.current = 'classroom_home'