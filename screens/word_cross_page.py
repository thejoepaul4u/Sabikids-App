import os
import json
import math
import random
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse


class CircularWheelWidget(FloatLayout):
    """Interactive circular letter picker mimicking popular word connect games."""
    def __init__(self, letters, on_word_submitted, on_letter_selected, **kwargs):
        super().__init__(**kwargs)
        self.letters = letters
        self.on_word_submitted = on_word_submitted
        self.on_letter_selected = on_letter_selected
        self.selected_indices = []
        self.letter_buttons = []
        
        with self.canvas.before:
            Color(0.1, 0.14, 0.22, 0.85)
            self.bg_circle = Ellipse(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_graphics, size=self._update_graphics)
        self.build_wheel()

    def _update_graphics(self, instance, value):
        self.bg_circle.pos = self.pos
        self.bg_circle.size = self.size
        self.layout_buttons()

    def build_wheel(self):
        self.clear_widgets()
        self.letter_buttons = []
        
        for i, char in enumerate(self.letters):
            btn = Button(
                text=char,
                font_size='18sp',
                bold=True,
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                background_color=(0.18, 0.68, 0.3, 1),
                background_normal=''
            )
            self.letter_buttons.append(btn)
            self.add_widget(btn)
        
        self.layout_buttons()

    def layout_buttons(self):
        if not self.letter_buttons:
            return
        
        center_x = self.center_x
        center_y = self.center_y
        radius = min(self.width, self.height) * 0.32
        
        count = len(self.letter_buttons)
        for i, btn in enumerate(self.letter_buttons):
            angle = (2 * math.pi * i) / count - math.pi / 2
            bx = center_x + radius * math.cos(angle) - btn.width / 2
            by = center_y + radius * math.sin(angle) - btn.height / 2
            btn.pos = (bx, by)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.check_touch(touch, is_release=False)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self.check_touch(touch, is_release=False)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.selected_indices:
            word = "".join([self.letters[i] for i in self.selected_indices])
            self.selected_indices = []
            if self.on_word_submitted:
                self.on_word_submitted(word)
            return True
        return super().on_touch_up(touch)

    def check_touch(self, touch, is_release=False):
        for i, btn in enumerate(self.letter_buttons):
            if btn.collide_point(*btn.to_widget(*touch.pos)):
                if i not in self.selected_indices:
                    self.selected_indices.append(i)
                    current_word = "".join([self.letters[idx] for idx in self.selected_indices])
                    if self.on_letter_selected:
                        self.on_letter_selected(current_word)


class WordCrossPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'word_cross_page')
        super().__init__(**kwargs)

        self.lives = 3
        self.active_levels = []
        self.current_level_idx = 0
        self.found_words = set()
        self.cell_labels = {}
        
        self.main_container = FloatLayout()
        self.content_flow = BoxLayout(
            orientation='vertical',
            padding=[dp(10), dp(6), dp(10), dp(6)],
            spacing=dp(8),
            size_hint=(1, 1)
        )

        # Header Navigation
        self.nav_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(40))
        self.back_btn = Button(text="Games", size_hint=(None, 1), width=dp(75), bold=True)
        self.back_btn.bind(on_release=self.go_back_to_hub)
        
        self.header_title = Label(text="[color=f1c40f]Word[/color] [color=2ecc71]Cross[/color]", markup=True, font_size='16sp', bold=True)
        
        self.reset_btn = Button(text="Reset", size_hint=(None, 1), width=dp(60), bold=True, background_color=(0.85, 0.25, 0.2, 1))
        self.reset_btn.bind(on_release=self.reset_game)

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.reset_btn)
        self.content_flow.add_widget(self.nav_box)

        # Live Guess Preview Pill
        self.lbl_guess_display = Label(
            text="[color=f1c40f][size=16sp]TEND[/size][/color]",
            markup=True,
            size_hint=(1, None),
            height=dp(30),
            halign='center'
        )
        self.content_flow.add_widget(self.lbl_guess_display)

        # Grid Board Area
        self.grid_wrapper = FloatLayout(size_hint=(1, 1))
        self.content_flow.add_widget(self.grid_wrapper)

        # Circular Letter Wheel Area
        self.wheel_container = FloatLayout(size_hint=(1, None), height=dp(220))
        self.content_flow.add_widget(self.wheel_container)

        self.main_container.add_widget(self.content_flow)
        self.add_widget(self.main_container)

    def on_pre_enter(self):
        self.reset_game()

    def start_new_round(self):
        self.grid_wrapper.clear_widgets()
        self.wheel_container.clear_widgets()
        self.found_words = set()

        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        self.build_crossword_grid(level)
        self.build_letter_wheel(level)

    def build_crossword_grid(self, level):
        rows, cols = level["grid_rows"], level["grid_cols"]
        self.cell_labels = {}

        board_container = FloatLayout(size_hint=(None, None), size=(cols * dp(36), rows * dp(36)))
        board_container.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        for word, data in level["words"].items():
            for idx, (r, c) in enumerate(data["coords"]):
                if (r, c) not in self.cell_labels:
                    cell = Label(
                        text="",
                        bold=True,
                        size_hint=(None, None),
                        size=(dp(34), dp(34)),
                        pos=(c * dp(36), (rows - 1 - r) * dp(36))
                    )
                    with cell.canvas.before:
                        Color(0.2, 0.25, 0.35, 1)
                        cell.bg = RoundedRectangle(pos=cell.pos, size=cell.size, radius=[dp(4)])
                    self.cell_labels[(r, c)] = cell
                    board_container.add_widget(cell)

        self.grid_wrapper.add_widget(board_container)

    def build_letter_wheel(self, level):
        letters = level["letters"]
        self.wheel = CircularWheelWidget(
            letters=letters,
            on_word_submitted=self.check_submitted_word,
            on_letter_selected=self.update_guess_display,
            size_hint=(None, None),
            size=(dp(200), dp(200)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.wheel_container.add_widget(self.wheel)

    def update_guess_display(self, partial_word):
        self.lbl_guess_display.text = f"[color=f1c40f][size=16sp]{partial_word}[/size][/color]"

    def check_submitted_word(self, word):
        level = self.active_levels[self.current_level_idx % len(self.active_levels)]
        target_words = level["words"]

        if word in target_words and word not in self.found_words:
            self.found_words.add(word)
            for idx, (r, c) in enumerate(target_words[word]["coords"]):
                cell = self.cell_labels.get((r, c))
                if cell:
                    cell.text = word[idx]
                    cell.bg.rgb = (0.18, 0.68, 0.3)  # Green tile reveal
            self.lbl_guess_display.text = "[color=2ecc71]Correct![/color]"
            
            if len(self.found_words) == len(target_words):
                self.current_level_idx += 1
                self.start_new_round()
        else:
            self.lbl_guess_display.text = "[color=e74c3c]Try Again[/color]"

    def reset_game(self, instance=None):
        self.active_levels = [
            {
                "subject": "Vocabulary Builder",
                "letters": ["T", "E", "N", "D"],
                "grid_rows": 5,
                "grid_cols": 5,
                "words": {
                    "TEND": {"coords": [[0, 3], [1, 3], [2, 3], [3, 3]], "clue": "To care for someone or something"},
                    "DENT": {"coords": [[2, 0], [2, 1], [2, 2], [2, 3]], "clue": "A slight hollow in a surface"}
                }
            }
        ]
        self.start_new_round()

    def go_back_to_hub(self, instance):
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'