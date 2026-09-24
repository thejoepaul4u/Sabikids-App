import os
import json
import random
import base64
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.animation import Animation


def encode_word(word_str):
    """Encodes target word to Base64 (reversed string) for runtime obfuscation."""
    try:
        return base64.b64encode(word_str[::-1].encode('utf-8')).decode('utf-8')
    except Exception:
        return word_str


def decode_word(encoded_str):
    """Decodes obfuscated Base64 string back into memory target word."""
    try:
        reversed_word = base64.b64decode(encoded_str.encode('utf-8')).decode('utf-8')
        return reversed_word[::-1]
    except Exception:
        return encoded_str


RAW_WORD_BANK = [
    {"word": "LOGIC", "hint": "Reasoning conducted according to strict principles."},
    {"word": "PROOF", "hint": "Evidence establishing a fact or truth."},
    {"word": "FOCUS", "hint": "The center of interest or activity."},
    {"word": "GRAPH", "hint": "A diagram showing relations between quantities."},
    {"word": "SOLVE", "hint": "Find an answer or solution to a problem."},
    {"word": "THEORY", "hint": "A system of ideas intended to explain something."},
    {"word": "FACTOR", "hint": "A number that when multiplied yields another."},
    {"word": "ENERGY", "hint": "The capacity of a physical system to perform work."},
    {"word": "SYSTEM", "hint": "A set of principles or procedures."},
    {"word": "VECTOR", "hint": "A quantity having direction and magnitude."},
    {"word": "PRISM", "hint": "A solid geometric figure with similar ends."}
]

WORD_BANK = [
    {"encoded_word": encode_word(item["word"]), "hint": item["hint"]}
    for item in RAW_WORD_BANK
]

COLOR_CORRECT = (0.15, 0.65, 0.25, 1)
COLOR_PRESENT = (0.85, 0.65, 0.1, 1)
COLOR_ABSENT = (0.25, 0.28, 0.35, 1)
COLOR_EMPTY = (0.12, 0.14, 0.18, 0.95)
COLOR_BORDER = (0.3, 0.35, 0.45, 1)


class WordleTile(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = '14sp'
        self.bold = True
        self.halign = 'center'
        self.valign = 'middle'
        self.color = (1, 1, 1, 1)
        self.size_hint = (1, 1)

        with self.canvas.before:
            self.bg_color = Color(*COLOR_EMPTY)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4)])
            self.border_color = Color(*COLOR_BORDER)
            self.border_line = Line(rounded_rectangle=(self.x, self.y, max(dp(1), self.width), max(dp(1), self.height), dp(4)), width=dp(1.2))

        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def set_status(self, status, char=""):
        self.text = char.upper()
        if status == "correct":
            self.bg_color.rgba = COLOR_CORRECT
            self.border_color.rgba = COLOR_CORRECT
        elif status == "present":
            self.bg_color.rgba = COLOR_PRESENT
            self.border_color.rgba = COLOR_PRESENT
        elif status == "absent":
            self.bg_color.rgba = COLOR_ABSENT
            self.border_color.rgba = COLOR_ABSENT
        elif status == "active":
            self.bg_color.rgba = COLOR_EMPTY
            self.border_color.rgba = (0.9, 0.9, 0.9, 1)
        else:
            self.bg_color.rgba = COLOR_EMPTY
            self.border_color.rgba = COLOR_BORDER

    def animate_reveal(self, status, char, delay=0.0):
        def do_flip(dt):
            current_h = self.height
            anim_shrink = Animation(height=dp(2), duration=0.1)

            def on_shrink_complete(animation, instance):
                self.set_status(status, char)
                anim_expand = Animation(height=current_h, duration=0.1)
                anim_expand.start(self)

            anim_shrink.bind(on_complete=on_shrink_complete)
            anim_shrink.start(self)

        Clock.schedule_once(do_flip, delay)

    def _update_canvas(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_line.rounded_rectangle = (instance.x, instance.y, max(dp(1), instance.width), max(dp(1), instance.height), dp(4))


class KeyboardKey(Button):
    def __init__(self, key_text, **kwargs):
        super().__init__(**kwargs)
        self.key_text = key_text
        self.text = "DEL" if key_text == "DELETE" else key_text
        self.font_size = '10sp'
        self.bold = True
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.color = (1, 1, 1, 1)
        self.status = "default"

        with self.canvas.before:
            self.bg_color = Color(0.2, 0.25, 0.32, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(3)])

        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def update_status(self, new_status):
        priority = {"default": 0, "absent": 1, "present": 2, "correct": 3}
        if priority.get(new_status, 0) > priority.get(self.status, 0):
            self.status = new_status
            if new_status == "correct":
                self.bg_color.rgba = COLOR_CORRECT
            elif new_status == "present":
                self.bg_color.rgba = COLOR_PRESENT
            elif new_status == "absent":
                self.bg_color.rgba = (0.12, 0.14, 0.18, 0.7)
                self.color = (0.5, 0.5, 0.5, 1)

    def reset_key(self):
        self.status = "default"
        self.bg_color.rgba = (0.2, 0.25, 0.32, 1)
        self.color = (1, 1, 1, 1)

    def _update_canvas(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


class VocabularyWordlePageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'vocabulary_wordle_page')
        super().__init__(**kwargs)

        self.max_attempts = 6
        self.target_data = {}
        self.target_word = ""
        self.word_length = 5
        self.current_attempt = 0
        self.current_guess = ""
        self.game_active = False
        self.active_modal = None
        self.keyboard_keys = {}
        self.grid_tiles = []

        self.time_left = 60
        self.timer_event = None
        self.win_streak = 0
        self.powerup_used = False

        # Audio Setup
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

        self.root_container = FloatLayout()

        bg_path = 'assets/vocabulary_wordle_background.png'
        self.bg_image = Image(
            source=bg_path if os.path.exists(bg_path) else '',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.1, 0.12, 0.16, 1)
        )
        self.root_container.add_widget(self.bg_image)

        self.main_layout = BoxLayout(
            orientation='vertical',
            padding=[dp(4), dp(2)],
            spacing=dp(2),
            size_hint=(1, 1)
        )

        # 1. Header Navigation Bar
        self.nav_bar = FloatLayout(size_hint=(1, None), height=dp(34))
        self.back_btn = Button(
            text="Games",
            size_hint=(None, None),
            size=(dp(70), dp(26)),
            pos_hint={'x': 0, 'center_y': 0.5},
            font_size='10sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.bind(on_release=self.go_back_to_hub)

        self.header_title = Label(
            text="[color=2ecc71]Vocabulary[/color] [color=3498db]Wordle[/color]",
            markup=True,
            font_size='14sp',
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
            size=(dp(55), dp(26)),
            pos_hint={'right': 1, 'center_y': 0.5},
            font_size='10sp',
            bold=True,
            background_color=(0.8, 0.3, 0.2, 1),
            background_normal=''
        )
        self.reset_btn.bind(on_release=self.reset_game)

        self.nav_bar.add_widget(self.back_btn)
        self.nav_bar.add_widget(self.header_title)
        self.nav_bar.add_widget(self.reset_btn)
        self.main_layout.add_widget(self.nav_bar)

        # 2. Stats Dashboard
        dash_box = BoxLayout(
            orientation='horizontal',
            spacing=dp(4),
            size_hint=(1, None),
            height=dp(24)
        )
        self.lbl_timer = Label(
            text="Time: 60s",
            font_size='10sp',
            bold=True,
            color=(0.9, 0.9, 0.9, 1),
            size_hint_x=0.3
        )
        self.lbl_streak = Label(
            text="Streak: 0",
            font_size='10sp',
            bold=True,
            color=(0.95, 0.6, 0.1, 1),
            size_hint_x=0.3
        )
        self.powerup_btn = Button(
            text="Reveal Hint",
            font_size='9sp',
            bold=True,
            size_hint_x=0.4,
            background_color=(0.2, 0.6, 0.8, 1),
            background_normal=''
        )
        self.powerup_btn.bind(on_release=self.use_powerup)

        dash_box.add_widget(self.lbl_timer)
        dash_box.add_widget(self.lbl_streak)
        dash_box.add_widget(self.powerup_btn)
        self.main_layout.add_widget(dash_box)

        # 3. Hint Banner (Dynamic Wrapping & Auto-Height Fix)
        self.lbl_hint = Label(
            text="Hint: [color=f1c40f]Academic Vocabulary[/color]",
            font_size='10sp',
            bold=True,
            markup=True,
            size_hint=(1, None),
            halign='center',
            valign='middle'
        )
        with self.lbl_hint.canvas.before:
            Color(0, 0, 0, 0.4)
            self.hint_bg = RoundedRectangle(pos=self.lbl_hint.pos, size=self.lbl_hint.size, radius=[dp(4)])

        self.lbl_hint.bind(
            width=self._update_hint_text_size,
            texture_size=self._update_hint_height,
            pos=lambda inst, val: setattr(self.hint_bg, 'pos', inst.pos),
            size=lambda inst, val: setattr(self.hint_bg, 'size', inst.size)
        )
        self.main_layout.add_widget(self.lbl_hint)

        # 4. Center Grid Area
        self.board_container = FloatLayout(size_hint=(1, 0.50))
        self.main_layout.add_widget(self.board_container)

        # 5. Keyboard Layout
        self.keyboard_container = BoxLayout(
            orientation='vertical',
            spacing=dp(1.5),
            padding=[dp(1), dp(1)],
            size_hint=(1, 0.35)
        )
        self.build_keyboard()
        self.main_layout.add_widget(self.keyboard_container)

        self.root_container.add_widget(self.main_layout)
        self.add_widget(self.root_container)

        Window.bind(on_key_down=self._on_physical_key_down)
        Window.bind(on_resize=self.on_window_resize)

    def _update_hint_text_size(self, instance, width):
        instance.text_size = (max(dp(10), width - dp(12)), None)

    def _update_hint_height(self, instance, texture_size):
        instance.height = max(dp(22), texture_size[1] + dp(4))

    def on_window_resize(self, instance, width, height):
        is_ultra_narrow = width < dp(320) or height < dp(360)

        self.nav_bar.height = dp(28) if is_ultra_narrow else dp(34)
        self.back_btn.size = (dp(60), dp(22)) if is_ultra_narrow else (dp(70), dp(26))
        self.reset_btn.size = (dp(45), dp(22)) if is_ultra_narrow else (dp(55), dp(26))
        self.header_title.font_size = '12sp' if is_ultra_narrow else '14sp'

        key_font = '8sp' if is_ultra_narrow else '10sp'
        for btn in self.keyboard_keys.values():
            btn.font_size = key_font

    def load_word_bank(self):
        """Loads obfuscated words from JSON curriculum file if available, falling back to default bank."""
        curriculum_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'assets', 'data', 'sabi_games_curriculum.json'
        )
        if os.path.exists(curriculum_path):
            try:
                with open(curriculum_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                game_node = db.get("games", {}).get("vocabulary_wordle", {})
                loaded_items = []
                for cat in game_node.get("categories", []):
                    for item in cat.get("words", []):
                        if "word" in item and "hint" in item:
                            loaded_items.append({
                                "encoded_word": encode_word(item["word"].upper()),
                                "hint": item["hint"]
                            })
                if loaded_items:
                    return loaded_items
            except Exception as e:
                print(f"[WORDLE LOAD ERROR]: {e}")

        return WORD_BANK

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")

    def on_pre_enter(self):
        self.show_how_to_play_popup()

    def on_leave(self):
        self.stop_timer()
        self.game_active = False

    def start_timer(self):
        self.stop_timer()
        self.time_left = 60
        self.lbl_timer.text = f"Time: {self.time_left}s"
        self.timer_event = Clock.schedule_interval(self._tick_timer, 1.0)

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def _tick_timer(self, dt):
        if not self.game_active:
            return False
        self.time_left -= 1
        self.lbl_timer.text = f"Time: {self.time_left}s"

        if self.time_left <= 10:
            self.lbl_timer.color = (1, 0.3, 0.3, 1)
        else:
            self.lbl_timer.color = (0.9, 0.9, 0.9, 1)

        if self.time_left <= 0:
            self.stop_timer()
            self.game_active = False
            self.play_sound("fail")
            self.win_streak = 0
            self.lbl_streak.text = "Streak: 0"
            self.show_game_over_popup(reason="Time Expired!")
            return False

    def use_powerup(self, instance):
        if not self.game_active or self.powerup_used:
            return

        self.powerup_used = True
        self.powerup_btn.disabled = True
        self.powerup_btn.background_color = (0.3, 0.3, 0.3, 0.6)

        first_char = self.target_word[0]
        self.lbl_hint.text = f"First Letter: [color=2ecc71]{first_char}[/color] | {self.target_data['hint']}"

    def build_grid(self):
        self.board_container.clear_widgets()
        self.grid_tiles.clear()

        grid = GridLayout(
            rows=self.max_attempts,
            cols=self.word_length,
            spacing=dp(2),
            size_hint=(0.94, 0.96),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        for row in range(self.max_attempts):
            row_tiles = []
            for col in range(self.word_length):
                tile = WordleTile()
                grid.add_widget(tile)
                row_tiles.append(tile)
            self.grid_tiles.append(row_tiles)

        self.board_container.add_widget(grid)

    def build_keyboard(self):
        self.keyboard_container.clear_widgets()
        self.keyboard_keys.clear()

        rows = [
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
            ["ENTER", "Z", "X", "C", "V", "B", "N", "M", "DELETE"]
        ]

        for row in rows:
            row_box = BoxLayout(orientation='horizontal', spacing=dp(1.5), size_hint=(1, 1))
            for key in row:
                btn = KeyboardKey(key_text=key)
                btn.size_hint_x = 1.3 if key in ["ENTER", "DELETE"] else 1.0
                btn.bind(on_release=self.on_key_press)
                self.keyboard_keys[key] = btn
                row_box.add_widget(btn)

            self.keyboard_container.add_widget(row_box)

    def _on_physical_key_down(self, window, key, scancode, codepoint, modifier):
        if not self.game_active or self.active_modal:
            return False

        if key == 8:
            self.handle_input_action("DELETE")
            return True
        elif key in (13, 271):
            self.handle_input_action("ENTER")
            return True
        elif codepoint and codepoint.isalpha():
            self.handle_input_action(codepoint.upper())
            return True

        return False

    def on_key_press(self, instance):
        if not self.game_active:
            return
        self.handle_input_action(instance.key_text)

    def handle_input_action(self, key):
        self.play_sound("click")

        if key == "DELETE":
            if len(self.current_guess) > 0:
                self.current_guess = self.current_guess[:-1]
                self.update_current_row_tiles()

        elif key == "ENTER":
            if len(self.current_guess) == self.word_length:
                self.submit_guess()
            else:
                self.shake_current_row()
                self.lbl_hint.text = f"[color=e74c3c]Must be {self.word_length} letters long![/color]"
                Clock.schedule_once(lambda dt: self.restore_hint(), 2.0)

        else:
            if len(self.current_guess) < self.word_length:
                self.current_guess += key
                self.update_current_row_tiles()

    def shake_current_row(self):
        if self.current_attempt >= self.max_attempts:
            return
        row_tiles = self.grid_tiles[self.current_attempt]
        for tile in row_tiles:
            start_x = tile.x
            anim = (Animation(x=start_x - dp(6), duration=0.04) +
                    Animation(x=start_x + dp(6), duration=0.04) +
                    Animation(x=start_x, duration=0.04))
            anim.start(tile)

    def restore_hint(self):
        if self.target_data:
            if self.powerup_used:
                self.lbl_hint.text = f"First Letter: [color=2ecc71]{self.target_word[0]}[/color] | {self.target_data['hint']}"
            else:
                self.lbl_hint.text = f"Hint: [color=f1c40f]{self.target_data['hint']}[/color]"

    def update_current_row_tiles(self):
        if self.current_attempt >= self.max_attempts:
            return

        row_tiles = self.grid_tiles[self.current_attempt]
        for col in range(self.word_length):
            if col < len(self.current_guess):
                row_tiles[col].set_status("active", self.current_guess[col])
            else:
                row_tiles[col].set_status("empty", "")

    def submit_guess(self):
        guess = self.current_guess
        target = self.target_word
        row_tiles = self.grid_tiles[self.current_attempt]

        target_letter_counts = {}
        for char in target:
            target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

        tile_statuses = ["absent"] * self.word_length

        for i in range(self.word_length):
            if guess[i] == target[i]:
                tile_statuses[i] = "correct"
                target_letter_counts[guess[i]] -= 1

        for i in range(self.word_length):
            if tile_statuses[i] != "correct":
                char = guess[i]
                if char in target_letter_counts and target_letter_counts[char] > 0:
                    tile_statuses[i] = "present"
                    target_letter_counts[char] -= 1

        for i in range(self.word_length):
            status = tile_statuses[i]
            char = guess[i]
            row_tiles[i].animate_reveal(status, char, delay=i * 0.12)

            if char in self.keyboard_keys:
                self.keyboard_keys[char].update_status(status)

        if guess == target:
            self.stop_timer()
            self.play_sound("win")
            self.game_active = False
            self.win_streak += 1
            self.lbl_streak.text = f"Streak: {self.win_streak}"
            Clock.schedule_once(lambda dt: self.show_victory_popup(), 0.8)
            return

        self.current_attempt += 1
        self.current_guess = ""

        if self.current_attempt >= self.max_attempts:
            self.stop_timer()
            self.play_sound("fail")
            self.game_active = False
            self.win_streak = 0
            self.lbl_streak.text = "Streak: 0"
            Clock.schedule_once(lambda dt: self.show_game_over_popup(reason="Out of attempts!"), 0.8)

    def dismiss_modal(self):
        if self.active_modal:
            self.active_modal.dismiss()
            self.active_modal = None

    def show_how_to_play_popup(self):
        self.game_active = False
        self.dismiss_modal()

        modal = ModalView(
            size_hint=(0.88, 0.6),
            auto_dismiss=False,
            background_color=(0, 0, 0, 0.8)
        )

        content = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(6)
        )
        with content.canvas.before:
            Color(0.12, 0.16, 0.22, 1)
            self.m_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(8)])
            Color(0.2, 0.6, 0.9, 1)
            self.m_line = Line(rounded_rectangle=(content.x, content.y, content.width, content.height, dp(8)), width=dp(1.2))

        content.bind(
            pos=lambda inst, val: [setattr(self.m_bg, 'pos', inst.pos), setattr(self.m_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8)))],
            size=lambda inst, val: [setattr(self.m_bg, 'size', inst.size), setattr(self.m_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8)))]
        )

        instructions = (
            "[color=3498db][size=14sp]HOW TO PLAY[/size][/color]\n\n"
            "[color=ffffff]Guess the word in [color=f1c40f]6 tries & 60s[/color].\n\n"
            "• [color=2ecc71]GREEN[/color] = Correct letter & spot\n"
            "• [color=f1c40f]YELLOW[/color] = Correct letter, wrong spot\n"
            "• [color=7f8c8d]GRAY[/color] = Letter not in word[/color]"
        )

        lbl = Label(text=instructions, markup=True, bold=True, halign='center', valign='middle', font_size='11sp')

        start_btn = Button(
            text="Let's Go!",
            size_hint=(1, None),
            height=dp(32),
            font_size='12sp',
            bold=True,
            background_color=(0.15, 0.65, 0.25, 1),
            background_normal=''
        )
        start_btn.bind(on_release=lambda inst: self.start_new_game())

        content.add_widget(lbl)
        content.add_widget(start_btn)
        modal.add_widget(content)

        self.active_modal = modal
        modal.open()

    def start_new_game(self):
        self.dismiss_modal()

        bank = self.load_word_bank()
        self.target_data = random.choice(bank)
        self.target_word = decode_word(self.target_data["encoded_word"]).upper()
        self.word_length = len(self.target_word)
        self.current_attempt = 0
        self.current_guess = ""
        self.game_active = True

        self.powerup_used = False
        self.powerup_btn.disabled = False
        self.powerup_btn.background_color = (0.2, 0.6, 0.8, 1)

        self.restore_hint()
        self.build_grid()
        for key_btn in self.keyboard_keys.values():
            key_btn.reset_key()

        self.start_timer()

    def show_victory_popup(self):
        self.dismiss_modal()

        modal = ModalView(
            size_hint=(0.85, 0.45),
            auto_dismiss=False,
            background_color=(0, 0, 0, 0.8)
        )

        content = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(6)
        )
        with content.canvas.before:
            Color(0.12, 0.16, 0.22, 1)
            self.m_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(8)])
            Color(0.15, 0.7, 0.25, 1)
            self.m_line = Line(rounded_rectangle=(content.x, content.y, content.width, content.height, dp(8)), width=dp(1.2))

        content.bind(
            pos=lambda inst, val: [setattr(self.m_bg, 'pos', inst.pos), setattr(self.m_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8)))],
            size=lambda inst, val: [setattr(self.m_bg, 'size', inst.size), setattr(self.m_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8)))]
        )

        lbl = Label(
            text=f"[color=2ecc71][size=16sp]BRILLIANT![/size][/color]\n\n"
                 f"[color=ffffff]Word: [color=f1c40f]{self.target_word}[/color][/color]\n"
                 f"[color=aaaaaa]Time Left: {self.time_left}s | Streak: {self.win_streak}[/color]",
            markup=True,
            bold=True,
            halign='center',
            valign='middle',
            font_size='11sp'
        )

        next_btn = Button(
            text="Next Word",
            size_hint=(1, None),
            height=dp(32),
            font_size='12sp',
            bold=True,
            background_color=(0.15, 0.65, 0.25, 1),
            background_normal=''
        )
        next_btn.bind(on_release=lambda inst: self.start_new_game())

        content.add_widget(lbl)
        content.add_widget(next_btn)
        modal.add_widget(content)

        self.active_modal = modal
        modal.open()

    def show_game_over_popup(self, reason="Out of attempts!"):
        self.dismiss_modal()

        modal = ModalView(
            size_hint=(0.85, 0.45),
            auto_dismiss=False,
            background_color=(0, 0, 0, 0.8)
        )

        content = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(6)
        )
        with content.canvas.before:
            Color(0.14, 0.08, 0.1, 1)
            self.m_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(8)])
            Color(0.9, 0.2, 0.2, 1)
            self.m_line = Line(rounded_rectangle=(content.x, content.y, content.width, content.height, dp(8)), width=dp(1.2))

        content.bind(
            pos=lambda inst, val: [setattr(self.m_bg, 'pos', inst.pos), setattr(self.m_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8)))],
            size=lambda inst, val: [setattr(self.m_bg, 'size', inst.size), setattr(self.m_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8)))]
        )

        lbl = Label(
            text=f"[color=e74c3c][size=16sp]GAME OVER[/size][/color]\n\n"
                 f"[color=ffffff]{reason}[/color]\n"
                 f"[color=ffffff]Target Word: [color=f1c40f]{self.target_word}[/color][/color]",
            markup=True,
            bold=True,
            halign='center',
            valign='middle',
            font_size='11sp'
        )

        try_again_btn = Button(
            text="Try Again",
            size_hint=(1, None),
            height=dp(32),
            font_size='12sp',
            bold=True,
            background_color=(0.85, 0.3, 0.2, 1),
            background_normal=''
        )
        try_again_btn.bind(on_release=lambda inst: self.start_new_game())

        content.add_widget(lbl)
        content.add_widget(try_again_btn)
        modal.add_widget(content)

        self.active_modal = modal
        modal.open()

    def reset_game(self, instance=None):
        self.stop_timer()
        self.play_sound("reset")
        self.win_streak = 0
        self.lbl_streak.text = "Streak: 0"
        self.show_how_to_play_popup()

    def go_back_to_hub(self, instance):
        self.stop_timer()
        self.play_sound("click")
        self.game_active = False
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'