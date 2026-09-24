import os
import random
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle, Ellipse, Mesh, Rectangle
from kivy.core.window import Window

from utils.sabi_games_curriculum_manager import SabiGamesCurriculumManager
from utils.update_popup import UpdateNotificationPopup


class FallingItem(Label):
    def __init__(self, text, is_target, base_speed=0.35, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.is_target = is_target
        self.base_speed = base_speed  
        self.font_size = '12sp'
        self.bold = True
        self.color = (1, 1, 1, 1)
        self.size_hint = (None, None)
        self.halign = 'center'
        self.valign = 'middle'
        self.bind(size=self.setter('text_size'))

        self.shape_type = random.choice(["circle", "square", "rectangle", "triangle"])
        if self.shape_type == "rectangle":
            self.size = (dp(65), dp(32))
        else:
            self.size = (dp(40), dp(40))

        self.draw_shape()
        self.bind(pos=self._update_shape, size=self._update_shape)

    def draw_shape(self):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.is_target:
                Color(0.95, 0.6, 0.1, 0.95)
            else:
                Color(0.18, 0.5, 0.72, 0.9)

            if self.shape_type == "circle":
                self.bg_shape = Ellipse(pos=self.pos, size=self.size)
            elif self.shape_type in ["square", "rectangle"]:
                self.bg_shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
            elif self.shape_type == "triangle":
                x, y = self.pos
                w, h = self.size
                vertices = [x, y, 0, 0, x + w / 2, y + h, 0, 0, x + w, y, 0, 0]
                indices = [0, 1, 2]
                self.bg_shape = Mesh(vertices=vertices, indices=indices, mode='triangles')

    def _update_shape(self, instance, value):
        if hasattr(self, 'bg_shape'):
            if self.shape_type in ["circle", "square", "rectangle"]:
                self.bg_shape.pos = instance.pos
                self.bg_shape.size = instance.size
            elif self.shape_type == "triangle":
                x, y = instance.pos
                w, h = instance.size
                vertices = [x, y, 0, 0, x + w / 2, y + h, 0, 0, x + w, y, 0, 0]
                self.bg_shape.vertices = vertices


class BasketWidget(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(90), dp(36))

        with self.canvas.before:
            Color(0.90, 0.55, 0.30, 1)
            self.basket_body = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(dp(4), dp(4)), (dp(4), dp(4)), (0, 0), (0, 0)]
            )

            Color(0.70, 0.35, 0.15, 1)
            self.basket_rim = RoundedRectangle(pos=self.pos, size=(self.width, dp(4)), radius=[dp(2)])

        self.label = Label(
            text="BASKET",
            bold=True,
            font_size='10sp',
            color=(1, 1, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.4},
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, instance, value):
        self.basket_body.pos = instance.pos
        self.basket_body.size = instance.size
        self.basket_rim.pos = (instance.x, instance.y + instance.height - dp(4))
        self.basket_rim.size = (instance.width, dp(4))


class ClippedPlayArea(StencilView, FloatLayout):
    pass


class SentenceCatcherPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'phonics_catcher_page')
        super().__init__(**kwargs)

        self.curriculum = []
        self.current_statement_data = None
        self.required_words = []
        self.full_statement_text = ""
        self.current_word_index = 0
        self.caught_words = []
        self.falling_items = []
        self.game_active = False

        self.score = 0
        self.high_score = 0
        self._basket_rel_x = 0.5

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

        # Background
        bg_path = 'assets/phonics_catcher_background.png' if os.path.exists('assets/phonics_catcher_background.png') else 'assets/memory_card_match_background.png'
        self.bg_image = Image(
            source=bg_path,
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.2, 0.2, 0.2, 1)
        )
        self.main_container.add_widget(self.bg_image)

        # --- COMPACT UNIFIED TOP CONTAINER ---
        self.top_panel = BoxLayout(
            orientation='vertical',
            size_hint=(0.96, None),
            height=dp(98),
            pos_hint={'top': 0.98, 'center_x': 0.5},
            spacing=dp(2)
        )

        # 1. Header Bar
        self.nav_box = FloatLayout(size_hint=(1, None), height=dp(28))
        
        self.back_btn = Button(
            text="Games",
            size_hint=(None, None),
            size=(dp(55), dp(24)),
            pos_hint={'x': 0.0, 'center_y': 0.5},
            font_size='10sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.bind(on_release=self.go_back_to_hub)

        self.header_title = Label(
            text="[color=f39c12]Sentence[/color] [color=27ae60]Catcher[/color]",
            markup=True,
            font_size='11sp',
            bold=True,
            size_hint=(0.6, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle',
            shorten=True,
            shorten_from='right'
        )
        self.header_title.bind(size=self.header_title.setter('text_size'))

        self.reset_btn = Button(
            text="Reset",
            size_hint=(None, None),
            size=(dp(50), dp(24)),
            pos_hint={'right': 1.0, 'center_y': 0.5},
            font_size='10sp',
            bold=True,
            background_color=(0.8, 0.3, 0.2, 0.9),
            background_normal=''
        )
        self.reset_btn.bind(on_release=self.reset_game)

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.reset_btn)
        self.top_panel.add_widget(self.nav_box)

        # 2. Score Banner
        self.score_box = FloatLayout(size_hint=(1, None), height=dp(22))
        with self.score_box.canvas.before:
            Color(0, 0, 0, 0.75)
            self.score_bg = RoundedRectangle(pos=self.score_box.pos, size=self.score_box.size, radius=[dp(4)])

        self.score_box.bind(pos=lambda inst, val: setattr(self.score_bg, 'pos', inst.pos),
                            size=lambda inst, val: setattr(self.score_bg, 'size', inst.size))

        self.score_label = Label(
            text="Score: 0   |   High Score: 0",
            font_size='10sp',
            bold=True,
            color=(0.95, 0.77, 0.05, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle',
            markup=True
        )
        self.score_label.bind(size=self.score_label.setter('text_size'))
        self.score_box.add_widget(self.score_label)
        self.top_panel.add_widget(self.score_box)

        # 3. Target Bar (Expanded Height & Using BoxLayout for zero overlap/clipping)
        self.target_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(42),
            padding=[dp(8), dp(2), dp(8), dp(2)],
            spacing=dp(5)
        )
        with self.target_box.canvas.before:
            Color(0, 0, 0, 0.75)
            self.target_bg = RoundedRectangle(pos=self.target_box.pos, size=self.target_box.size, radius=[dp(4)])

        self.target_box.bind(pos=lambda inst, val: setattr(self.target_bg, 'pos', inst.pos),
                             size=lambda inst, val: setattr(self.target_bg, 'size', inst.size))

        self.lbl_target_info = Label(
            text="",
            font_size='10sp',
            bold=True,
            markup=True,
            size_hint=(0.45, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_target_info.bind(size=self.lbl_target_info.setter('text_size'))

        self.lbl_status_info = Label(
            text="",
            font_size='9sp',
            bold=True,
            markup=True,
            size_hint=(0.55, 1),
            halign='right',
            valign='middle'
        )
        self.lbl_status_info.bind(size=self.lbl_status_info.setter('text_size'))

        self.target_box.add_widget(self.lbl_target_info)
        self.target_box.add_widget(self.lbl_status_info)
        self.top_panel.add_widget(self.target_box)

        self.main_container.add_widget(self.top_panel)

        # Play Area
        self.play_area = ClippedPlayArea(
            size_hint=(1, None),
            pos_hint={'x': 0}
        )
        self.main_container.add_widget(self.play_area)

        # Basket Widget
        self.basket = BasketWidget()
        self.main_container.add_widget(self.basket)

        # Bottom Control Bar
        self.bottom_bar = FloatLayout(
            size_hint=(1, None),
            height=dp(42),
            pos_hint={'x': 0, 'y': 0}
        )
        with self.bottom_bar.canvas.before:
            Color(0.20, 0.22, 0.25, 0.95)
            self.bottom_bar_bg = Rectangle(pos=self.bottom_bar.pos, size=self.bottom_bar.size)

        self.bottom_bar.bind(pos=lambda inst, val: setattr(self.bottom_bar_bg, 'pos', inst.pos),
                             size=lambda inst, val: setattr(self.bottom_bar_bg, 'size', inst.size))

        self.btn_left = Button(
            text="< LEFT",
            font_size='11sp',
            bold=True,
            size_hint=(0.48, 0.8),
            pos_hint={'x': 0.01, 'center_y': 0.5},
            background_color=(0.12, 0.14, 0.16, 1),
            background_normal=''
        )
        self.btn_left.bind(on_release=lambda x: self.move_basket(-dp(45)))

        self.btn_right = Button(
            text="RIGHT >",
            font_size='11sp',
            bold=True,
            size_hint=(0.48, 0.8),
            pos_hint={'right': 0.99, 'center_y': 0.5},
            background_color=(0.12, 0.14, 0.16, 1),
            background_normal=''
        )
        self.btn_right.bind(on_release=lambda x: self.move_basket(dp(45)))

        self.bottom_bar.add_widget(self.btn_left)
        self.bottom_bar.add_widget(self.btn_right)

        self.main_container.add_widget(self.bottom_bar)

        self.main_container.bind(height=self._sync_layout_bounds, width=self._sync_layout_bounds)
        Window.bind(on_resize=self.on_window_resize)

        self.add_widget(self.main_container)

    def on_window_resize(self, instance, width, height):
        self._sync_layout_bounds()

    def _sync_layout_bounds(self, *args):
        if self.main_container.height <= 0:
            return

        bottom_h = dp(42)
        self.play_area.y = bottom_h
        
        # Deterministically calculate top panel bottom position immediately on first frame
        top_panel_height = self.top_panel.height
        top_panel_y = self.main_container.height * 0.98 - top_panel_height
        play_area_height = top_panel_y - bottom_h

        self.play_area.height = max(dp(80), play_area_height)
        self.basket.y = bottom_h

        if self.main_container.width > 0:
            min_x = self.basket.width / 2.0 + dp(10)
            max_x = self.main_container.width - (self.basket.width / 2.0) - dp(10)
            if max_x > min_x:
                target_x = self._basket_rel_x * self.main_container.width
                self.basket.center_x = max(min_x, min(max_x, target_x))

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")

    def load_game_data(self):
        items = SabiGamesCurriculumManager.get_game_words("phonics_catcher")
        if items:
            return items

        return [
            {
                "statement": "THE BOY RAN",
                "words": [
                    {"target": "THE", "distractors": ["AND", "WAS", "FOR", "SEE"]},
                    {"target": "BOY", "distractors": ["CAT", "DOG", "MAN", "GIRL"]},
                    {"target": "RAN", "distractors": ["SAT", "FLY", "JUMP", "BIG"]}
                ]
            },
            {
                "statement": "I SEE CAT",
                "words": [
                    {"target": "I", "distractors": ["WE", "HE", "YOU", "IT"]},
                    {"target": "SEE", "distractors": ["LOOK", "RUN", "GET", "RED"]},
                    {"target": "CAT", "distractors": ["DOG", "BAT", "COW", "RAT"]}
                ]
            }
        ]

    def on_pre_enter(self):
        self.curriculum = self.load_game_data()
        self.score = 0
        self.update_score_display()
        # Force immediate layout calculation before the first frame renders
        self._sync_layout_bounds()
        Clock.schedule_once(lambda dt: self._sync_layout_bounds(), 0.05)
        
        self.start_new_round()

        Window.bind(on_keyboard=self.on_keyboard_down)

        SabiGamesCurriculumManager.check_game_update(
            game_id="phonics_catcher",
            on_update_found_callback=self.prompt_game_update
        )

    def on_leave(self):
        self.game_active = False
        Clock.unschedule(self.game_loop)
        Clock.unschedule(self.spawn_item)

        Window.unbind(on_keyboard=self.on_keyboard_down)

    def on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        if not self.game_active:
            return False

        if scancode in [276, 80, 97]:
            self.move_basket(-dp(45))
            return True
        elif scancode in [275, 79, 100]:
            self.move_basket(dp(45))
            return True

        return False

    def prompt_game_update(self, game_id):
        def apply_update():
            if SabiGamesCurriculumManager.apply_pending_update("phonics_catcher"):
                self.curriculum = self.load_game_data()
                self.reset_game(None)

        popup = UpdateNotificationPopup(
            on_confirm_callback=apply_update,
            update_type="sabi_games",
            game_title="Phonics Catcher"
        )
        popup.open()

    def update_score_display(self):
        if self.score > self.high_score:
            self.high_score = self.score
        self.score_label.text = f"Score: [color=f1c40f]{self.score}[/color]   |   High Score: [color=2ecc71]{self.high_score}[/color]"

    def start_new_round(self):
        self.clear_falling_items()
        self.caught_words.clear()
        self.current_word_index = 0
        self.lbl_status_info.text = ""

        if not self.curriculum:
            return

        self.current_statement_data = random.choice(self.curriculum)
        self.full_statement_text = self.current_statement_data.get("statement", "")
        self.required_words = self.current_statement_data.get("words", [])

        self.update_target_label()

        self._basket_rel_x = 0.5
        if self.main_container.width:
            self.basket.center_x = self.main_container.width / 2.0

        self.game_active = True
        Clock.unschedule(self.game_loop)
        Clock.unschedule(self.spawn_item)

        Clock.schedule_interval(self.game_loop, 1.0 / 60.0)
        Clock.schedule_interval(self.spawn_item, 1.4)

    def update_target_label(self):
        if self.current_word_index < len(self.required_words):
            target_word = self.required_words[self.current_word_index]["target"]
            step_str = f"({self.current_word_index + 1}/{len(self.required_words)})"
            self.lbl_target_info.text = f"Catch: [color=f1c40f]{target_word}[/color] {step_str}"

    def move_basket(self, delta_x):
        if not self.game_active or not self.main_container.width:
            return

        min_x = self.basket.width / 2.0 + dp(10)
        max_x = self.main_container.width - (self.basket.width / 2.0) - dp(10)

        if max_x > min_x:
            new_x = self.basket.center_x + delta_x
            clamped_x = max(min_x, min(max_x, new_x))
            self.basket.center_x = clamped_x
            self._basket_rel_x = clamped_x / self.main_container.width

    def spawn_item(self, dt):
        if not self.game_active or not self.play_area.width or self.current_word_index >= len(self.required_words):
            return

        current_target_obj = self.required_words[self.current_word_index]
        target_text = current_target_obj["target"]
        distractors = current_target_obj.get("distractors", ["A", "B", "C"])

        is_target = random.random() < 0.55
        text = target_text if is_target else random.choice(distractors)

        item = FallingItem(text=text, is_target=is_target, base_speed=0.35)
        spawn_x = random.uniform(dp(15), max(dp(16), self.play_area.width - dp(65)))
        # Spawn items precisely at the top edge of the play area
        item.pos = (spawn_x, max(0, self.play_area.height - dp(40)))

        self.play_area.add_widget(item)
        self.falling_items.append(item)

    def game_loop(self, dt):
        if not self.game_active or self.play_area.height <= 0:
            return

        basket_left = self.basket.x
        basket_right = self.basket.x + self.basket.width
        basket_top = self.basket.y + self.basket.height

        for item in list(self.falling_items):
            fall_pixels = self.play_area.height * item.base_speed * dt
            item.y -= fall_pixels

            item_center_x = item.x + item.width / 2.0
            abs_item_bottom = self.play_area.y + item.y

            if abs_item_bottom <= basket_top:
                if basket_left <= item_center_x <= basket_right:
                    self.handle_collisions([item])
                else:
                    if item in self.falling_items:
                        self.play_area.remove_widget(item)
                        self.falling_items.remove(item)

    def handle_collisions(self, collided_items):
        if not self.game_active or self.current_word_index >= len(self.required_words):
            return

        current_target_word = self.required_words[self.current_word_index]["target"]
        target_item = next((item for item in collided_items if item.text == current_target_word), None)

        if target_item:
            self.play_sound("win")
            self.caught_words.append(target_item.text)
            self.current_word_index += 1

            for item in collided_items:
                if item in self.falling_items:
                    self.play_area.remove_widget(item)
                    self.falling_items.remove(item)

            if self.current_word_index >= len(self.required_words):
                self.game_active = False
                Clock.unschedule(self.game_loop)
                Clock.unschedule(self.spawn_item)
                self.clear_falling_items()

                self.score += 10
                self.update_score_display()

                catched_sentence = " ".join(self.caught_words)
                self.lbl_target_info.text = f"[color=26a65b]{catched_sentence}[/color]"
                self.lbl_status_info.text = "[color=2ecc71]+10 Points![/color]"
                Clock.schedule_once(lambda dt: self.start_new_round(), 2.0)
            else:
                self.lbl_status_info.text = "[color=2ecc71]Good Catch![/color]"
                self.update_target_label()
        else:
            wrong_item = collided_items[0]
            self.play_sound("fail")
            self.game_active = False
            Clock.unschedule(self.game_loop)
            Clock.unschedule(self.spawn_item)
            self.clear_falling_items()

            self.lbl_status_info.text = f"[color=e74c3c]Game Over ({wrong_item.text})[/color]"

    def reset_game(self, instance=None):
        self.play_sound("reset")
        self.score = 0
        self.update_score_display()
        self.start_new_round()

    def clear_falling_items(self):
        for item in self.falling_items:
            self.play_area.remove_widget(item)
        self.falling_items.clear()

    def go_back_to_hub(self, instance):
        self.play_sound("click")
        self.game_active = False
        Clock.unschedule(self.game_loop)
        Clock.unschedule(self.spawn_item)
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'