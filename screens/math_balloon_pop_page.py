import os
import random
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Ellipse

from utils.sabi_games_curriculum_manager import SabiGamesCurriculumManager
from utils.update_popup import UpdateNotificationPopup


class BalloonButton(Button):
    def __init__(self, value, color_rgb, balloon_size=(dp(55), dp(70)), **kwargs):
        super().__init__(**kwargs)
        self.value = value
        self.text = f"[b]{value}[/b]"
        self.markup = True
        self.font_size = '16sp'
        self.size_hint = (None, None)
        self.size = balloon_size
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.color_rgb = color_rgb
        self.speed = random.uniform(dp(1.0), dp(2.2))

        with self.canvas.before:
            Color(*self.color_rgb)
            self.balloon_shape = Ellipse(pos=self.pos, size=self.size)

        def update_shape(instance, value):
            self.balloon_shape.pos = instance.pos
            self.balloon_shape.size = instance.size

        self.bind(pos=update_shape, size=update_shape)


class MathBalloonPopPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'math_balloon_pop_page')
        super().__init__(**kwargs)

        self.score = 0
        self.high_score = 0
        self.target_sum = 10
        self.current_sum = 0
        self.current_op = "add"
        self.active_balloons = []
        self.selected_balloons = []
        self.game_loop_event = None
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
                    try:
                        loaded_sound = SoundLoader.load(sound_path)
                        if loaded_sound:
                            break
                    except Exception as e:
                        print(f"[AUDIO LOAD ERROR]: {e}")
            self.sounds[key] = loaded_sound

        self.main_container = FloatLayout()

        # Background
        self.bg_image = Image(
            source='assets/math_balloon_background.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.2, 0.2, 0.2, 1)
        )
        self.main_container.add_widget(self.bg_image)

        # Main Vertical Content Stack
        self.main_stack = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(4), dp(4), dp(4), dp(4)],
            spacing=dp(2)
        )

        # 1. Top Header Navigation Bar
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
            text="[color=e74c3c]Math[/color] [color=3498db]Balloon Pop[/color]",
            markup=True,
            font_size='15sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(150),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )

        self.score_label = Label(
            text="[color=f1c40f]Score: 0[/color]\n[color=26a65b]Best: 0[/color]",
            markup=True,
            font_size='10sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(80),
            pos_hint={'right': 0.98, 'center_y': 0.5},
            halign='right',
            valign='middle'
        )

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.score_label)
        self.main_stack.add_widget(self.nav_box)

        # 2. Target Display Card
        self.target_card = FloatLayout(size_hint=(0.96, None), height=dp(28), pos_hint={'center_x': 0.5})
        with self.target_card.canvas.before:
            Color(0, 0, 0, 0.65)
            self.card_bg = RoundedRectangle(pos=self.target_card.pos, size=self.target_card.size, radius=[dp(6)])

        def update_card_bg(instance, value):
            self.card_bg.pos = instance.pos
            self.card_bg.size = instance.size

        self.target_card.bind(pos=update_card_bg, size=update_card_bg)

        self.target_label = Label(
            text="",
            font_size='11sp',
            bold=True,
            markup=True,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )
        self.target_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(8)), None))
        )
        self.target_card.add_widget(self.target_label)
        self.main_stack.add_widget(self.target_card)

        # 3. Operation Mode Selection Row
        self.mode_box = BoxLayout(orientation='horizontal', spacing=dp(4), size_hint=(0.96, None), height=dp(28), pos_hint={'center_x': 0.5})
        self.op_buttons = {}
        ops = [("+ Add", "add"), ("- Sub", "subtract"), ("x Mul", "multiply"), ("/ Div", "divide")]

        for title, mode in ops:
            btn = Button(
                text=title,
                font_size='10sp',
                bold=True,
                background_normal='',
                background_color=(0.2, 0.6, 0.86, 1) if mode == self.current_op else (0.2, 0.2, 0.2, 0.7)
            )
            btn.bind(on_release=lambda instance, m=mode: self.set_operation_mode(m))
            self.op_buttons[mode] = btn
            self.mode_box.add_widget(btn)

        self.main_stack.add_widget(self.mode_box)

        # 4. Feedback & Restart Control Area
        self.feedback_box = BoxLayout(
            orientation='vertical',
            size_hint=(0.96, None),
            height=dp(30),
            pos_hint={'center_x': 0.5},
            spacing=dp(2)
        )

        self.feedback_label = Label(
            text="",
            font_size='11sp',
            bold=True,
            size_hint=(1, 1),
            halign='center',
            valign='middle',
            markup=True
        )
        self.feedback_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(8)), None))
        )

        self.retry_btn = Button(
            text="Restart Game",
            font_size='11sp',
            bold=True,
            size_hint=(1, 1),
            background_color=(0.8, 0.3, 0.2, 1),
            background_normal='',
            opacity=0,
            disabled=True
        )
        self.retry_btn.bind(on_release=self.retry_game)

        self.feedback_box.add_widget(self.feedback_label)
        self.main_stack.add_widget(self.feedback_box)

        # 5. Play Arena
        self.play_area = FloatLayout(size_hint=(1, 1))
        self.main_stack.add_widget(self.play_area)

        self.main_container.add_widget(self.main_stack)
        self.add_widget(self.main_container)

        Window.bind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        is_ultra_narrow = width < dp(320) or height < dp(340)

        self.nav_box.height = dp(32) if is_ultra_narrow else dp(38)
        self.back_btn.size = (dp(65), dp(24)) if is_ultra_narrow else (dp(75), dp(28))
        self.back_btn.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.header_title.font_size = '13sp' if is_ultra_narrow else '15sp'
        self.score_label.font_size = '9sp' if is_ultra_narrow else '10sp'

        self.target_card.height = dp(22) if is_ultra_narrow else dp(28)
        self.target_label.font_size = '10sp' if is_ultra_narrow else '11sp'

        self.mode_box.height = dp(24) if is_ultra_narrow else dp(28)
        for btn in self.op_buttons.values():
            btn.font_size = '9sp' if is_ultra_narrow else '10sp'

        self.feedback_box.height = dp(24) if is_ultra_narrow else dp(30)
        self.feedback_label.font_size = '10sp' if is_ultra_narrow else '11sp'
        self.retry_btn.font_size = '10sp' if is_ultra_narrow else '11sp'

    def set_operation_mode(self, mode):
        self.current_op = mode
        for m, btn in self.op_buttons.items():
            btn.background_color = (0.2, 0.6, 0.86, 1) if m == mode else (0.2, 0.2, 0.2, 0.7)
        self.play_sound("click")
        self.score = 0
        self.update_score_display()
        self.start_game()

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")

    def on_pre_enter(self):
        self.score = 0
        self.update_score_display()
        self.start_game()

        try:
            SabiGamesCurriculumManager.check_game_update(
                game_id="math_balloon_pop",
                on_update_found_callback=self.prompt_game_update
            )
        except Exception as e:
            print(f"[GAME SYNC ERROR]: {e}")

    def prompt_game_update(self, game_id):
        def apply_update():
            try:
                success = SabiGamesCurriculumManager.apply_pending_update("math_balloon_pop")
                if success:
                    self.start_game()
            except Exception as e:
                print(f"[UPDATE APPLY ERROR]: {e}")

        try:
            popup = UpdateNotificationPopup(
                on_confirm_callback=apply_update,
                update_type="sabi_games",
                game_title="Math Balloon Pop"
            )
            popup.open()
        except Exception as e:
            print(f"[POPUP ERROR]: {e}")

    def on_leave(self):
        if self.game_loop_event:
            self.game_loop_event.cancel()

    def start_game(self):
        self.is_game_over = False
        self.feedback_label.text = ""
        
        if self.retry_btn in self.feedback_box.children:
            self.feedback_box.remove_widget(self.retry_btn)
        if self.feedback_label not in self.feedback_box.children:
            self.feedback_box.add_widget(self.feedback_label)

        self.retry_btn.opacity = 0
        self.retry_btn.disabled = True

        self.clear_balloons()
        self.set_new_target()

        if self.game_loop_event:
            self.game_loop_event.cancel()

        self.game_loop_event = Clock.schedule_interval(self.update_game, 1 / 30.0)

    def set_new_target(self):
        self.selected_balloons.clear()
        
        if self.current_op == "add":
            self.target_sum = random.randint(6, 25)
            self.current_sum = 0
        elif self.current_op == "subtract":
            self.target_sum = random.randint(2, 12)
            self.current_sum = random.randint(15, 30)
        elif self.current_op == "multiply":
            factor1 = random.randint(2, 6)
            factor2 = random.randint(2, 5)
            self.target_sum = factor1 * factor2
            self.current_sum = 1
        elif self.current_op == "divide":
            divisor = random.randint(2, 5)
            self.target_sum = random.randint(2, 8)
            self.current_sum = self.target_sum * divisor * random.choice([2, 3])

        self.update_target_label()

    def update_target_label(self):
        op_symbols = {"add": "+", "subtract": "-", "multiply": "×", "divide": "÷"}
        sym = op_symbols.get(self.current_op, "+")
        self.target_label.text = f"Mode: [color=3498db]{sym}[/color]  |  Target: [color=f1c40f]{self.target_sum}[/color]  |  Current: [color=26a65b]{self.current_sum}[/color]"

    def update_score_display(self):
        self.score_label.text = f"[color=f1c40f]Score: {self.score}[/color]\n[color=26a65b]Best: {self.high_score}[/color]"

    def spawn_balloon(self):
        if self.is_game_over or len(self.active_balloons) >= 5:
            return

        val = random.randint(1, 10)
        colors = [
            (0.89, 0.28, 0.22, 0.95),
            (0.18, 0.53, 0.86, 0.95),
            (0.15, 0.68, 0.37, 0.95),
            (0.95, 0.61, 0.07, 0.95),
            (0.58, 0.27, 0.72, 0.95)
        ]

        b_width = max(dp(40), min(dp(65), Window.width * 0.16))
        b_height = b_width * 1.25

        balloon = BalloonButton(value=val, color_rgb=random.choice(colors), balloon_size=(b_width, b_height))
        
        max_spawn_x = max(dp(10), self.play_area.width - b_width - dp(10))
        spawn_x = random.uniform(dp(5), max_spawn_x)
        balloon.pos = (spawn_x, -b_height)
        balloon.bind(on_release=lambda btn: self.pop_balloon(btn))

        self.play_area.add_widget(balloon)
        self.active_balloons.append(balloon)

    def update_game(self, dt):
        if self.is_game_over:
            return

        try:
            if random.random() < 0.04:
                self.spawn_balloon()

            to_remove = []
            for balloon in list(self.active_balloons):
                balloon.y += balloon.speed
                if balloon.y > self.play_area.height:
                    to_remove.append(balloon)

            for balloon in to_remove:
                if balloon in self.active_balloons:
                    self.active_balloons.remove(balloon)
                if balloon in self.play_area.children:
                    self.play_area.remove_widget(balloon)
        except Exception as e:
            print(f"[GAME LOOP ERROR]: {e}")

    def pop_balloon(self, balloon):
        if self.is_game_over or balloon.disabled:
            return

        balloon.disabled = True
        self.play_sound("click")
        
        popped_value = balloon.value
        previous_sum = self.current_sum

        if self.current_op == "add":
            self.current_sum += popped_value
            is_win = self.current_sum == self.target_sum
            is_fail = self.current_sum > self.target_sum
            equation = f"{previous_sum} + {popped_value} = {self.current_sum}"
        elif self.current_op == "subtract":
            self.current_sum -= popped_value
            is_win = self.current_sum == self.target_sum
            is_fail = self.current_sum < self.target_sum
            equation = f"{previous_sum} - {popped_value} = {self.current_sum}"
        elif self.current_op == "multiply":
            self.current_sum *= popped_value
            is_win = self.current_sum == self.target_sum
            is_fail = self.current_sum > self.target_sum
            equation = f"{previous_sum} × {popped_value} = {self.current_sum}"
        elif self.current_op == "divide":
            if popped_value != 0 and self.current_sum % popped_value == 0:
                self.current_sum //= popped_value
            is_win = self.current_sum == self.target_sum
            is_fail = self.current_sum < self.target_sum
            equation = f"{previous_sum} ÷ {popped_value} = {self.current_sum}"

        if balloon in self.active_balloons:
            self.active_balloons.remove(balloon)

        if balloon in self.play_area.children:
            self.play_area.remove_widget(balloon)

        if is_win:
            self.play_sound("win")
            self.score += 10
            if self.score > self.high_score:
                self.high_score = self.score
            self.update_score_display()
            self.feedback_label.text = f"[color=26a65b]Superstar! {equation}[/color]"
            self.set_new_target()
        elif is_fail:
            correction = f"Incorrect: {equation} (Target {self.target_sum})"
            self.trigger_game_over(correction)
        else:
            self.feedback_label.text = ""
            self.update_target_label()

    def trigger_game_over(self, correction_msg):
        self.is_game_over = True
        self.play_sound("fail")

        if self.game_loop_event:
            self.game_loop_event.cancel()

        self.clear_balloons()
        
        if self.feedback_label in self.feedback_box.children:
            self.feedback_box.remove_widget(self.feedback_label)
        if self.retry_btn not in self.feedback_box.children:
            self.feedback_box.add_widget(self.retry_btn)

        self.retry_btn.text = f"Retry: {correction_msg}"
        self.retry_btn.opacity = 1
        self.retry_btn.disabled = False

    def retry_game(self, instance=None):
        self.play_sound("reset")
        self.score = 0
        self.update_score_display()
        self.start_game()

    def clear_balloons(self):
        for balloon in list(self.active_balloons):
            if balloon in self.play_area.children:
                self.play_area.remove_widget(balloon)
        self.active_balloons.clear()

    def go_back_to_hub(self, instance=None):
        self.play_sound("reset")
        if self.game_loop_event:
            self.game_loop_event.cancel()
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'