import os
import random
import math
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle, Ellipse, Mesh, Line
from kivy.animation import Animation
from kivy.core.window import Window

from utils.update_popup import UpdateNotificationPopup


# Exact Primary & Secondary Palette
COLOR_MAP = {
    "red": (0.9, 0.1, 0.1, 1),
    "blue": (0.1, 0.45, 0.85, 1),
    "green": (0.15, 0.7, 0.25, 1),
    "yellow": (1.0, 0.85, 0.0, 1),
    "purple": (0.55, 0.2, 0.75, 1),
    "orange": (0.95, 0.45, 0.05, 1),
    "pink": (0.95, 0.4, 0.6, 1),
    "black": (0.1, 0.1, 0.1, 1)
}

# Standard Early-Years Geometric Figures
SHAPE_DISPLAY_NAMES = {
    "circle": "Circle",
    "square": "Square",
    "triangle": "Triangle",
    "rectangle": "Rectangle",
    "oval": "Oval",
    "diamond": "Diamond",
    "pentagon": "Pentagon",
    "hexagon": "Hexagon",
    "octagon": "Octagon",
    "star": "Star"
}

SHAPES_LIST = list(SHAPE_DISPLAY_NAMES.keys())


def generate_regular_polygon(center_x, center_y, radius, sides, start_angle=-math.pi/2):
    vertices = []
    indices = []
    vertices.extend([center_x, center_y, 0, 0])
    
    for i in range(sides):
        angle = start_angle + (2 * math.pi * i / sides)
        vx = center_x + radius * math.cos(angle)
        vy = center_y + radius * math.sin(angle)
        vertices.extend([vx, vy, 0, 0])

    for i in range(1, sides + 1):
        next_i = 1 if i == sides else i + 1
        indices.extend([0, i, next_i])

    return vertices, indices


def generate_5_point_star(center_x, center_y, outer_r, inner_r):
    vertices = []
    indices = []
    vertices.extend([center_x, center_y, 0, 0])
    points = 5
    total_vertices = points * 2

    for i in range(total_vertices):
        angle = -math.pi / 2 + (math.pi * i / points)
        r = outer_r if i % 2 == 0 else inner_r
        vx = center_x + r * math.cos(angle)
        vy = center_y + r * math.sin(angle)
        vertices.extend([vx, vy, 0, 0])

    for i in range(1, total_vertices + 1):
        next_i = 1 if i == total_vertices else i + 1
        indices.extend([0, i, next_i])

    return vertices, indices


class ShapeWidget(FloatLayout):
    def __init__(self, shape_type, color_name, widget_size=(dp(65), dp(65)), **kwargs):
        super().__init__(**kwargs)
        self.shape_type = shape_type
        self.color_name = color_name
        self.color_rgba = COLOR_MAP.get(color_name, (0.5, 0.5, 0.5, 1))
        
        self.size_hint = (None, None)
        self.size = widget_size

        display_name = SHAPE_DISPLAY_NAMES.get(shape_type, shape_type.title())
        self.label = Label(
            text=f"{color_name.title()}\n{display_name}",
            font_size='10sp',
            bold=True,
            halign='center',
            valign='middle',
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.draw_shape()
        self.add_widget(self.label)
        self.bind(pos=self._update_shape, size=self._update_shape)

    def update_attributes(self, shape_type, color_name):
        self.shape_type = shape_type
        self.color_name = color_name
        self.color_rgba = COLOR_MAP.get(color_name, (0.5, 0.5, 0.5, 1))
        display_name = SHAPE_DISPLAY_NAMES.get(shape_type, shape_type.title())
        self.label.text = f"{color_name.title()}\n{display_name}"
        self.draw_shape()

    def draw_shape(self):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        cx, cy = x + w / 2.0, y + h / 2.0
        r = min(w, h) / 2.0

        with self.canvas.before:
            Color(*self.color_rgba)

            if self.shape_type == "circle":
                Ellipse(pos=self.pos, size=self.size)

            elif self.shape_type == "oval":
                Ellipse(pos=(x, y + h * 0.15), size=(w, h * 0.7))

            elif self.shape_type == "square":
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])

            elif self.shape_type == "rectangle":
                RoundedRectangle(pos=(x, y + h * 0.2), size=(w, h * 0.6), radius=[dp(5)])

            elif self.shape_type == "triangle":
                v, ind = generate_regular_polygon(cx, cy, r, sides=3)
                Mesh(vertices=v, indices=ind, mode='triangles')

            elif self.shape_type == "diamond":
                v, ind = generate_regular_polygon(cx, cy, r, sides=4, start_angle=0)
                Mesh(vertices=v, indices=ind, mode='triangles')

            elif self.shape_type in ["pentagon", "hexagon", "octagon"]:
                sides_map = {"pentagon": 5, "hexagon": 6, "octagon": 8}
                v, ind = generate_regular_polygon(cx, cy, r, sides=sides_map[self.shape_type])
                Mesh(vertices=v, indices=ind, mode='triangles')

            elif self.shape_type == "star":
                v, ind = generate_5_point_star(cx, cy, r, r * 0.4)
                Mesh(vertices=v, indices=ind, mode='triangles')

    def _update_shape(self, instance, value):
        self.draw_shape()


class TargetBucket(Button):
    def __init__(self, shape_type, color_name, **kwargs):
        super().__init__(**kwargs)
        self.shape_type = shape_type
        self.color_name = color_name
        self.color_rgba = COLOR_MAP.get(color_name, (0.5, 0.5, 0.5, 1))

        self.size_hint = (None, None)
        self.size = (dp(80), dp(72))
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''

        with self.canvas.before:
            Color(0.12, 0.14, 0.18, 0.95)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])

            self.border_color = Color(*self.color_rgba)
            self.border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)), width=dp(2.5))

        display_name = SHAPE_DISPLAY_NAMES.get(shape_type, shape_type.title())
        self.text = f"[b]{color_name.title()}[/b]\n{display_name}"
        self.markup = True
        self.font_size = '10sp'
        self.halign = 'center'
        self.valign = 'middle'
        self.bind(size=self.setter('text_size'))

        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def update_target(self, shape_type, color_name):
        self.shape_type = shape_type
        self.color_name = color_name
        self.color_rgba = COLOR_MAP.get(color_name, (0.5, 0.5, 0.5, 1))
        display_name = SHAPE_DISPLAY_NAMES.get(shape_type, shape_type.title())
        self.text = f"[b]{color_name.title()}[/b]\n{display_name}"
        self._update_canvas(self, None)

    def _update_canvas(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_color.rgba = self.color_rgba
        self.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(10))


class ShapeColorSorterPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'shape_color_sorter_page')
        super().__init__(**kwargs)

        self.curriculum = []
        self.matches = 0
        self.target_goal = 50
        self.goal_step = 50
        self.best_goal_reached = 0
        
        self.lives = 3
        self.timer = 5
        self.round_number = 1
        self.targets = []
        self.current_ammo = None
        self.game_active = False
        self.overlay_popup = None

        # Audio
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
        bg_path = 'assets/shape_color_sorter_background.png'
        self.bg_image = Image(
            source=bg_path if os.path.exists(bg_path) else '',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(0.2, 0.2, 0.2, 1)
        )
        self.main_container.add_widget(self.bg_image)

        # Header Navigation (Compact & Scaled)
        self.nav_box = FloatLayout(size_hint=(1, None), height=dp(36), pos_hint={'top': 0.99})
        self.back_btn = Button(
            text="Games",
            size_hint=(None, None),
            size=(dp(70), dp(28)),
            pos_hint={'x': 0.02, 'center_y': 0.5},
            font_size='11sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.bind(on_release=self.go_back_to_hub)

        self.header_title = Label(
            text="[color=e74c3c]Shape[/color] & [color=3498db]Color[/color] [color=2ecc71]Sorter[/color]",
            markup=True,
            font_size='12sp',
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
            size=(dp(55), dp(28)),
            pos_hint={'right': 0.98, 'center_y': 0.5},
            font_size='11sp',
            bold=True,
            background_color=(0.8, 0.3, 0.2, 0.9),
            background_normal=''
        )
        self.reset_btn.bind(on_release=self.reset_game)

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.nav_box.add_widget(self.reset_btn)
        self.main_container.add_widget(self.nav_box)

        # Header Score Box
        self.score_box = FloatLayout(
            size_hint=(0.96, None),
            height=dp(28),
            pos_hint={'center_x': 0.5, 'top': 0.93}
        )
        with self.score_box.canvas.before:
            Color(0, 0, 0, 0.8)
            self.score_bg = RoundedRectangle(pos=self.score_box.pos, size=self.score_box.size, radius=[dp(5)])

        self.score_box.bind(pos=lambda inst, val: setattr(self.score_bg, 'pos', inst.pos),
                            size=lambda inst, val: setattr(self.score_bg, 'size', inst.size))

        self.lbl_time = Label(
            text="Time: [color=3498db]5s[/color]",
            font_size='10sp',
            bold=True,
            markup=True,
            size_hint=(None, 1),
            width=dp(75),
            pos_hint={'x': 0.02, 'center_y': 0.5},
            halign='left',
            valign='middle'
        )
        self.lbl_time.bind(size=self.lbl_time.setter('text_size'))

        self.lbl_matches = Label(
            text=f"Matches: [color=f1c40f]0[/color] (Goal: {self.target_goal})",
            font_size='10sp',
            bold=True,
            markup=True,
            size_hint=(0.5, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle',
            shorten=True
        )
        self.lbl_matches.bind(size=self.lbl_matches.setter('text_size'))

        self.lbl_lives = Label(
            text="Lives: [color=e74c3c][3/3][/color]",
            font_size='10sp',
            bold=True,
            markup=True,
            size_hint=(None, 1),
            width=dp(75),
            pos_hint={'right': 0.98, 'center_y': 0.5},
            halign='right',
            valign='middle'
        )
        self.lbl_lives.bind(size=self.lbl_lives.setter('text_size'))

        self.score_box.add_widget(self.lbl_time)
        self.score_box.add_widget(self.lbl_matches)
        self.score_box.add_widget(self.lbl_lives)
        self.main_container.add_widget(self.score_box)

        # Instruction Status
        self.lbl_status = Label(
            text="[color=f1c40f]Match the bottom shape before time runs out![/color]",
            font_size='10sp',
            bold=True,
            markup=True,
            size_hint=(0.96, None),
            height=dp(24),
            pos_hint={'center_x': 0.5, 'top': 0.86},
            halign='center',
            valign='middle',
            shorten=True,
            shorten_from='right'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        self.main_container.add_widget(self.lbl_status)

        # Play Area
        self.play_area = FloatLayout(
            size_hint=(1, None),
            pos_hint={'x': 0}
        )
        self.main_container.add_widget(self.play_area)

        self.main_container.bind(size=self._sync_layout_bounds)
        Window.bind(on_resize=self.on_window_resize)

        self.add_widget(self.main_container)

    def on_window_resize(self, instance, width, height):
        self._sync_layout_bounds()

    def _sync_layout_bounds(self, *args):
        if self.main_container.height <= 0:
            return
        # Dynamically fit play area between instruction status and bottom
        top_limit = self.main_container.height * 0.85
        bottom_limit = dp(10)
        self.play_area.y = bottom_limit
        self.play_area.height = max(dp(200), top_limit - bottom_limit)

    def play_sound(self, sound_key):
        snd = self.sounds.get(sound_key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")

    def load_game_data(self):
        dataset = []
        for color in COLOR_MAP.keys():
            for shape in SHAPES_LIST:
                dataset.append({"shape": shape, "color": color})
        return dataset

    def on_pre_enter(self):
        try:
            Window.rotation = 0
        except Exception:
            pass

        self.curriculum = self.load_game_data()
        self.matches = 0
        self.target_goal = 50
        self.best_goal_reached = 0
        self._sync_layout_bounds()
        self.show_how_to_play_popup()

    def on_leave(self):
        self.stop_game_loops()

    def stop_game_loops(self):
        self.game_active = False
        Clock.unschedule(self.timer_tick)

    def update_score_display(self):
        safe_lives = max(0, self.lives)
        self.lbl_time.text = f"Time: [color=3498db]{self.timer}s[/color]"
        self.lbl_matches.text = f"Matches: [color=f1c40f]{self.matches}[/color] (Goal: {self.target_goal})"
        self.lbl_lives.text = f"Lives: [color=e74c3c][{safe_lives}/3][/color]"

    def show_how_to_play_popup(self):
        self.stop_game_loops()
        self.dismiss_overlay()

        self.overlay_popup = FloatLayout(
            size_hint=(0.94, 0.72),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        with self.overlay_popup.canvas.before:
            Color(0.08, 0.12, 0.18, 0.98)
            self.overlay_bg = RoundedRectangle(
                pos=self.overlay_popup.pos,
                size=self.overlay_popup.size,
                radius=[dp(12)]
            )
            Color(0.2, 0.6, 0.9, 1)
            self.overlay_border = Line(
                rounded_rectangle=(self.overlay_popup.x, self.overlay_popup.y, self.overlay_popup.width, self.overlay_popup.height, dp(12)),
                width=dp(2.5)
            )

        self.overlay_popup.bind(
            pos=lambda inst, val: [
                setattr(self.overlay_bg, 'pos', inst.pos),
                setattr(self.overlay_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12)))
            ],
            size=lambda inst, val: [
                setattr(self.overlay_bg, 'size', inst.size),
                setattr(self.overlay_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12)))
            ]
        )

        instructions = (
            "[color=3498db][size=15sp]HOW TO PLAY[/size][/color]\n\n"
            "[color=ffffff]Look at the target shape appearing at the bottom of your screen.\n\n"
            "Tap the top box that matches its [color=f1c40f]exact shape and color[/color] before the timer expires.\n\n"
            "Reach [color=2ecc71]50 matches[/color] to complete your first milestone target![/color]"
        )

        intro_lbl = Label(
            text=instructions,
            markup=True,
            bold=True,
            font_size='11sp',
            halign='center',
            valign='middle',
            size_hint=(0.92, 0.65),
            pos_hint={'center_x': 0.5, 'top': 0.90}
        )
        intro_lbl.bind(size=intro_lbl.setter('text_size'))

        start_btn = Button(
            text="Let's Go!",
            size_hint=(None, None),
            size=(dp(120), dp(36)),
            pos_hint={'center_x': 0.5, 'y': 0.08},
            font_size='13sp',
            bold=True,
            background_color=(0.15, 0.65, 0.25, 1),
            background_normal=''
        )
        start_btn.bind(on_release=lambda inst: self.start_new_round())

        self.overlay_popup.add_widget(intro_lbl)
        self.overlay_popup.add_widget(start_btn)
        self.main_container.add_widget(self.overlay_popup)

    def start_new_round(self):
        self.stop_game_loops()
        self.dismiss_overlay()
        self.play_area.clear_widgets()
        self.targets.clear()

        self.lives = 3
        self.lbl_status.text = f"[color=f1c40f]Target: Hit {self.target_goal} matches to advance![/color]"
        self.update_score_display()

        # Build 3 Target Buckets at Top of Play Area
        selected_targets = random.sample(self.curriculum, min(3, len(self.curriculum)))
        count = len(selected_targets)
        for idx, target in enumerate(selected_targets):
            t = TargetBucket(shape_type=target["shape"], color_name=target["color"])
            t.pos_hint = {'center_x': (idx + 0.5) / count, 'top': 0.95}
            t.bind(on_release=self.fire_at_target)
            self.play_area.add_widget(t)
            self.targets.append(t)

        self.game_active = True
        self.spawn_ammo()

        Clock.schedule_interval(self.timer_tick, 1.0)

    def spawn_ammo(self):
        if not self.game_active or not self.targets:
            return

        self.timer = max(3, 6 - self.round_number)
        self.update_score_display()

        if self.current_ammo and self.current_ammo.parent:
            self.play_area.remove_widget(self.current_ammo)

        target = random.choice(self.targets)
        self.current_ammo = ShapeWidget(shape_type=target.shape_type, color_name=target.color_name)
        self.current_ammo.pos_hint = {'center_x': 0.5, 'y': 0.08}
        self.play_area.add_widget(self.current_ammo)

    def fire_at_target(self, target_bucket):
        if not self.game_active or not self.current_ammo:
            return

        fired_shape = self.current_ammo.shape_type
        fired_color = self.current_ammo.color_name

        if fired_shape == target_bucket.shape_type and fired_color == target_bucket.color_name:
            self.play_sound("win")
            self.matches += 1
            
            if self.matches > self.best_goal_reached:
                self.best_goal_reached = self.matches

            if self.matches >= self.target_goal:
                self.show_goal_achievement_popup()
                return
            else:
                self.lbl_status.text = "[color=2ecc71]Correct Match![/color]"
        else:
            self.lose_life("Wrong Box Selected!")

        projectile = ShapeWidget(shape_type=fired_shape, color_name=fired_color)
        projectile.pos = self.current_ammo.pos
        self.play_area.add_widget(projectile)

        target_center_x = target_bucket.x + target_bucket.width / 2.0
        target_center_y = target_bucket.y + target_bucket.height / 2.0

        anim = Animation(
            x=target_center_x - projectile.width / 2.0,
            y=target_center_y - projectile.height / 2.0,
            duration=0.15,
            transition='out_quad'
        )
        anim.bind(on_complete=lambda a, w: self.play_area.remove_widget(w) if w.parent else None)
        anim.start(projectile)

        available = list(self.curriculum)
        random.shuffle(available)
        for idx, t in enumerate(self.targets):
            data = available[idx % len(available)]
            t.update_target(data["shape"], data["color"])

        if self.game_active:
            self.spawn_ammo()

    def show_goal_achievement_popup(self):
        self.stop_game_loops()
        self.play_sound("win")
        self.update_score_display()

        self.dismiss_overlay()

        completed_goal = self.target_goal
        self.target_goal += self.goal_step

        self.overlay_popup = FloatLayout(
            size_hint=(0.94, 0.62),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        with self.overlay_popup.canvas.before:
            Color(0.08, 0.12, 0.18, 0.96)
            self.overlay_bg = RoundedRectangle(
                pos=self.overlay_popup.pos,
                size=self.overlay_popup.size,
                radius=[dp(12)]
            )
            Color(0.15, 0.7, 0.25, 1)
            self.overlay_border = Line(
                rounded_rectangle=(self.overlay_popup.x, self.overlay_popup.y, self.overlay_popup.width, self.overlay_popup.height, dp(12)),
                width=dp(2.5)
            )

        self.overlay_popup.bind(
            pos=lambda inst, val: [
                setattr(self.overlay_bg, 'pos', inst.pos),
                setattr(self.overlay_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12)))
            ],
            size=lambda inst, val: [
                setattr(self.overlay_bg, 'size', inst.size),
                setattr(self.overlay_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12)))
            ]
        )

        title_lbl = Label(
            text=f"[color=2ecc71][size=15sp]GOAL ACHIEVED![/size][/color]\n\n"
                 f"[color=ffffff]You hit the target of {completed_goal} matches![/color]\n"
                 f"[color=f1c40f]Next Goal: {self.target_goal} Matches[/color]",
            markup=True,
            bold=True,
            font_size='11sp',
            halign='center',
            valign='middle',
            size_hint=(0.92, 0.5),
            pos_hint={'center_x': 0.5, 'top': 0.90}
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))

        next_btn = Button(
            text="Let's Go!",
            size_hint=(None, None),
            size=(dp(120), dp(36)),
            pos_hint={'center_x': 0.5, 'y': 0.10},
            font_size='13sp',
            bold=True,
            background_color=(0.15, 0.65, 0.25, 1),
            background_normal=''
        )
        next_btn.bind(on_release=lambda inst: self.start_new_round())

        self.overlay_popup.add_widget(title_lbl)
        self.overlay_popup.add_widget(next_btn)
        self.main_container.add_widget(self.overlay_popup)

    def trigger_game_over(self, reason):
        self.play_sound("fail")
        self.stop_game_loops()
        self.update_score_display()

        self.dismiss_overlay()

        self.overlay_popup = FloatLayout(
            size_hint=(0.94, 0.62),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        with self.overlay_popup.canvas.before:
            Color(0.14, 0.08, 0.1, 0.96)
            self.overlay_bg = RoundedRectangle(
                pos=self.overlay_popup.pos,
                size=self.overlay_popup.size,
                radius=[dp(12)]
            )
            Color(0.9, 0.2, 0.2, 1)
            self.overlay_border = Line(
                rounded_rectangle=(self.overlay_popup.x, self.overlay_popup.y, self.overlay_popup.width, self.overlay_popup.height, dp(12)),
                width=dp(2.5)
            )

        self.overlay_popup.bind(
            pos=lambda inst, val: [
                setattr(self.overlay_bg, 'pos', inst.pos),
                setattr(self.overlay_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12)))
            ],
            size=lambda inst, val: [
                setattr(self.overlay_bg, 'size', inst.size),
                setattr(self.overlay_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12)))
            ]
        )

        title_lbl = Label(
            text=f"[color=e74c3c][size=15sp]GAME OVER[/size][/color]\n\n"
                 f"[color=ffffff]Out of Lives! {reason}[/color]\n\n"
                 f"[color=f1c40f]Highest Goal: {self.best_goal_reached} Matches[/color]",
            markup=True,
            bold=True,
            font_size='11sp',
            halign='center',
            valign='middle',
            size_hint=(0.92, 0.55),
            pos_hint={'center_x': 0.5, 'top': 0.90}
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))

        try_again_btn = Button(
            text="Try Again",
            size_hint=(None, None),
            size=(dp(120), dp(36)),
            pos_hint={'center_x': 0.5, 'y': 0.10},
            font_size='13sp',
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

    def timer_tick(self, dt):
        if not self.game_active:
            return

        self.timer -= 1
        self.update_score_display()

        if self.timer <= 0:
            self.lose_life("Time Expired!")
            if self.game_active:
                self.spawn_ammo()

    def lose_life(self, reason):
        self.play_sound("fail")
        self.lives -= 1
        self.lbl_status.text = f"[color=e74c3c]{reason} (-1 Life)[/color]"
        self.update_score_display()

        if self.lives <= 0:
            self.trigger_game_over(reason)

    def reset_game(self, instance=None):
        self.play_sound("reset")
        self.matches = 0
        self.target_goal = 50
        self.round_number = 1
        self.show_how_to_play_popup()

    def go_back_to_hub(self, instance):
        self.play_sound("click")
        self.stop_game_loops()
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'