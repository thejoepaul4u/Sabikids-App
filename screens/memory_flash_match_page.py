import os
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
from kivy.graphics import Color, RoundedRectangle

from utils.sabi_games_curriculum_manager import SabiGamesCurriculumManager
from utils.update_popup import UpdateNotificationPopup


class MemoryCardButton(Button):
    def __init__(self, card_id, label, icon="assets/images/question.png", card_size=dp(60), **kwargs):
        super().__init__(**kwargs)
        self.card_id = card_id
        self.card_label = label
        self.card_icon = icon
        self.is_flipped = False
        self.is_matched = False
        self.size_hint = (None, None)
        self.size = (card_size, card_size)
        self.background_normal = ''

        self.layout = BoxLayout(orientation='vertical', padding=dp(2), spacing=dp(1))

        self.img_widget = Image(
            source=self.card_icon if os.path.exists(self.card_icon) else 'assets/images/question.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 0.65)
        )

        self.label_widget = Label(
            text="?",
            font_size='9sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.35),
            halign='center',
            valign='middle'
        )
        self.label_widget.bind(size=self.label_widget.setter('text_size'))

        self.layout.add_widget(self.img_widget)
        self.layout.add_widget(self.label_widget)
        self.add_widget(self.layout)

        self.bind(pos=self._update_layout, size=self._update_layout)
        self.show_back()

    def _update_layout(self, instance, value):
        self.layout.pos = self.pos
        self.layout.size = self.size

    def update_card_dimensions(self, new_size):
        self.size = (new_size, new_size)

    def show_back(self):
        self.is_flipped = False
        self.img_widget.source = 'assets/images/question.png' if os.path.exists('assets/images/question.png') else ''
        self.label_widget.text = "?"
        self.background_color = (0.12, 0.36, 0.52, 1)

    def show_front(self):
        self.is_flipped = True
        if os.path.exists(self.card_icon):
            self.img_widget.source = self.card_icon
        else:
            self.img_widget.source = 'assets/images/default_card.png'
        self.label_widget.text = self.card_label
        self.background_color = (0.2, 0.6, 0.86, 1)

    def set_matched(self):
        self.is_matched = True
        self.disabled = True
        self.background_color = (0.15, 0.65, 0.36, 1)


class MemoryFlashMatchPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'memory_card_match_page')
        super().__init__(**kwargs)

        self.cards_data = []
        self.flipped_cards = []
        self.matched_pairs_count = 0
        self.total_pairs = 0
        self.is_lock_input = True
        self.current_card_size = dp(60)

        # Score, Timer & Carryover State
        self.score = 0
        self.high_score = 0
        self.time_remaining = 0
        self.preview_time = 3
        self.play_time = 20
        self.carryover_time = 0
        self.timer_event = None

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
        self.bg_image = Image(
            source='assets/memory_card_match_background.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.2, 0.2, 0.2, 1)
        )
        self.main_container.add_widget(self.bg_image)

        # Main Vertical Layout Stack
        self.main_stack = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(4), dp(4), dp(4), dp(4)],
            spacing=dp(2)
        )

        # Header Navigation Box
        self.nav_box = FloatLayout(size_hint=(1, None), height=dp(40))
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
            text="[color=26a65b]Memory[/color] [color=e67e22]Flash Match[/color]",
            markup=True,
            font_size='15sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(180),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.main_stack.add_widget(self.nav_box)

        # Score Banner Display
        self.score_box = FloatLayout(
            size_hint=(0.96, None),
            height=dp(26),
            pos_hint={'center_x': 0.5}
        )
        with self.score_box.canvas.before:
            Color(0, 0, 0, 0.75)
            self.score_bg = RoundedRectangle(pos=self.score_box.pos, size=self.score_box.size, radius=[dp(6)])

        self.score_box.bind(
            pos=lambda inst, val: setattr(self.score_bg, 'pos', inst.pos),
            size=lambda inst, val: setattr(self.score_bg, 'size', inst.size)
        )

        self.score_label = Label(
            text="Score: 0   |   High Score: 0",
            font_size='11sp',
            bold=True,
            color=(0.95, 0.77, 0.05, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            markup=True,
            halign='center',
            valign='middle'
        )
        self.score_box.add_widget(self.score_label)
        self.main_stack.add_widget(self.score_box)

        # Feedback & Timer Card
        self.info_box = FloatLayout(size_hint=(1, None), height=dp(26))
        with self.info_box.canvas.before:
            Color(0, 0, 0, 0.65)
            self.info_bg = RoundedRectangle(pos=self.info_box.pos, size=self.info_box.size, radius=[dp(6)])

        self.info_box.bind(
            pos=lambda inst, val: setattr(self.info_bg, 'pos', inst.pos),
            size=lambda inst, val: setattr(self.info_bg, 'size', inst.size)
        )

        self.feedback_label = Label(
            text="Get Ready to Memorize!",
            font_size='11sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            markup=True,
            halign='center',
            valign='middle'
        )
        self.feedback_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(10)), None))
        )
        self.info_box.add_widget(self.feedback_label)
        self.main_stack.add_widget(self.info_box)

        # Dynamic Grid Field Container
        self.grid_wrapper = FloatLayout(size_hint=(1, 1))
        self.cards_grid = GridLayout(cols=4, spacing=dp(4), size_hint=(None, None))
        self.cards_grid.bind(minimum_width=self.cards_grid.setter('width'), minimum_height=self.cards_grid.setter('height'))
        self.cards_grid.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.grid_wrapper.add_widget(self.cards_grid)
        self.main_stack.add_widget(self.grid_wrapper)

        # Action Buttons Bottom Bar
        self.action_box = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(32))
        self.reset_btn = Button(
            text="Reset Game",
            font_size='11sp',
            bold=True,
            background_color=(0.8, 0.3, 0.2, 1),
            background_normal=''
        )
        self.reset_btn.bind(on_release=self.reset_game)

        self.next_btn = Button(
            text="Next Round ->",
            font_size='11sp',
            bold=True,
            background_color=(0.15, 0.65, 0.36, 1),
            background_normal='',
            disabled=True
        )
        self.next_btn.bind(on_release=self.start_next_round)

        self.action_box.add_widget(self.reset_btn)
        self.action_box.add_widget(self.next_btn)
        self.main_stack.add_widget(self.action_box)

        self.main_container.add_widget(self.main_stack)
        self.add_widget(self.main_container)

        Window.bind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        is_ultra_narrow = width < dp(320) or height < dp(340)

        self.nav_box.height = dp(32) if is_ultra_narrow else dp(40)
        self.back_btn.size = (dp(65), dp(24)) if is_ultra_narrow else (dp(75), dp(28))
        self.back_btn.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.header_title.font_size = '13sp' if is_ultra_narrow else '15sp'

        self.score_box.height = dp(22) if is_ultra_narrow else dp(26)
        self.score_label.font_size = '10sp' if is_ultra_narrow else '11sp'

        self.info_box.height = dp(22) if is_ultra_narrow else dp(26)
        self.feedback_label.font_size = '10sp' if is_ultra_narrow else '11sp'

        self.action_box.height = dp(28) if is_ultra_narrow else dp(32)
        self.reset_btn.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.next_btn.font_size = '10sp' if is_ultra_narrow else '11sp'

        self.recalculate_grid_dimensions()

    def recalculate_grid_dimensions(self):
        if not self.cards_grid.children:
            return

        total_cards = len(self.cards_grid.children)
        avail_w = max(dp(160), Window.width - dp(24))
        avail_h = max(dp(140), Window.height - dp(140))

        cols = self.cards_grid.cols
        rows = (total_cards + cols - 1) // cols

        max_w = (avail_w - (cols - 1) * dp(4)) / cols
        max_h = (avail_h - (rows - 1) * dp(4)) / rows

        self.current_card_size = max(dp(28), min(dp(65), max_w, max_h))

        for card in self.cards_grid.children:
            card.update_card_dimensions(self.current_card_size)

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")

    def load_game_data(self):
        pairs = SabiGamesCurriculumManager.get_game_words("memory_card_match")
        if pairs:
            return pairs

        return [
            {"card_id": "lion", "label": "LION", "icon": "assets/images/lion.png"},
            {"card_id": "dog", "label": "DOG", "icon": "assets/images/dog.png"},
            {"card_id": "cat", "label": "CAT", "icon": "assets/images/cat.png"},
            {"card_id": "fish", "label": "FISH", "icon": "assets/images/fish.png"},
            {"card_id": "apple", "label": "APPLE", "icon": "assets/images/apple.png"},
            {"card_id": "star", "label": "STAR", "icon": "assets/images/star.png"},
            {"card_id": "sun", "label": "SUN", "icon": "assets/images/sun.png"},
            {"card_id": "moon", "label": "MOON", "icon": "assets/images/moon.png"},
            {"card_id": "bird", "label": "BIRD", "icon": "assets/images/bird.png"},
            {"card_id": "tree", "label": "TREE", "icon": "assets/images/tree.png"}
        ]

    def on_pre_enter(self):
        self.cards_data = self.load_game_data()
        self.score = 0
        self.carryover_time = 0
        self.update_score_display()
        self.start_round()

        SabiGamesCurriculumManager.check_game_update(
            game_id="memory_card_match",
            on_update_found_callback=self.prompt_game_update
        )

    def on_leave(self):
        self.stop_timer()

    def prompt_game_update(self, game_id):
        def apply_update():
            success = SabiGamesCurriculumManager.apply_pending_update("memory_card_match")
            if success:
                self.cards_data = self.load_game_data()
                self.reset_game(None)

        popup = UpdateNotificationPopup(
            on_confirm_callback=apply_update,
            update_type="sabi_games",
            game_title="Memory Card Match"
        )
        popup.open()

    def update_score_display(self):
        if self.score > self.high_score:
            self.high_score = self.score
        self.score_label.text = f"Score: [color=f1c40f]{self.score}[/color]   |   High Score: [color=2ecc71]{self.high_score}[/color]"

    def stop_timer(self):
        if self.timer_event:
            Clock.unschedule(self.timer_event)
            self.timer_event = None

    def start_round(self):
        self.stop_timer()
        self.cards_grid.clear_widgets()
        self.flipped_cards.clear()
        self.matched_pairs_count = 0
        self.is_lock_input = True
        self.next_btn.disabled = True

        if not self.cards_data:
            return

        total_available = len(self.cards_data)
        min_pairs = 3
        max_pairs = min(10, total_available)

        chosen_pairs_count = random.randint(min_pairs, max_pairs)
        selected_pairs = random.sample(self.cards_data, chosen_pairs_count)
        self.total_pairs = len(selected_pairs)
        total_cards = self.total_pairs * 2

        if total_cards <= 8:
            self.cards_grid.cols = 4
            self.preview_time = 3
            self.play_time = 20
        elif total_cards <= 12:
            self.cards_grid.cols = 4
            self.preview_time = 4
            self.play_time = 30
        elif total_cards <= 16:
            self.cards_grid.cols = 4
            self.preview_time = 5
            self.play_time = 45
        else:
            self.cards_grid.cols = 5
            self.preview_time = 6
            self.play_time = 60

        deck = []
        for item in selected_pairs:
            deck.append(item.copy())
            deck.append(item.copy())

        random.shuffle(deck)

        for card_info in deck:
            btn = MemoryCardButton(
                card_id=card_info["card_id"],
                label=card_info["label"],
                icon=card_info.get("icon", "assets/images/default_card.png"),
                card_size=dp(50)
            )
            btn.show_front()
            btn.bind(on_release=self.on_card_tap)
            self.cards_grid.add_widget(btn)

        self.recalculate_grid_dimensions()

        self.time_remaining = self.preview_time
        if self.carryover_time > 0:
            self.feedback_label.text = f"Memorize {total_cards} Cards! (+{self.carryover_time}s Bonus Time)"
        else:
            self.feedback_label.text = f"Memorize {total_cards} Cards! Starting in [color=f1c40f]{self.time_remaining}s[/color]"
            
        self.timer_event = Clock.schedule_interval(self.update_preview_timer, 1.0)

    def update_preview_timer(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.feedback_label.text = f"Memorize Cards! Starting in [color=f1c40f]{self.time_remaining}s[/color]"
        else:
            self.stop_timer()
            self.hide_cards_and_start_play()

    def hide_cards_and_start_play(self):
        for card in self.cards_grid.children:
            card.show_back()

        self.is_lock_input = False
        self.time_remaining = self.play_time + self.carryover_time
        self.carryover_time = 0

        self.feedback_label.text = f"Match Pairs! Time Left: [color=e74c3c]{self.time_remaining}s[/color]"
        self.timer_event = Clock.schedule_interval(self.update_game_timer, 1.0)

    def update_game_timer(self, dt):
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self.feedback_label.text = f"Match Pairs! Time Left: [color=e74c3c]{self.time_remaining}s[/color]"
        else:
            self.stop_timer()
            self.trigger_game_over()

    def trigger_game_over(self):
        self.is_lock_input = True
        self.carryover_time = 0
        self.play_sound("fail")
        self.feedback_label.text = f"[color=e74c3c]Time's Up! Game Over![/color]"

        for card in self.cards_grid.children:
            card.show_front()

        self.update_score_display()

    def on_card_tap(self, card_btn):
        if self.is_lock_input or card_btn.is_flipped or card_btn.is_matched:
            return

        self.play_sound("click")
        card_btn.show_front()
        self.flipped_cards.append(card_btn)

        if len(self.flipped_cards) == 2:
            self.is_lock_input = True
            Clock.schedule_once(self.evaluate_flip_match, 0.4)

    def evaluate_flip_match(self, dt):
        card1, card2 = self.flipped_cards[0], self.flipped_cards[1]

        if card1.card_id == card2.card_id:
            self.play_sound("win")
            card1.set_matched()
            card2.set_matched()
            self.matched_pairs_count += 1

            self.score += 10
            self.update_score_display()

            self.feedback_label.text = f"[color=26a65b]Matched {card1.card_label}! (+10)[/color]"

            if self.matched_pairs_count == self.total_pairs:
                self.stop_timer()
                self.carryover_time = self.time_remaining
                self.feedback_label.text = f"[color=26a65b]Cleared! +{self.carryover_time}s Carried To Next Round![/color]"
                self.next_btn.disabled = False
            else:
                self.is_lock_input = False
        else:
            self.play_sound("fail")
            card1.show_back()
            card2.show_back()
            self.feedback_label.text = f"Not a match! Time Left: [color=e74c3c]{self.time_remaining}s[/color]"
            self.is_lock_input = False

        self.flipped_cards.clear()

    def reset_game(self, instance=None):
        self.play_sound("reset")
        self.score = 0
        self.carryover_time = 0
        self.update_score_display()
        self.start_round()

    def start_next_round(self, instance=None):
        self.play_sound("click")
        self.start_round()

    def go_back_to_hub(self, instance=None):
        self.play_sound("click")
        self.stop_timer()
        self.carryover_time = 0
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'