import os
import random
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.animation import Animation
from kivy.utils import platform

# Safely import plyer for mobile orientation support
try:
    from plyer import orientation
except ImportError:
    orientation = None


class KnowledgeHuntPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'flag_map_master_page')
        super().__init__(**kwargs)

        # Physics & Metrics with Initial Scale Factor Integration
        sf = self.scale_factor

        self.score = 0
        self.high_score = 0
        self.coins_collected = 0
        self.game_speed = dp(6.5) * sf
        self.gravity = dp(1.2) * sf
        self.jump_strength = dp(22) * sf
        self.move_speed = dp(5) * sf
        
        self.ground_y = dp(110) * sf
        self.player_x = dp(80) * sf
        self.player_y = self.ground_y
        self.player_vy = 0
        
        self.normal_width = dp(45) * sf
        self.normal_height = dp(58) * sf
        self.slide_height = dp(26) * sf
        
        self.is_jumping = False
        self.is_sliding = False
        self.slide_duration = 0
        self.move_left = False
        self.move_right = False
        self.game_active = False

        self.obstacles = []
        self.coins = []
        self.game_loop_event = None
        self.overlay_popup = None

        # Permanent Ground Banners
        self.ground_messages = [
            "Every obstacle bypassed brings you closer to wisdom.",
            "Dodge distractions — protect your focus to gain knowledge.",
            "Overcoming challenges is the true path to learning."
        ]
        self.message_timer = 0
        self.current_msg_idx = 0

        # Assets
        self.asset_dir = os.path.join("assets", "images", "runner")
        
        self.run_frames = [
            os.path.join(self.asset_dir, "player_run1.png"),
            os.path.join(self.asset_dir, "player_run2.png"),
            os.path.join(self.asset_dir, "player_run3.png"),
            os.path.join(self.asset_dir, "player_run4.png"),
        ]
        self.jump_frame = os.path.join(self.asset_dir, "player_jump.png")
        self.slide_frame = os.path.join(self.asset_dir, "player_slide.png")

        self.obs_low_img = os.path.join(self.asset_dir, "crate_obstacle.png")
        self.obs_high_img = os.path.join(self.asset_dir, "barrier_obstacle.png")
        self.coin_img = os.path.join(self.asset_dir, "coin.png")
        self.bg_img_path = os.path.join(self.asset_dir, "runner_bg.png")
        self.ground_img_path = os.path.join(self.asset_dir, "ground.png")

        # Control Arrow Asset Paths
        self.arrow_up_img = os.path.join(self.asset_dir, "arrow_up.png")
        self.arrow_down_img = os.path.join(self.asset_dir, "arrow_down.png")
        self.arrow_left_img = os.path.join(self.asset_dir, "arrow_left.png")
        self.arrow_right_img = os.path.join(self.asset_dir, "arrow_right.png")

        self.anim_frame_idx = 0
        self.anim_counter = 0

        # Audio
        self.sounds = {}
        sound_files = {
            "jump": "pop.wav", 
            "hit": "wrong.wav", 
            "reset": "reset.wav",
            "coin": "coin.wav"
        }
        for key, fname in sound_files.items():
            path = os.path.join("assets", "audio", fname)
            self.sounds[key] = SoundLoader.load(path) if os.path.exists(path) else None

        # Cross-platform Background Music Setup
        self.bg_music_path = os.path.join("assets", "audio", "knowledgehuntgame_bgmusic.mp3")
        self.bg_music = None

        self.main_container = FloatLayout()

        # Canvas Setup
        with self.main_container.canvas.before:
            Color(1, 1, 1, 1)
            bg_src = self.bg_img_path if os.path.exists(self.bg_img_path) else ''
            
            # Static Background
            self.bg_rect1 = Rectangle(
                pos=(0, 0),
                size=self.size,
                source=bg_src
            )
            # Textured Ground Layer
            ground_src = self.ground_img_path if os.path.exists(self.ground_img_path) else ''
            Color(0.2, 0.2, 0.2, 1)
            self.ground_rect = Rectangle(
                pos=(0, 0), 
                size=(Window.width, self.ground_y),
                source=ground_src
            )

        with self.main_container.canvas:
            Color(1, 1, 1, 1)
            first_frame = self.run_frames[0] if os.path.exists(self.run_frames[0]) else ''
            self.player_rect = Rectangle(
                pos=(self.player_x, self.player_y),
                size=(self.normal_width, self.normal_height),
                source=first_frame
            )

        self.main_container.bind(pos=self.update_canvas_bounds, size=self.update_canvas_bounds)
        Window.bind(on_resize=self.on_window_resize)

        # Header Navigation
        self.nav_box = FloatLayout(size_hint=(1, None), height=dp(48), pos_hint={'top': 1})
        self.back_btn = Button(
            text="Games",
            size_hint=(None, None),
            size=(dp(85), dp(32)),
            pos_hint={'x': 0.02, 'center_y': 0.5},
            font_size=f'{int(16 * sf)}sp',
            bold=True,
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal=''
        )
        self.back_btn.mute_sound = True
        self.bind_button_dim_effect(self.back_btn)
        self.back_btn.bind(on_release=self.go_back_to_hub)

        self.header_title = Label(
            text="[color=f1c40f]Knowledge[/color] [color=e74c3c]Hunt[/color]",
            markup=True,
            font_size=f'{int(18 * sf)}sp',
            bold=True,
            size_hint=(None, None),
            size=(dp(200), dp(48)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        self.nav_box.add_widget(self.back_btn)
        self.nav_box.add_widget(self.header_title)
        self.main_container.add_widget(self.nav_box)

        # HUD Score Header
        self.lbl_score = Label(
            text="Best: [color=2ecc71]0m[/color]  |  Scrolls: [color=f1c40f]0[/color]",
            markup=True,
            font_size=f'{int(16 * sf)}sp',
            bold=True,
            size_hint=(1, None),
            height=dp(30),
            pos_hint={'center_x': 0.5, 'top': 0.92}
        )
        self.main_container.add_widget(self.lbl_score)

        # SABI RUNNER Footer Branding (Compact size, crisp bold weight)
        self.lbl_footer = Label(
            text="[b][color=2ecc71]S[/color][color=e67e22]A[/color][color=f1c40f]B[/color][color=3498db]I[/color] [color=ffffff]RUNNER (0m)[/color][/b]",
            markup=True,
            font_size=f'{int(18 * sf)}sp', 
            size_hint=(1, None),
            height=dp(25),
            pos_hint={'center_x': 0.5, 'y': 0.015}
        )
        self.main_container.add_widget(self.lbl_footer)

        # Permanent Ground Educational Banner (Kept small and tight, fully bolded)
        self.lbl_banner = Label(
            text=f"[b][color=ffffff]{self.ground_messages[0]}[/color][/b]",
            markup=True,
            font_size=f'{int(19 * sf)}sp', 
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint=(0.85, None),
            height=dp(27),
            pos_hint={'center_x': 0.5, 'y': 0.065}
        )
        self.lbl_banner.bind(size=self.lbl_banner.setter('text_size'))
        self.main_container.add_widget(self.lbl_banner)

        # Initialize Touch Controls
        self.setup_controls()
        self.add_widget(self.main_container)

    @property
    def scale_factor(self):
        current_width = Window.width if Window.width > 0 else dp(800)
        scale = current_width / dp(800)
        return max(0.65, min(scale, 1.1))

    def update_physics_metrics(self):
        sf = self.scale_factor
        self.game_speed = dp(6.5) * sf
        self.gravity = dp(1.2) * sf
        self.jump_strength = dp(22) * sf
        self.move_speed = dp(5) * sf
        
        self.ground_y = dp(110) * sf
        self.normal_width = dp(45) * sf
        self.normal_height = dp(58) * sf
        self.slide_height = dp(26) * sf

    def bind_button_dim_effect(self, btn):
        def on_press_effect(instance):
            Animation(opacity=0.6, d=0.05).start(instance)
            
        def on_release_effect(instance):
            Animation(opacity=1.0, d=0.1).start(instance)

        btn.bind(on_press=on_press_effect)
        btn.bind(on_release=on_release_effect)

    def setup_controls(self):
        sf = self.scale_factor
        
        btn_w = max(dp(42), dp(52) * sf)
        btn_h = max(dp(36), dp(45) * sf)
        self.btn_sz = (btn_w, btn_h)
        self.btn_spacing = dp(8) * sf

        # ------------------ LEFT SIDE: MOVEMENT (LEFT / RIGHT) ------------------
        btn_left_src = self.arrow_left_img if os.path.exists(self.arrow_left_img) else ''
        self.btn_left = Button(
            text="" if btn_left_src else "◄",
            font_size=f'{int(20 * sf)}sp',
            bold=True,
            size_hint=(None, None),
            size=self.btn_sz,
            pos_hint={'x': 0.02},
            background_normal=btn_left_src,
            background_down=btn_left_src,
            background_color=(1, 1, 1, 1) if btn_left_src else (0.2, 0.25, 0.38, 0.95),
            border=(0, 0, 0, 0)
        )
        self.btn_left.mute_sound = True
        self.bind_button_dim_effect(self.btn_left)
        self.btn_left.bind(on_press=lambda b: setattr(self, 'move_left', True))
        self.btn_left.bind(on_release=lambda b: setattr(self, 'move_left', False))

        btn_right_src = self.arrow_right_img if os.path.exists(self.arrow_right_img) else ''
        self.btn_right = Button(
            text="" if btn_right_src else "►",
            font_size=f'{int(20 * sf)}sp',
            bold=True,
            size_hint=(None, None),
            size=self.btn_sz,
            pos_hint={'x': 0.02 + (btn_w / Window.width) + dp(10) / Window.width},
            background_normal=btn_right_src,
            background_down=btn_right_src,
            background_color=(1, 1, 1, 1) if btn_right_src else (0.2, 0.25, 0.38, 0.95),
            border=(0, 0, 0, 0)
        )
        self.btn_right.mute_sound = True
        self.bind_button_dim_effect(self.btn_right)
        self.btn_right.bind(on_press=lambda b: setattr(self, 'move_right', True))
        self.btn_right.bind(on_release=lambda b: setattr(self, 'move_right', False))

        # ------------------ RIGHT SIDE: ACTIONS (JUMP / SLIDE STACKED) ------------------
        btn_up_src = self.arrow_up_img if os.path.exists(self.arrow_up_img) else ''
        self.btn_up = Button(
            text="" if btn_up_src else "▲",
            font_size=f'{int(20 * sf)}sp',
            bold=True,
            size_hint=(None, None),
            size=self.btn_sz,
            background_normal=btn_up_src,
            background_down=btn_up_src,
            background_color=(1, 1, 1, 1) if btn_up_src else (0.18, 0.65, 0.3, 0.95),
            border=(0, 0, 0, 0)
        )
        self.btn_up.mute_sound = True
        self.bind_button_dim_effect(self.btn_up)
        self.btn_up.bind(on_release=lambda b: self.do_jump())

        btn_down_src = self.arrow_down_img if os.path.exists(self.arrow_down_img) else ''
        self.btn_down = Button(
            text="" if btn_down_src else "▼",
            font_size=f'{int(20 * sf)}sp',
            bold=True,
            size_hint=(None, None),
            size=self.btn_sz,
            background_normal=btn_down_src,
            background_down=btn_down_src,
            background_color=(1, 1, 1, 1) if btn_down_src else (0.85, 0.45, 0.15, 0.95),
            border=(0, 0, 0, 0)
        )
        self.btn_down.mute_sound = True
        self.bind_button_dim_effect(self.btn_down)
        self.btn_down.bind(on_release=lambda b: self.do_slide())

        self.main_container.add_widget(self.btn_left)
        self.main_container.add_widget(self.btn_right)
        self.main_container.add_widget(self.btn_up)
        self.main_container.add_widget(self.btn_down)

        self.reposition_control_buttons()

    def reposition_control_buttons(self):
        sf = self.scale_factor
        
        # Center the left movement buttons nicely along the lower section
        middle_ground_y = (self.ground_y - self.btn_sz[1]) / 2.0
        self.btn_left.y = max(dp(6), middle_ground_y)
        self.btn_right.y = self.btn_left.y
        
        # Keep right movement buttons positioned side-by-side using pixel offsets
        btn_w = self.btn_sz[0]
        btn_h = self.btn_sz[1]
        left_margin = Window.width * 0.02
        self.btn_left.x = left_margin
        self.btn_right.x = left_margin + btn_w + dp(10)

        # Dynamically fit the stacked right-side actions within the ground bounds (ground_y)
        total_stack_height = (btn_h * 2) + dp(4)
        available_space = max(dp(4), self.ground_y - total_stack_height)
        bottom_margin = available_space / 2.0

        self.btn_down.x = Window.width - btn_w - left_margin
        self.btn_up.x = self.btn_down.x

        self.btn_down.y = bottom_margin
        self.btn_up.y = bottom_margin + btn_h + dp(4)

    def update_canvas_bounds(self, instance, value):
        self.bg_rect1.size = instance.size
        self.ground_rect.size = (instance.width, self.ground_y)

    def on_window_resize(self, window, width, height):
        old_ground_y = self.ground_y
        sf = self.scale_factor
        self.update_physics_metrics()

        self.update_canvas_bounds(self.main_container, None)

        # Live adjustment for player position if grounded
        if not self.is_jumping and abs(self.player_y - old_ground_y) < dp(5):
            self.player_y = self.ground_y

        p_height = self.slide_height if self.is_sliding else self.normal_height
        p_width = self.normal_width + dp(12) if self.is_sliding else self.normal_width
        self.player_rect.pos = (self.player_x, self.player_y)
        self.player_rect.size = (p_width, p_height)

        # Live adjustment for active obstacles and coins relative to the new ground level
        for obs in self.obstacles:
            if obs['type'] == 'LOW':
                obs['y'] = self.ground_y
                obs['w'] = dp(62) * sf
                obs['h'] = dp(45) * sf
            else:
                obs['y'] = self.ground_y + (dp(45) * sf)
                obs['w'] = dp(65) * sf
                obs['h'] = dp(50) * sf
            obs['rect'].pos = (obs['x'], obs['y'])
            obs['rect'].size = (obs['w'], obs['h'])

        for coin in self.coins:
            # Maintain relative vertical offset proportion
            relative_offset = (coin['y'] - old_ground_y) if old_ground_y > 0 else dp(50)
            coin['y'] = self.ground_y + relative_offset
            coin['w'] = dp(28) * sf
            coin['h'] = dp(28) * sf
            coin['rect'].pos = (coin['x'], coin['y'])
            coin['rect'].size = (coin['w'], coin['h'])

        # Live adjustment for active game over popup dimensions
        if self.overlay_popup:
            popup_w = min(dp(500) * sf, Window.width * 0.95)
            popup_h = min(dp(400) * sf, Window.height * 0.95)
            self.overlay_popup.size = (popup_w, popup_h)

        is_ultra_narrow = width < dp(500) or height < dp(400) or height > width * 4.5

        self.nav_box.height = dp(38) if is_ultra_narrow else dp(48)
        self.back_btn.size = (dp(70), dp(26)) if is_ultra_narrow else (dp(85), dp(32))
        
        base_font_mult = 0.9 if is_ultra_narrow else 1.0
        
        self.back_btn.font_size = f'{int(16 * sf * base_font_mult)}sp'
        self.header_title.font_size = f'{int(18 * sf * base_font_mult)}sp'
        self.lbl_score.font_size = f'{int(14 * sf * base_font_mult)}sp'
        
        # Keep banner and footer compact so they never crowd the touch control arrows
        self.lbl_banner.font_size = f'{int(15 * sf * base_font_mult)}sp' 
        self.lbl_footer.font_size = f'{int(18 * sf * base_font_mult)}sp'

        btn_w = max(dp(36), (dp(45) if is_ultra_narrow else dp(52)) * sf)
        btn_h = max(dp(32), (dp(38) if is_ultra_narrow else dp(45)) * sf)
        self.btn_sz = (btn_w, btn_h)
        for btn in [self.btn_left, self.btn_right, self.btn_up, self.btn_down]:
            btn.size = self.btn_sz
            btn.font_size = f'{int(18 * sf * base_font_mult)}sp'

        self.reposition_control_buttons()

    def play_sound(self, key):
        snd = self.sounds.get(key)
        if snd:
            try:
                snd.stop()
                snd.play()
            except Exception:
                pass

    def start_bg_music(self):
        if os.path.exists(self.bg_music_path):
            try:
                if not self.bg_music:
                    self.bg_music = SoundLoader.load(self.bg_music_path)
                if self.bg_music:
                    self.bg_music.loop = True
                    self.bg_music.volume = 0.5
                    self.bg_music.play()
            except Exception as e:
                print(f"Background music error: {e}")

    def stop_bg_music(self):
        if self.bg_music:
            try:
                self.bg_music.stop()
                self.bg_music.unload()
                self.bg_music = None
            except Exception as e:
                print(f"Background music stop error: {e}")

    def set_device_landscape(self):
        if platform in ('android', 'ios'):
            if orientation:
                try:
                    orientation.set_landscape()
                except Exception as e:
                    print(f"Plyer orientation landscape error: {e}")
            
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    activity = PythonActivity.mActivity
                    ActivityInfo = autoclass('android.content.pm.ActivityInfo')
                    activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE)
                except Exception as ex:
                    print(f"Android native landscape lock error: {ex}")

    def set_device_portrait(self):
        if platform in ('android', 'ios'):
            if orientation:
                try:
                    orientation.set_portrait()
                except Exception as e:
                    print(f"Plyer orientation portrait error: {e}")
            
            if platform == 'android':
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    activity = PythonActivity.mActivity
                    ActivityInfo = autoclass('android.content.pm.ActivityInfo')
                    activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED)
                except Exception as ex:
                    print(f"Android native unlock error: {ex}")

    def on_pre_enter(self):
        self.set_device_landscape()
        Window.bind(on_key_down=self.handle_key_down)
        Window.bind(on_key_up=self.handle_key_up)
        self.start_bg_music()
        self.reset_game()

    def on_leave(self):
        self.set_device_portrait()
        Window.unbind(on_key_down=self.handle_key_down)
        Window.unbind(on_key_up=self.handle_key_up)
        self.stop_bg_music()
        self.stop_game_loop()

    def stop_game_loop(self):
        if self.game_loop_event:
            Clock.unschedule(self.game_loop_event)
            self.game_loop_event = None

    def handle_key_down(self, window, key, scancode, codepoint, modifier):
        if not self.game_active:
            return False
        
        if key in (273, 32, 119):
            self.do_jump()
            return True
        elif key in (274, 115):
            self.do_slide()
            return True
        elif key in (276, 97):
            self.move_left = True
            return True
        elif key in (275, 100):
            self.move_right = True
            return True
        return False

    def handle_key_up(self, window, key, scancode, *args):
        if key in (276, 97):
            self.move_left = False
            return True
        elif key in (275, 100):
            self.move_right = False
            return True
        return False

    def do_jump(self):
        if not self.is_jumping:
            self.is_jumping = True
            self.is_sliding = False
            self.player_vy = self.jump_strength
            self.play_sound("jump")

    def do_slide(self):
        if not self.is_jumping and not self.is_sliding:
            self.is_sliding = True
            self.slide_duration = 45

    def update_player_animation(self):
        if self.is_jumping:
            if os.path.exists(self.jump_frame):
                self.player_rect.source = self.jump_frame
        elif self.is_sliding:
            if os.path.exists(self.slide_frame):
                self.player_rect.source = self.slide_frame
        else:
            self.anim_counter += 1
            if self.anim_counter % 5 == 0:
                self.anim_frame_idx = (self.anim_frame_idx + 1) % len(self.run_frames)
                frame_path = self.run_frames[self.anim_frame_idx]
                if os.path.exists(frame_path):
                    self.player_rect.source = frame_path

    def update(self, dt):
        if not self.game_active:
            return

        self.score += 1
        distance_meters = self.score // 5

        self.message_timer += 1
        if self.message_timer >= 300:
            self.message_timer = 0
            self.current_msg_idx = (self.current_msg_idx + 1) % len(self.ground_messages)
            self.lbl_banner.text = f"[b][i]{self.ground_messages[self.current_msg_idx]}[/i][/b]"

        self.lbl_score.text = (
            f"Best: [color=2ecc71]{self.high_score // 5}m[/color]  |  "
            f"Scrolls: [color=f1c40f]{self.coins_collected}[/color]"
        )
        self.lbl_footer.text = (
            f"[b][color=1e824c]S[/color][color=d35400]A[/color][color=f39c12]B[/color][color=2980b9]I[/color] "
            f"[color=ffffff]RUNNER ({distance_meters}m)[/color][/b]"
        )

        if self.move_left:
            self.player_x = max(dp(20), self.player_x - self.move_speed)
        if self.move_right:
            self.player_x = min(Window.width - dp(180), self.player_x + self.move_speed)

        if self.is_jumping:
            self.player_y += self.player_vy
            self.player_vy -= self.gravity
            if self.player_y <= self.ground_y:
                self.player_y = self.ground_y
                self.player_vy = 0
                self.is_jumping = False

        if self.is_sliding:
            self.slide_duration -= 1
            if self.slide_duration <= 0:
                self.is_sliding = False

        p_height = self.slide_height if self.is_sliding else self.normal_height
        p_width = self.normal_width + dp(12) if self.is_sliding else self.normal_width

        self.player_rect.pos = (self.player_x, self.player_y)
        self.player_rect.size = (p_width, p_height)
        
        self.update_player_animation()

        min_gap = int(dp(560) * self.scale_factor)
        max_gap = int(dp(800) * self.scale_factor)

        if not self.obstacles or (Window.width - self.obstacles[-1]['x']) > dp(random.randint(min_gap, max_gap)):
            self.spawn_obstacle()
            if random.random() > 0.3:
                self.spawn_coin()

        player_box = {'x': self.player_x, 'y': self.player_y, 'w': p_width, 'h': p_height}

        for coin in list(self.coins):
            coin['x'] -= self.game_speed
            coin['rect'].pos = (coin['x'], coin['y'])

            if self.check_collision(player_box, coin):
                self.coins_collected += 1
                self.play_sound("coin")
                self.main_container.canvas.remove(coin['rect'])
                self.coins.remove(coin)
            elif coin['x'] < -dp(40):
                self.main_container.canvas.remove(coin['rect'])
                self.coins.remove(coin)

        for obs in list(self.obstacles):
            obs['x'] -= self.game_speed
            obs['rect'].pos = (obs['x'], obs['y'])

            if self.check_collision(player_box, obs):
                self.trigger_game_over("Hit an Obstacle!")
                return

            if obs['x'] < -dp(80):
                self.main_container.canvas.remove(obs['rect'])
                self.obstacles.remove(obs)

    def spawn_obstacle(self):
        sf = self.scale_factor
        obs_type = random.choice(["LOW", "HIGH"])
        
        if obs_type == "LOW":
            w, h = dp(62) * sf, dp(45) * sf
            y = self.ground_y
            img_src = self.obs_low_img if os.path.exists(self.obs_low_img) else ''
            fallback_color = (0.85, 0.25, 0.2, 1) if not img_src else (1, 1, 1, 1)
        else:
            w, h = dp(65) * sf, dp(50) * sf
            y = self.ground_y + (dp(45) * sf)
            img_src = self.obs_high_img if os.path.exists(self.obs_high_img) else ''
            fallback_color = (0.7, 0.2, 0.8, 1) if not img_src else (1, 1, 1, 1)

        with self.main_container.canvas:
            Color(*fallback_color)
            rect = Rectangle(pos=(Window.width, y), size=(w, h), source=img_src)

        self.obstacles.append({'rect': rect, 'x': Window.width, 'y': y, 'w': w, 'h': h, 'type': obs_type})

    def spawn_coin(self):
        sf = self.scale_factor
        w, h = dp(28) * sf, dp(28) * sf
        y = self.ground_y + (dp(random.choice([25, 80, 130])) * sf)
        img_src = self.coin_img if os.path.exists(self.coin_img) else ''
        fallback_color = (1, 0.84, 0, 1) if not img_src else (1, 1, 1, 1)

        with self.main_container.canvas:
            Color(*fallback_color)
            rect = Rectangle(pos=(Window.width + dp(80), y), size=(w, h), source=img_src)

        self.coins.append({'rect': rect, 'x': Window.width + dp(80), 'y': y, 'w': w, 'h': h})

    def check_collision(self, p, o):
        if o.get('type') == 'HIGH' and p['h'] == self.slide_height:
            return False
            
        return (
            p['x'] < o['x'] + o['w'] and
            p['x'] + p['w'] > o['x'] and
            p['y'] < o['y'] + o['h'] and
            p['y'] + p['h'] > o['y']
        )

    def trigger_game_over(self, reason):
        self.stop_game_loop()
        self.game_active = False
        self.play_sound("hit")
        
        if self.score > self.high_score:
            self.high_score = self.score

        self.dismiss_overlay()
        
        sf = self.scale_factor
        popup_w = min(dp(420) * sf, Window.width * 0.85)
        popup_h = min(dp(320) * sf, Window.height * 0.85)

        self.overlay_popup = FloatLayout(
            size_hint=(None, None),
            size=(popup_w, popup_h),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        with self.overlay_popup.canvas.before:
            Color(0.1, 0.14, 0.22, 0.98)
            self.overlay_bg = RoundedRectangle(pos=self.overlay_popup.pos, size=self.overlay_popup.size, radius=[dp(14)])
            Color(0.85, 0.25, 0.2, 1)
            self.overlay_border = Line(rounded_rectangle=(self.overlay_popup.x, self.overlay_popup.y, self.overlay_popup.width, self.overlay_popup.height, dp(14)), width=dp(2))

        def update_popup(inst, val):
            self.overlay_bg.pos = inst.pos
            self.overlay_bg.size = inst.size
            self.overlay_border.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(14))

        self.overlay_popup.bind(pos=update_popup, size=update_popup)

        # Adjusted font sizes and compact spacing so "GAME OVER" never gets clipped on small screens
        title_lbl = Label( 
            text=f"[color=e74c3c][size={int(14 * sf)}sp][b]GAME OVER[/b][/size][/color]\n"
                 f"[size={int(16 * sf)}sp][b]Distance: [color=f1c40f]{self.score // 5}m[/color] | "
                 f"Knowledge Scrolls: [color=f1c40f]{self.coins_collected}[/color][/b][/size]\n\n"
                 f"[size={int(17 * sf)}sp][b][color=ecf0f1]Obstacles test your path to learning! Identify real-life distractions, "
                 f"dodge them with discipline, and protect your focus to gain knowledge.[/color][/b][/size]\n",
            markup=True,
            halign='center',
            valign='middle',
            size_hint=(0.92, 0.72),
            pos_hint={'center_x': 0.5, 'center_y': 0.56}
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))

        btn_retry = Button(
            text="Play Again",
            size_hint=(None, None),
            size=(dp(140) * sf, dp(36) * sf),
            pos_hint={'center_x': 0.5, 'y': 0.06},
            font_size=f'{int(14 * sf)}sp',
            bold=True,
            background_color=(0.18, 0.68, 0.3, 1),
            background_normal=''
        )
        btn_retry.mute_sound = True
        self.bind_button_dim_effect(btn_retry)
        btn_retry.bind(on_release=self.reset_game)

        self.overlay_popup.add_widget(title_lbl)
        self.overlay_popup.add_widget(btn_retry)
        self.main_container.add_widget(self.overlay_popup)

    def dismiss_overlay(self):
        if self.overlay_popup and self.overlay_popup.parent:
            self.main_container.remove_widget(self.overlay_popup)
            self.overlay_popup = None

    def reset_game(self, instance=None):
        self.stop_game_loop()
        self.dismiss_overlay()
        self.play_sound("reset")

        for obs in self.obstacles:
            self.main_container.canvas.remove(obs['rect'])
        for coin in self.coins:
            self.main_container.canvas.remove(coin['rect'])

        sf = self.scale_factor
        self.update_physics_metrics()
        self.obstacles = []
        self.coins = []
        self.score = 0
        self.coins_collected = 0
        self.player_x = dp(80) * sf
        self.player_y = self.ground_y
        self.player_vy = 0
        self.is_jumping = False
        self.is_sliding = False
        self.move_left = False
        self.move_right = False
        self.game_active = True

        self.game_loop_event = Clock.schedule_interval(self.update, 1.0 / 60.0)

    def go_back_to_hub(self, instance):
        self.stop_game_loop()
        self.play_sound("reset")
        self.game_active = False
        if self.manager and self.manager.has_screen('sabi_games_hub_page'):
            self.manager.current = 'sabi_games_hub_page'