from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Line, RoundedRectangle, InstructionGroup, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from utils.curriculum_manager import CurriculumManager
from utils.tts_engine import TTSEngine


# Exact Color Definitions matching the visual palette theme
COLOR_GREEN = (0.04, 0.22, 0.12, 1)      # Deep Forest Green (Notes)
COLOR_ORANGE = (0.60, 0.20, 0.05, 1)     # Dark Orange (MCQ / Activity)
COLOR_YELLOW = (0.55, 0.42, 0.05, 1)     # Dark Yellow (Fill Gaps)
COLOR_BLUE = (0.05, 0.22, 0.38, 1)       # Dark Navy Blue (Theory)
COLOR_WHITE = (0.92, 0.92, 0.95, 1)      # Soft Dark Vibe White (Challenge)


# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    base_scale = Window.width / dp(400)
    return max(0.85, min(1.25, base_scale))


class TopicPathScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.class_id = None
        self.subject_id = None
        self.topic_id = None
        self.node_widgets = []
        self.nodes = []

        self.lines_group = InstructionGroup()
        
        # Base Root Container
        self.main_container = FloatLayout()

        # 1. TOP NAVBAR
        self.navbar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(4), dp(4)],
            spacing=dp(4),
            pos_hint={'top': 1}
        )
        
        with self.navbar.canvas.before:
            Color(0.08, 0.12, 0.22, 1)
            self.nav_bg = RoundedRectangle(pos=self.navbar.pos, size=self.navbar.size)
        self.navbar.bind(pos=self._update_nav_bg, size=self._update_nav_bg)

        self.back_btn = Button(
            text="Topics",
            font_size='12sp', bold=True,
            size_hint=(None, None),
            size=(dp(55), dp(34)),
            pos_hint={'center_y': 0.5},
            background_normal='', background_color=(0.7, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            halign='center', valign='middle'
        )
        self.back_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))
        self.back_btn.bind(on_release=self.go_back)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners[/color]",
            markup=True,
            font_size='15sp',
            bold=True,
            size_hint=(1, 1),
            halign='center',
            valign='middle'
        )
        self.brand_title.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(2)), None)))
        self.navbar.add_widget(self.brand_title)

        self.nav_spacer = Label(size_hint=(None, None), size=(dp(55), dp(34)))
        self.navbar.add_widget(self.nav_spacer)

        # 2. SCROLLABLE STAGE TREE PATH
        self.scroll = ScrollView(
            size_hint=(1, None),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )

        self.scroll_layout = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            padding=[dp(10), dp(12), dp(10), dp(20)],
            spacing=dp(12)
        )
        self.scroll_layout.bind(minimum_height=self.scroll_layout.setter('height'))

        self.header_label = Label(
            text="Topic Title",
            font_size='16sp',
            bold=True,
            halign='center',
            valign='middle',
            color=(1, 1, 1, 1),
            size_hint_y=None
        )
        self.header_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        self.header_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(28), value[1] + dp(4))))
        self.scroll_layout.add_widget(self.header_label)

        self.path_container = RelativeLayout(
            size_hint=(1, None),
            height=dp(500)
        )
        self.path_container.canvas.before.add(self.lines_group)
        self.path_container.bind(size=self._on_container_resize, pos=self._on_container_resize)
        self.scroll_layout.add_widget(self.path_container)

        self.scroll.add_widget(self.scroll_layout)

        self.main_container.add_widget(self.scroll)
        self.main_container.add_widget(self.navbar)
        self.add_widget(self.main_container)

        # Dynamic Window Resize Binding
        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _update_scroll_bounds(self, *args):
        fixed_header_height = self.navbar.height
        top_offset = fixed_header_height + dp(4)
        
        self.scroll.y = 0
        self.scroll.height = max(dp(80), Window.height - top_offset)

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()
        self._update_scroll_bounds()

        if Window.width < dp(320):
            btn_w = dp(42 * scale)
            self.brand_title.font_size = f"{int(18 * scale)}sp"
            self.back_btn.font_size = f"{int(10 * scale)}sp"
            self.back_btn.text = "Topics"
        else:
            btn_w = dp(65 * scale)
            self.brand_title.font_size = f"{int(20 * scale)}sp"
            self.back_btn.font_size = f"{int(12 * scale)}sp"
            self.back_btn.text = "Topics"

        nav_h = dp(50 * scale)
        self.navbar.height = nav_h
        btn_h = dp(36 * scale)
        self.back_btn.size = (btn_w, btn_h)
        self.nav_spacer.size = (btn_w, btn_h)

        self.header_label.font_size = f"{int(18 * scale)}sp"

        if Window.width >= dp(768):
            side_padding = max(dp(30), (Window.width - dp(850)) / 2)
            self.scroll_layout.padding = [side_padding, dp(16), side_padding, dp(24)]
            self.scroll_layout.spacing = dp(14)
        else:
            side_pad = max(dp(6), Window.width * 0.03)
            self.scroll_layout.padding = [side_pad, dp(8), side_pad, dp(16)]
            self.scroll_layout.spacing = dp(10)

        self._relayout_path()

    def on_pre_enter(self, *args):
        """Halts voice audio immediately when navigating to topic path screen."""
        TTSEngine.stop_immediately()
        selected_class_id = getattr(self.manager, 'selected_class_id', '') or ''
        cid = selected_class_id.lower()

        if any(keyword in cid for keyword in ["junior", "senior", "jss", "sss", "ss"]):
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Students[/color]"
        else:
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Pupils[/color]"

    def _update_nav_bg(self, instance, value):
        self.nav_bg.pos = instance.pos
        self.nav_bg.size = instance.size

    def set_topic_context(self, class_id, subject_id, topic_id, topic_title=None):
        self.class_id = class_id
        self.subject_id = subject_id
        self.topic_id = topic_id

        topic_data = CurriculumManager.get_topic_data(class_id, subject_id, topic_id)
        
        if not topic_data and hasattr(self, 'manager') and self.manager and hasattr(self.manager, 'selected_topic_data'):
            topic_data = getattr(self.manager, 'selected_topic_data', {})

        resolved_title = None
        if isinstance(topic_data, dict):
            resolved_title = topic_data.get("title") or topic_data.get("name") or topic_data.get("topic_name")

        if not resolved_title and topic_title:
            resolved_title = topic_title

        if not resolved_title and topic_id:
            resolved_title = str(topic_id)

        self.header_label.text = resolved_title if resolved_title else "Lesson"

        self.path_container.clear_widgets()
        self.node_widgets = []

        tier_id = CurriculumManager.get_tier_id_for_class(class_id)

        if tier_id == "pre_primary":
            self.nodes = [
                {"id": "notes", "title": "Stage 1", "sub": "Classroom", "type": "notes", "color": COLOR_GREEN},
                {"id": "activity", "title": "Stage 2", "sub": "Activities", "type": "identify_image", "color": COLOR_ORANGE}
            ]
            if isinstance(topic_data, dict) and topic_data.get("challenge"):
                self.nodes.append({
                    "id": "challenge", 
                    "title": "Stage 3", 
                    "sub": "Home Task", 
                    "type": "challenge", 
                    "color": COLOR_WHITE
                })
        else:
            self.nodes = [
                {"id": "notes", "title": "Stage 1", "sub": "Classroom", "type": "notes", "color": COLOR_GREEN},
                {"id": "mcq", "title": "Stage 2", "sub": "MCQ Quiz", "type": "mcq", "color": COLOR_ORANGE},
                {"id": "fill_blank", "title": "Stage 3", "sub": "Fill Gaps", "type": "fill_blank", "color": COLOR_YELLOW},
                {"id": "theory", "title": "Stage 4", "sub": "Theory", "type": "theory", "color": COLOR_BLUE},
                {"id": "quiz_all", "title": "Stage 5", "sub": "Challenge", "type": "all", "color": COLOR_WHITE}
            ]

        for index, node in enumerate(self.nodes):
            node_text_color = (0.1, 0.1, 0.1, 1) if node["color"] == COLOR_WHITE else (1, 1, 1, 1)

            btn = Button(
                text=str(index + 1),
                size_hint=(None, None),
                background_normal='',
                background_color=(0, 0, 0, 0),
                bold=True,
                color=node_text_color,
                halign='center', valign='middle'
            )
            
            with btn.canvas.before:
                Color(*node["color"])
                btn.circle_bg = Ellipse(pos=btn.pos, size=btn.size)
            
            btn.node_type = node["type"]
            btn.bind(on_release=self.open_node_content)
            btn.bind(pos=self._update_btn_circle, size=self._update_btn_circle)

            lbl = Label(
                text=node["sub"],
                size_hint=(None, None),
                bold=True,
                color=(1, 1, 1, 1),
                halign='center',
                valign='middle'
            )
            lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))
            
            with lbl.canvas.before:
                Color(0.12, 0.15, 0.22, 0.92)
                lbl.bg_rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(8)])
            lbl.bind(pos=self._update_lbl_bg, size=self._update_lbl_bg)

            self.path_container.add_widget(btn)
            self.path_container.add_widget(lbl)
            self.node_widgets.append({'btn': btn, 'lbl': lbl})

        self._apply_responsive_structure()

    def _update_btn_circle(self, instance, value):
        if hasattr(instance, 'circle_bg'):
            instance.circle_bg.pos = instance.pos
            instance.circle_bg.size = instance.size

    def _update_lbl_bg(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def _on_container_resize(self, *args):
        self._relayout_path()

    def _relayout_path(self, *args):
        if not self.node_widgets:
            return

        scale = get_responsive_scale()
        row_height = dp(130 * scale)
        node_dim = dp(75 * scale)
        
        # Dynamically resize path_container based on scale
        total_height = len(self.node_widgets) * row_height + dp(60)
        self.path_container.height = max(total_height, dp(420 * scale))

        container_w = self.path_container.width if self.path_container.width > 0 else dp(350)
        x_offsets = [0, dp(50 * scale), dp(80 * scale), dp(25 * scale), -dp(35 * scale)]

        for index, item in enumerate(self.node_widgets):
            btn = item['btn']
            lbl = item['lbl']

            # Dynamic resizing of node elements
            btn.size = (node_dim, node_dim)
            btn.font_size = f"{int(24 * scale)}sp"

            lbl.size = (dp(110 * scale), dp(26 * scale))
            lbl.font_size = f"{int(13 * scale)}sp"

            # Dynamic positioning
            offset_x = x_offsets[index % len(x_offsets)]
            center_x = (container_w / 2.0) + offset_x
            pos_y = self.path_container.height - ((index + 1) * row_height)

            btn.pos = (center_x - (btn.width / 2.0), pos_y)
            lbl.pos = (center_x - (lbl.width / 2.0), pos_y - dp(24 * scale))

        self._draw_connecting_lines()

    def _draw_connecting_lines(self, *args):
        self.lines_group.clear()

        if len(self.node_widgets) < 2:
            return

        self.lines_group.add(Color(0.4, 0.55, 0.75, 0.8))

        for i in range(len(self.node_widgets) - 1):
            w1 = self.node_widgets[i]['btn']
            w2 = self.node_widgets[i + 1]['btn']

            self.lines_group.add(
                Line(
                    points=[w1.center_x, w1.center_y, w2.center_x, w2.center_y],
                    width=3.5,
                    cap='round',
                    joint='round'
                )
            )

    def open_node_content(self, instance):
        TTSEngine.stop_immediately()
        content_screen = self.manager.get_screen('content_viewer')

        class_id = self.class_id or getattr(self.manager, 'selected_class_id', None)
        subject_id = self.subject_id or getattr(self.manager, 'selected_subject_id', None)
        topic_id = self.topic_id or getattr(self.manager, 'selected_topic_id', None)

        topic_data = CurriculumManager.get_topic_data(class_id, subject_id, topic_id)
        
        if not topic_data and hasattr(self, 'manager') and self.manager and hasattr(self.manager, 'selected_topic_data'):
            topic_data = getattr(self.manager, 'selected_topic_data', {})

        topic_title = topic_data.get("title", "") if isinstance(topic_data, dict) else self.header_label.text

        content_screen.load_node_content(
            class_id=class_id,
            subject_id=subject_id,
            topic_id=topic_id,
            node_type=instance.node_type,
            topic_title=topic_title
        )
        self.manager.current = 'content_viewer'

    def go_back(self, instance=None):
        TTSEngine.stop_immediately()
        self.manager.current = 'topic_list'