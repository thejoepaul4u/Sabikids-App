import os
import time
import random
import webbrowser
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
import database


def get_responsive_scale():
    """Calculates scaling relative to screen width, bound safely between 0.85x and 1.25x."""
    base_scale = Window.width / dp(400)
    return max(0.80, min(1.25, base_scale))


class HeroBannerLayout(FloatLayout):
    """Custom FloatLayout to support swipe gestures specifically over the Hero Banner."""
    def __init__(self, hero_screen_ref, **kwargs):
        super().__init__(**kwargs)
        self.hero_screen_ref = hero_screen_ref
        self.touch_start_x = 0
        self.touch_start_y = 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.touch_start_x = touch.x
            self.touch_start_y = touch.y
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            dx = touch.x - self.touch_start_x
            dy = touch.y - self.touch_start_y
            # Check if horizontal swipe was dominant and longer than threshold (40px)
            if abs(dx) > dp(40) and abs(dx) > abs(dy) * 1.5:
                if dx < 0:
                    self.hero_screen_ref.next_hero_bg()
                else:
                    self.hero_screen_ref.prev_hero_bg()
                return True
        return super().on_touch_up(touch)


class HomePageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'home_page')
        super().__init__(**kwargs)
        
        # --- HERO BACKGROUND CAROUSEL ASSETS ---
        self.hero_backgrounds = [
            "assets/hero_bg_bick.png",
            "assets/hero_bg_zumarock.png",
            "assets/hero_bg_bowertower.png",
            "assets/hero_bg_north.png",
            "assets/hero_bg_cocoahouse.png",
            "assets/hero_bg_olumorock.png",
            "assets/hero_bg_christmas.png",
            "assets/hero_bg_culture.png",
            "assets/hero_bg_wolesoyinkanationalcenterforart.png",
            "assets/hero_bg_acientkanoart.png",
            "assets/hero_bg_lake.png",
        ]
        self.current_hero_bg_index = 0

        # Root layout taking full screen
        self.main_container = FloatLayout(size_hint=(1, 1))

        # --- 1. FLEXIBLE SCROLL VIEW ---
        self.scroll_view = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(4)
        )
        
        # Single Stack Vertical Container for Body Content
        self.layout = BoxLayout(
            orientation='vertical',
            size_hint_x=None,
            size_hint_y=None
        )
        self.layout.bind(minimum_height=self.layout.setter('height'))

        # Centering Wrapper
        self.wrapper_layout = AnchorLayout(
            anchor_x='center',
            anchor_y='top',
            size_hint=(1, None)
        )
        self.layout.bind(height=self.wrapper_layout.setter('height'))
        self.wrapper_layout.add_widget(self.layout)

        # --- 2. HERO SECTION PANEL ---
        self.hero_container = HeroBannerLayout(hero_screen_ref=self, size_hint=(1, None))
        self.hero_container.bind(pos=self.paint_beautiful_hero_canvas, size=self.paint_beautiful_hero_canvas)
        
        # Dynamically scaled tracker box container using flexible percentage sizing
        self.tracker_box = Label(
            text="...", bold=True, color=(1, 1, 1, 1),
            size_hint=(0.42, None), height=dp(28), pos_hint={'x': 0.04, 'top': 0.94},
            markup=True, halign='center', valign='middle'
        )
        self.tracker_box.bind(width=lambda inst, val: setattr(inst, 'text_size', (val - dp(6), None)))
        
        with self.tracker_box.canvas.before:
            Color(0.1, 0.1, 0.1, 0.7)
            self.track_bg_rect = RoundedRectangle()
        self.tracker_box.bind(pos=self.sync_tracker_bg_dimensions, size=self.sync_tracker_bg_dimensions)
        self.hero_container.add_widget(self.tracker_box)
        
        self.center_text_box = BoxLayout(
            orientation='vertical', spacing=dp(6), size_hint=(0.80, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.42}
        )
        self.center_text_box.bind(minimum_height=self.center_text_box.setter('height'))

        self.welcome_label = Label(
            text="Welcome back!", bold=True, color=(1, 1, 1, 1),
            halign='center', valign='middle', size_hint_y=None
        )
        self.welcome_label.bind(width=lambda instance, val: setattr(instance, 'text_size', (val, None)))
        self.welcome_label.bind(texture_size=lambda instance, val: setattr(instance, 'height', val[1]))
        self.center_text_box.add_widget(self.welcome_label)
        
        self.motivation_label = Label(
            text='"Loading daily inspiration..."', italic=True, bold=True, markup=True,
            color=(0.95, 0.95, 0.95, 1), halign='center', valign='middle', size_hint_y=None
        )
        self.motivation_label.bind(width=lambda instance, val: setattr(instance, 'text_size', (val, None)))
        self.motivation_label.bind(texture_size=lambda instance, val: setattr(instance, 'height', val[1]))
        self.center_text_box.add_widget(self.motivation_label)
        
        self.hero_container.add_widget(self.center_text_box)

        # Left & Right Background Carousel Navigation Arrows (Pure White Text, Completely Transparent Background)
        self.hero_left_arrow = Button(
            text="<", bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(32), dp(40)),
            pos_hint={'x': 0.015, 'center_y': 0.42},
            background_color=(0, 0, 0, 0)
        )
        self.hero_left_arrow.bind(on_release=lambda x: self.prev_hero_bg())
        self.hero_container.add_widget(self.hero_left_arrow)

        self.hero_right_arrow = Button(
            text=">", bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(32), dp(40)),
            pos_hint={'right': 0.985, 'center_y': 0.42},
            background_color=(0, 0, 0, 0)
        )
        self.hero_right_arrow.bind(on_release=lambda x: self.next_hero_bg())
        self.hero_container.add_widget(self.hero_right_arrow)

        self.layout.add_widget(self.hero_container)

        # --- 3. BODY BUTTONS GRID ---
        self.row_split = BoxLayout(
            orientation='horizontal', 
            size_hint=(1, None)
        )
        
        # Classroom Panel
        self.classroom_panel = FloatLayout(size_hint=(1, 1))
        with self.classroom_panel.canvas.before:
            self.classroom_color = Color(0.04, 0.22, 0.12, 1)
            self.classroom_bg_rect = RoundedRectangle(radius=[dp(18)])
        
        def sync_classroom_bg(instance, value):
            self.classroom_bg_rect.pos = instance.pos
            self.classroom_bg_rect.size = instance.size
        self.classroom_panel.bind(pos=sync_classroom_bg, size=sync_classroom_bg)
        
        self.classroom_img_box = FloatLayout(size_hint=(0.22, 1.0), pos_hint={'x': 0, 'y': 0})
        with self.classroom_img_box.canvas:
            self.classroom_img_color = Color(1, 1, 1, 1)
            self.classroom_img_rect = RoundedRectangle(
                source='assets/classroom_icon.png' if os.path.exists('assets/classroom_icon.png') else '',
                radius=[dp(18), 0, 0, dp(18)]
            )
        def sync_classroom_img(instance, value):
            self.classroom_img_rect.pos = instance.pos
            self.classroom_img_rect.size = instance.size
        self.classroom_img_box.bind(pos=sync_classroom_img, size=sync_classroom_img)
        self.classroom_panel.add_widget(self.classroom_img_box)
        
        self.classroom_txt = Label(
            text="My Classroom\n[color=cfd8dc]Tap to enter.[/color]",
            bold=True, halign='left', valign='middle', markup=True,
            size_hint=(0.73, 1), pos_hint={'x': 0.25, 'center_y': 0.5}
        )
        self.classroom_txt.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.classroom_panel.add_widget(self.classroom_txt)
        
        self.classroom_btn = Button(
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
            background_normal='', background_color=(0, 0, 0, 0)
        )
        self.classroom_btn.bind(on_release=self.on_my_classroom_click)
        self.classroom_panel.add_widget(self.classroom_btn)
        self.row_split.add_widget(self.classroom_panel)
        
        # i-Sabi Challenges Panel
        self.challenges_panel = FloatLayout(size_hint=(1, 1))
        with self.challenges_panel.canvas.before:
            self.challenges_color = Color(0.05, 0.22, 0.38, 1)
            self.challenges_bg_rect = RoundedRectangle(radius=[dp(18)])
        
        def sync_challenges_bg(instance, value):
            self.challenges_bg_rect.pos = instance.pos
            self.challenges_bg_rect.size = instance.size
        self.challenges_panel.bind(pos=sync_challenges_bg, size=sync_challenges_bg)
        
        self.challenges_img_box = FloatLayout(size_hint=(0.22, 1.0), pos_hint={'x': 0, 'y': 0})
        with self.challenges_img_box.canvas:
            self.challenges_img_color = Color(1, 1, 1, 1)
            self.challenges_img_rect = RoundedRectangle(
                source='assets/challenges_icon.png' if os.path.exists('assets/challenges_icon.png') else '',
                radius=[dp(18), 0, 0, dp(18)]
            )
        def sync_challenges_img(instance, value):
            self.challenges_img_rect.pos = instance.pos
            self.challenges_img_rect.size = instance.size
        self.challenges_img_box.bind(pos=sync_challenges_img, size=sync_challenges_img)
        self.challenges_panel.add_widget(self.challenges_img_box)
        
        self.challenges_txt = Label(
            text="i-[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=38b6ff]i[/color] Challenges\n[color=cfd8dc]Tap to enter.[/color]",
            bold=True, halign='left', valign='middle', markup=True,
            size_hint=(0.73, 1), pos_hint={'x': 0.25, 'center_y': 0.5}
        )
        self.challenges_txt.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.challenges_panel.add_widget(self.challenges_txt)
        
        self.challenges_btn = Button(
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
            background_normal='', background_color=(0, 0, 0, 0)
        )
        self.challenges_btn.bind(on_release=self.isabi_challenges_click)
        self.challenges_panel.add_widget(self.challenges_btn)
        self.row_split.add_widget(self.challenges_panel)
        self.layout.add_widget(self.row_split)
        
        # Games & Tv Banner
        gt_asset = 'assets/games_tv_banner.png' if os.path.exists('assets/games_tv_banner.png') else ('assets/fun_factory_banner.png' if os.path.exists('assets/fun_factory_banner.png') else 'assets/game_banner.png')
        self.games_tv_btn = Button(
            text="  Games & Tv  \n[color=ffffff]Tap to play, watch & learn![/color]", 
            bold=True, halign='center', valign='middle', markup=True,
            size_hint=(1, None),
            background_normal=gt_asset if os.path.exists(gt_asset) else '',
            background_down=gt_asset if os.path.exists(gt_asset) else '',
            background_color=(0.3, 0.4, 0.3, 0.4),
            border=(0, 0, 0, 0)
        )
        self.games_tv_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (val - dp(16), None)))
        self.games_tv_btn.bind(on_release=self.open_games_tv_hub)
        self.layout.add_widget(self.games_tv_btn)

        self.scroll_view.add_widget(self.wrapper_layout)
        # Add ScrollView to main container first so Navbar and Footer sit above it
        self.main_container.add_widget(self.scroll_view)

        # --- 4. HEADER NAVIGATION BAR ---
        self.navbar = FloatLayout(size_hint=(1, None), height=dp(55), pos_hint={'top': 1, 'x': 0})
        
        with self.navbar.canvas.before:
            Color(0, 0, 0, 1)
            self.nav_bg = RoundedRectangle(pos=self.navbar.pos, size=self.navbar.size)
        def sync_nav_bg(inst, val):
            self.nav_bg.pos = inst.pos
            self.nav_bg.size = inst.size
        self.navbar.bind(pos=sync_nav_bg, size=sync_nav_bg)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=38b6ff]i[/color] [color=ffffff]Learners[/color]",
            bold=True, markup=True,
            size_hint=(None, None), size=(dp(180), dp(36)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.navbar.add_widget(self.brand_title)
        
        self.settings_btn = Button(
            text="Settings", bold=True,
            size_hint=(None, None), size=(dp(85), dp(32)),
            pos_hint={'right': 0.98, 'center_y': 0.5},
            background_normal='', background_color=(0.2, 0.2, 0.2, 1),
            color=(0.9, 0.9, 0.9, 1)
        )
        self.settings_btn.bind(on_release=self.open_parental_admin_gate)
        self.navbar.add_widget(self.settings_btn)
        self.main_container.add_widget(self.navbar)

        # --- 5. FLOATING MOTIVATION BANNER FOOTER ---
        self.footer_banner = FloatLayout(size_hint=(1, None), height=dp(30), pos_hint={'x': 0, 'y': 0})
        
        bar_asset = 'assets/ticker_bar.png'
        has_bar = os.path.exists(bar_asset)
        
        with self.footer_banner.canvas.before:
            Color(0.05, 0.05, 0.08, 0.85)
            self.footer_dark_rect = RoundedRectangle(
                pos=self.footer_banner.pos,
                size=self.footer_banner.size,
                radius=[dp(10), dp(10), 0, 0]
            )
            
            Color(1, 1, 1, 0.15 if has_bar else 0)
            self.footer_bar_rect = RoundedRectangle(
                source=bar_asset if has_bar else '',
                pos=self.footer_banner.pos,
                size=self.footer_banner.size,
                radius=[dp(10), dp(10), 0, 0]
            )
            
        def sync_affirmation_bar(instance, value):
            self.footer_dark_rect.pos = instance.pos
            self.footer_dark_rect.size = instance.size
            self.footer_bar_rect.pos = instance.pos
            self.footer_bar_rect.size = instance.size
            
        self.footer_banner.bind(pos=sync_affirmation_bar, size=sync_affirmation_bar)

        self.marquee_label = Label(
            text="Loading affirmations...", bold=True, markup=True,
            size_hint=(None, 1), width=dp(650), pos_hint={'y': 0}
        )
        self.marquee_label.pos_hint = {'x': 1.0}
        self.footer_banner.add_widget(self.marquee_label)
        self.main_container.add_widget(self.footer_banner)
        

        # Quotes setup
        self.motivation_quotes = [
            "[color=e67e22]Did you know?[/color] Your brain generates enough electricity to power a small lightbulb.",
            "[color=e67e22]Did you know?[/color] Honey never spoils; archaeologists have found 3,000-year-old honey in Egyptian tombs that is still edible.",
            "[color=e67e22]Did you know?[/color] Water can boil and freeze at the same time under specific conditions called the 'triple point'.",
            "[color=e67e22]Did you know?[/color] Bamboo can grow up to 35 inches in a single day under the right conditions.",
            "[color=e67e22]Did you know?[/color] Lightning is five times hotter than the surface of the Sun.",
            "[color=e67e22]Did you know?[/color] A single cloud can weigh more than 1 million pounds (over 450,000 kilograms).",
            "[color=e67e22]Did you know?[/color] Your body has about 60,000 miles of blood vessels—enough to circle the Earth twice!",
            "[color=e67e22]Did you know?[/color] Sound travels about 4 times faster in water than it does through air.",
            "[color=e67e22]Did you know?[/color] There are more trees on Earth than stars in the Milky Way galaxy.",
            "[color=e67e22]Did you know?[/color] Hot water can freeze faster than cold water under certain conditions (known as the Mpemba effect).",
            "[color=e67e22]Did you know?[/color] Octopuses have three hearts and blue-colored blood.",
            "[color=e67e22]Did you know?[/color] A teaspoon of a neutron star would weigh about 6 billion tons on Earth.",
            "[color=e67e22]Did you know?[/color] The human eye can distinguish between roughly 10 million different colors.",
            "[color=e67e22]Did you know?[/color] Time moves slightly faster at high altitudes because gravity is weaker further from Earth's center.",
            "[color=e67e22]Did you know?[/color] A year on Venus is shorter than a day on Venus because it rotates extremely slowly on its axis."
        
        ]
        
        self.sabi_affirmations = []
        self.current_affirmation_index = 0
        
        self.quote_event = None
        self.marquee_event = None

        # Bind resize events
        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

        # ATTACH MAIN CONTAINER TO THE SCREEN ITSELF
        self.add_widget(self.main_container)

    def next_hero_bg(self):
        """Cycles to the next hero background picture and persists the choice."""
        self.current_hero_bg_index = (self.current_hero_bg_index + 1) % len(self.hero_backgrounds)
        database.update_user_profile({"hero_bg_index": self.current_hero_bg_index})
        self.paint_beautiful_hero_canvas(self.hero_container)

    def prev_hero_bg(self):
        """Cycles to the previous hero background picture and persists the choice."""
        self.current_hero_bg_index = (self.current_hero_bg_index - 1) % len(self.hero_backgrounds)
        database.update_user_profile({"hero_bg_index": self.current_hero_bg_index})
        self.paint_beautiful_hero_canvas(self.hero_container)

    def _apply_responsive_structure(self, *args):
        """Scales sizes and relies on ScrollView to expand container heights cleanly downwards."""
        scale = get_responsive_scale()
        
        # --- TYPOGRAPHY & FONT SCALING ---
        self.brand_title.font_size = f"{int(20 * scale)}sp"         # Sabi Learners title
        self.settings_btn.font_size = f"{int(13 * scale)}sp"        # Settings button font
        if hasattr(self, 'back_btn'):
            self.back_btn.font_size = f"{int(13 * scale)}sp"        # Back button font
        self.tracker_box.font_size = f"{int(12 * scale)}sp"         # Subscription timer font
        self.tracker_box.height = dp(25 * scale)                    # Timer box height
        self.welcome_label.font_size = f"{int(20 * scale)}sp"       # Header greeting font
        self.motivation_label.font_size = f"{int(13.5 * scale)}sp"  # Motivational quote font
        
        # Carousel Arrows Font Scaling
        self.hero_left_arrow.font_size = f"{int(22 * scale)}sp"
        self.hero_right_arrow.font_size = f"{int(22 * scale)}sp"
        self.hero_left_arrow.size = (dp(30 * scale), dp(40 * scale))
        self.hero_right_arrow.size = (dp(30 * scale), dp(40 * scale))

        # Grid dynamic text formatting
        sub_txt_size = f"{int(12.5 * scale)}sp"                      # Subtitle text font size
        self.classroom_txt.text = f"My Classroom\n[size={sub_txt_size}][color=cfd8dc]Tap to enter.[/color][/size]"
        self.classroom_txt.font_size = f"{int(17 * scale)}sp"       # Classroom title font
        
        self.challenges_txt.text = f"i-[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=38b6ff]i[/color] Challenges\n[size={sub_txt_size}][color=cfd8dc]Tap to enter.[/color][/size]"
        self.challenges_txt.font_size = f"{int(17 * scale)}sp"      # Challenges title font
        
        gt_sub_size = f"{int(12.5 * scale)}sp"                       # Games & Tv subtitle font size
        self.games_tv_btn.text = f"  Games & Tv  \n[size={gt_sub_size}][color=ffffff]Tap to play, watch & learn![/color][/size]"
        self.games_tv_btn.font_size = f"{int(18 * scale)}sp"     # Games & Tv title font
        self.marquee_label.font_size = f"{int(14 * scale)}sp"       # Ticker marquee text font

        # --- CONTAINER PADDING & OVERLAY CLEARANCE ---
        top_padding = dp(70)     # Header navbar clearance
        bottom_padding = dp(10)  # Footer ticker clearance

        if Window.width >= dp(768):
            # --- WIDESCREEN / DESKTOP LAYOUT ---
            self.settings_btn.size = (dp(80 * scale), dp(36 * scale))  # Settings button size
            if hasattr(self, 'back_btn'):
                self.back_btn.size = (dp(80 * scale), dp(36 * scale))  # Back button size on wide screens
            self.wrapper_layout.anchor_y = 'top'                    # Center content vertically
            self.layout.width = min(Window.width * 0.90, dp(900))      # Card width on wide screens
            self.layout.spacing = dp(40)                               # Space between elements
            self.layout.padding = [dp(30), top_padding, dp(30), bottom_padding] # Main layout padding
            
            self.hero_container.height = dp(200)                       # Hero banner height
            
            # Side-by-side row split
            self.row_split.orientation = 'horizontal'                   # Split buttons side-by-side
            self.classroom_panel.size_hint = (0.5, 1)                  # Classroom card half-width
            self.challenges_panel.size_hint = (0.5, 1)                 # Challenges card half-width
            self.row_split.height = dp(110)                             # Row split section height
            self.row_split.spacing = dp(20)                            # Space between row buttons
            
            self.games_tv_btn.height = dp(110)                      # Games & Tv card height
        else:
            # --- MOBILE LAYOUT ---
            self.settings_btn.size = (dp(55 * scale), dp(30 * scale))  # Settings button size
            if hasattr(self, 'back_btn'):
                self.back_btn.size = (dp(55 * scale), dp(30 * scale))  # Back button size on mobile
            self.wrapper_layout.anchor_y = 'top'                       # Align content to top
            self.layout.width = min(Window.width * 0.92, dp(600))      # Card width on mobile
            self.layout.spacing = dp(25)                               # Space between elements
            self.layout.padding = [dp(15), top_padding, dp(15), bottom_padding] # Main layout padding
            
            # Dynamic height calculation for hero text wrapping
            self.hero_container.height = max(dp(140), self.center_text_box.height + dp(100)) # Hero banner height
            
            # Adaptive Stacking on narrow mobile screens
            if Window.width < dp(450):
                self.row_split.orientation = 'vertical'                # Stack buttons vertically
                self.classroom_panel.size_hint = (1, None)             # Full width on narrow mobile
                self.classroom_panel.height = dp(85)                   # Classroom card height
                self.challenges_panel.size_hint = (1, None)            # Full width on narrow mobile
                self.challenges_panel.height = dp(85)                  # Challenges card height
                self.row_split.height = dp(180)                        # Total stacked row height
                self.row_split.spacing = dp(10)                        # Space between stacked buttons
            else:
                self.row_split.orientation = 'horizontal'              # Keep side-by-side on wide mobile
                self.classroom_panel.size_hint = (0.5, 1)              # Classroom card half-width
                self.challenges_panel.size_hint = (0.5, 1)             # Challenges card half-width
                self.row_split.height = dp(100)                         # Row split section height
                self.row_split.spacing = dp(25)                        # Space between row buttons
            
            self.games_tv_btn.height = dp(100)                       # Games & Tv card height

    def paint_beautiful_hero_canvas(self, instance, *args):
        instance.canvas.before.clear()
        x, y = instance.pos
        w, h = instance.size
        
        selected_asset = self.hero_backgrounds[self.current_hero_bg_index]
        bg_asset = selected_asset if os.path.exists(selected_asset) else ("assets/liquid_glass.png" if os.path.exists("assets/liquid_glass.png") else "")
        
        radius = dp(18)
        line_w = 4.5
        
        nx, ny = x - 1.2, y - 1.2
        nw, nh = w + 2.4, h + 2.4
        nr = radius + 1.2
        
        with instance.canvas.before:
            Color(0, 0, 0, 0.70)
            RoundedRectangle(pos=(x + 6, y - 8), size=(w - 12, 10), radius=[0, 0, dp(14), dp(14)])

            Color(0.38, 0.40, 0.45, 1) 
            RoundedRectangle(pos=(x, y), size=(w, h), source=bg_asset, radius=[radius])
            
            Color(0.04, 0.05, 0.08, 0.45) 
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[radius])

            Color(0.25, 0.28, 0.32, 1)
            Line(rounded_rectangle=(x, y, w, h, radius), width=1.5)
            
            Color(0.16, 0.50, 0.28, 1)
            Line(points=[nx, ny + nh - nr - 20, nx, ny + nh - nr, nx + nr, ny + nh, nx + nr + 20, ny + nh], width=line_w)
            Color(0.90, 0.49, 0.13, 1)
            Line(points=[nx + nw - nr - 20, ny + nh, nx + nw - nr, ny + nh, nx + nw, ny + nh - nr, nx + nw, ny + nh - nr - 20], width=line_w)
            Color(0.95, 0.77, 0.06, 1)
            Line(points=[nx + nw, ny + nr + 20, nx + nw, ny + nr, nx + nw - nr, ny, nx + nw - nr - 20, ny], width=line_w)
            Color(0.16, 0.50, 0.73, 1)
            Line(points=[nx + nr + 20, ny, nx + nr, ny, nx, ny + nr, nx, ny + nr + 20], width=line_w)

    def sync_tracker_bg_dimensions(self, instance, *args):
        self.track_bg_rect.pos = instance.pos
        self.track_bg_rect.size = instance.size

    def on_pre_enter(self):
        profile = database.get_user_profile()
        
        # Load persisted hero background choice
        saved_bg_index = int(profile.get("hero_bg_index", 0))
        if 0 <= saved_bg_index < len(self.hero_backgrounds):
            self.current_hero_bg_index = saved_bg_index
        else:
            self.current_hero_bg_index = 0
        self.paint_beautiful_hero_canvas(self.hero_container)
        
        db_child_name = profile.get("child_name", "Superstar").strip()
        name_parts = db_child_name.split()
        first_name = name_parts[0].title() if name_parts else "Superstar"
        
        is_first_time = int(profile.get("is_first_time_login", 1))
        if is_first_time == 1:
            self.welcome_label.text = f"Welcome, {first_name}!"
            database.update_user_profile({"is_first_time_login": 0})
        else:
            self.welcome_label.text = f"Welcome back, {first_name}!"
            
        self.sabi_affirmations = [
            f"[color=ffffff]{first_name}, you are capable of achieving great things![/color]",
            f"[color=26a56b]Your mind is growing sharper and smarter every single day.[/color]",
            f"[color=e67e22]You are a Sabi Learner — building your future step by step.[/color]",
            f"[color=f1c40f]Keep pushing forward; your hard work will definitely pay off.[/color]",
            f"[color=38b6ff]You have the brilliance to solve any challenge in front of you.[/color]",
            f"[color=ffffff]GO {first_name} — stay focused and keep striving for excellence![/color]",
            f"[color=38b6ff]Sabi Learner alert: {first_name} is unstoppable today![/color]"
        ]
        
        self.cycle_new_motivation_quote()
        if not self.quote_event:
            self.quote_event = Clock.schedule_interval(lambda dt: self.cycle_new_motivation_quote(), 12.0)
        
        self.initialize_next_affirmation_marquee()
        if not self.marquee_event:
            self.marquee_event = Clock.schedule_interval(self.animate_affirmation_slide, 0.016)
        
        app = App.get_running_app()
        rem = app.rem_sec if (app and hasattr(app, 'rem_sec')) else float(profile.get("free_seconds_remaining", database.DEFAULT_FREE_SECONDS))
        self.update_tracker_display(rem)

    def update_tracker_display(self, total_seconds):
        """Pure UI update formatting without making redundant SQLite reads on the main thread."""
        app = App.get_running_app()
        plan_name = getattr(app, 'chosen_plan_type', 'Demo')
        status = getattr(app, 'subscription_status', 'ACTIVE')
        
        if total_seconds <= 0 or status == "EXPIRED":
            self.tracker_box.text = f"[color=e74c3c]{plan_name} Expired[/color]"
        else:
            hrs = int(total_seconds // 3600)
            mins = int((total_seconds % 3600) // 60)
            secs = int(total_seconds % 60)
            if hrs > 0:
                self.tracker_box.text = f"[color=e67e22]{hrs:02d}:{mins:02d}:{secs:02d}[/color]"
            else:
                self.tracker_box.text = f"[color=e67e22]{mins:02d}:{secs:02d}[/color]"

    def on_leave(self):
        if self.quote_event: 
            self.quote_event.cancel()
            self.quote_event = None
        if self.marquee_event: 
            self.marquee_event.cancel()
            self.marquee_event = None

    def cycle_new_motivation_quote(self):
        current_text = self.motivation_label.text
        available_choices = [q for q in self.motivation_quotes if q != current_text]
        if available_choices:
            self.motivation_label.text = random.choice(available_choices)

    def initialize_next_affirmation_marquee(self):
        if self.sabi_affirmations:
            self.marquee_label.text = self.sabi_affirmations[self.current_affirmation_index]
            self.marquee_label.pos_hint = {'x': 1.0}
            self.current_affirmation_index = (self.current_affirmation_index + 1) % len(self.sabi_affirmations)

    def animate_affirmation_slide(self, dt):
        current_x = self.marquee_label.pos_hint['x']
        new_x = current_x - (0.15 * dt)
        if new_x < -0.8:
            self.initialize_next_affirmation_marquee()
        else:
            self.marquee_label.pos_hint = {'x': new_x}

    def check_access_permission(self):
        profile = database.get_user_profile()
        status = profile.get("subscription_status", "ACTIVE")
        app = App.get_running_app()
        rem_sec = app.rem_sec if (app and hasattr(app, 'rem_sec')) else float(profile.get("free_seconds_remaining", 0.0))
        plan_name = profile.get("chosen_plan_type", "Demo")
        
        if status == "EXPIRED" or rem_sec <= 0:
            self.show_subscription_access_dialog(
                f"{plan_name} Expired", 
                "Your active usage duration has ended. Choose a pass to keep learning!"
            )
            return False
        return True

    def show_subscription_access_dialog(self, title_text, message_text):
        scale = get_responsive_scale()
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=[dp(20), dp(20), dp(20), dp(15)])
        
        dialog_title = Label(
            text=f"[color=e74c3c]{title_text}[/color]",
            font_size=f"{int(20 * scale)}sp", bold=True, markup=True,
            halign='center', valign='middle', size_hint_y=None, height=dp(35)
        )
        content.add_widget(dialog_title)
        
        dialog_msg = Label(
            text=message_text,
            font_size=f"{int(14 * scale)}sp", color=(0.9, 0.9, 0.9, 1),
            halign='center', valign='middle', size_hint_y=None, height=dp(70)
        )
        dialog_msg.bind(width=lambda inst, val: setattr(inst, 'text_size', (val - dp(20), None)))
        content.add_widget(dialog_msg)
        
        btn_box = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))
        renew_btn = Button(
            text="Choose Plan", font_size=f"{int(15 * scale)}sp", bold=True,
            background_color=(0.16, 0.50, 0.28, 1), background_normal=''
        )
        cancel_btn = Button(
            text="Cancel", font_size=f"{int(15 * scale)}sp", bold=True,
            background_color=(0.3, 0.3, 0.3, 1), background_normal=''
        )
        
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(renew_btn)
        content.add_widget(btn_box)
        
        popup = Popup(
            title="", title_size=0, separator_height=0,
            content=content, size_hint=(0.85, 0.42), auto_dismiss=False
        )
        
        def route_to_plans(inst):
            popup.dismiss()
            if self.manager:
                plans_screen = self.manager.get_screen('plans_page')
                plans_screen.from_settings = False
                self.manager.current = 'plans_page'
                
        renew_btn.bind(on_release=route_to_plans)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def on_my_classroom_click(self, instance):
        if not self.check_access_permission():
            return
        if self.manager and self.manager.has_screen('classroom_home'):
            self.manager.current = 'classroom_home'

    def isabi_challenges_click(self, instance):
        if not self.check_access_permission():
            return
        if self.manager and self.manager.has_screen('isabi_level'):
            self.manager.current = 'isabi_level'

    def open_games_tv_hub(self, instance):
        scale = get_responsive_scale()
        
        # 1. Dynamic Width Guardrails
        popup_width = max(dp(280), min(Window.width * 0.88, dp(420)))
        
        # 2. Main Content Layout
        content = BoxLayout(
            orientation='vertical', 
            spacing=dp(12), 
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter('height'))

        # Header Box
        header_box = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(45))
        
        popup_title = Label(
            text="Games & Tv",
            font_size=f"{int(20 * scale)}sp", bold=True, color=(1, 1, 1, 1),
            halign='center', valign='middle', size_hint=(1, None), height=dp(30)
        )
        popup_title.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        header_box.add_widget(popup_title)
        
        accent_strip = BoxLayout(
            orientation='horizontal', spacing=dp(8),
            padding=[dp(20), 0, dp(20), 0], size_hint=(1, None), height=dp(4)
        )
        sabi_colors = [(0.15, 0.65, 0.36, 1), (0.90, 0.49, 0.13, 1), (0.95, 0.77, 0.06, 1), (0.22, 0.71, 1.00, 1)]
        for c in sabi_colors:
            segment = Widget(size_hint=(0.25, 1))
            with segment.canvas:
                Color(*c)
                rect = RoundedRectangle(pos=segment.pos, size=segment.size, radius=[dp(3)])
            def sync_segment(inst, val, r=rect):
                r.pos = inst.pos
                r.size = inst.size
            segment.bind(pos=sync_segment, size=sync_segment)
            accent_strip.add_widget(segment)
            
        header_box.add_widget(accent_strip)
        content.add_widget(header_box)
        
        # Action Buttons
        sabi_markup = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=38b6ff]i[/color]"
        games_sub_size = f"{int(11.5 * scale)}sp"
        
        sabi_games_btn = Button(
            text=f"{sabi_markup} Games\n[size={games_sub_size}][color=cfd8dc]Play to Learn.[/color][/size]",
            markup=True, font_size=f"{int(16 * scale)}sp", bold=True, halign='center', valign='middle',
            size_hint=(1, None), height=dp(58), background_color=(0.11, 0.35, 0.20, 1), background_normal=''
        )
        sabi_games_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (val - dp(10), None)))
        sabi_games_btn.bind(on_release=lambda x: self.launch_feature("brain_games", popup))
        content.add_widget(sabi_games_btn)
        
        sabi_tv_btn = Button(
            text=f"{sabi_markup} Tv\n[size={games_sub_size}][color=cfd8dc]Coming Soon![/color][/size]",
            markup=True, font_size=f"{int(16 * scale)}sp", bold=True, halign='center', valign='middle',
            size_hint=(1, None), height=dp(58), background_color=(0.12, 0.36, 0.52, 1), background_normal=''
        )
        sabi_tv_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (val - dp(10), None)))
        sabi_tv_btn.bind(on_release=lambda x: self.launch_feature("video_series", popup))
        content.add_widget(sabi_tv_btn)
        
        close_btn = Button(
            text="Close", font_size=f"{int(14 * scale)}sp", bold=True, halign='center', valign='middle',
            size_hint=(1, None), height=dp(38), background_color=(0.35, 0.35, 0.35, 1), background_normal=''
        )
        close_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        content.add_widget(close_btn)

        # 3. ScrollView Container
        popup_scroll = ScrollView(
            size_hint=(1, None),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(4)
        )
        popup_scroll.add_widget(content)

        # 4. Auto-adjusting height bound by screen max (90% screen height limit)
        max_allowed_height = Window.height * 0.90
        
        def update_popup_height(instance, value):
            target_height = min(content.height, max_allowed_height)
            popup.height = target_height
            popup_scroll.height = target_height

        content.bind(height=update_popup_height)

        # 5. Build Compact Popup
        popup = Popup(
            title="", title_size=0, separator_height=0, separator_color=(0, 0, 0, 0),
            content=popup_scroll, 
            size_hint=(None, None), 
            width=popup_width,
            height=dp(250),
            auto_dismiss=True
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def launch_feature(self, feature_type, popup_instance):
        if feature_type == "brain_games":
            if not self.check_access_permission():
                popup_instance.dismiss()
                return
            popup_instance.dismiss()
            if self.manager and self.manager.has_screen('sabi_games_hub_page'):
                self.manager.current = 'sabi_games_hub_page'
        elif feature_type == "video_series":
            popup_instance.dismiss()
            #youtube_channel_url = "youtube link"
            #try:
                #webbrowser.open(youtube_channel_url)
            #except Exception as e:
                #print(f"[YOUTUBE LAUNCH ERROR]: {e}")

    def open_parental_admin_gate(self, instance):
        if self.manager:
            self.manager.current = 'settings_page'