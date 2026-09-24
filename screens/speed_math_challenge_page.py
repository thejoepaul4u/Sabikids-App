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
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.animation import Animation


def encode_data(plain_str):
    """Encodes math problem or answer to Base64 (reversed string) for runtime obfuscation."""
    try:
        return base64.b64encode(plain_str[::-1].encode('utf-8')).decode('utf-8')
    except Exception:
        return plain_str


def decode_data(encoded_str):
    """Decodes obfuscated Base64 string back into runtime memory."""
    try:
        reversed_str = base64.b64decode(encoded_str.encode('utf-8')).decode('utf-8')
        return reversed_str[::-1]
    except Exception:
        return encoded_str


FALLBACK_QUESTIONS = [
    {"expr": "15 + 27", "ans": "42", "type": "arithmetic"},
    {"expr": "84 - 39", "ans": "45", "type": "arithmetic"},
    {"expr": "12 * 7", "ans": "84", "type": "arithmetic"},
    {"expr": "144 / 12", "ans": "12", "type": "arithmetic"},
    {"expr": "2/5 + 1/5", "ans": "3/5", "type": "fraction"},
    {"expr": "3/4 - 1/2", "ans": "1/4", "type": "fraction"},
    {"expr": "2x + 5 = 15, x =", "ans": "5", "type": "algebra"},
    {"expr": "3x - 4 = 11, x =", "ans": "5", "type": "algebra"},
    {"expr": "x/2 + 3 = 9, x =", "ans": "12", "type": "algebra"}
]

OBFUSCATED_BANK = [
    {
        "encoded_expr": encode_data(q["expr"]),
        "encoded_ans": encode_data(q["ans"]),
        "type": q["type"]
    }
    for q in FALLBACK_QUESTIONS
]


class SpeedMathChallengePageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'speed_math_challenge_page')
        super().__init__(**kwargs)

        self.score = 0
        self.high_score = 0
        self.streak = 0
        self.time_left = 60
        self.game_active = False
        self.accepting_input = True
        self.timer_event = None
        self.active_modal = None
        self.current_problem = None
        self.feedback_event = None
        self.keypad_buttons = []

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

        # Background
        bg_path = 'assets/speed_math_background.png'
        self.bg_image = Image(
            source=bg_path if os.path.exists(bg_path) else '',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.08, 0.12, 0.2, 1)
        )
        self.root_container.add_widget(self.bg_image)

        # Responsive layout structure matching Wordle formatting metrics
        self.main_layout = BoxLayout(
            orientation='vertical',
            padding=[dp(4), dp(2)],
            spacing=dp(2),
            size_hint=(1, 1)
        )

        # 1. Header Navigation Bar (Responsive Heights & Spacing)
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
            text="[color=3498db]Speed Math[/color] [color=e74c3c]Challenge[/color]",
            markup=True,
            font_size='14sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(180),
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

        # 2. Score & Stats Dashboard
        dash_box = BoxLayout(
            orientation='horizontal',
            spacing=dp(4),
            size_hint=(1, None),
            height=dp(24)
        )
        self.lbl_score = Label(
            text="Score: 0",
            font_size='10sp',
            bold=True,
            color=(0.2, 0.8, 0.4, 1),
            size_hint_x=0.33
        )
        self.lbl_timer = Label(
            text="Time: 60s",
            font_size='10sp',
            bold=True,
            color=(0.9, 0.9, 0.9, 1),
            size_hint_x=0.33
        )
        self.lbl_streak = Label(
            text="Streak: 0x",
            font_size='10sp',
            bold=True,
            color=(0.95, 0.6, 0.1, 1),
            size_hint_x=0.34
        )

        dash_box.add_widget(self.lbl_score)
        dash_box.add_widget(self.lbl_timer)
        dash_box.add_widget(self.lbl_streak)
        self.main_layout.add_widget(dash_box)

        # 3. Main Problem Area (Flexible sizing container)
        self.problem_card = FloatLayout(size_hint=(1, 0.38))
        with self.problem_card.canvas.before:
            Color(0.12, 0.16, 0.24, 0.9)
            self.p_bg = RoundedRectangle(pos=self.problem_card.pos, size=self.problem_card.size, radius=[dp(6)])
            Color(0.2, 0.5, 0.8, 1)
            self.p_line = Line(rounded_rectangle=(self.problem_card.x, self.problem_card.y, self.problem_card.width, self.problem_card.height, dp(6)), width=dp(1.2))

        self.problem_card.bind(
            pos=lambda inst, val: [setattr(self.p_bg, 'pos', inst.pos), setattr(self.p_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(6)))],
            size=lambda inst, val: [setattr(self.p_bg, 'size', inst.size), setattr(self.p_line, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(6)))]
        )

        self.lbl_problem_type = Label(
            text="[color=f1c40f]Arithmetic[/color]",
            markup=True,
            font_size='10sp',
            bold=True,
            size_hint=(1, None),
            height=dp(20),
            pos_hint={'top': 0.95, 'center_x': 0.5}
        )
        self.lbl_problem_display = Label(
            text="Ready?",
            markup=True,
            font_size='26sp',
            bold=True,
            color=(1, 1, 1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.problem_card.add_widget(self.lbl_problem_type)
        self.problem_card.add_widget(self.lbl_problem_display)
        self.main_layout.add_widget(self.problem_card)

        # 4. Input & Controls Area
        input_box = BoxLayout(
            orientation='horizontal',
            spacing=dp(4),
            size_hint=(1, None),
            height=dp(38)
        )
        self.ans_input = TextInput(
            hint_text="Enter answer...",
            multiline=False,
            font_size='13sp',
            padding=[dp(8), dp(8)],
            size_hint_x=0.72,
            background_color=(0.18, 0.22, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.2, 0.7, 1, 1)
        )
        self.ans_input.bind(on_text_validate=self.submit_answer)

        self.submit_btn = Button(
            text="SUBMIT",
            font_size='11sp',
            bold=True,
            size_hint_x=0.28,
            background_color=(0.15, 0.65, 0.25, 1),
            background_normal=''
        )
        self.submit_btn.bind(on_release=self.submit_answer)

        input_box.add_widget(self.ans_input)
        input_box.add_widget(self.submit_btn)
        self.main_layout.add_widget(input_box)

        # 5. On-Screen Keypad (Compact responsive grid layout)
        self.keypad_grid = GridLayout(
            cols=4,
            spacing=dp(1.5),
            size_hint=(1, 0.38)
        )
        keypad_keys = ["7", "8", "9", "/", "4", "5", "6", "-", "1", "2", "3", "CLEAR", "0", ".", "DEL", "ENTER"]
        for key in keypad_keys:
            btn = Button(
                text=key,
                font_size='11sp',
                bold=True,
                background_color=(0.22, 0.28, 0.38, 1) if key not in ["ENTER", "CLEAR", "DEL"] else (0.8, 0.4, 0.1, 1) if key == "CLEAR" else (0.2, 0.6, 0.8, 1),
                background_normal=''
            )
            btn.bind(on_release=self.on_keypad_press)
            self.keypad_grid.add_widget(btn)
            self.keypad_buttons.append(btn)

        self.main_layout.add_widget(self.keypad_grid)

        self.root_container.add_widget(self.main_layout)
        self.add_widget(self.root_container)

        Window.bind(on_key_down=self._on_physical_key_down)
        Window.bind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        is_ultra_narrow = width < dp(320) or height < dp(360)

        self.nav_bar.height = dp(28) if is_ultra_narrow else dp(34)
        self.back_btn.size = (dp(60), dp(22)) if is_ultra_narrow else (dp(70), dp(26))
        self.reset_btn.size = (dp(45), dp(22)) if is_ultra_narrow else (dp(55), dp(26))
        self.header_title.font_size = '11sp' if is_ultra_narrow else '14sp'

        key_font = '9sp' if is_ultra_narrow else '11sp'
        for btn in self.keypad_buttons:
            btn.font_size = key_font

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
        self.lbl_timer.color = (0.9, 0.9, 0.9, 1)
        self.timer_event = Clock.schedule_interval(self._tick_timer, 1.0)

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def _tick_timer(self, dt):
        if not self.game_active:
            return True

        self.time_left -= 1
        self.lbl_timer.text = f"Time: {self.time_left}s"

        if self.time_left <= 10:
            self.lbl_timer.color = (1, 0.3, 0.3, 1)
        else:
            self.lbl_timer.color = (0.9, 0.9, 0.9, 1)

        if self.time_left <= 0:
            self.stop_timer()
            self.game_active = False
            self.accepting_input = False
            self.play_sound("fail")
            self.show_game_over_popup()
            return False
        return True

    def generate_dynamic_problem(self):
        p_type = random.choice(["arithmetic", "fraction", "algebra"])

        if p_type == "arithmetic":
            op = random.choice(["+", "-", "*", "/"])
            if op == "+":
                a, b = random.randint(10, 99), random.randint(10, 99)
                expr, ans = f"{a} + {b}", str(a + b)
            elif op == "-":
                a, b = random.randint(20, 99), random.randint(10, 50)
                if a < b:
                    a, b = b, a
                expr, ans = f"{a} - {b}", str(a - b)
            elif op == "*":
                a, b = random.randint(4, 15), random.randint(3, 12)
                expr, ans = f"{a} * {b}", str(a * b)
            else:
                b = random.randint(3, 12)
                ans_val = random.randint(3, 15)
                a = b * ans_val
                expr, ans = f"{a} / {b}", str(ans_val)

        elif p_type == "fraction":
            denom = random.choice([3, 4, 5, 6, 8])
            num1 = random.randint(1, denom - 1)
            num2 = random.randint(1, denom - 1)
            op = random.choice(["+", "-"])
            if op == "+":
                expr = f"{num1}/{denom} + {num2}/{denom}"
                ans = f"{num1 + num2}/{denom}"
            else:
                if num1 < num2:
                    num1, num2 = num2, num1
                expr = f"{num1}/{denom} - {num2}/{denom}"
                ans = f"{num1 - num2}/{denom}"

        else:
            coef = random.randint(2, 6)
            x_val = random.randint(2, 10)
            const = random.randint(1, 15)
            rhs = (coef * x_val) + const
            expr = f"{coef}x + {const} = {rhs}, x ="
            ans = str(x_val)

        return {
            "encoded_expr": encode_data(expr),
            "encoded_ans": encode_data(ans),
            "type": p_type
        }

    def next_question(self):
        if self.feedback_event:
            self.feedback_event.cancel()
            self.feedback_event = None

        if random.random() < 0.7:
            self.current_problem = self.generate_dynamic_problem()
        else:
            self.current_problem = random.choice(OBFUSCATED_BANK)

        raw_expr = decode_data(self.current_problem["encoded_expr"])
        p_type = self.current_problem.get("type", "Math").capitalize()

        self.lbl_problem_type.text = f"[color=f1c40f]{p_type}[/color]"
        self.lbl_problem_display.font_size = '26sp'
        self.lbl_problem_display.text = raw_expr
        self.ans_input.text = ""
        self.ans_input.focus = True

    def submit_answer(self, instance=None):
        if not self.game_active or not self.accepting_input or not self.current_problem:
            return

        user_ans = self.ans_input.text.strip().replace(" ", "")
        correct_ans = decode_data(self.current_problem["encoded_ans"]).strip().replace(" ", "")

        if user_ans == correct_ans:
            self.play_sound("win")
            self.streak += 1
            
            added_points = min(self.streak, 3)
            self.score += added_points
            
            if self.score > self.high_score:
                self.high_score = self.score

            self.lbl_score.text = f"Score: {self.score}"
            self.lbl_streak.text = f"Streak: {self.streak}x"
            
            # Reload time on correct answer
            self.start_timer()

            self.animate_feedback(correct=True)
            self.next_question()

        else:
            self.play_sound("fail")
            self.streak = max(0, self.streak - 1)
            
            penalty = max(1, min(self.streak, 3)) if self.streak > 0 else 1
            self.score = max(0, self.score - penalty)

            self.lbl_score.text = f"Score: {self.score}"
            self.lbl_streak.text = f"Streak: {self.streak}x"
            
            self.lbl_problem_display.font_size = '18sp'
            self.lbl_problem_display.text = f"[color=e74c3c]Incorrect![/color]\n[color=2ecc71]Correct: {correct_ans}[/color]"
            self.animate_feedback(correct=False)
            
            self.ans_input.text = ""
            self.accepting_input = False
            self.feedback_event = Clock.schedule_once(self._resume_after_miss, 0.8)

    def _resume_after_miss(self, dt):
        self.accepting_input = True
        if self.game_active:
            self.next_question()

    def animate_feedback(self, correct=True):
        color = (0.2, 0.8, 0.3, 1) if correct else (0.9, 0.2, 0.2, 1)
        anim = Animation(color=color, duration=0.15) + Animation(color=(1, 1, 1, 1), duration=0.15)
        anim.start(self.lbl_problem_display)

    def on_keypad_press(self, instance):
        if not self.game_active or not self.accepting_input:
            return
        self.play_sound("click")
        key = instance.text
        if key == "CLEAR":
            self.ans_input.text = ""
        elif key == "DEL":
            self.ans_input.text = self.ans_input.text[:-1]
        elif key == "ENTER":
            self.submit_answer()
        else:
            self.ans_input.text += key

    def _on_physical_key_down(self, window, key, scancode, codepoint, modifier):
        if not self.game_active or not self.accepting_input or self.active_modal:
            return False
        if key in (13, 271):
            self.submit_answer()
            return True
        return False

    def dismiss_modal(self):
        if self.active_modal:
            self.active_modal.dismiss()
            self.active_modal = None

    def show_how_to_play_popup(self):
        self.game_active = False
        self.accepting_input = False
        self.stop_timer()
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
            "[color=3498db][size=14sp]SPEED MATH CHALLENGE[/size][/color]\n\n"
            "[color=ffffff]Solve arithmetic, fractions & algebra in [color=f1c40f]60s[/color].\n\n"
            "• [color=2ecc71]Correct answers[/color] reset timer & boost streak!\n"
            "• [color=e74c3c]Missed answers[/color] reduce streak & points!\n"
            "• Keep answering correctly to survive!\n"
            "• Type simplified fractions like [color=2ecc71]3/5[/color][/color]"
        )

        lbl = Label(text=instructions, markup=True, bold=True, halign='center', valign='middle', font_size='11sp')

        start_btn = Button(
            text="Start Challenge!",
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
        self.score = 0
        self.streak = 0
        self.game_active = True
        self.accepting_input = True
        self.lbl_score.text = "Score: 0"
        self.lbl_streak.text = "Streak: 0x"

        self.next_question()
        self.start_timer()

    def show_game_over_popup(self):
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
            text=f"[color=e74c3c][size=16sp]TIME'S UP![/size][/color]\n\n"
                 f"[color=ffffff]Final Score: [color=f1c40f]{self.score}[/color][/color]\n"
                 f"[color=2ecc71]Highest Score: {self.high_score}[/color]",
            markup=True,
            bold=True,
            halign='center',
            valign='middle',
            font_size='11sp'
        )

        try_again_btn = Button(
            text="Play Again",
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
        self.show_how_to_play_popup()

    def go_back_to_hub(self, instance):
        self.stop_timer()
        self.play_sound("click")
        self.game_active = False
        self.accepting_input = False
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'