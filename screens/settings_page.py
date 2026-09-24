import os
import json
import re
import sqlite3
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.app import App

import database


# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    base_scale = Window.width / dp(400)
    return max(0.85, min(1.25, base_scale))


class AlphabeticTextInput(TextInput):
    def __init__(self, warning_label=None, max_chars=None, **kwargs):
        super().__init__(**kwargs)
        self.warning_label = warning_label
        self.max_chars = max_chars
        self._clear_trigger = None

    def insert_text(self, substring, from_undo=False):
        if re.search(r'[^a-zA-Z\s\'\-]', substring):
            self.show_input_warning()
        clean_string = re.sub(r'[^a-zA-Z\s\'\-]', '', substring)

        if self.max_chars:
            if len(self.text) + len(clean_string) > self.max_chars:
                self.show_char_limit_warning()
                # Truncate string to allowed remaining character count
                allowed = self.max_chars - len(self.text)
                if allowed > 0:
                    clean_string = clean_string[:allowed]
                else:
                    return

        return super().insert_text(clean_string, from_undo=from_undo)

    def show_char_limit_warning(self):
        if self.warning_label:
            self.warning_label.text = f"Maximum limit of {self.max_chars} characters reached!"
            self.warning_label.color = (0.8, 0.2, 0.2, 1)
            if self._clear_trigger:
                self._clear_trigger.cancel()
            self._clear_trigger = Clock.schedule_once(self.clear_input_warning, 2.0)

    def show_input_warning(self):
        if self.warning_label:
            self.warning_label.text = "Only letters, spaces, hyphens, and apostrophes are allowed."
            self.warning_label.color = (0.8, 0.2, 0.2, 1)
            if self._clear_trigger:
                self._clear_trigger.cancel()
            self._clear_trigger = Clock.schedule_once(self.clear_input_warning, 2.0)

    def clear_input_warning(self, dt):
        if self.warning_label:
            self.warning_label.text = ""


class SettingsPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'settings_page')
        super().__init__(**kwargs)
        
        self.main_container = FloatLayout()
        
        # --- 1. BRANDING TOP NAVBAR ---
        self.navbar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(4), dp(4)],
            spacing=dp(2),
            pos_hint={'top': 1}
        )
        
        self.back_btn = Button(
            text="Home",
            font_size='12sp', bold=True,
            size_hint=(None, None), size=(dp(70), dp(34)),
            pos_hint={'center_y': 0.5},
            background_normal='', background_color=(0.7, 0.2, 0.2, 1),
            color=(0.9, 0.9, 0.9, 1),
            halign='center', valign='middle'
        )
        self.back_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))
        self.back_btn.bind(on_release=self.go_back_to_home)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners Settings[/color]",
            font_size='15sp', bold=True, markup=True,
            size_hint=(1, 1),
            halign='center', valign='middle'
        )
        self.brand_title.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(2)), None)))
        self.navbar.add_widget(self.brand_title)

        self.nav_spacer = Label(size_hint=(None, None), size=(dp(70), dp(34)))
        self.navbar.add_widget(self.nav_spacer)

        # --- 2. SCROLLABLE SETTINGS CONTENT BODY ---
        self.scroll_view = ScrollView(
            size_hint=(1, None),
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(12),
            padding=[dp(12), dp(10), dp(12), dp(20)],
            size_hint=(1, None)
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        # SECTION A: PARENT & STUDENT PROFILE
        self.profile_toggle_btn = Button(
            text="Parent & Student Profile",
            font_size='15sp', bold=True, color=(1, 1, 1, 1),
            size_hint_y=None, height=dp(48), halign='center', valign='middle',
            background_color=(0.16, 0.50, 0.28, 1), background_normal=''
        )
        self.profile_toggle_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.profile_toggle_btn.bind(on_release=self.show_profile_fields)

        self.profile_dropdown_box = BoxLayout(
            orientation='vertical', spacing=dp(6), size_hint_y=None
        )
        self.profile_dropdown_box.bind(minimum_height=self.profile_dropdown_box.setter('height'))

        profile_close_header_btn = Button(
            text="Parent & Student Profile",
            font_size='16sp', bold=True, color=(0.16, 0.50, 0.28, 1),
            size_hint_y=None, height=dp(35), halign='center', valign='middle',
            background_color=(0, 0, 0, 0), background_normal=''
        )
        profile_close_header_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        profile_close_header_btn.bind(on_release=lambda x: self.hide_profile_fields())
        self.profile_dropdown_box.add_widget(profile_close_header_btn)

        self.parent_warning = Label(text="", font_size='11sp', size_hint_y=None, height=dp(16), halign='center', valign='middle')
        self.parent_warning.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        
        self.child_warning = Label(text="", font_size='11sp', size_hint_y=None, height=dp(16), halign='center', valign='middle')
        self.child_warning.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))

        self.child_name_input = AlphabeticTextInput(
            hint_text="e.g., Mohammed", multiline=False, write_tab=False,
            font_size='14sp', size_hint_y=None, height=dp(44), warning_label=self.child_warning,
            max_chars=15
        )
        self.child_name_input.bind(text=self.reset_save_button)

        self.parent_name_input = AlphabeticTextInput(
            hint_text="e.g., Mr Joe (Optional)", multiline=False, write_tab=False,
            font_size='14sp', size_hint_y=None, height=dp(44), warning_label=self.parent_warning,
            max_chars=30
        )
        self.parent_name_input.bind(text=self.reset_save_button)

        lbl_child = Label(text="First Name/Nickname (Max 15 letters):", font_size='13sp', size_hint_y=None, height=dp(22), halign='center', valign='middle')
        lbl_child.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.profile_dropdown_box.add_widget(lbl_child)
        self.profile_dropdown_box.add_widget(self.child_name_input)
        self.profile_dropdown_box.add_widget(self.child_warning)
        
        lbl_parent = Label(text="Parent/Guardian Name (Max 30 letters):", font_size='13sp', size_hint_y=None, height=dp(22), halign='center', valign='middle')
        lbl_parent.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(4)), None)))
        self.profile_dropdown_box.add_widget(lbl_parent)
        self.profile_dropdown_box.add_widget(self.parent_name_input)
        self.profile_dropdown_box.add_widget(self.parent_warning)
        
        self.save_profile_btn = Button(
            text="Save Profile Updates", font_size='14sp', bold=True,
            size_hint_y=None, height=dp(44),
            halign='center', valign='middle',
            background_color=(0.16, 0.50, 0.28, 1), background_normal=''
        )
        self.save_profile_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.save_profile_btn.bind(on_release=self.save_profile_changes)
        self.profile_dropdown_box.add_widget(self.save_profile_btn)

        # SECTION B: SUBSCRIPTION & USAGE PLAN
        self.plan_toggle_btn = Button(
            text="Subscription & Usage Plan",
            font_size='15sp', bold=True, color=(1, 1, 1, 1),
            size_hint_y=None, height=dp(48), halign='center', valign='middle',
            background_color=(0.12, 0.36, 0.52, 1), background_normal=''
        )
        self.plan_toggle_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.plan_toggle_btn.bind(on_release=self.show_plan_fields)

        self.plan_dropdown_box = BoxLayout(
            orientation='vertical', spacing=dp(10), size_hint_y=None
        )
        self.plan_dropdown_box.bind(minimum_height=self.plan_dropdown_box.setter('height'))

        plan_close_header_btn = Button(
            text="Subscription & Usage Plan",
            font_size='16sp', bold=True, color=(0.12, 0.36, 0.52, 1),
            size_hint_y=None, height=dp(35), halign='center', valign='middle',
            background_color=(0, 0, 0, 0), background_normal=''
        )
        plan_close_header_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        plan_close_header_btn.bind(on_release=lambda x: self.hide_plan_fields())
        self.plan_dropdown_box.add_widget(plan_close_header_btn)
        
        self.plan_info_label = Label(
            text="Active Plan: Loading...",
            font_size='13sp', color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None, height=dp(45), halign='center', valign='middle'
        )
        self.plan_info_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.plan_dropdown_box.add_widget(self.plan_info_label)
        
        change_plan_btn = Button(
            text="Change / Upgrade Learning Plan", font_size='14sp', bold=True,
            size_hint_y=None, height=dp(44), halign='center', valign='middle',
            background_color=(0.12, 0.36, 0.52, 1), background_normal=''
        )
        change_plan_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        change_plan_btn.bind(on_release=self.go_to_plans_page)
        self.plan_dropdown_box.add_widget(change_plan_btn)

        # SECTION C: STORAGE & MEDIA CACHE
        self.cache_toggle_btn = Button(
            text="Storage & Media Cache",
            font_size='15sp', bold=True, color=(1, 1, 1, 1),
            size_hint_y=None, height=dp(48), halign='center', valign='middle',
            background_color=(0.85, 0.55, 0.15, 1), background_normal=''
        )
        self.cache_toggle_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.cache_toggle_btn.bind(on_release=self.show_cache_fields)

        self.cache_dropdown_box = BoxLayout(
            orientation='vertical', spacing=dp(10), size_hint_y=None
        )
        self.cache_dropdown_box.bind(minimum_height=self.cache_dropdown_box.setter('height'))

        cache_close_header_btn = Button(
            text="Storage & Media Cache",
            font_size='16sp', bold=True, color=(0.85, 0.55, 0.15, 1),
            size_hint_y=None, height=dp(35), halign='center', valign='middle',
            background_color=(0, 0, 0, 0), background_normal=''
        )
        cache_close_header_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        cache_close_header_btn.bind(on_release=lambda x: self.hide_cache_fields())
        self.cache_dropdown_box.add_widget(cache_close_header_btn)

        self.cache_status_label = Label(
            text="Tap below to clear downloaded media and free up device space.",
            font_size='12sp', color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None, height=dp(30), halign='center', valign='middle'
        )
        self.cache_status_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.cache_dropdown_box.add_widget(self.cache_status_label)

        # Cache Buttons Layout
        self.cache_btns_layout = BoxLayout(
            orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(44)
        )

        self.clear_audio_cache_btn = Button(
            text="Clear Audio Cache", font_size='13sp', bold=True,
            size_hint_x=0.5, halign='center', valign='middle',
            background_color=(0.85, 0.55, 0.15, 1), background_normal=''
        )
        self.clear_audio_cache_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(4)), None)))
        self.clear_audio_cache_btn.bind(on_release=self.execute_clear_audio_cache)

        self.clear_video_cache_btn = Button(
            text="Clear Video Cache", font_size='13sp', bold=True,
            size_hint_x=0.5, halign='center', valign='middle',
            background_color=(0.75, 0.45, 0.15, 1), background_normal=''
        )
        self.clear_video_cache_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(4)), None)))
        self.clear_video_cache_btn.bind(on_release=self.execute_clear_video_cache)

        self.cache_btns_layout.add_widget(self.clear_audio_cache_btn)
        self.cache_btns_layout.add_widget(self.clear_video_cache_btn)

        self.cache_dropdown_box.add_widget(self.cache_btns_layout)

        # SECTION D: DANGER ZONE
        self.delete_acc_btn = Button(
            text="Delete Account", font_size='14sp', bold=True,
            size_hint_y=None, height=dp(48), halign='center', valign='middle',
            background_color=(0.7, 0.2, 0.2, 1), background_normal=''
        )
        self.delete_acc_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        self.delete_acc_btn.bind(on_release=self.prompt_delete_confirmation)

        self.content_layout.add_widget(self.profile_toggle_btn)
        self.content_layout.add_widget(self.plan_toggle_btn)
        self.content_layout.add_widget(self.cache_toggle_btn)
        self.content_layout.add_widget(self.delete_acc_btn)

        self.scroll_view.add_widget(self.content_layout)
        self.main_container.add_widget(self.scroll_view)
        self.main_container.add_widget(self.navbar)
        self.add_widget(self.main_container)

        # --- RESPONSIVE BOUNDING BINDINGS ---
        Window.bind(on_resize=self._apply_responsive_structure)
        self._apply_responsive_structure()

    def _update_scroll_bounds(self, *args):
        fixed_header_height = self.navbar.height
        top_offset = fixed_header_height + dp(4)
        self.scroll_view.y = 0
        self.scroll_view.height = max(dp(80), Window.height - top_offset)

    def _apply_responsive_structure(self, *args):
        scale = get_responsive_scale()
        self._update_scroll_bounds()

        # Dynamic Navbar Sizing & Font Scaling
        nav_h = dp(46 * scale)
        self.navbar.height = nav_h
        
        if Window.width < dp(320):
            btn_w = dp(50 * scale)
            self.brand_title.font_size = f"{int(20 * scale)}sp"
            self.back_btn.font_size = f"{int(10 * scale)}sp"
            self.clear_audio_cache_btn.font_size = f"{int(10 * scale)}sp"
            self.clear_video_cache_btn.font_size = f"{int(10 * scale)}sp"
        else:
            btn_w = dp(70 * scale)
            self.brand_title.font_size = f"{int(18 * scale)}sp"
            self.back_btn.font_size = f"{int(12 * scale)}sp"
            self.clear_audio_cache_btn.font_size = f"{int(12 * scale)}sp"
            self.clear_video_cache_btn.font_size = f"{int(12 * scale)}sp"

        btn_h = dp(32 * scale)
        self.back_btn.size = (btn_w, btn_h)
        self.nav_spacer.size = (btn_w, btn_h)

        # Dynamic Font Sizes for Section Buttons & Labels
        sec_font = f"{int(16 * scale)}sp"
        self.profile_toggle_btn.font_size = sec_font
        self.plan_toggle_btn.font_size = sec_font
        self.cache_toggle_btn.font_size = sec_font
        self.delete_acc_btn.font_size = sec_font
        self.save_profile_btn.font_size = sec_font

        # Stack cache buttons vertically on extremely tight viewports
        if Window.width < dp(340):
            self.cache_btns_layout.orientation = 'vertical'
            self.cache_btns_layout.height = dp(75 * scale)
            self.clear_audio_cache_btn.size_hint = (1, 0.5)
            self.clear_video_cache_btn.size_hint = (1, 0.5)
        else:
            self.cache_btns_layout.orientation = 'horizontal'
            self.cache_btns_layout.height = dp(44 * scale)
            self.clear_audio_cache_btn.size_hint = (0.5, 1)
            self.clear_video_cache_btn.size_hint = (0.5, 1)

        # Responsive Padding
        if Window.width >= dp(768):
            side_padding = max(dp(20), (Window.width - dp(700)) / 2)
            self.content_layout.padding = [side_padding, dp(14), side_padding, dp(24)]
            self.content_layout.spacing = dp(14)
        else:
            side_pad = max(dp(6), Window.width * 0.03)
            self.content_layout.padding = [side_pad, dp(8), side_pad, dp(16)]
            self.content_layout.spacing = dp(10)

    def _get_active_curriculum_media_paths(self):
        """Collects all exact audio and video file paths directly from CurriculumManager."""
        audio_paths = set()
        video_paths = set()

        # Base application directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # Load curriculum via CurriculumManager to ensure correct JSON location
        from utils.curriculum_manager import CurriculumManager
        data = CurriculumManager.load_curriculum()

        tiers = data.get("tiers", [])
        for tier in tiers:
            for cls in tier.get("classes", []):
                for subj in cls.get("subjects", []):
                    for topic in subj.get("topics", []):

                        # Grab Lesson Audio
                        a_path = topic.get("audio_path")
                        if a_path:
                            full_a_path = os.path.normpath(os.path.join(base_dir, a_path))
                            audio_paths.add(full_a_path)

                        # Grab Quiz Audio
                        for q in topic.get("quiz", []):
                            q_audio = q.get("audio_path")
                            if q_audio:
                                full_q_audio = os.path.normpath(os.path.join(base_dir, q_audio))
                                audio_paths.add(full_q_audio)

                        # Grab Lesson Video
                        v_path = topic.get("video_path") or topic.get("animation_video_concept")
                        if v_path and v_path.endswith(('.mp4', '.mkv', '.avi', '.mov')):
                            full_v_path = os.path.normpath(os.path.join(base_dir, v_path))
                            video_paths.add(full_v_path)

        return audio_paths, video_paths

    def execute_clear_audio_cache(self, instance):
        audio_paths, _ = self._get_active_curriculum_media_paths()
        deleted_count = 0
        bytes_freed = 0

        for file_path in audio_paths:
            if os.path.isfile(file_path):
                try:
                    bytes_freed += os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"[CACHE CLEANER]: Failed to remove {file_path}: {e}")

        mb_freed = round(bytes_freed / (1024 * 1024), 2)
        if deleted_count > 0:
            self.cache_status_label.text = f"Cleared {deleted_count} lesson audio file(s) ({mb_freed} MB freed)!"
            self.cache_status_label.color = (0.2, 0.8, 0.2, 1)
        else:
            self.cache_status_label.text = "No downloaded lesson audio files found to clear."
            self.cache_status_label.color = (0.8, 0.8, 0.8, 1)

    def execute_clear_video_cache(self, instance):
        _, video_paths = self._get_active_curriculum_media_paths()
        deleted_count = 0
        bytes_freed = 0

        for file_path in video_paths:
            if os.path.isfile(file_path):
                try:
                    bytes_freed += os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"[CACHE CLEANER]: Failed to remove {file_path}: {e}")

        mb_freed = round(bytes_freed / (1024 * 1024), 2)
        if deleted_count > 0:
            self.cache_status_label.text = f"Cleared {deleted_count} lesson video file(s) ({mb_freed} MB freed)!"
            self.cache_status_label.color = (0.2, 0.8, 0.2, 1)
        else:
            self.cache_status_label.text = "No downloaded lesson video files found to clear."
            self.cache_status_label.color = (0.8, 0.8, 0.8, 1)

    def show_profile_fields(self, instance=None):
        if self.profile_toggle_btn in self.content_layout.children:
            idx = self.content_layout.children.index(self.profile_toggle_btn)
            self.content_layout.remove_widget(self.profile_toggle_btn)
            self.content_layout.add_widget(self.profile_dropdown_box, index=idx)

    def hide_profile_fields(self):
        if self.profile_dropdown_box in self.content_layout.children:
            idx = self.content_layout.children.index(self.profile_dropdown_box)
            self.content_layout.remove_widget(self.profile_dropdown_box)
            self.content_layout.add_widget(self.profile_toggle_btn, index=idx)

    def show_plan_fields(self, instance=None):
        if self.plan_toggle_btn in self.content_layout.children:
            idx = self.content_layout.children.index(self.plan_toggle_btn)
            self.content_layout.remove_widget(self.plan_toggle_btn)
            self.content_layout.add_widget(self.plan_dropdown_box, index=idx)

    def hide_plan_fields(self):
        if self.plan_dropdown_box in self.content_layout.children:
            idx = self.content_layout.children.index(self.plan_dropdown_box)
            self.content_layout.remove_widget(self.plan_dropdown_box)
            self.content_layout.add_widget(self.plan_toggle_btn, index=idx)

    def show_cache_fields(self, instance=None):
        if self.cache_toggle_btn in self.content_layout.children:
            idx = self.content_layout.children.index(self.cache_toggle_btn)
            self.content_layout.remove_widget(self.cache_toggle_btn)
            self.content_layout.add_widget(self.cache_dropdown_box, index=idx)

    def hide_cache_fields(self):
        if self.cache_dropdown_box in self.content_layout.children:
            idx = self.content_layout.children.index(self.cache_dropdown_box)
            self.content_layout.remove_widget(self.cache_dropdown_box)
            self.content_layout.add_widget(self.cache_toggle_btn, index=idx)

    def reset_save_button(self, *args):
        if self.save_profile_btn.text != "Save Profile Updates":
            self.save_profile_btn.text = "Save Profile Updates"
            self.save_profile_btn.background_color = (0.16, 0.50, 0.28, 1)

    def update_plan_info_display(self):
        profile = database.get_user_profile()
        app = App.get_running_app()
        
        plan = profile.get("chosen_plan_type", "Demo")
        status = profile.get("subscription_status", "ACTIVE")
        rem_sec = app.rem_sec if (app and hasattr(app, 'rem_sec')) else float(profile.get("free_seconds_remaining", database.DEFAULT_FREE_SECONDS))

        if status == "EXPIRED" or rem_sec <= 0:
            self.plan_info_label.text = f"Active Plan: {plan} [color=e74c3c](Expired)[/color]"
            self.plan_info_label.markup = True
            self.plan_info_label.height = dp(40)
        else:
            hrs = int(rem_sec // 3600)
            mins = int((rem_sec % 3600) // 60)
            secs = int(rem_sec % 60)
            
            if hrs > 0:
                time_str = f"{hrs}h {mins}m remaining"
            else:
                time_str = f"{mins}m {secs}s remaining"
                
            self.plan_info_label.text = f"Active Plan: {plan}\n({time_str})"
            self.plan_info_label.markup = False
            self.plan_info_label.height = dp(45)

    def on_pre_enter(self):
        profile = database.get_user_profile()
        self.parent_name_input.text = profile.get("parent_name", "")
        self.child_name_input.text = profile.get("child_name", "")
        
        self.update_plan_info_display()

        self.cache_status_label.text = "Tap below to clear downloaded media and free up device space."
        self.cache_status_label.color = (0.8, 0.8, 0.8, 1)

        self.hide_profile_fields()
        self.hide_plan_fields()
        self.hide_cache_fields()
        self.scroll_view.scroll_y = 1.0

    def save_profile_changes(self, instance):
        p_raw = self.parent_name_input.text.strip()
        c_raw = self.child_name_input.text.strip()

        if not c_raw:
            self.save_profile_btn.text = "Please complete child name!"
            self.save_profile_btn.background_color = (0.7, 0.2, 0.2, 1)
            return

        if len(c_raw) > 15:
            self.child_warning.text = "First name/Nickname must be 15 letters or fewer!"
            self.child_warning.color = (0.8, 0.2, 0.2, 1)
            self.save_profile_btn.text = "Name must be 15 letters or fewer!"
            self.save_profile_btn.background_color = (0.7, 0.2, 0.2, 1)
            return

        if len(p_raw) > 30:
            self.parent_warning.text = "Parent/Guardian name must be 30 letters or fewer!"
            self.parent_warning.color = (0.8, 0.2, 0.2, 1)
            self.save_profile_btn.text = "Parent name must be 30 letters or fewer!"
            self.save_profile_btn.background_color = (0.7, 0.2, 0.2, 1)
            return

        p_name = " ".join(p_raw.split()).title() if p_raw else ""
        c_name = " ".join(c_raw.split()).title()

        database.update_user_profile({
            "parent_name": p_name,
            "child_name": c_name
        })

        self.parent_name_input.text = p_name
        self.child_name_input.text = c_name

        self.hide_profile_fields()

    def go_to_plans_page(self, instance):
        if self.manager:
            plans_screen = self.manager.get_screen('plans_page')
            plans_screen.from_settings = True
            self.manager.current = 'plans_page'

    def go_back_to_home(self, instance=None):
        if self.manager:
            self.manager.current = 'home_page'

    def prompt_delete_confirmation(self, instance):
        scale = get_responsive_scale()
        popup_root = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(12), dp(12), dp(12), dp(12)])

        # Popup Header Title
        title_lbl = Label(
            text="Confirm Account Deletion",
            font_size=f"{int(16 * scale)}sp", bold=True, color=(0.9, 0.2, 0.2, 1),
            size_hint_y=None, height=dp(28),
            halign='center', valign='middle'
        )
        title_lbl.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(8)), None)))
        popup_root.add_widget(title_lbl)

        # Scrollable Body Area
        scroll_container = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        scroll_content = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, padding=[dp(4), dp(4)])
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        msg = (
            "Are you sure you want to delete this account?\n\n"
            "• Saved profile details and account settings and active pass time will be wiped.\n"
            "• If your demo trial was already used, it will not be reset.\n"
            "• You will be redirected to the account registration screen."
        )
        msg_lbl = Label(
            text=msg, font_size=f"{int(12 * scale)}sp", color=(0.85, 0.85, 0.85, 1),
            halign='center', valign='middle', size_hint_y=None,
            line_height=1.2
        )
        msg_lbl.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(10)), None)))
        msg_lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(dp(60), val[1] + dp(10))))
        
        scroll_content.add_widget(msg_lbl)
        scroll_container.add_widget(scroll_content)
        popup_root.add_widget(scroll_container)

        # Bottom Buttons Row
        btn_row = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(38 * scale))
        
        cancel_btn = Button(
            text="Keep Account", font_size=f"{int(12 * scale)}sp", bold=True,
            background_color=(0.3, 0.3, 0.3, 1), background_normal='',
            halign='center', valign='middle'
        )
        cancel_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(4)), None)))

        delete_btn = Button(
            text="Delete Account", font_size=f"{int(12 * scale)}sp", bold=True,
            background_color=(0.8, 0.2, 0.2, 1), background_normal='',
            halign='center', valign='middle'
        )
        delete_btn.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(10), val - dp(4)), None)))
        
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(delete_btn)
        popup_root.add_widget(btn_row)

        popup_width = min(Window.width * 0.92, dp(380))
        popup_height = min(Window.height * 0.75, dp(260 * scale))

        popup = Popup(
            title="", title_size=0, separator_height=0,
            content=popup_root, size_hint=(None, None),
            width=popup_width, height=popup_height,
            auto_dismiss=True
        )

        def execute_wipe(btn_instance):
            popup.dismiss()
            database.delete_user_account()
            
            app = App.get_running_app()
            if app:
                app.sync_from_database()
                
            print("[ACCOUNT ENGINE]: User account wiped. Demo state preserved.")
            
            if self.manager:
                self.manager.current = 'auth_page'

        cancel_btn.bind(on_release=popup.dismiss)
        delete_btn.bind(on_release=execute_wipe)
        popup.open()