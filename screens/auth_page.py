import re
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp


def get_responsive_scale():
    base_scale = Window.width / dp(380)
    return max(0.85, min(1.25, base_scale))


class ResponsiveTextInput(TextInput):
    """ Dynamically expands vertically based on both hint_text and typed text wrapping """
    def __init__(self, warning_label=None, max_words=None, max_chars=None, **kwargs):
        super().__init__(**kwargs)
        self.warning_label = warning_label
        self.max_words = max_words
        self.max_chars = max_chars
        self._clear_trigger = None
        
        # Ensure text wraps properly inside internal padding
        self.bind(width=self._recalculate_box_height)
        self.bind(text=self._recalculate_box_height)

    def _recalculate_box_height(self, *args):
        # Calculate available interior width for text/hint
        pad_x = self.padding[0] + self.padding[2]
        avail_w = max(dp(20), self.width - pad_x)

        # Estimate lines needed for display text or hint text
        display_str = self.text if self.text else self.hint_text
        if not display_str:
            lines = 1
        else:
            # Approx character limit per line based on font size
            char_width = self.font_size * 0.55
            chars_per_line = max(1, int(avail_w / char_width))
            
            # Count wrapped lines across all paragraphs
            lines = 0
            for paragraph in display_str.split('\n'):
                lines += max(1, (len(paragraph) + chars_per_line - 1) // chars_per_line)

        # Calculate dynamic height: base line height + padding
        line_height = self.font_size * 1.3
        pad_y = self.padding[1] + self.padding[3]
        calculated_h = (lines * line_height) + pad_y + dp(12)
        
        self.height = max(dp(38), calculated_h)

    def insert_text(self, substring, from_undo=False):
        # Prevent manual enter presses while keeping multiline wrapping visual
        if '\n' in substring or '\r' in substring:
            substring = substring.replace('\n', '').replace('\r', '')

        # Project what the full string will be
        cursor_pos = self.cursor_index()
        projected_text = self.text[:cursor_pos] + substring + self.text[cursor_pos:]

        # Check character limit if set
        if self.max_chars and len(projected_text) > self.max_chars:
            self.show_limit_warning(f"Maximum limit of {self.max_chars} characters reached!")
            return

        # Check word limit if set
        if self.max_words:
            words = projected_text.strip().split()
            # If adding trailing spaces after hitting word limit
            if len(words) > self.max_words or (len(words) == self.max_words and substring.isspace() and self.text.endswith(' ')):
                self.show_limit_warning(f"Maximum limit of {self.max_words} words reached!")
                return

        return super().insert_text(substring, from_undo=from_undo)

    def show_limit_warning(self, message=None):
        if self.warning_label:
            msg = message if message else f"Maximum limit of {self.max_words} words reached!"
            self.warning_label.text = msg
            self.warning_label.color = (0.8, 0.2, 0.2, 1)
            if self._clear_trigger:
                self._clear_trigger.cancel()
            self._clear_trigger = Clock.schedule_once(self.clear_input_warning, 2.5)

    def clear_input_warning(self, dt):
        if self.warning_label:
            self.warning_label.text = ""


class AlphabeticTextInput(ResponsiveTextInput):
    def insert_text(self, substring, from_undo=False):
        if re.search(r'[^a-zA-Z\s\'\-]', substring):
            self.show_input_warning()
        clean_string = re.sub(r'[^a-zA-Z\s\'\-]', '', substring)
        return super().insert_text(clean_string, from_undo=from_undo)

    def show_input_warning(self):
        if self.warning_label:
            self.warning_label.text = "Only letters, spaces, hyphens, and apostrophes allowed."
            self.warning_label.color = (0.8, 0.2, 0.2, 1)
            if self._clear_trigger:
                self._clear_trigger.cancel()
            self._clear_trigger = Clock.schedule_once(self.clear_input_warning, 2.5)


class AuthPageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.root_layout = BoxLayout(orientation='vertical', size_hint=(1, 1))

        # 1. FIXED TOP NAVBAR
        self.navbar = BoxLayout(
            orientation='horizontal', 
            size_hint=(1, None), 
            height=dp(48),
            padding=[dp(6), dp(4)],
            spacing=dp(4)
        )
        
        self.back_btn = Button(
            text="Back",
            font_size='11sp',
            bold=True,
            size_hint=(None, 1),
            width=dp(60),
            background_color=(0.7, 0.2, 0.2, 1),
            background_normal='',
            halign='center', valign='middle'
        )
        self.back_btn.bind(on_release=self.go_back_to_splash)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners[/color]",
            font_size='16sp', bold=True, markup=True,
            size_hint=(1, 1),
            halign='center', valign='middle',
            shorten=True, shorten_from='right'
        )
        self.brand_title.bind(size=self._update_text_bounds)
        self.navbar.add_widget(self.brand_title)

        self.nav_spacer = Label(size_hint=(None, 1), width=dp(60))
        self.navbar.add_widget(self.nav_spacer)

        self.root_layout.add_widget(self.navbar)

        # 2. VERTICAL SCROLL VIEW
        self.scroll_view = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.form_layout = BoxLayout(
            orientation='vertical', 
            padding=[dp(12), dp(10)], 
            spacing=dp(8), 
            size_hint_x=1, 
            size_hint_y=None
        )
        self.form_layout.bind(minimum_height=self.form_layout.setter('height'))
        self.form_layout.bind(width=self._on_form_width_changed)
        
        self.scroll_view.add_widget(self.form_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        self.add_widget(self.root_layout)

        # Build Form Elements
        self.build_registration_fields()

        # Responsive listener on Window resize
        Window.bind(on_resize=self._trigger_responsive_update)
        Clock.schedule_once(lambda dt: self._apply_responsive_structure(), 0)

    def _update_text_bounds(self, instance, value):
        instance.text_size = value

    def _trigger_responsive_update(self, *args):
        Clock.schedule_once(lambda dt: self._apply_responsive_structure(), 0)

    def _on_form_width_changed(self, instance, width):
        avail_width = max(dp(80), width - instance.padding[0] - instance.padding[2])
        
        for lbl in [self.form_header, self.lbl_child, self.child_warning, 
                    self.lbl_parent, self.parent_warning]:
            lbl.text_size = (avail_width, None)

        self.lbl_terms.text_size = (max(dp(60), avail_width - dp(32)), None)
        self.submit_btn.text_size = (max(dp(60), avail_width - dp(12)), None)

    def _refit_label_height(self, instance, *args):
        if instance.texture_size[1] > 0:
            instance.height = instance.texture_size[1] + dp(4)

    def _refit_button_height(self, instance, *args):
        if instance.texture_size[1] > 0:
            instance.height = max(dp(44), instance.texture_size[1] + dp(16))

    def _apply_responsive_structure(self, *args):
        # Calculate dynamic global scale factor from window width
        scale = get_responsive_scale()

        # --- TYPOGRAPHY SCALING ---
        self.brand_title.font_size = f"{int(20 * scale)}sp"  # Sabi Learners header title font
        self.back_btn.font_size = f"{int(12 * scale)}sp"     # Back button text font
        self.form_header.font_size = f"{int(22 * scale)}sp"   # Form header title font
        
        self.lbl_child.font_size = f"{int(14 * scale)}sp"     # First name field label font
        self.child_warning.font_size = f"{int(11 * scale)}sp" # First name warning label font
        self.lbl_parent.font_size = f"{int(14 * scale)}sp"   # Parent name field label font
        self.parent_warning.font_size = f"{int(11 * scale)}sp"# Parent name warning label font
        self.lbl_terms.font_size = f"{int(13 * scale)}sp"    # Terms & conditions label font
        self.submit_btn.font_size = f"{int(14 * scale)}sp"   # Main action button font

        # --- INPUT FIELD TYPOGRAPHY (Numeric dp values for TextInput) ---
        input_font_size = dp(14 * scale)                      # Base font size for input fields
        for inp in [self.child_input, self.parent_input]:
            inp.font_size = input_font_size                   # Set numeric font size on input

        # --- TOP NAVIGATION BAR DIMENSIONS ---
        self.navbar.height = dp(52 * scale)                   # Top header bar height
        nav_btn_w = dp(75 * scale)                            # Back button & spacer width balance
        self.back_btn.width = nav_btn_w                       # Actionable back button width
        self.nav_spacer.width = nav_btn_w                     # Right side invisible spacer width

        # --- DYNAMIC LAYOUT PADDING & SPACING ---
        if Window.width >= dp(550):
            side_pad = dp(Window.width * 0.18)                # Side margin padding on wide/desktop screens
            self.form_layout.padding = [side_pad, dp(15), side_pad, dp(15)] # Container padding on wide screens
            self.form_layout.spacing = dp(12)                 # Space between input fields on wide screens
        else:
            self.form_layout.padding = [dp(12), dp(10), dp(12), dp(10)]     # Container padding on mobile screens
            self.form_layout.spacing = dp(10)                 # Space between input fields on mobile screens

        # --- RE-EVALUATE ELEMENT BOUNDS & DYNAMIC HEIGHTS ---
        self._on_form_width_changed(self.form_layout, self.form_layout.width) # Update label text wrapping bounds
        for inp in [self.child_input, self.parent_input]:
            inp._recalculate_box_height()                     # Recalculate input box heights for new font sizes

    def go_back_to_splash(self, instance):
        if self.manager:
            self.manager.current = 'receiving_page'

    def reset_submit_button(self, *args):
        if self.submit_btn.text != "Get Started":
            self.submit_btn.text = "Get Started"
            self.submit_btn.background_color = (0.16, 0.50, 0.28, 1)

    def build_registration_fields(self):
        # Header
        self.form_header = Label(
            text="Registration", 
            font_size='18sp', 
            bold=True, 
            color=(0.16, 0.50, 0.28, 1), 
            size_hint=(1, None), 
            height=dp(28),
            halign='center', valign='middle'
        )
        self.form_layout.add_widget(self.form_header)
        
        # First Name / Nickname
        self.lbl_child = Label(
            text="First Name / Nickname (Max 15 letters):", 
            font_size='12sp', 
            halign='left', valign='middle', 
            size_hint=(1, None), height=dp(18)
        )
        self.lbl_child.bind(texture_size=self._refit_label_height)
        self.form_layout.add_widget(self.lbl_child)
        
        self.child_warning = Label(
            text="", 
            font_size='10sp', 
            size_hint=(1, None), height=dp(0), 
            halign='left', valign='middle'
        )
        self.child_warning.bind(texture_size=self._refit_label_height)
        
        self.child_input = AlphabeticTextInput(
            hint_text="e.g., Onyebuchi", 
            multiline=True, write_tab=False, 
            size_hint=(1, None), height=dp(38), 
            warning_label=self.child_warning,
            max_words=15,
            max_chars=15,
            font_size='12sp',
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        self.child_input.bind(text=self.reset_submit_button)
        self.form_layout.add_widget(self.child_input)
        self.form_layout.add_widget(self.child_warning)

        # Parent / Guardian Name (Optional)
        self.lbl_parent = Label(
            text="Parent / Guardian Name (Max 30 letters):", 
            font_size='12sp', 
            halign='left', valign='middle', 
            size_hint=(1, None), height=dp(18)
        )
        self.lbl_parent.bind(texture_size=self._refit_label_height)
        self.form_layout.add_widget(self.lbl_parent)
        
        self.parent_warning = Label(
            text="", 
            font_size='10sp', 
            size_hint=(1, None), height=dp(0), 
            halign='left', valign='middle'
        )
        self.parent_warning.bind(texture_size=self._refit_label_height)
        
        self.parent_input = AlphabeticTextInput(
            hint_text="e.g., Mrs Adeyemo (optional)", 
            multiline=True, write_tab=False, 
            size_hint=(1, None), height=dp(38), 
            warning_label=self.parent_warning,
            max_words=30,
            max_chars=30,
            font_size='12sp',
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        self.parent_input.bind(text=self.reset_submit_button)
        self.form_layout.add_widget(self.parent_input)
        self.form_layout.add_widget(self.parent_warning)
        
        # Checkbox Row
        self.terms_checkbox_layout = BoxLayout(
            orientation='horizontal', 
            size_hint=(1, None), 
            height=dp(36), 
            spacing=dp(8)
        )
        self.terms_check = CheckBox(
            size_hint=(None, None), 
            size=(dp(24), dp(24)), 
            color=(0.2, 0.9, 0.4, 1),
            pos_hint={'center_y': 0.5}  # Centers checkbox vertically relative to multi-line text
        )

        self.terms_check.bind(active=self.reset_submit_button)
        self.terms_checkbox_layout.add_widget(self.terms_check)
        
        self.lbl_terms = Label(
            text="I agree to the Sabi Learners Privacy & Terms", 
            font_size='11sp', 
            halign='left', valign='top',
            size_hint=(1, None),
            height=dp(24)
        )
        self.lbl_terms.bind(texture_size=self._update_terms_layout_height)
        self.terms_checkbox_layout.add_widget(self.lbl_terms)
        
        self.form_layout.add_widget(self.terms_checkbox_layout)
        
        # Submit Button
        self.submit_btn = Button(
            text="Get Started", 
            font_size='12sp', 
            bold=True, 
            size_hint=(1, None), 
            height=dp(44), 
            background_color=(0.16, 0.50, 0.28, 1), 
            background_normal='',
            halign='center', valign='middle'
        )
        self.submit_btn.bind(texture_size=self._refit_button_height)
        self.submit_btn.bind(on_release=self.process_signin)
        self.form_layout.add_widget(self.submit_btn)

    def _update_terms_layout_height(self, instance, *args):
        if instance.texture_size[1] > 0:
            new_h = max(dp(24), instance.texture_size[1] + dp(4))
            instance.height = new_h
            self.terms_checkbox_layout.height = new_h

    def process_signin(self, instance):
        p_raw = self.parent_input.text.strip()
        c_raw = self.child_input.text.strip()
        is_agreed = self.terms_check.active 
        
        if not c_raw or not is_agreed:
            self.submit_btn.text = "Please complete first name/nickname and agree to terms!"
            self.submit_btn.background_color = (0.7, 0.2, 0.2, 1)
            return

        p_name = " ".join(p_raw.split()).title() if p_raw else ""
        c_compressed = " ".join(c_raw.split())
        
        child_name_list = c_compressed.split()
        child_target_word = child_name_list[-1] if len(child_name_list) > 1 else c_compressed
        c_name = child_target_word.title() 
            
        try:
            import database
            database.update_user_profile({
                "registration_step": "plans_page",
                "is_verified": 1,
                "parent_name": p_name,
                "child_name": c_name
            })
            print("[SQLITE TRANSACTION]: User profile registered locally.")
        except Exception as e:
            print(f"Error saving profile: {e}")
        
        if self.manager:
            import database
            self.manager.temp_user_data = database.get_user_profile()
            self.manager.current = 'plans_page'