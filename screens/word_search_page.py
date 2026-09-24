import os
import json
import random
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line


WORD_SEARCH_POOL = [
    {
        "subject": "General Science & Nature",
        "grid_size": 8,
        "words": [
            {"word": "ENERGY", "hint": "The capacity for doing work"},
            {"word": "ATOM", "hint": "Basic unit of a chemical element"},
            {"word": "CELL", "hint": "Basic structural unit of living organisms"},
            {"word": "FORCE", "hint": "Push or pull upon an object"}
        ]
    },
    {
        "subject": "African History & Geography",
        "grid_size": 8,
        "words": [
            {"word": "NIGER", "hint": "Major river flowing through West Africa"},
            {"word": "ABUJA", "hint": "Capital city of Nigeria"},
            {"word": "SAHARA", "hint": "Vast desert across Northern Africa"},
            {"word": "KANO", "hint": "Historic commercial center in Northern Nigeria"},
            {"word": "BENIN", "hint": "Historic Kingdom and West African Nation"},
            {"word": "NILE", "hint": "Longest river in Africa"}
        ]
    }
]


class WordSearchPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'word_search_page')
        super().__init__(**kwargs)

        self.score = 0
        self.high_score = 0
        self.time_remaining = 0
        self.base_play_time = 60  
        self.carryover_time = 0   
        self.timer_event = None

        self.active_levels = []
        self.current_level_idx = 0
        self.found_words = set()
        self.selected_cells = []  
        self.grid_buttons = {}    
        self.grid_letters = {}    
        self.game_active = False
        self.overlay_popup = None

        sound_files = {
            "click": ["pop.ogg", "pop.wav"],
            "win": ["correct.ogg", "correct.wav"],
            "fail": ["wrong.ogg", "wrong.wav"],
            "reset": ["reset.ogg", "reset.wav"]
        }
        self.sounds = {}
        for key, files in sound_files.items():
            loaded_sound = None
            for filename in files:
                sound_path = os.path.join("assets", "audio", filename)
                if os.path.exists(sound_path):
                    loaded_sound = SoundLoader.load(sound_path)
                    if loaded_sound:
                        break
            self.sounds[key] = loaded_sound

        self.main_container = FloatLayout()

        bg_path = 'assets/word_search_background.png'
        self.bg_image = Image(
            source=bg_path if os.path.exists(bg_path) else '',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.08, 0.12, 0.2, 1)
        )
        self.main_container.add_widget(self.bg_image)

        # Content Vertical Wrapper to auto-stack items without overlap
        self.content_stack = BoxLayout(
            orientation='vertical',
            padding=[dp(4), dp(2)],
            spacing=dp(2),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )

        # 1. Header Navigation Bar
        self.nav_box = FloatLayout(size_hint=(1, None), height=dp(38))
        self.back_btn = Button(
            text="Games",
            size_hint=(None, None),
            size=(dp(75), dp(28)),
            pos_hint={'x': 0.02, 'center_y': 0.5},
            font_size='11sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.bind(on_release=self.go_back_to_hub)

        self.header_title = Label(
            text="[color=f1c40f]Word[/color] [color=3498db]Search[/color]",
            markup=True,
            font_size='15sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(140),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )

        self.reset_btn = Button(
            text="Reset",
            size_hint=(None, None),
            size=(dp(65), dp(28)),
            pos_hint={'right': 0.98, 'center_y': 0.5},
            font_size='11sp',
            bold=True,
            background_color=(0.85, 0.25, 0.2, 0.9),
            background_normal=''
        )
        self.reset_btn.bind(on_release=self.reset_game)

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.reset_btn)
        self.content_stack.add_widget(self.nav_box)

        # 2. Status Display Bar
        self.score_box = FloatLayout(
            size_hint=(0.96, None),
            height=dp(26),
            pos_hint={'center_x': 0.5}
        )
        with self.score_box.canvas.before:
            Color(0.04, 0.06, 0.12, 0.8)
            self.score_bg = RoundedRectangle(pos=self.score_box.pos, size=self.score_box.size, radius=[dp(6)])

        self.score_box.bind(
            pos=lambda inst, val: setattr(self.score_bg, 'pos', inst.pos),
            size=lambda inst, val: setattr(self.score_bg, 'size', inst.size)
        )

        self.lbl_status = Label(
            text="Score: [color=f1c40f]0[/color]  |  High Score: [color=2ecc71]0[/color]",
            font_size='11sp',
            bold=True,
            markup=True,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center'
        )
        self.score_box.add_widget(self.lbl_status)
        self.content_stack.add_widget(self.score_box)

        # 3. Subject Banner
        self.lbl_subject_banner = Label(
            text="SUBJECT: [color=f1c40f]GENERAL[/color]  |  Time: [color=e74c3c]60s[/color]",
            markup=True,
            font_size='11sp',
            bold=True,
            size_hint=(1, None),
            height=dp(20),
            halign='center',
            valign='middle'
        )
        self.content_stack.add_widget(self.lbl_subject_banner)

        # 4. Target Words Indicator (With Multi-Line Text Wrapping Fix)
        self.lbl_target_words = Label(
            text="Targets: ENERGY | ATOM | CELL | FORCE",
            markup=True,
            font_size='10sp',
            bold=True,
            size_hint=(1, None),
            halign='center',
            valign='middle'
        )
        self.lbl_target_words.bind(
            width=self._update_target_text_size,
            texture_size=self._update_target_height
        )
        self.content_stack.add_widget(self.lbl_target_words)

        # 5. Dynamic Play Area
        self.play_area = FloatLayout(
            size_hint=(1, 1)
        )
        self.content_stack.add_widget(self.play_area)

        self.main_container.add_widget(self.content_stack)
        self.add_widget(self.main_container)

        Window.bind(on_resize=self.on_window_resize)

    def _update_target_text_size(self, instance, width):
        instance.text_size = (max(dp(10), width - dp(16)), None)

    def _update_target_height(self, instance, texture_size):
        instance.height = max(dp(20), texture_size[1] + dp(4))

    def on_window_resize(self, instance, width, height):
        is_ultra_narrow = width < dp(320) or height < dp(340)
        
        self.nav_box.height = dp(32) if is_ultra_narrow else dp(38)
        self.back_btn.size = (dp(65), dp(24)) if is_ultra_narrow else (dp(75), dp(28))
        self.reset_btn.size = (dp(55), dp(24)) if is_ultra_narrow else (dp(65), dp(28))
        self.back_btn.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.reset_btn.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.header_title.font_size = '13sp' if is_ultra_narrow else '15sp'
        
        self.score_box.height = dp(22) if is_ultra_narrow else dp(26)
        self.lbl_status.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.lbl_subject_banner.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.lbl_target_words.font_size = '9sp' if is_ultra_narrow else '10sp'

        if self.game_active:
            self.rebuild_ui_layout()

    def rebuild_ui_layout(self):
        if not self.active_levels:
            return
        self.play_area.clear_widgets()
        self.generate_and_build_grid()
        self.build_control_buttons()

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")

    def stop_timer(self):
        if self.timer_event:
            Clock.unschedule(self.timer_event)
            self.timer_event = None

    def on_pre_enter(self):
        self.reset_game()

    def on_leave(self):
        self.stop_timer()

    def update_status_display(self):
        if self.score > self.high_score:
            self.high_score = self.score
        self.lbl_status.text = (
            f"Score: [color=f1c40f]{self.score}[/color]  |  "
            f"High Score: [color=2ecc71]{self.high_score}[/color]"
        )

    def update_words_display(self):
        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        display_targets = []
        for w_obj in level["words"]:
            w = w_obj["word"]
            if w in self.found_words:
                display_targets.append(f"[color=2ecc71][s]{w}[/s][/color]")
            else:
                display_targets.append(f"[color=ffffff]{w}[/color]")
        
        self.lbl_target_words.text = "Targets: " + " | ".join(display_targets)

    def start_new_round(self):
        self.stop_timer()
        self.dismiss_overlay()
        self.play_area.clear_widgets()

        self.game_active = True
        self.found_words = set()
        self.selected_cells = []
        self.grid_buttons = {}
        self.grid_letters = {}

        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        
        self.time_remaining = self.base_play_time + self.carryover_time
        self.carryover_time = 0  

        self.lbl_subject_banner.text = (
            f"SUBJECT: [color=f1c40f]{level['subject'].upper()}[/color]  |  "
            f"Time: [color=e74c3c]{self.time_remaining}s[/color]"
        )

        self.update_status_display()
        self.update_words_display()

        self.generate_and_build_grid()
        self.build_control_buttons()

        self.timer_event = Clock.schedule_interval(self.update_game_timer, 1.0)

    def update_game_timer(self, dt):
        self.time_remaining -= 1
        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        if self.time_remaining > 0:
            self.lbl_subject_banner.text = (
                f"SUBJECT: [color=f1c40f]{level['subject'].upper()}[/color]  |  "
                f"Time: [color=e74c3c]{self.time_remaining}s[/color]"
            )
        else:
            self.stop_timer()
            self.trigger_game_over("Time's Up!")

    def generate_and_build_grid(self):
        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        size = level["grid_size"]

        if not self.grid_letters:
            grid = [["" for _ in range(size)] for _ in range(size)]

            for w_obj in level["words"]:
                word = w_obj["word"].upper()
                placed = False
                attempts = 0

                while not placed and attempts < 100:
                    attempts += 1
                    direction = random.choice(["H", "V"])  
                    if direction == "H":
                        r = random.randint(0, size - 1)
                        c = random.randint(0, size - len(word))
                        can_place = all(grid[r][c + i] in ("", word[i]) for i in range(len(word)))
                        if can_place:
                            for i in range(len(word)):
                                grid[r][c + i] = word[i]
                            placed = True
                    else:
                        r = random.randint(0, size - len(word))
                        c = random.randint(0, size - 1)
                        can_place = all(grid[r + i][c] in ("", word[i]) for i in range(len(word)))
                        if can_place:
                            for i in range(len(word)):
                                grid[r + i][c] = word[i]
                            placed = True

            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for r in range(size):
                for c in range(size):
                    if grid[r][c] == "":
                        grid[r][c] = random.choice(alphabet)
                    self.grid_letters[(r, c)] = grid[r][c]

        # Scaled bounds for small screens
        avail_w = max(dp(180), Window.width * 0.92)
        avail_h = max(dp(160), Window.height * 0.42)
        cell_size = max(dp(16), min(dp(34), avail_w / size, avail_h / size))

        grid_layout = GridLayout(
            rows=size,
            cols=size,
            spacing=dp(1.5),
            size_hint=(None, None),
            width=cell_size * size,
            height=cell_size * size,
            pos_hint={'center_x': 0.5, 'top': 0.98}
        )

        for r in range(size):
            for c in range(size):
                char = self.grid_letters[(r, c)]
                bg_col = (0.18, 0.68, 0.3, 1) if self.is_pos_in_found_word((r, c)) else (
                    (0.9, 0.6, 0.1, 1) if (r, c) in self.selected_cells else (0.18, 0.24, 0.35, 1)
                )
                btn = Button(
                    text=char,
                    font_size=f'{max(8, int(cell_size * 0.4))}sp',
                    bold=True,
                    color=(0.9, 0.9, 0.9, 1),
                    background_color=bg_col,
                    background_normal=''
                )
                btn.bind(on_release=lambda b, pos=(r, c): self.cell_clicked(pos))
                self.grid_buttons[(r, c)] = btn
                grid_layout.add_widget(btn)

        self.play_area.add_widget(grid_layout)

    def build_control_buttons(self):
        is_narrow = Window.width < dp(340)
        
        ctrl_wrapper = BoxLayout(
            orientation='vertical',
            spacing=dp(2),
            size_hint=(None, None),
            width=min(Window.width * 0.9, dp(320)),
            height=dp(55) if is_narrow else dp(65),
            pos_hint={'center_x': 0.5, 'y': 0.01}
        )

        lbl_instructions = Label(
            text="[color=f1c40f]* Select words forward/reverse order.[/color]",
            markup=True,
            font_size='9sp' if is_narrow else '10sp',
            bold=True,
            halign='center',
            valign='middle',
            size_hint=(1, None),
            height=dp(16) if is_narrow else dp(22)
        )
        lbl_instructions.bind(size=lbl_instructions.setter('text_size'))

        ctrl_box = BoxLayout(
            orientation='horizontal',
            spacing=dp(6),
            size_hint=(None, None),
            width=min(Window.width * 0.85, dp(210)),
            height=dp(28) if is_narrow else dp(32),
            pos_hint={'center_x': 0.5}
        )

        btn_clear = Button(
            text="Clear",
            font_size='10sp' if is_narrow else '12sp',
            bold=True,
            background_color=(0.85, 0.3, 0.25, 1),
            background_normal=''
        )
        btn_clear.bind(on_release=self.clear_selection)

        btn_submit = Button(
            text="Check Word",
            font_size='10sp' if is_narrow else '12sp',
            bold=True,
            background_color=(0.18, 0.68, 0.3, 1),
            background_normal=''
        )
        btn_submit.bind(on_release=self.submit_selection)

        ctrl_box.add_widget(btn_clear)
        ctrl_box.add_widget(btn_submit)

        ctrl_wrapper.add_widget(lbl_instructions)
        ctrl_wrapper.add_widget(ctrl_box)

        self.play_area.add_widget(ctrl_wrapper)

    def cell_clicked(self, pos):
        if not self.game_active:
            return

        self.play_sound("click")
        btn = self.grid_buttons[pos]

        if pos in self.selected_cells:
            self.selected_cells.remove(pos)
            btn.background_color = (0.18, 0.24, 0.35, 1)
        else:
            self.selected_cells.append(pos)
            btn.background_color = (0.9, 0.6, 0.1, 1)  

    def clear_selection(self, instance=None):
        if not self.game_active:
            return
        self.play_sound("click")
        for pos in self.selected_cells:
            if not self.is_pos_in_found_word(pos):
                self.grid_buttons[pos].background_color = (0.18, 0.24, 0.35, 1)
        self.selected_cells = []

    def is_pos_in_found_word(self, pos):
        if pos in self.grid_buttons:
            btn = self.grid_buttons[pos]
            return list(btn.background_color) == [0.18, 0.68, 0.3, 1]
        return False

    def submit_selection(self, instance=None):
        if not self.game_active or not self.selected_cells:
            return

        selected_word = "".join(self.grid_letters[pos] for pos in self.selected_cells)
        reversed_word = selected_word[::-1]

        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        target_words = [w["word"].upper() for w in level["words"]]

        matched_word = None
        if selected_word in target_words and selected_word not in self.found_words:
            matched_word = selected_word
        elif reversed_word in target_words and reversed_word not in self.found_words:
            matched_word = reversed_word

        if matched_word:
            self.play_sound("win")
            self.found_words.add(matched_word)

            for pos in self.selected_cells:
                self.grid_buttons[pos].background_color = (0.18, 0.68, 0.3, 1)

            self.selected_cells = []
            self.update_words_display()

            if len(self.found_words) == len(target_words):
                self.stop_timer()
                
                self.score += 10
                self.carryover_time = self.time_remaining
                self.update_status_display()

                self.current_level_idx += 1
                self.start_new_round()
        else:
            self.play_sound("fail")
            self.clear_selection()

    def trigger_game_over(self, reason):
        self.stop_timer()
        self.game_active = False
        self.carryover_time = 0
        self.play_sound("fail")
        self.update_status_display()
        self.dismiss_overlay()

        popup_w = min(Window.width * 0.9, dp(260))
        self.overlay_popup = FloatLayout(
            size_hint=(None, None),
            size=(popup_w, dp(150)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        with self.overlay_popup.canvas.before:
            Color(0.12, 0.16, 0.24, 0.98)
            self.overlay_bg = RoundedRectangle(pos=self.overlay_popup.pos, size=self.overlay_popup.size, radius=[dp(10)])
            Color(0.85, 0.25, 0.2, 1)
            self.overlay_border = Line(rounded_rectangle=(self.overlay_popup.x, self.overlay_popup.y, self.overlay_popup.width, self.overlay_popup.height, dp(10)), width=dp(1.5))

        def update_popup_bg(inst, val):
            self.overlay_bg.pos = inst.pos
            self.overlay_bg.size = inst.size
            self.overlay_border.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(10))

        self.overlay_popup.bind(pos=update_popup_bg, size=update_popup_bg)

        title_lbl = Label(
            text=f"[color=e74c3c][size=16sp]GAME OVER[/size][/color]\n\n"
                 f"[color=ffffff]{reason}[/color]",
            markup=True,
            bold=True,
            halign='center',
            valign='middle',
            size_hint=(0.9, 0.55),
            pos_hint={'center_x': 0.5, 'top': 0.92}
        )

        try_again_btn = Button(
            text="Try Again",
            size_hint=(None, None),
            size=(dp(110), dp(32)),
            pos_hint={'center_x': 0.5, 'y': 0.12},
            font_size='12sp',
            bold=True,
            background_color=(0.85, 0.3, 0.2, 1),
            background_normal=''
        )
        try_again_btn.bind(on_release=self.reset_game)

        self.overlay_popup.add_widget(title_lbl)
        self.overlay_popup.add_widget(try_again_btn)
        self.main_container.add_widget(self.overlay_popup)

    def dismiss_overlay(self):
        if self.overlay_popup and self.overlay_popup.parent:
            self.main_container.remove_widget(self.overlay_popup)
            self.overlay_popup = None

    def reset_game(self, instance=None):
        self.stop_timer()
        self.play_sound("reset")
        self.score = 0
        self.carryover_time = 0
        
        loaded_levels = []
        json_path = os.path.join("assets", "data", "sabi_games_curriculum.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    word_search_data = data.get("games", {}).get("word_search", {})
                    categories = word_search_data.get("categories", [])
                    
                    for cat in categories:
                        words_list = []
                        for w in cat.get("words", []):
                            if isinstance(w, str):
                                words_list.append({"word": w, "hint": ""})
                            elif isinstance(w, dict):
                                words_list.append(w)
                                
                        if words_list:
                            loaded_levels.append({
                                "subject": cat.get("title", "General Science"),
                                "grid_size": 8,
                                "words": words_list
                            })
            except Exception as e:
                print(f"[LOAD ERROR]: {e}")

        self.active_levels = loaded_levels if loaded_levels else list(WORD_SEARCH_POOL)
        random.shuffle(self.active_levels)
        self.current_level_idx = 0
        self.start_new_round()

    def go_back_to_hub(self, instance):
        self.stop_timer()
        self.play_sound("click")
        self.game_active = False
        self.carryover_time = 0
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'