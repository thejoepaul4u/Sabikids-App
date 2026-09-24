import os
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
from kivy.core.window import Window
from kivy.clock import Clock

from utils.curriculum_manager import CurriculumManager
from utils.update_popup import UpdateNotificationPopup


# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    base_scale = Window.width / dp(380)
    # Increased floor to 0.95 so small screen fonts remain readable and bold
    return max(0.95, min(1.30, base_scale))


# 4 Dark Vibe Palette Colors in exact requested sequence
SUBJECT_CARD_COLORS = [
    (0.55, 0.42, 0.05, 1),  # Dark Yellow
    (0.04, 0.22, 0.12, 1),  # Deep Forest Green
    (0.60, 0.20, 0.05, 1),  # Dark Orange
    (0.05, 0.22, 0.38, 1),  # Dark Navy Blue
]


class MainTierCard(ButtonBehavior, BoxLayout):
    def __init__(self, title, subtitle, bg_color, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(80)
        self.padding = [dp(14), dp(10), dp(14), dp(10)]
        self.spacing = dp(8)
        self.is_expanded = False
        self.bg_color = bg_color

        with self.canvas.before:
            self.rect_color = Color(*bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        text_box = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_x=0.85)
        
        self.title_label = Label(
            text=f"[b]{title}[/b]",
            font_size='16sp',
            markup=True,
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle'
        )
        self.title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        text_box.add_widget(self.title_label)

        self.sub_label = Label(
            text=f"[b]{subtitle}[/b]",
            font_size='13sp',
            markup=True,
            color=(1, 1, 1, 0.98),
            halign='left',
            valign='top'
        )
        self.sub_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        text_box.add_widget(self.sub_label)

        self.add_widget(text_box)

        self.arrow_label = Label(
            text="v",
            font_size='16sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_x=0.15,
            halign='center',
            valign='middle'
        )
        self.arrow_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(2)), None)))
        self.add_widget(self.arrow_label)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def set_expanded_state(self, expanded):
        self.is_expanded = expanded
        self.arrow_label.text = "^" if expanded else "v"

    # Prevents press tinting on touch
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.rect_color.rgba = self.bg_color
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self.rect_color.rgba = self.bg_color
        return super().on_touch_up(touch)


class DynamicItemButton(ButtonBehavior, BoxLayout):
    def __init__(self, title, subtitle, item_id, item_data=None, bg_color=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(70)
        self.padding = [dp(14), dp(8), dp(14), dp(8)]
        self.spacing = dp(2)
        self.item_id = item_id
        self.item_title = title
        self.item_data = item_data or {}
        self.bg_color = bg_color if bg_color else (0.20, 0.23, 0.28, 1)

        with self.canvas.before:
            self.rect_color = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.lbl_title = Label(
            text=f"[b]{title}[/b]",
            font_size='15sp',
            markup=True,
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.add_widget(self.lbl_title)

        self.lbl_sub = Label(
            text=f"[b]{subtitle}[/b]",
            font_size='12sp',
            markup=True,
            color=(0.95, 0.95, 0.98, 1),
            halign='left',
            valign='top'
        )
        self.lbl_sub.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.add_widget(self.lbl_sub)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    # Prevents press tinting on touch
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.rect_color.rgba = self.bg_color
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self.rect_color.rgba = self.bg_color
        return super().on_touch_up(touch)


class ClassroomHomeScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'classroom_home')
        super().__init__(**kwargs)
        
        self.selected_class_id = None
        self.selected_class_title = None
        self.expanded_tier = None
        self._ticker_event = None
        
        self.main_container = FloatLayout()

        # Top Bar Navigation
        self.navbar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(4), dp(4)],
            spacing=dp(2),
            pos_hint={'top': 1}
        )
        
        self.back_btn = Button(
            text="Home",
            font_size='12sp',
            bold=True,
            size_hint=(None, None),
            size=(dp(70), dp(34)),
            pos_hint={'center_y': 0.5},
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal='',
            halign='center', valign='middle'
        )
        self.back_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))
        self.back_btn.bind(on_release=self.handle_back_button)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=ffffff]My[/color] [color=26a65b]C[/color][color=e67e22]l[/color][color=f1c40f]a[/color][color=2980b9]s[/color][color=26a65b]s[/color][color=ffffff]room[/color]",
            font_size='15sp', bold=True, markup=True,
            size_hint=(1, 1),
            halign='center', valign='middle'
        )
        self.brand_title.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(2)), None)))
        self.navbar.add_widget(self.brand_title)

        self.nav_spacer = Label(size_hint=(None, None), size=(dp(70), dp(34)))
        self.navbar.add_widget(self.nav_spacer)
        
        self.scroll = ScrollView(
            size_hint=(1, None),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )

        self.content = BoxLayout(
            orientation='vertical',
            spacing=dp(12),
            padding=[dp(10), dp(10), dp(10), dp(20)],
            size_hint=(1, None)
        )
        self.content.bind(minimum_height=self.content.setter('height'))

        # --- RECURRING INTERNET CONNECTIVITY REMINDER BANNER ---
        self.notice_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(36),
            padding=[dp(10), dp(6)],
            spacing=dp(6)
        )
        with self.notice_box.canvas.before:
            Color(0.12, 0.16, 0.22, 1)
            self.notice_rect = RoundedRectangle(pos=self.notice_box.pos, size=self.notice_box.size, radius=[dp(6)])
        self.notice_box.bind(
            pos=lambda inst, val: setattr(self.notice_rect, 'pos', val),
            size=lambda inst, val: setattr(self.notice_rect, 'size', val)
        )

        self.notice_messages = [
            "Connect to the internet periodically to check for new lessons and updates.",
            "Curriculum are designed following official NERDC educational guidelines",
            "Notes & Contents are AI-Powered and Human Creativity & Compilation.",
        ]
        self.notice_index = 0

        self.notice_label = Label(
            text=f"[color=f1c40f][b]Note:[/b][/color] [color=dddddd]{self.notice_messages[0]}[/color]",
            markup=True,
            font_size='12sp',
            halign='left',
            valign='middle',
            size_hint=(1, None)
        )
        self.notice_label.bind(texture_size=self._on_notice_label_texture)
        self.notice_box.bind(width=self._update_notice_text_width)
        self.notice_box.add_widget(self.notice_label)
        self.content.add_widget(self.notice_box)

        self.welcome_label = Label(
            text="[size=20sp][b]Select Education Level:[/b][/size]",
            markup=True,
            font_size='15sp',
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(30)
        )
        self.welcome_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.content.add_widget(self.welcome_label)

        # ENSURE SINGLE COLUMN (COLUMNS = 1 ALWAYS)
        self.cards_grid = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.cards_grid.bind(minimum_height=self.cards_grid.setter('height'))
        self.content.add_widget(self.cards_grid)

        self.scroll.add_widget(self.content)
        self.main_container.add_widget(self.scroll)
        self.main_container.add_widget(self.navbar)
        self.add_widget(self.main_container)

        # --- RESPONSIVE BOUNDING BINDINGS ---
        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _update_notice_text_width(self, instance, val):
        self.notice_label.text_size = (max(dp(20), val - dp(20)), None)

    def _on_notice_label_texture(self, instance, val):
        self.notice_label.height = val[1]
        self.notice_box.height = max(dp(36), val[1] + dp(12))

    def _rotate_notice_text(self, dt):
        self.notice_index = (self.notice_index + 1) % len(self.notice_messages)
        msg = self.notice_messages[self.notice_index]
        self.notice_label.text = f"[color=f1c40f][b]Note:[/b][/color] [color=dddddd]{msg}[/color]"

    def _update_scroll_bounds(self, *args):
        fixed_header_height = self.navbar.height
        top_offset = fixed_header_height + dp(4)
        self.scroll.y = 0
        self.scroll.height = max(dp(80), Window.height - top_offset)

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()
        self._update_scroll_bounds()

        # Dynamic Navbar Sizing
        nav_h = dp(46 * scale)
        self.navbar.height = nav_h

        # Dynamic Notice Banner Sizing
        self.notice_label.font_size = f"{int(12 * scale)}sp"
        self._update_notice_text_width(self.notice_box, self.notice_box.width)

        # Mobile vs Standard layout configurations
        if Window.width < dp(320):
            btn_w = dp(55 * scale)
            self.brand_title.font_size = f"{int(18 * scale)}sp"
            self.back_btn.font_size = f"{int(11 * scale)}sp"
        else:
            btn_w = dp(70 * scale)
            self.brand_title.font_size = f"{int(18 * scale)}sp"
            self.back_btn.font_size = f"{int(12 * scale)}sp"

        # Back Button & Spacer Dimensions
        btn_h = dp(32 * scale)
        self.back_btn.size = (btn_w, btn_h)
        self.nav_spacer.size = (btn_w, btn_h)

        # Welcome Text Font Sizing
        self.welcome_label.font_size = f"{int(16 * scale)}sp"

        # Content Padding and Spacing
        if Window.width >= dp(768):
            side_padding = max(dp(20), (Window.width - dp(750)) / 2)
            self.content.padding = [side_padding, dp(14), side_padding, dp(24)]
            self.content.spacing = dp(14)
        else:
            side_pad = max(dp(6), Window.width * 0.03)
            self.content.padding = [side_pad, dp(8), side_pad, dp(16)]
            self.content.spacing = dp(10)

        # --- DYNAMICALLY RESIZE EXISTING WIDGETS ON LIVE WINDOW RESIZE ---
        for child in self.cards_grid.children:
            if isinstance(child, MainTierCard):
                child.height = dp(75 * scale)
                child.title_label.font_size = f"{int(16 * scale)}sp"
                child.sub_label.font_size = f"{int(12.5 * scale)}sp"
                child.arrow_label.font_size = f"{int(16 * scale)}sp"
            elif isinstance(child, DynamicItemButton):
                child.height = dp(70 * scale)
                child.lbl_title.font_size = f"{int(15 * scale)}sp"
                child.lbl_sub.font_size = f"{int(12 * scale)}sp"
            elif isinstance(child, Label) and child != self.welcome_label:
                child.font_size = f"{int(18 * scale)}sp"
                child.height = dp(40 * scale)
            elif isinstance(child, BoxLayout):  # Dropdown container for tiers
                for sub_child in child.children:
                    if isinstance(sub_child, DynamicItemButton):
                        sub_child.height = dp(62 * scale)
                        sub_child.lbl_title.font_size = f"{int(14 * scale)}sp"
                        sub_child.lbl_sub.font_size = f"{int(11.5 * scale)}sp"

    def on_enter(self):
        if not self._ticker_event:
            self._ticker_event = Clock.schedule_interval(self._rotate_notice_text, 4.0)

    def on_leave(self):
        if self._ticker_event:
            self._ticker_event.cancel()
            self._ticker_event = None

    def on_pre_enter(self):
        CurriculumManager.reload_data()
    
        if self.selected_class_id:
            self.show_subject_selection_view()
        else:
            self.show_class_tier_view()
            CurriculumManager.check_global_update(
                on_update_found_callback=self.prompt_global_update
            )

    def show_class_tier_view(self):
        self.selected_class_id = None
        self.selected_class_title = None
        self.expanded_tier = None
        self.back_btn.text = "Home"
        self.welcome_label.text = "[size=20sp][b]Select Education Level:[/b][/size]"
        self.brand_title.text = "[color=ffffff]My[/color] [color=26a65b]C[/color][color=e67e22]l[/color][color=f1c40f]a[/color][color=2980b9]s[/color][color=26a65b]s[/color][color=ffffff]room[/color]"
        self.render_tiers()

    def render_tiers(self):
        scale = get_responsive_scale()
        self.cards_grid.clear_widgets()
        tiers = CurriculumManager.get_tiers()

        tier_colors = {
            "pre_primary": (0.04, 0.22, 0.12, 1),
            "primary": (0.60, 0.20, 0.05, 1),
            "junior_secondary": (0.55, 0.42, 0.05, 1),
            "senior_secondary": (0.05, 0.22, 0.38, 1)
        }

        for idx, tier in enumerate(tiers):
            tier_id = tier.get("tier_id", "")
            tier_title = tier.get("title", "")

            # --- INSERT SABI KIDS HEADER BEFORE PRE-PRIMARY ---
            if "pre" in tier_id.lower() or idx == 0:
                sabi_kids_header = Label(
                    text="[color=26a65b]  S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Pupils:[/color]",
                    font_size=f"{int(18 * scale)}sp",
                    bold=True,
                    markup=True,
                    size_hint_y=None,
                    height=dp(40 * scale),
                    halign='left',
                    valign='middle'
                )
                sabi_kids_header.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
                self.cards_grid.add_widget(sabi_kids_header)

            # --- INSERT SINGLE SABI TEENS HEADER BEFORE JUNIOR SECONDARY ---
            if "junior" in tier_title.lower() or "junior" in tier_id.lower():
                sabi_teens_header = Label(
                    text="[color=26a65b]  S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Students:[/color]",
                    font_size=f"{int(18 * scale)}sp",
                    bold=True,
                    markup=True,
                    size_hint_y=None,
                    height=dp(40 * scale),
                    halign='left',
                    valign='middle'
                )
                sabi_teens_header.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
                self.cards_grid.add_widget(sabi_teens_header)

            if "pre" in tier_id.lower():
                solid_color = tier_colors["pre_primary"]
            elif "junior" in tier_id.lower() or "jss" in tier_id.lower():
                solid_color = tier_colors["junior_secondary"]
            elif "senior" in tier_title.lower() or "senior" in tier_id.lower():
                solid_color = tier_colors["senior_secondary"]
            elif "primary" in tier_id.lower():
                solid_color = tier_colors["primary"]
            else:
                default_palette = [
                    tier_colors["pre_primary"],
                    tier_colors["primary"],
                    tier_colors["junior_secondary"],
                    tier_colors["senior_secondary"]
                ]
                solid_color = default_palette[idx % len(default_palette)]

            card = MainTierCard(
                title=tier.get("title", ""),
                subtitle=tier.get("subtitle", ""),
                bg_color=solid_color
            )
            card.height = dp(75 * scale)
            card.title_label.font_size = f"{int(16 * scale)}sp"
            card.sub_label.font_size = f"{int(12.5 * scale)}sp"
            card.arrow_label.font_size = f"{int(16 * scale)}sp"

            is_open = (self.expanded_tier == tier_id)
            card.set_expanded_state(is_open)
            
            card.bind(on_release=lambda inst, t_id=tier_id: self.toggle_tier_dropdown(t_id))
            self.cards_grid.add_widget(card)

            if is_open:
                dropdown_box = BoxLayout(
                    orientation='vertical',
                    spacing=dp(8),
                    size_hint_y=None,
                    padding=[dp(10), dp(4), dp(4), dp(4)]
                )
                dropdown_box.bind(minimum_height=dropdown_box.setter('height'))

                for sub_class in tier.get("classes", []):
                    sub_btn = DynamicItemButton(
                        title=sub_class.get("title", ""),
                        subtitle=sub_class.get("subtitle", ""),
                        item_id=sub_class.get("class_id", ""),
                        item_data=sub_class
                    )
                    sub_btn.height = dp(62 * scale)
                    sub_btn.lbl_title.font_size = f"{int(14 * scale)}sp"
                    sub_btn.lbl_sub.font_size = f"{int(11.5 * scale)}sp"
                    sub_btn.bind(on_release=self.on_class_selected)
                    dropdown_box.add_widget(sub_btn)

                self.cards_grid.add_widget(dropdown_box)
    
    def toggle_tier_dropdown(self, tier_id):
        self.expanded_tier = None if self.expanded_tier == tier_id else tier_id
        self.render_tiers()

    def prompt_global_update(self, update_type="global"):
        popup = UpdateNotificationPopup(
            on_confirm_callback=lambda: self.apply_class_update(None),
            update_type="global"
        )
        popup.open()

    def on_class_selected(self, instance):
        self.selected_class_id = instance.item_id
        self.selected_class_title = instance.item_title
        print(f"[CLASSROOM]: Selected Class -> {self.selected_class_title} ({self.selected_class_id})")

        self.show_subject_selection_view()

        CurriculumManager.check_class_update(
            class_id=self.selected_class_id,
            on_update_found_callback=self.prompt_class_update
        )

    def prompt_class_update(self, class_id, update_type="class"):
        popup = UpdateNotificationPopup(
            on_confirm_callback=lambda: self.apply_class_update(class_id),
            update_type="class"
        )
        popup.open()

    def apply_class_update(self, class_id):
        success = CurriculumManager.apply_pending_update(target_class_id=class_id)
        if success:
            if self.selected_class_id:
                self.show_subject_selection_view()
            else:
                self.show_class_tier_view()

    def show_subject_selection_view(self):
        scale = get_responsive_scale()
        self.back_btn.text = " Levels"
        self.welcome_label.text = f"[size=18sp][b]{self.selected_class_title}[/b] — Select Subject:[/size]"

        cid = (self.selected_class_id or "").lower()
        if any(keyword in cid for keyword in ["junior", "senior", "jss", "sss", "ss"]):
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Students[/color]"
        else:
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Pupils[/color]"

        self.cards_grid.clear_widgets()
        
        subjects = CurriculumManager.get_subjects_for_class(self.selected_class_id)

        if not subjects:
            no_sub_label = Label(
                text="[color=888888]No subjects added yet for this class.\nDownload/Update subjects.[/color]",
                markup=True,
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(100)
            )
            no_sub_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
            self.cards_grid.add_widget(no_sub_label)
            return

        for idx, item in enumerate(subjects):
            selected_color = SUBJECT_CARD_COLORS[idx % len(SUBJECT_CARD_COLORS)]
            btn = DynamicItemButton(
                title=item.get("title", ""),
                subtitle=item.get("subtitle", ""),
                item_id=item.get("subject_id", ""),
                item_data=item,
                bg_color=selected_color
            )
            btn.height = dp(70 * scale)
            btn.lbl_title.font_size = f"{int(15 * scale)}sp"
            btn.lbl_sub.font_size = f"{int(12 * scale)}sp"
            btn.bind(on_release=self.on_subject_selected)
            self.cards_grid.add_widget(btn)

    def on_subject_selected(self, instance):
        subject_data = instance.item_data or {}
        print(f"[CLASSROOM]: Selected Subject -> {instance.item_title}")

        if self.manager:
            self.manager.selected_class_id = self.selected_class_id
            self.manager.selected_class_title = self.selected_class_title
            self.manager.selected_subject_data = subject_data

        if self.manager and self.manager.has_screen('topic_list'):
            self.manager.current = 'topic_list'

    def handle_back_button(self, instance):
        if self.selected_class_id is not None:
            self.show_class_tier_view()
        else:
            self.selected_class_id = None
            if self.manager and self.manager.has_screen('home_page'):
                self.manager.current = 'home_page'