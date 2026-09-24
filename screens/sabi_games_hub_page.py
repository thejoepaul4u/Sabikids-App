import os
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp


def get_responsive_scale():
    base_scale = Window.width / dp(360)
    # Increased minimum floor to 0.88 to prevent text from over-shrinking on small screens
    return max(0.88, min(1.15, base_scale))


class GameCardWidget(BoxLayout):
    """Card widget that handles both wide and narrow screen layouts cleanly."""
    def __init__(self, title, description, badge_text, badge_color, is_available=True, on_play_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.padding = [dp(14), dp(10)]
        self.spacing = dp(10)
        self.on_play_callback = on_play_callback
        self.is_available = is_available

        # Card Canvas Background
        with self.canvas.before:
            self.bg_color = Color(0.12, 0.16, 0.22, 1)
            self.bg_rect = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self.update_rect, size=self.update_rect)

        # Main Info Box (Text Column)
        self.info_box = BoxLayout(orientation='vertical', spacing=dp(3), size_hint_y=None)
        self.info_box.bind(minimum_height=self.info_box.setter('height'))

        self.title_label = Label(
            text=f"[b]{title}[/b]",
            markup=True,
            font_size='16sp',
            color=(1, 1, 1, 1),
            size_hint_y=None,
            halign='left',
            valign='middle'
        )
        self.title_label.bind(width=self._sync_text_bounds)
        self.title_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))

        self.desc_label = Label(
            text=description,
            font_size='12.5sp',
            color=(0.75, 0.78, 0.82, 1),
            size_hint_y=None,
            halign='left',
            valign='middle'
        )
        self.desc_label.bind(width=self._sync_text_bounds)
        self.desc_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))

        self.badge_label = Label(
            text=f"[size=11sp]{badge_text}[/size]",
            markup=True,
            font_size='11sp',
            color=badge_color,
            size_hint_y=None,
            halign='left',
            valign='middle'
        )
        self.badge_label.bind(width=self._sync_text_bounds)
        self.badge_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))

        self.info_box.add_widget(self.title_label)
        self.info_box.add_widget(self.desc_label)
        self.info_box.add_widget(self.badge_label)
        self.add_widget(self.info_box)

        # Play / Status Button
        btn_text = "PLAY" if self.is_available else "SOON"
        btn_bg = (0.15, 0.65, 0.36, 1) if self.is_available else (0.28, 0.28, 0.32, 1)

        self.play_btn = Button(
            text=btn_text,
            font_size='12.5sp',
            bold=True,
            size_hint=(None, None),
            size=(dp(75), dp(36)),
            pos_hint={'center_y': 0.5},
            background_color=btn_bg,
            background_normal='',
            disabled=not self.is_available
        )
        self.play_btn.mute_sound = True  # Prevents sound conflict/UI freeze
        
        if self.is_available:
            self.play_btn.bind(on_release=self.trigger_play)
        self.add_widget(self.play_btn)

        # Dynamic Card Height Adjustment
        self.bind(minimum_height=self._update_card_height)
        self.height = dp(80)

    def _sync_text_bounds(self, instance, width_val):
        instance.text_size = (max(dp(20), width_val), None)

    def _update_card_height(self, instance, min_h):
        padded_height = min_h + self.padding[1] + self.padding[3]
        self.height = max(dp(75), padded_height)

    def update_rect(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def trigger_play(self, instance):
        if self.on_play_callback:
            self.on_play_callback()

    def apply_scale(self, scale):
        # Layout orientation swap for small screens
        if Window.width < dp(340):
            self.orientation = 'vertical'
            self.play_btn.pos_hint = {'center_x': 0.5}
            self.play_btn.size = (dp(110 * scale), dp(34 * scale))
        else:
            self.orientation = 'horizontal'
            self.play_btn.pos_hint = {'center_y': 0.5}
            self.play_btn.size = (dp(75 * scale), dp(36 * scale))

        # Increased font size baselines and minimum floors
        title_font = max(14, int(16 * scale))
        desc_font = max(11, int(12.5 * scale))
        badge_font = max(10, int(11 * scale))
        btn_font = max(11, int(12.5 * scale))

        self.title_label.font_size = f"{title_font}sp"
        self.desc_label.font_size = f"{desc_font}sp"
        self.badge_label.font_size = f"{badge_font}sp"
        self.play_btn.font_size = f"{btn_font}sp"


class SabiGamesHubScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'sabi_games_hub_page')
        super().__init__(**kwargs)

        # Initialize Background Sound Engine
        self.bg_music = None
        music_path = os.path.join("assets", "audio", "sabigamesaudio.mp3")
        if os.path.exists(music_path):
            self.bg_music = SoundLoader.load(music_path)
            if self.bg_music:
                self.bg_music.loop = True
                self.bg_music.volume = 0.5  # Balanced background volume

        self.main_container = FloatLayout()

        # --- TOP HEADER NAVIGATION BAR ---
        self.nav_box = BoxLayout(
            size_hint=(1, None),
            height=dp(50),
            pos_hint={'top': 1, 'x': 0},
            padding=[dp(10), dp(5)],
            spacing=dp(5)
        )
        
        self.back_btn = Button(
            text="Home",
            size_hint=(None, 1),
            width=dp(80),
            font_size='13sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.mute_sound = True  # Prevents sound conflict/UI freeze
        self.back_btn.bind(on_release=self.go_back_home)
        self.back_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(2)), None)))
        
        self.header_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Games[/color]",
            markup=True,
            font_size='20sp',
            bold=True,
            halign='center',
            valign='middle'
        )
        self.header_title.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(2)), None)))

        self.nav_spacer = Label(size_hint=(None, 1), width=dp(80))

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.nav_spacer)
        self.main_container.add_widget(self.nav_box)

        # --- SCROLLABLE GAMES LIST ---
        self.scroll_view = ScrollView(
            size_hint=(1, None),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )

        self.scroll_content = GridLayout(
            cols=1,
            spacing=dp(10),
            size_hint_y=None,
            padding=[dp(10), dp(10)]
        )
        self.scroll_content.bind(minimum_height=self.scroll_content.setter('height'))

        # SECTION A: SABI KIDS GAMES
        self.kids_header = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Kids:[/color]",
            markup=True,
            font_size='17sp',
            bold=True,
            size_hint_y=None,
            height=dp(30),
            halign='left',
            valign='middle'
        )
        self.kids_header.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.scroll_content.add_widget(self.kids_header)

        # 1. Word Builder
        self.card1 = GameCardWidget(
            title=" Word Builder",
            description="Unscramble letters to spell hidden words.",
            badge_text="Ready to Play",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_word_builder
        )
        self.scroll_content.add_widget(self.card1)

        # 2. Math Balloon Pop
        self.card2 = GameCardWidget(
            title=" Math Balloon Pop",
            description="Pop balloons to hit target math values.",
            badge_text="Ready to Play",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_math_balloon_pop
        )
        self.scroll_content.add_widget(self.card2)

        # 3. Memory Card/Flash Match
        self.card3 = GameCardWidget(
            title=" Memory Flash Match",
            description="Test and sharpen your quick recall.",
            badge_text="Ready to Play",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_memory_flash_match
        )
        self.scroll_content.add_widget(self.card3)

        # 4. Phonics & Sight Words Catcher/Sentence Catcher
        self.card4 = GameCardWidget(
            title=" Sentence Catcher",
            description="Catch words in order to build full sentences.",
            badge_text="Ready to Play",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_sentence_catcher
        )
        self.scroll_content.add_widget(self.card4)

        # 5. Shape & Color Sorter
        self.card5 = GameCardWidget(
            title=" Shape & Color Sorter",
            description="Match colorful shapes into target boxes",
            badge_text="Ready to Play",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_shape_color_sorter
        )
        self.scroll_content.add_widget(self.card5)

        # SECTION B: SABI TEENS GAMES
        self.teens_header = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Teens:[/color]",
            markup=True,
            font_size='17sp',
            bold=True,
            size_hint_y=None,
            height=dp(35),
            halign='left',
            valign='bottom'
        )
        self.teens_header.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.scroll_content.add_widget(self.teens_header)

        # 6. Vocabulary Wordle
        self.card6 = GameCardWidget(
            title=" Vocabulary Wordle",
            description="Guess academic vocabulary terms.",
            badge_text="Teens Game",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_vocabulary_wordle
        )
        self.scroll_content.add_widget(self.card6)

        # 7. Speed Math Challenge
        self.card7 = GameCardWidget(
            title=" Speed Math Challenge",
            description="Timed arithmetic, fractions, and equations.",
            badge_text="Teens Game",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_speed_Math
        )
        self.scroll_content.add_widget(self.card7)

        # 8. Word puzzle
        #self.card8 = GameCardWidget(
            #title="8. Word Cross",
            #description="Solve puzzles across core academic subjects.",
            #badge_text="Teens Game",
            #badge_color=(0.15, 0.65, 0.36, 1),
            #is_available=True,
            #on_play_callback=self.launch_word_cross
        #)
        #self.scroll_content.add_widget(self.card8)

        # 9. Crossword & Word Search
        self.card9 = GameCardWidget(
            title=" Word Search",
            description="Interactive search for hidden words.",
            badge_text="Teens Game",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_word_search
        )
        self.scroll_content.add_widget(self.card9)

        # SECTION C: SABI KIDS & TEENS GAMES
        self.kids_and_teens_header = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Kids & Teens:[/color]",
            markup=True,
            font_size='17sp',
            bold=True,
            size_hint_y=None,
            height=dp(35),
            halign='left',
            valign='bottom'
        )
        self.kids_and_teens_header.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.scroll_content.add_widget(self.kids_and_teens_header)

        # 10. Running game
        self.card10 = GameCardWidget(
            title=" Knowledge Hunt",
            description="Dash through obstacles and gather scrolls.",
            badge_text="Kids & Teens Game",
            badge_color=(0.15, 0.65, 0.36, 1),
            is_available=True,
            on_play_callback=self.launch_knowledge_hunt
        )
        self.scroll_content.add_widget(self.card10)

        self.scroll_view.add_widget(self.scroll_content)
        self.main_container.add_widget(self.scroll_view)
        self.add_widget(self.main_container)

        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _update_scroll_bounds(self, *args):
        nav_height = self.nav_box.height
        self.scroll_view.y = 0
        self.scroll_view.height = max(dp(80), Window.height - nav_height)

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()
        self._update_scroll_bounds()

        self.scroll_content.cols = 1

        # Adjust top navigation layout
        if Window.width < dp(320):
            btn_w = dp(65 * scale)
            self.back_btn.text = "Home"
            self.back_btn.font_size = "11sp"
            self.header_title.font_size = "17sp"
        else:
            btn_w = dp(80 * scale)
            self.back_btn.text = " Home"
            self.back_btn.font_size = f"{int(13 * scale)}sp"
            self.header_title.font_size = f"{int(20 * scale)}sp"

        nav_h = dp(48 * scale)
        self.nav_box.height = nav_h
        self.back_btn.width = btn_w
        self.nav_spacer.width = btn_w

        # Increased section header sizes to fill space better
        header_font = f"{max(14, int(17 * scale))}sp"
        self.kids_header.font_size = header_font
        self.teens_header.font_size = header_font
        self.kids_and_teens_header.font_size = header_font

        if Window.width >= dp(768):
            side_padding = max(dp(30), (Window.width - dp(850)) / 2)
            self.scroll_content.padding = [side_padding, dp(16), side_padding, dp(24)]
            self.scroll_content.spacing = dp(12)
        else:
            side_pad = max(dp(8), Window.width * 0.02)
            self.scroll_content.padding = [side_pad, dp(8), side_pad, dp(12)]
            self.scroll_content.spacing = dp(8)

        for child in self.scroll_content.children:
            if isinstance(child, GameCardWidget):
                child.apply_scale(scale)

    def on_pre_enter(self):
        self._apply_responsive_structure()
        if self.bg_music:
            try:
                self.bg_music.play()
            except Exception as e:
                print(f"Audio playback note: {e}")

    def on_leave(self):
        if self.bg_music:
            try:
                self.bg_music.stop()
            except Exception as e:
                print(f"Audio stop note: {e}")

    def launch_word_builder(self):
        if self.manager and self.manager.has_screen('word_builder_page'):
            self.manager.current = 'word_builder_page'

    def launch_math_balloon_pop(self):
        if self.manager and self.manager.has_screen('math_balloon_pop_page'):
            self.manager.current = 'math_balloon_pop_page'

    def launch_memory_flash_match(self):
        if self.manager and self.manager.has_screen('memory_flash_match_page'):
            self.manager.current = 'memory_flash_match_page'

    def launch_sentence_catcher(self):
        if self.manager and self.manager.has_screen('sentence_catcher_page'):
            self.manager.current = 'sentence_catcher_page'

    def launch_shape_color_sorter(self):
        if self.manager and self.manager.has_screen('shape_color_sorter_page'):
            self.manager.current = 'shape_color_sorter_page'

    def launch_vocabulary_wordle(self):
        if self.manager and self.manager.has_screen('vocabulary_wordle_page'):
            self.manager.current = 'vocabulary_wordle_page'

    def launch_speed_Math(self):
        if self.manager and self.manager.has_screen('speed_math_challenge_page'):
            self.manager.current = 'speed_math_challenge_page'

    #def launch_word_cross(self):
        #if self.manager and self.manager.has_screen('word_cross_page'):
            #self.manager.current = 'word_cross_page'

    def launch_word_search(self):
        if self.manager and self.manager.has_screen('word_search_page'):
            self.manager.current = 'word_search_page'

    def launch_knowledge_hunt(self):
        if self.manager and self.manager.has_screen('knowledge_hunt_game_page'):
            self.manager.current = 'knowledge_hunt_game_page'

    def go_back_home(self, instance):
        if self.manager:
            self.manager.current = 'home_page'