import os
import json
import random
import string

from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle

from utils.sabi_games_curriculum_manager import SabiGamesCurriculumManager
from utils.update_popup import UpdateNotificationPopup


class WordTileButton(Button):
    def __init__(self, char, tile_type="scrambled", **kwargs):
        super().__init__(**kwargs)
        self.char = char
        self.tile_type = tile_type
        self.text = f"[b]{char}[/b]"
        self.markup = True
        self.font_size = '16sp'
        self.size_hint = (None, None)
        self.size = (dp(36), dp(36))
        self.background_normal = ''
        
        if tile_type == "scrambled":
            self.background_color = (0.12, 0.36, 0.52, 1)
        elif tile_type == "placed":
            self.background_color = (0.15, 0.65, 0.36, 1)
        else:
            self.background_color = (0.25, 0.25, 0.25, 1)


class WordBuilderPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'word_builder_page')
        super().__init__(**kwargs)

        self.words_data = []
        self.current_index = 0
        self.score = 0
        self.high_score = 0
        self.target_word = ""
        self.scrambled_letters = []
        self.placed_letters = []
        self.is_game_over = False

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

        # Background Image
        self.bg_image = Image(
            source='assets/word_builder_sky.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.2, 0.2, 0.2, 1)
        )
        self.main_container.add_widget(self.bg_image)

        # Responsive Nav Header Bar
        self.nav_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(48),
            pos_hint={'top': 1, 'x': 0},
            padding=[dp(6), dp(4)],
            spacing=dp(4)
        )
        
        self.back_btn = Button(
            text="Games",
            size_hint=(None, 1),
            width=dp(70),
            font_size='11sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.bind(on_release=self.go_back_to_hub)
        
        self.header_title = Label(
            text="[color=26a65b]Word[/color] [color=e67e22]Builder[/color]",
            markup=True,
            font_size='16sp',
            bold=True,
            size_hint=(1, 1),
            halign='center',
            valign='middle',
            shorten=True
        )

        self.score_label = Label(
            text="[color=f1c40f]Score: 0[/color]\n[color=26a65b]Best: 0[/color]",
            markup=True,
            font_size='10sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(95),
            halign='right',
            valign='middle'
        )

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.score_label)
        self.main_container.add_widget(self.nav_box)

        # Main Play Area Flow
        self.content_box = BoxLayout(
            orientation='vertical',
            size_hint=(0.96, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.45},
            spacing=dp(8),
            padding=dp(4)
        )
        self.content_box.bind(minimum_height=self.content_box.setter('height'))

        # 1. Responsive Auto-Wrapping Hint Box
        self.hint_box = FloatLayout(
            size_hint=(1, None),
            height=dp(48)
        )

        with self.hint_box.canvas.before:
            Color(0, 0, 0, 0.65)
            self.hint_bg = RoundedRectangle(
                pos=self.hint_box.pos, 
                size=self.hint_box.size, 
                radius=[dp(8)]
            )

        def update_hint_bg(instance, value):
            self.hint_bg.pos = instance.pos
            self.hint_bg.size = instance.size

        self.hint_box.bind(pos=update_hint_bg, size=update_hint_bg)

        self.hint_scroll = ScrollView(
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False
        )

        self.hint_label = Label(
            text="Hint: Loading...",
            font_size='12sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        
        def _update_hint_text_dimensions(inst, val):
            inst.text_size = (max(dp(100), self.content_box.width - dp(16)), None)
            inst.texture_update()
            inst.height = max(dp(44), inst.texture_size[1] + dp(10))
            self.hint_box.height = min(dp(80), inst.height)

        self.hint_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(dp(44), val[1])))
        self.content_box.bind(width=lambda inst, val: _update_hint_text_dimensions(self.hint_label, val))

        self.hint_scroll.add_widget(self.hint_label)
        self.hint_box.add_widget(self.hint_scroll)
        self.content_box.add_widget(self.hint_box)

        # 2. Answer Target Slots Grid (Supports Wrapping Rows)
        self.answer_grid = GridLayout(
            cols=6,
            spacing=dp(4),
            size_hint=(None, None)
        )
        self.answer_grid.bind(minimum_width=self.answer_grid.setter('width'))
        self.answer_grid.bind(minimum_height=self.answer_grid.setter('height'))
        
        self.answer_wrapper = FloatLayout(size_hint=(1, None), height=dp(44))
        self.answer_grid.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.answer_wrapper.add_widget(self.answer_grid)
        self.content_box.add_widget(self.answer_wrapper)

        # 2. Scrambled Choice Tiles Grid (Supports Wrapping Rows)
        self.tiles_grid = GridLayout(
            cols=6,
            spacing=dp(4),
            size_hint=(None, None)
        )
        self.tiles_grid.bind(minimum_width=self.tiles_grid.setter('width'))
        self.tiles_grid.bind(minimum_height=self.tiles_grid.setter('height'))

        self.tiles_wrapper = FloatLayout(size_hint=(1, None), height=dp(44))
        self.tiles_grid.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.tiles_wrapper.add_widget(self.tiles_grid)
        self.content_box.add_widget(self.tiles_wrapper)

        # Result Feedback
        self.feedback_label = Label(
            text="",
            font_size='12sp',
            bold=True,
            size_hint_y=None,
            height=dp(22),
            halign='center',
            shorten=True
        )
        self.feedback_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.content_box.add_widget(self.feedback_label)

        # Action Buttons
        self.action_box = BoxLayout(
            spacing=dp(8),
            size_hint=(1, None),
            height=dp(38)
        )
        
        self.clear_btn = Button(
            text="Reset",
            font_size='12sp',
            bold=True,
            background_color=(0.8, 0.3, 0.2, 1),
            background_normal=''
        )
        self.clear_btn.bind(on_release=self.reset_current_word)

        self.next_btn = Button(
            text="Next Word ->",
            font_size='12sp',
            bold=True,
            background_color=(0.15, 0.65, 0.36, 1),
            background_normal='',
            disabled=True
        )
        self.next_btn.bind(on_release=self.load_next_word)

        self.action_box.add_widget(self.clear_btn)
        self.action_box.add_widget(self.next_btn)
        self.content_box.add_widget(self.action_box)

        self.main_container.add_widget(self.content_box)
        self.add_widget(self.main_container)

        Window.bind(on_resize=self._apply_responsive_reflow)

    def _apply_responsive_reflow(self, instance, width, height):
        scale = max(0.75, min(1.1, width / dp(360)))

        self.nav_box.height = dp(42) if width < dp(320) else dp(48)
        self.back_btn.width = dp(65 * scale)
        self.score_label.width = dp(85 * scale)

        btn_font = f"{max(9, int(11 * scale))}sp"
        self.back_btn.font_size = btn_font
        self.score_label.font_size = f"{max(9, int(10 * scale))}sp"
        self.header_title.font_size = f"{max(13, int(16 * scale))}sp"

        # 3. Always display full Score and Best Score
        self.update_score_display()

        # Dynamic Grid Wrapping for Narrow Screens
        avail_w = max(dp(120), width * 0.9)
        
        # Calculate dynamic cell sizes and columns for answer slots
        ans_count = max(1, len(self.placed_letters or "123"))
        ans_cols = min(ans_count, max(4, int(avail_w / dp(34))))
        self.answer_grid.cols = ans_cols
        
        ans_tile_s = max(dp(26), min(dp(42), (avail_w - (ans_cols * dp(4))) / ans_cols))
        ans_rows = (ans_count + ans_cols - 1) // ans_cols
        
        for child in self.answer_grid.children:
            child.size = (ans_tile_s, ans_tile_s)
            child.font_size = f"{max(10, int(ans_tile_s * 0.45))}sp"
            
        self.answer_wrapper.height = ans_rows * (ans_tile_s + dp(4))

        # Calculate dynamic cell sizes and columns for scrambled letter tiles
        tile_count = max(1, len(self.scrambled_letters or "123456"))
        tile_cols = min(tile_count, max(4, int(avail_w / dp(34))))
        self.tiles_grid.cols = tile_cols
        
        tile_s = max(dp(26), min(dp(42), (avail_w - (tile_cols * dp(4))) / tile_cols))
        tile_rows = (tile_count + tile_cols - 1) // tile_cols

        for child in self.tiles_grid.children:
            child.size = (tile_s, tile_s)
            child.font_size = f"{max(10, int(tile_s * 0.45))}sp"

        self.tiles_wrapper.height = tile_rows * (tile_s + dp(4))

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: Could not play {sound_key}: {e}")

    def load_game_data(self):
        words = SabiGamesCurriculumManager.get_game_words("word_builder")
        if words:
            random.shuffle(words)
            return words

        fallback = [
            {"word": "CAT", "hint": "A small pet that says Meow"},
            {"word": "SUN", "hint": "Shines bright in the sky"},
            {"word": "BOOK", "hint": "Something you read in school"},
            {"word": "LION", "hint": "King of the jungle"},
            {"word": "MILK", "hint": "A healthy white drink from cows"},
            {"word": "FISH", "hint": "Swims in water and has gills"}
        ]
        random.shuffle(fallback)
        return fallback

    def on_pre_enter(self):
        self.words_data = self.load_game_data()
        self.current_index = 0
        self.load_word_game()
        self._apply_responsive_reflow(Window, Window.width, Window.height)
        
        SabiGamesCurriculumManager.check_game_update(
            game_id="word_builder",
            on_update_found_callback=self.prompt_game_update
        )

    def prompt_game_update(self, game_id):
        def apply_update():
            success = SabiGamesCurriculumManager.apply_pending_update("word_builder")
            if success:
                print("[WORD BUILDER]: Content updated successfully! Reloading levels...")
                self.words_data = self.load_game_data()
                self.current_index = 0
                self.load_word_game()

        popup = UpdateNotificationPopup(
            on_confirm_callback=apply_update,
            update_type="sabi_games",
            game_title="Word Builder"
        )
        popup.open()

    def load_word_game(self):
        self.answer_grid.clear_widgets()
        self.tiles_grid.clear_widgets()
        self.feedback_label.text = ""
        self.is_game_over = False

        self.clear_btn.disabled = False
        self.next_btn.text = "Next Word ->"
        self.next_btn.disabled = True
        self.next_btn.background_color = (0.15, 0.65, 0.36, 1)

        if not self.words_data:
            return

        current_data = self.words_data[self.current_index]
        self.target_word = current_data["word"].upper()
        self.hint_label.text = f"Hint: {current_data['hint']}"

        self.placed_letters = [""] * len(self.target_word)

        letters = list(self.target_word)
        extra_count = 3 if len(self.target_word) <= 4 else 2
        
        available_distractors = [c for c in string.ascii_uppercase if c not in letters]
        distractors = random.sample(available_distractors, min(extra_count, len(available_distractors)))
        
        all_tiles = letters + distractors
        random.shuffle(all_tiles)
        self.scrambled_letters = all_tiles

        for idx in range(len(self.target_word)):
            slot_btn = WordTileButton(char="_", tile_type="empty")
            slot_btn.bind(on_release=lambda btn, i=idx: self.remove_letter_from_slot(i))
            self.answer_grid.add_widget(slot_btn)

        for idx, char in enumerate(self.scrambled_letters):
            tile_btn = WordTileButton(char=char, tile_type="scrambled")
            tile_btn.bind(on_release=lambda btn, c=char, i=idx: self.place_letter(btn, c, i))
            self.tiles_grid.add_widget(tile_btn)

        self._apply_responsive_reflow(Window, Window.width, Window.height)

    def place_letter(self, btn, char, original_idx):
        if self.is_game_over:
            return

        self.play_sound("click")

        for idx in range(len(self.placed_letters)):
            if self.placed_letters[idx] == "":
                self.placed_letters[idx] = char
                btn.disabled = True
                btn.opacity = 0.3

                slot_btn = self.answer_grid.children[len(self.target_word) - 1 - idx]
                slot_btn.text = f"[b]{char}[/b]"
                slot_btn.background_color = (0.15, 0.65, 0.36, 1)
                break

        self.check_word_completion()

    def remove_letter_from_slot(self, slot_idx):
        if self.is_game_over:
            return

        if self.placed_letters[slot_idx] != "":
            self.play_sound("click")
            removed_char = self.placed_letters[slot_idx]
            self.placed_letters[slot_idx] = ""

            slot_btn = self.answer_grid.children[len(self.target_word) - 1 - slot_idx]
            slot_btn.text = "[b]_[/b]"
            slot_btn.background_color = (0.25, 0.25, 0.25, 1)

            for child in reversed(self.tiles_grid.children):
                if child.char == removed_char and child.disabled:
                    child.disabled = False
                    child.opacity = 1.0
                    break

            self.feedback_label.text = ""

    def check_word_completion(self):
        if "" not in self.placed_letters:
            formed_word = "".join(self.placed_letters)
            if formed_word == self.target_word:
                self.is_game_over = True
                self.play_sound("win")
                self.feedback_label.text = f"[color=26a65b]Superstar! {self.target_word} is correct![/color]"
                self.feedback_label.markup = True
                self.score += 10
                
                if self.score > self.high_score:
                    self.high_score = self.score
                
                self.update_score_display()
                self.disable_all_tiles()
                self.clear_btn.disabled = True
                self.next_btn.disabled = False
            else:
                self.trigger_game_over()

    def disable_all_tiles(self):
        for child in self.tiles_grid.children:
            child.disabled = True

    def trigger_game_over(self):
        self.is_game_over = True
        self.play_sound("fail")
        self.feedback_label.text = f"[color=e74c3c]Game Over! Word: {self.target_word}[/color]"
        self.feedback_label.markup = True

        self.clear_btn.disabled = True
        self.next_btn.text = "Restart Game"
        self.next_btn.disabled = False
        self.next_btn.background_color = (0.8, 0.3, 0.2, 1)

    def update_score_display(self):
        if Window.width < dp(320):
            self.score_label.text = f"[color=f1c40f]Score: {self.score}[/color]\n[color=26a65b]Best: {self.high_score}[/color]"
        else:
            self.score_label.text = f"[color=f1c40f]Score: {self.score}[/color] | [color=26a65b]Best: {self.high_score}[/color]"

    def reset_current_word(self, instance):
        if not self.is_game_over:
            self.play_sound("reset")
            self.load_word_game()

    def load_next_word(self, instance):
        self.play_sound("click")
        if self.next_btn.text == "Restart Game":
            self.score = 0
            self.update_score_display()
            random.shuffle(self.words_data)
            self.current_index = 0
            self.load_word_game()
        else:
            self.current_index += 1
            if self.current_index >= len(self.words_data):
                random.shuffle(self.words_data)
                self.current_index = 0
            self.load_word_game()

    def go_back_to_hub(self, instance):
        self.play_sound("click")
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'