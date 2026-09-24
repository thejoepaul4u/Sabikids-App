import os
import threading
import urllib.request
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image, AsyncImage
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

import database
from utils.curriculum_manager import CurriculumManager
from utils.tts_engine import TTSEngine


# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    # Elevated min scale floor to prevent tiny, blurry fonts on small screens
    base_scale = Window.width / dp(400)
    return max(0.95, min(1.30, base_scale))


class ClickableVideoPlayer(VideoPlayer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_zoomed = False
        self.modal = None
        self.modal_layout = None
        self.original_parent = None
        self.original_size_hint_y = None
        self.original_height = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.is_double_tap:
                self.toggle_zoom()
                return True
        return super().on_touch_down(touch)

    def toggle_zoom(self):
        if not self.is_zoomed:
            self.original_parent = self.parent
            self.original_size_hint_y = self.size_hint_y
            self.original_height = self.height

            if self.original_parent:
                self.original_parent.remove_widget(self)

            self.modal = ModalView(size_hint=(1, 1), background_color=(0, 0, 0, 0.95))
            self.modal_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

            self.size_hint_y = 1
            self.height = dp(0)

            close_btn = Button(
                text="Exit Fullscreen",
                size_hint_y=None,
                height=dp(52),
                background_color=(0.8, 0.25, 0.25, 1),
                bold=True,
                font_size='15sp'
            )
            close_btn.bind(on_release=lambda instance: self.toggle_zoom())

            self.modal_layout.add_widget(self)
            self.modal_layout.add_widget(close_btn)
            self.modal.add_widget(self.modal_layout)
            
            self.is_zoomed = True
            self.modal.open()

        else:
            if self.modal_layout and self in self.modal_layout.children:
                self.modal_layout.remove_widget(self)

            if self.modal:
                self.modal.dismiss()
                self.modal = None
                self.modal_layout = None

            self.size_hint_y = self.original_size_hint_y
            self.height = self.original_height

            if self.original_parent:
                if self.parent:
                    self.parent.remove_widget(self)
                self.original_parent.add_widget(self)

            self.is_zoomed = False


class ContentViewerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.topic_data = None
        self.node_type = None
        self.questions = []
        self.current_q_index = 0

        self.correct_count = 0
        self.wrong_count = 0
        self.active_video_player = None

        # Base Root Container
        self.main_container = FloatLayout()

        # 1. TOP NAVBAR
        self.navbar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(4), dp(4)],
            spacing=dp(4),
            pos_hint={'top': 1}
        )
        
        with self.navbar.canvas.before:
            Color(0.08, 0.12, 0.22, 1)
            self.nav_bg = RoundedRectangle(pos=self.navbar.pos, size=self.navbar.size)
        self.navbar.bind(pos=self._update_nav_bg, size=self._update_nav_bg)

        self.back_btn = Button(
            text="Back",
            font_size='13sp', bold=True,
            size_hint=(None, None),
            size=(dp(65), dp(38)),
            pos_hint={'center_y': 0.5},
            background_normal='', background_color=(0.8, 0.25, 0.25, 1),
            color=(1, 1, 1, 1),
            halign='center', valign='middle'
        )
        self.back_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))
        self.back_btn.bind(on_release=self.go_back)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners[/color]",
            markup=True,
            font_size='16sp',
            bold=True,
            size_hint=(1, 1),
            halign='center',
            valign='middle'
        )
        self.brand_title.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(2)), None)))
        self.navbar.add_widget(self.brand_title)

        self.nav_spacer = Label(size_hint=(None, None), size=(dp(65), dp(38)))
        self.navbar.add_widget(self.nav_spacer)

        # 2. SCROLLABLE BODY CONTENT
        self.scroll = ScrollView(
            size_hint=(1, None),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )

        self.content_container = BoxLayout(
            orientation='vertical',
            spacing=dp(12),
            size_hint=(1, None),
            padding=[dp(10), dp(12), dp(10), dp(20)]
        )
        self.content_container.bind(minimum_height=self.content_container.setter('height'))
        self.scroll.add_widget(self.content_container)

        self.main_container.add_widget(self.scroll)
        self.main_container.add_widget(self.navbar)
        self.add_widget(self.main_container)

        # Dynamic Window Resize Binding
        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _update_scroll_bounds(self, *args):
        fixed_header_height = self.navbar.height
        top_offset = fixed_header_height + dp(4)
        
        self.scroll.y = 0
        self.scroll.height = max(dp(80), Window.height - top_offset)

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()
        self._update_scroll_bounds()

        if Window.width < dp(340):
            btn_w = dp(50 * scale)
            self.brand_title.font_size = f"{int(15 * scale)}sp"
            self.back_btn.font_size = f"{int(12 * scale)}sp"
            self.back_btn.text = "Back"
        else:
            btn_w = dp(72 * scale)
            self.brand_title.font_size = f"{int(17 * scale)}sp"
            self.back_btn.font_size = f"{int(13 * scale)}sp"
            self.back_btn.text = "Back"

        nav_h = dp(54 * scale)
        self.navbar.height = nav_h
        btn_h = dp(38 * scale)
        self.back_btn.size = (btn_w, btn_h)
        self.nav_spacer.size = (btn_w, btn_h)

        if Window.width >= dp(768):
            side_padding = max(dp(30), (Window.width - dp(850)) / 2)
            self.content_container.padding = [side_padding, dp(16), side_padding, dp(24)]
            self.content_container.spacing = dp(14)
        else:
            side_pad = max(dp(8), Window.width * 0.03)
            self.content_container.padding = [side_pad, dp(10), side_pad, dp(18)]
            self.content_container.spacing = dp(12)

        # Re-scale active children dynamically without forcing a reload
        self._update_dynamic_child_scales(self.content_container, scale)

    def _update_dynamic_child_scales(self, parent_widget, scale):
        """Recursively update font sizes and heights of dynamically rendered widgets on screen resize."""
        for child in parent_widget.children:
            if hasattr(child, 'base_font_size'):
                child.font_size = f"{int(child.base_font_size * scale)}sp"
            if hasattr(child, 'base_height'):
                child.height = dp(child.base_height * scale)

            if isinstance(child, BoxLayout):
                self._update_dynamic_child_scales(child, scale)

    def _update_nav_bg(self, instance, value):
        self.nav_bg.pos = instance.pos
        self.nav_bg.size = instance.size

    def _update_card_rect(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def cleanup_media(self):
        """Completely stop and dismiss video playback, fullscreen modals, and voice audio."""
        TTSEngine.stop_immediately()

        if hasattr(self, 'active_video_player') and self.active_video_player:
            try:
                if getattr(self.active_video_player, 'is_zoomed', False) and getattr(self.active_video_player, 'modal', None):
                    self.active_video_player.modal.dismiss()
                    self.active_video_player.is_zoomed = False

                self.active_video_player.state = 'stop'
                
                if hasattr(self.active_video_player, '_video') and self.active_video_player._video:
                    self.active_video_player._video.unload()

                if self.active_video_player.parent:
                    self.active_video_player.parent.remove_widget(self.active_video_player)

            except Exception as e:
                print("Error cleaning up media player:", e)
            finally:
                self.active_video_player = None

    def on_leave(self, *args):
        self.cleanup_media()

    def load_node_content(self, class_id=None, subject_id=None, topic_id=None, node_type="notes", topic_title=""):
        self.cleanup_media()

        active_class = class_id or getattr(self.manager, 'selected_class_id', '') or ''
        cid = str(active_class).lower()
        teens_keywords = ["junior", "senior", "jss", "sss", "ss", "sec"]

        if any(keyword in cid for keyword in teens_keywords):
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Students[/color]"
        else:
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Pupils[/color]"

        self.node_type = node_type
        self.correct_count = 0
        self.wrong_count = 0
        
        if class_id and subject_id and topic_id:
            self.topic_data = CurriculumManager.get_topic_data(class_id, subject_id, topic_id)
        else:
            self.topic_data = None
        
        if not self.topic_data and hasattr(self, 'manager') and self.manager:
            if hasattr(self.manager, 'selected_topic_data') and self.manager.selected_topic_data:
                self.topic_data = self.manager.selected_topic_data

        self.content_container.clear_widgets()

        resolved_title = ""
        if self.topic_data and isinstance(self.topic_data, dict):
            resolved_title = self.topic_data.get("title") or self.topic_data.get("name") or ""
        
        if not resolved_title and topic_title:
            resolved_title = topic_title
        elif not resolved_title and topic_id:
            resolved_title = str(topic_id)

        type_names = {
            "notes": "Lesson Notes",
            "mcq": "MCQ Quiz",
            "fill_blank": "Fill Gaps",
            "theory": "Theory Practice",
            "identify_image": "Fun Activity",
            "challenge": "Challenge Module",
            "all": "Challenge Module"
        }
        stage_name = type_names.get(node_type, "Stage Content")

        scale = get_responsive_scale()
        header_text = f"{stage_name}: {resolved_title}" if resolved_title else stage_name
        
        top_header_lbl = Label(
            text=header_text,
            font_size=f"{int(17 * scale)}sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        top_header_lbl.base_font_size = 17
        top_header_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        top_header_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(4))))
        self.content_container.add_widget(top_header_lbl)

        if not self.topic_data:
            empty_msg = f"No content added yet for [{stage_name}].\n\n"
            empty_lbl = Label(
                text=empty_msg,
                font_size=f"{int(15 * scale)}sp",
                bold=True,
                color=(0.8, 0.85, 0.9, 1),
                halign='center',
                valign='middle',
                size_hint_y=None
            )
            empty_lbl.base_font_size = 15
            empty_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            empty_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(60), value[1] + dp(8))))
            self.content_container.add_widget(empty_lbl)
            return

        if node_type == "notes":
            self.render_notes_view()
        elif node_type in ["challenge", "all"]:
            self.render_challenge_view()
        else:
            self.render_quiz_view(node_type)

    def render_challenge_view(self):
        scale = get_responsive_scale()
        topic_dict = self.topic_data if isinstance(self.topic_data, dict) else {}
        challenge = topic_dict.get("challenge", {})
        
        if isinstance(challenge, list) and challenge:
            challenge = challenge[0]
            
        if not isinstance(challenge, dict):
            challenge = {}

        title_text = challenge.get("title") or "Take-Home Activity & Challenge"
        instructions = challenge.get("instructions", "")
        task_question = challenge.get("task_question", "")
        
        if instructions and task_question and instructions != task_question:
            task_text = f"{instructions}\n\n[b]Activity Task:[/b] {task_question}"
        else:
            task_text = task_question or instructions or "No activity details generated for this topic yet."

        parent_guide = challenge.get(
            "parent_grading_guide", 
            "Parent / Guardian: Assist your child with this home task and reward their completion!"
        )

        task_card = BoxLayout(orientation='vertical', padding=[dp(12), dp(10)], spacing=dp(8), size_hint_y=None)
        task_card.bind(minimum_height=task_card.setter('height'))
        
        with task_card.canvas.before:
            Color(0.18, 0.22, 0.30, 1)
            task_card.bg_rect = RoundedRectangle(pos=task_card.pos, size=task_card.size, radius=[dp(10)])
        task_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        title_lbl = Label(
            text=f"[b][color=3399ff]{title_text}[/color][/b]",
            markup=True, font_size=f"{int(17 * scale)}sp", size_hint_y=None, halign='left', valign='middle'
        )
        title_lbl.base_font_size = 17
        title_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        title_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(28), value[1] + dp(4))))

        task_lbl = Label(
            text=f"[b]Home Activity:[/b]\n{task_text}",
            markup=True, font_size=f"{int(15 * scale)}sp", size_hint_y=None, color=(0.95, 0.95, 0.95, 1), halign='left'
        )
        task_lbl.base_font_size = 15
        task_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        task_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(6))))

        task_card.add_widget(title_lbl)
        task_card.add_widget(task_lbl)

        parent_card = BoxLayout(orientation='vertical', padding=[dp(12), dp(10)], spacing=dp(8), size_hint_y=None)
        parent_card.bind(minimum_height=parent_card.setter('height'))

        with parent_card.canvas.before:
            Color(0.22, 0.20, 0.28, 1)
            parent_card.bg_rect = RoundedRectangle(pos=parent_card.pos, size=parent_card.size, radius=[dp(10)])
        parent_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        parent_lbl = Label(
            text=f"[b][color=ffaa00]Parent / Guardian Guide:[/color][/b]\n{parent_guide}",
            markup=True, font_size=f"{int(14 * scale)}sp", size_hint_y=None, color=(0.9, 0.9, 0.9, 1), halign='left'
        )
        parent_lbl.base_font_size = 14
        parent_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        parent_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(6))))

        parent_card.add_widget(parent_lbl)

        self.content_container.add_widget(task_card)
        self.content_container.add_widget(parent_card)

    def render_notes_view(self, mode="notes"):
        self.cleanup_media()
        scale = get_responsive_scale()

        header_lbl_widget = None
        if self.content_container.children:
            header_lbl_widget = self.content_container.children[-1]

        self.content_container.clear_widgets()
        if header_lbl_widget:
            self.content_container.add_widget(header_lbl_widget)

        # 1. TOP TAB SWITCHER
        mode_box = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(46 * scale),
            spacing=dp(8)
        )
        mode_box.base_height = 46

        notes_tab_btn = Button(
            text="Lesson Notes",
            size_hint_x=0.5,
            background_color=(0.18, 0.65, 0.36, 1),
            background_normal='',
            bold=True,
            font_size=f"{int(15 * scale)}sp",
            halign='center', valign='middle'
        )
        notes_tab_btn.base_font_size = 15
        notes_tab_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(4)), None)))
        if mode != "notes":
            notes_tab_btn.background_color = (0.2, 0.25, 0.35, 1)
        notes_tab_btn.bind(on_release=lambda b: self.render_notes_view(mode="notes"))

        video_tab_btn = Button(
            text="Lesson Video",
            size_hint_x=0.5,
            background_color=(0.9, 0.45, 0.1, 1),
            background_normal='',
            bold=True,
            font_size=f"{int(15 * scale)}sp",
            halign='center', valign='middle'
        )
        video_tab_btn.base_font_size = 15
        video_tab_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(4)), None)))
        if mode != "video":
            video_tab_btn.background_color = (0.2, 0.25, 0.35, 1)
        video_tab_btn.bind(on_release=lambda b: self.render_notes_view(mode="video"))

        mode_box.add_widget(notes_tab_btn)
        mode_box.add_widget(video_tab_btn)
        self.content_container.add_widget(mode_box)

        # 2. DEDICATED MEDIA CONTAINER
        self.media_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(10),
            padding=[0, dp(4), 0, dp(4)]
        )
        self.media_container.bind(minimum_height=self.media_container.setter('height'))
        self.content_container.add_widget(self.media_container)

        # 3. MODE: VIDEO LESSON
        if mode == "video":
            video_file_path = ""
            if isinstance(self.topic_data, dict):
                video_file_path = self.topic_data.get("video_path") or self.topic_data.get("animation_video_concept") or ""

            if not video_file_path:
                empty_lbl = Label(
                    text="No lesson video uploaded/downloaded for this topic.",
                    font_size=f"{int(15 * scale)}sp",
                    bold=True,
                    color=(0.8, 0.85, 0.9, 1),
                    halign='center',
                    valign='middle',
                    size_hint_y=None
                )
                empty_lbl.base_font_size = 15
                empty_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
                empty_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(60), value[1] + dp(8))))
                self.media_container.add_widget(empty_lbl)

            elif os.path.exists(video_file_path):
                self.active_video_player = ClickableVideoPlayer(
                    source=video_file_path,
                    state='pause',
                    options={'eos': 'loop'},
                    size_hint_y=None,
                    height=dp(280 * scale)
                )
                self.active_video_player.base_height = 280
                self.active_video_player.original_parent = self.media_container
                self.media_container.add_widget(self.active_video_player)

            else:
                video_dl_btn = Button(
                    text="Download Lesson Video (Offline Playback)",
                    size_hint_y=None,
                    height=dp(48 * scale),
                    background_color=(0.9, 0.45, 0.1, 1),
                    background_normal='',
                    bold=True,
                    font_size=f"{int(14 * scale)}sp",
                    halign='center', valign='middle'
                )
                video_dl_btn.base_height = 48
                video_dl_btn.base_font_size = 14
                video_dl_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))

                def download_video_action(btn_inst):
                    video_dl_btn.text = "Downloading Video... Please wait"
                    video_dl_btn.disabled = True
                    threading.Thread(
                        target=self._download_video_thread, 
                        args=(video_file_path, video_dl_btn), 
                        daemon=True
                    ).start()

                video_dl_btn.bind(on_release=download_video_action)
                self.media_container.add_widget(video_dl_btn)

        # 4. MODE: TEXT & VOICE NOTES
        else:
            diagram_path = self.topic_data.get("diagram", "") if isinstance(self.topic_data, dict) else ""

            if diagram_path and os.path.exists(diagram_path) and diagram_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')):
                try:
                    img = Image(source=diagram_path, size_hint_y=None, height=dp(200 * scale), fit_mode="contain")
                    img.base_height = 200
                    self.media_container.add_widget(img)
                except Exception:
                    pass

            notes_text = self.topic_data.get("notes", "") if isinstance(self.topic_data, dict) else ""
            audio_file_path = self.topic_data.get("audio_path", "") if isinstance(self.topic_data, dict) else ""

            if not notes_text:
                notes_text = "No written lesson notes added for this topic."

            audio_prompt_box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                padding=[dp(8), dp(6)]
            )
            with audio_prompt_box.canvas.before:
                Color(0.12, 0.28, 0.45, 1)
                audio_prompt_box.bg_rect = RoundedRectangle(
                    pos=audio_prompt_box.pos, 
                    size=audio_prompt_box.size
                )
            audio_prompt_box.bind(pos=self._update_card_rect, size=self._update_card_rect)
            
            prompt_label = Label(
                text="[b]Voice Assistant:[/b] Tap Play below to hear your lesson teacher!",
                markup=True,
                font_size=f"{int(13 * scale)}sp",
                color=(0.85, 0.95, 1, 1),
                halign='center',
                valign='middle',
                size_hint_y=None
            )
            prompt_label.base_font_size = 13
            prompt_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            prompt_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(26), value[1] + dp(4))))
            audio_prompt_box.bind(minimum_height=audio_prompt_box.setter('height'))
            audio_prompt_box.add_widget(prompt_label)
            self.media_container.add_widget(audio_prompt_box)

            has_local_audio = os.path.exists(audio_file_path) if audio_file_path else False

            if audio_file_path and not has_local_audio:
                dl_btn = Button(
                    text="Download Lesson & Question Audio For This Topic",
                    size_hint_y=None,
                    height=dp(48 * scale),
                    background_color=(0.2, 0.6, 0.86, 1),
                    background_normal='',
                    bold=True,
                    font_size=f"{int(14 * scale)}sp",
                    halign='center', valign='middle'
                )
                dl_btn.base_height = 48
                dl_btn.base_font_size = 14
                dl_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))

                def download_audio_action(btn_inst):
                    dl_btn.text = "Downloading Audio..."
                    dl_btn.disabled = True

                    def fetch_task():
                        try:
                            urls_to_download = []
                            if audio_file_path:
                                urls_to_download.append(audio_file_path)

                            for q in self.topic_data.get("quiz", []):
                                q_audio = q.get("audio_path", "")
                                if q_audio:
                                    urls_to_download.append(q_audio)

                            for rel_path in urls_to_download:
                                raw_url = f"https://raw.githubusercontent.com/thejoepaul4u/Sabikids-App/refs/heads/main/{rel_path}"
                                dir_name = os.path.dirname(rel_path)
                                if dir_name and not os.path.exists(dir_name):
                                    os.makedirs(dir_name, exist_ok=True)
            
                                if not os.path.exists(rel_path):
                                    urllib.request.urlretrieve(raw_url, rel_path)

                            Clock.schedule_once(lambda dt: self.render_notes_view(mode="notes"), 0.1)

                        except urllib.error.HTTPError as http_err:
                            if http_err.code == 404:
                                Clock.schedule_once(lambda dt: self._set_dl_status(dl_btn, "Audio Not Available For This Lesson", retryable=False), 0)
                            else:
                                Clock.schedule_once(lambda dt: self._set_dl_status(dl_btn, f"Server Error ({http_err.code}). Tap to Retry", retryable=True), 0)

                        except Exception:
                            Clock.schedule_once(lambda dt: self._set_dl_status(dl_btn, "Network Error. Check Connection & Retry", retryable=True), 0)

                    threading.Thread(target=fetch_task, daemon=True).start()

                dl_btn.bind(on_release=download_audio_action)
                self.media_container.add_widget(dl_btn)

            tts_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46 * scale), spacing=dp(8))
            tts_box.base_height = 46
            
            play_btn = Button(
                text="Play Voice",
                size_hint_x=0.5,
                background_color=(0.18, 0.65, 0.36, 1),
                background_normal='',
                bold=True,
                font_size=f"{int(14 * scale)}sp",
                halign='center', valign='middle'
            )
            play_btn.base_font_size = 14
            play_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(4)), None)))
            
            def smart_play(instance):
                if hasattr(self, 'active_video_player') and self.active_video_player:
                    try:
                        self.active_video_player.state = 'stop'
                    except Exception:
                        pass

                if audio_file_path and os.path.exists(audio_file_path):
                    TTSEngine.play_file(audio_file_path)
                else:
                    TTSEngine.stop_immediately()
                    prompt_label.text = "[b]Voice Assistant:[/b] [color=ff5555]Audio not available. Please download audio first.[/color]"

            play_btn.bind(on_release=smart_play)

            stop_btn = Button(
                text="Stop Voice",
                size_hint_x=0.5,
                background_color=(0.8, 0.25, 0.25, 1),
                background_normal='',
                bold=True,
                font_size=f"{int(14 * scale)}sp",
                halign='center', valign='middle'
            )
            stop_btn.base_font_size = 14
            stop_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(4)), None)))
            stop_btn.bind(on_release=lambda b: TTSEngine.stop_immediately())

            tts_box.add_widget(play_btn)
            tts_box.add_widget(stop_btn)
            self.media_container.add_widget(tts_box)

            formatted_notes = notes_text
            while "**" in formatted_notes:
                formatted_notes = formatted_notes.replace("**", "[b]", 1).replace("**", "[/b]", 1)

            notes_label = Label(
                text=formatted_notes,
                markup=True,
                font_size=f"{int(16 * scale)}sp",
                line_height=1.25,
                color=(0.95, 0.95, 0.98, 1),
                size_hint=(1, None),
                halign='left',
                valign='top'
            )
            notes_label.base_font_size = 16
            notes_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            notes_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(8))))
            self.media_container.add_widget(notes_label)

    def _set_dl_status(self, btn, message, retryable=True):
        btn.text = message
        btn.disabled = not retryable
        if not retryable:
            btn.background_color = (0.4, 0.4, 0.45, 1)

    def reset_dl_btn(self, btn):
        btn.text = "Download Failed. Retry?"
        btn.disabled = False

    def _download_video_thread(self, local_rel_path, btn_widget):
        try:
            raw_url = f"https://raw.githubusercontent.com/thejoepaul4u/Sabikids-App/refs/heads/main/{local_rel_path}"
            
            dir_name = os.path.dirname(local_rel_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)

            req = urllib.request.urlopen(raw_url)
            with open(local_rel_path, 'wb') as out_file:
                while True:
                    chunk = req.read(1024 * 64)
                    if not chunk:
                        break
                    out_file.write(chunk)

            Clock.schedule_once(lambda dt: self.render_notes_view(mode="video"), 0.1)

        except Exception as e:
            print("Video Download Failed:", e)
            Clock.schedule_once(lambda dt: self._reset_video_dl_btn(btn_widget), 0)

    def _reset_video_dl_btn(self, btn):
        btn.text = "Video Download Failed. Retry?"
        btn.disabled = False

    def render_quiz_view(self, target_type):
        all_quizzes = self.topic_data.get("quiz", []) if isinstance(self.topic_data, dict) else []

        if target_type == "all":
            self.questions = all_quizzes
        elif target_type in ("mcq", "identify_image", "visual_choice"):
            self.questions = [
                q for q in all_quizzes 
                if q.get("type") in ("mcq", "identify_image", "visual_choice")
            ]
        else:
            self.questions = [q for q in all_quizzes if q.get("type") == target_type]

        if not self.questions:
            scale = get_responsive_scale()
            empty_lbl = Label(
                text="No question items created for this specific stage module yet.",
                font_size=f"{int(15 * scale)}sp",
                bold=True,
                color=(0.8, 0.8, 0.85, 1),
                halign='center',
                valign='middle',
                size_hint_y=None
            )
            empty_lbl.base_font_size = 15
            empty_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            empty_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(60), value[1] + dp(8))))
            self.content_container.add_widget(empty_lbl)
            return

        self.current_q_index = 0
        self.display_question(self.current_q_index)

    def display_question(self, index):
        TTSEngine.stop_immediately()
        scale = get_responsive_scale()

        header_lbl_widget = None
        if self.content_container.children:
            header_lbl_widget = self.content_container.children[-1]

        self.content_container.clear_widgets()
        if header_lbl_widget:
            self.content_container.add_widget(header_lbl_widget)

        q_data = self.questions[index]

        header_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38 * scale), spacing=dp(8))
        header_box.base_height = 38

        q_counter_label = Label(
            text=f"Question {index + 1} of {len(self.questions)}",
            font_size=f"{int(14 * scale)}sp",
            bold=True,
            color=(0.65, 0.75, 0.9, 1),
            halign='left',
            valign='middle'
        )
        q_counter_label.base_font_size = 14
        q_counter_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(4)), None)))
        header_box.add_widget(q_counter_label)

        q_audio_path = q_data.get("audio_path", "")
        read_btn = Button(
            text="Listen",
            size_hint_x=None,
            width=dp(80 * scale),
            background_color=(0.18, 0.65, 0.36, 1),
            background_normal='',
            bold=True,
            font_size=f"{int(13 * scale)}sp",
            halign='center', valign='middle'
        )
        read_btn.base_font_size = 13
        read_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))

        def play_q_audio(inst):
            if q_audio_path and os.path.exists(q_audio_path):
                TTSEngine.play_file(q_audio_path)
            else:
                TTSEngine.stop_immediately()
                read_btn.text = "No Audio"
                read_btn.background_color = (0.5, 0.5, 0.5, 1)

        read_btn.bind(on_release=play_q_audio)
        header_box.add_widget(read_btn)
        self.content_container.add_widget(header_box)

        q_label = Label(
            text=q_data.get("question", ""),
            font_size=f"{int(17 * scale)}sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            halign='left',
            valign='middle'
        )
        q_label.base_font_size = 17
        q_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        q_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(28), value[1] + dp(4))))
        self.content_container.add_widget(q_label)

        top_img = q_data.get("image_url") or q_data.get("image_path") or q_data.get("image")
        if top_img:
            if str(top_img).startswith("http://") or str(top_img).startswith("https://"):
                q_image_widget = AsyncImage(
                    source=top_img,
                    size_hint_y=None,
                    height=dp(190 * scale),
                    fit_mode="contain"
                )
            elif os.path.exists(top_img):
                q_image_widget = Image(
                    source=top_img,
                    size_hint_y=None,
                    height=dp(190 * scale),
                    fit_mode="contain"
                )
            else:
                q_image_widget = None

            if q_image_widget:
                q_image_widget.base_height = 190
                self.content_container.add_widget(q_image_widget)

        q_type = q_data.get("type", "mcq")

        if q_type in ("mcq", "identify_image", "visual_choice"):
            options = q_data.get("options", [])
            for opt in options:
                opt_str = opt.get("value", "") if isinstance(opt, dict) else str(opt)
                img_path = opt.get("image", "") if isinstance(opt, dict) else ""

                if img_path:
                    opt_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(58 * scale), spacing=dp(8))
                    opt_box.base_height = 58
                    if str(img_path).startswith("http"):
                        opt_img = AsyncImage(source=img_path, size_hint_x=None, width=dp(48 * scale), fit_mode="contain")
                    elif os.path.exists(img_path):
                        opt_img = Image(source=img_path, size_hint_x=None, width=dp(48 * scale), fit_mode="contain")
                    else:
                        opt_img = None
                    
                    if opt_img:
                        opt_box.add_widget(opt_img)

                    btn = Button(
                        text=opt_str,
                        size_hint_x=1,
                        background_color=(0.2, 0.3, 0.45, 1),
                        background_normal='',
                        bold=True,
                        font_size=f"{int(15 * scale)}sp",
                        color=(1, 1, 1, 1),
                        halign='center', valign='middle'
                    )
                    btn.base_font_size = 15
                    btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(4)), None)))
                    btn.bind(on_release=lambda b, chosen=opt_str: self.check_answer(chosen, q_data))
                    opt_box.add_widget(btn)
                    self.content_container.add_widget(opt_box)
                else:
                    btn = Button(
                        text=opt_str,
                        size_hint_y=None,
                        height=dp(52 * scale),
                        background_color=(0.2, 0.3, 0.45, 1),
                        background_normal='',
                        bold=True,
                        font_size=f"{int(15 * scale)}sp",
                        color=(1, 1, 1, 1),
                        halign='center', valign='middle'
                    )
                    btn.base_height = 52
                    btn.base_font_size = 15
                    btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
                    btn.bind(on_release=lambda b, chosen=opt_str: self.check_answer(chosen, q_data))
                    self.content_container.add_widget(btn)

        elif q_type in ("fill_blank", "theory"):
            inp = TextInput(
                hint_text="Type your answer here...",
                multiline=(q_type == "theory"),
                size_hint_y=None,
                font_size=f"{int(15 * scale)}sp",
                height=dp(90 * scale) if q_type == "theory" else dp(46 * scale)
            )
            inp.base_font_size = 15
            inp.base_height = 90 if q_type == "theory" else 46
            self.content_container.add_widget(inp)

            tip_label = Label(
                text="[b]Pro Tip:[/b] Type key terms exactly as taught!",
                markup=True,
                font_size=f"{int(13 * scale)}sp",
                color=(0.95, 0.8, 0.35, 1),
                size_hint_y=None,
                halign='left',
                valign='middle'
            )
            tip_label.base_font_size = 13
            tip_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            tip_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(20), value[1] + dp(2))))
            self.content_container.add_widget(tip_label)

            sub_btn = Button(
                text="Submit Answer",
                size_hint_y=None,
                height=dp(48 * scale),
                background_color=(0.18, 0.80, 0.44, 1),
                background_normal='',
                bold=True,
                font_size=f"{int(15 * scale)}sp",
                halign='center', valign='middle'
            )
            sub_btn.base_height = 48
            sub_btn.base_font_size = 15
            sub_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            sub_btn.bind(on_release=lambda b: self.check_answer(inp.text.strip(), q_data))
            self.content_container.add_widget(sub_btn)

    def check_answer(self, user_answer, q_data):
        TTSEngine.stop_immediately()
        scale = get_responsive_scale()

        correct_answer = str(q_data.get("correct_answer", "")).strip().lower()
        user_val = str(user_answer).strip().lower()

        if q_data.get("type") in ["theory", "fill_blank"]:
            is_correct = (user_val == correct_answer) or (correct_answer in user_val and len(user_val) > 0)
        else:
            is_correct = (user_val == correct_answer)

        if is_correct:
            self.correct_count += 1
        else:
            self.wrong_count += 1

        header_lbl_widget = None
        if self.content_container.children:
            header_lbl_widget = self.content_container.children[-1]

        self.content_container.clear_widgets()
        if header_lbl_widget:
            self.content_container.add_widget(header_lbl_widget)

        status_text = "Correct!" if is_correct else f"Incorrect (Correct answer: {q_data.get('correct_answer')})"
        status_color = (0.2, 0.85, 0.4, 1) if is_correct else (0.9, 0.3, 0.3, 1)

        res_label = Label(
            text=status_text,
            font_size=f"{int(18 * scale)}sp",
            bold=True,
            color=status_color,
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        res_label.base_font_size = 18
        res_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        res_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(32), value[1] + dp(4))))
        self.content_container.add_widget(res_label)

        explanation_text = f"Explanation:\n{q_data.get('explanation', 'Good job!')}"
        exp_label = Label(
            text=explanation_text,
            font_size=f"{int(15 * scale)}sp",
            bold=True,
            color=(0.9, 0.9, 0.95, 1),
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        exp_label.base_font_size = 15
        exp_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        exp_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(6))))
        self.content_container.add_widget(exp_label)

        if self.current_q_index + 1 < len(self.questions):
            next_btn = Button(
                text="Next Question",
                size_hint_y=None,
                height=dp(48 * scale),
                background_color=(0.2, 0.5, 0.8, 1),
                background_normal='',
                bold=True,
                font_size=f"{int(15 * scale)}sp",
                halign='center', valign='middle'
            )
            next_btn.base_height = 48
            next_btn.base_font_size = 15
            next_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            next_btn.bind(on_release=lambda b: self.advance_question())
            self.content_container.add_widget(next_btn)
        else:
            finish_btn = Button(
                text="View Summary Results",
                size_hint_y=None,
                height=dp(48 * scale),
                background_color=(0.18, 0.80, 0.44, 1),
                background_normal='',
                bold=True,
                font_size=f"{int(15 * scale)}sp",
                halign='center', valign='middle'
            )
            finish_btn.base_height = 48
            finish_btn.base_font_size = 15
            finish_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
            finish_btn.bind(on_release=lambda b: self.render_score_summary_view())
            self.content_container.add_widget(finish_btn)

    def advance_question(self):
        self.current_q_index += 1
        self.display_question(self.current_q_index)

    def render_score_summary_view(self):
        scale = get_responsive_scale()

        header_lbl_widget = None
        if self.content_container.children:
            header_lbl_widget = self.content_container.children[-1]

        self.content_container.clear_widgets()
        if header_lbl_widget:
            self.content_container.add_widget(header_lbl_widget)

        profile = database.get_user_profile()
        child_name = profile.get("child_name", "").strip() if isinstance(profile, dict) else ""
        display_name = child_name if child_name else "Champion"

        total_q = len(self.questions)
        score_percentage = (self.correct_count / total_q * 100) if total_q > 0 else 0

        if score_percentage >= 70:
            header_text = "OUTSTANDING JOB!"
            header_color = (0.2, 0.85, 0.4, 1)
            advice = f"You are so intelligent, {display_name}! You mastered this module like a superstar! Keep up the amazing work!"
        elif score_percentage >= 40:
            header_text = "GOOD EFFORT!"
            header_color = (0.95, 0.77, 0.06, 1)
            advice = f"Great work, {display_name}! You got most questions right. Review the lesson notes and try again to get a 100% score!"
        else:
            header_text = "KEEP TRYING!"
            header_color = (0.9, 0.4, 0.2, 1)
            advice = f"Don't give up, {display_name}! Practice makes perfect. Reviewing lesson notes will help you pass next time!"

        result_header = Label(
            text=header_text,
            font_size=f"{int(19 * scale)}sp",
            bold=True,
            color=header_color,
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        result_header.base_font_size = 19
        result_header.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        result_header.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(32), value[1] + dp(4))))
        self.content_container.add_widget(result_header)

        summary_card = BoxLayout(orientation='vertical', size_hint_y=None, padding=[dp(12), dp(10)], spacing=dp(4))
        summary_card.bind(minimum_height=summary_card.setter('height'))
        with summary_card.canvas.before:
            Color(0.15, 0.20, 0.32, 1)
            summary_card.bg_rect = RoundedRectangle(pos=summary_card.pos, size=summary_card.size, radius=[dp(8)])
        summary_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        c1 = Label(text=f"Questions Correct: {self.correct_count}", font_size=f"{int(15 * scale)}sp", bold=True, color=(0.2, 0.85, 0.4, 1), halign='center', size_hint_y=None)
        c1.base_font_size = 15
        c1.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        c1.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(22), value[1] + dp(2))))

        c2 = Label(text=f"Questions Missed: {self.wrong_count}", font_size=f"{int(15 * scale)}sp", bold=True, color=(0.9, 0.3, 0.3, 1), halign='center', size_hint_y=None)
        c2.base_font_size = 15
        c2.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        c2.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(22), value[1] + dp(2))))

        c3 = Label(text=f"Total Questions: {total_q}", font_size=f"{int(14 * scale)}sp", bold=True, color=(0.85, 0.9, 0.95, 1), halign='center', size_hint_y=None)
        c3.base_font_size = 14
        c3.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        c3.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(20), value[1] + dp(2))))

        summary_card.add_widget(c1)
        summary_card.add_widget(c2)
        summary_card.add_widget(c3)
        self.content_container.add_widget(summary_card)

        enc_label = Label(
            text=advice,
            font_size=f"{int(15 * scale)}sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        enc_label.base_font_size = 15
        enc_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        enc_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(6))))
        self.content_container.add_widget(enc_label)

        finish_btn = Button(
            text="Finish Module & Return",
            size_hint_y=None,
            height=dp(48 * scale),
            background_color=(0.18, 0.80, 0.44, 1),
            background_normal='',
            bold=True,
            font_size=f"{int(15 * scale)}sp",
            halign='center', valign='middle'
        )
        finish_btn.base_height = 48
        finish_btn.base_font_size = 15
        finish_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        finish_btn.bind(on_release=self.go_back)
        self.content_container.add_widget(finish_btn)

    def go_back(self, instance=None):
        self.cleanup_media()
        if self.manager:
            self.manager.current = 'topic_path'

    def on_pre_enter(self):
        selected_class_id = getattr(self.manager, 'selected_class_id', '') or ''
        cid = selected_class_id.lower()

        if any(keyword in cid for keyword in ["junior", "senior", "jss", "sss", "ss"]):
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Students[/color]"
        else:
            self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Pupils[/color]"