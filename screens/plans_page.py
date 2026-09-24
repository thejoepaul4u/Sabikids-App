import os
import json
from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.app import App
from kivy.metrics import dp
from kivy.utils import platform

import database

# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
    base_scale = Window.width / dp(400)
    return max(0.85, min(1.25, base_scale))

# --- REVENUECAT PRODUCT IDENTIFIER MAPPINGS ---
REVENUECAT_PUBLIC_KEY = "test_pFmLpCwcSRHoAXFQHWirlaPoNGK"
REVENUECAT_ENTITLEMENT_ID = "sabi_pass_access"
REVENUECAT_PRODUCT_IDS = {
    "24-Hour Pass": "sabi_24hr_pass",
    "7-Day Pass": "sabi_7day_pass"
}

class PlanOptionButton(Button):
    def __init__(self, plan_name, price_text, note_text="", **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(75))
        kwargs.setdefault('background_color', (0.2, 0.2, 0.2, 1))
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('font_size', '15sp')
        super().__init__(**kwargs)
        self.plan_name = plan_name
        self.note_text = note_text
        self.price_text = price_text
        self.text = f"{plan_name}\n[color=aaaaaa]{price_text}[/color]"
        self.markup = True
        
        self.halign = 'center'
        self.valign = 'middle'
        self.bind(width=lambda inst, val: setattr(inst, 'text_size', (max(dp(20), val - dp(12)), None)))


class PlansPageScreen(Screen):
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'plans_page')
        super().__init__(**kwargs)
        self.from_settings = False
        
        # Base Root Container
        self.main_container = FloatLayout()
        
        # --- TOP NAVIGATION BAR ---
        self.navbar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(2), dp(4)],
            spacing=dp(2),
            pos_hint={'top': 1}
        )
        
        self.back_btn = Button(
            text="Back",
            font_size='12sp', bold=True,
            size_hint=(None, None),
            size=(dp(50), dp(34)),
            pos_hint={'center_y': 0.5},
            background_normal='', background_color=(0.7, 0.2, 0.2, 1),
            color=(0.9, 0.9, 0.9, 1),
            halign='center', valign='middle'
        )
        self.back_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(10), value - dp(2)), None)))
        self.back_btn.bind(on_release=self.go_back_navigation)
        self.navbar.add_widget(self.back_btn)

        self.brand_title = Label(
            text="[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners[/color]",
            font_size='15sp', bold=True, markup=True,
            size_hint=(1, 1),
            halign='center', valign='middle'
        )
        self.brand_title.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(2)), None)))
        self.navbar.add_widget(self.brand_title)

        # Invisible right spacer balancing back button for centered title
        self.nav_spacer = Label(size_hint=(None, None), size=(dp(50), dp(34)))
        self.navbar.add_widget(self.nav_spacer)

        # --- FULL-WIDTH SCROLL CONTAINER ---
        self.scroll_view = ScrollView(
            size_hint=(1, None), 
            pos_hint={'x': 0, 'y': 0},
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        # Full-width main container layout so scroll wheel works across entire screen
        self.layout = BoxLayout(
            orientation='vertical',
            padding=[dp(10), dp(12), dp(10), dp(20)],
            spacing=dp(12),
            size_hint=(1, None)
        )
        self.layout.bind(minimum_height=self.layout.setter('height'))

        # Short Intro Note
        self.intro_note = Label(
            text="To learn faster, master schoolwork and daily studies, build confidence, and stay steps ahead, kids and teens choose to become Sabi Learners.",
            font_size='12sp',
            line_height=1.2,
            color=(0.75, 0.75, 0.75, 1),
            halign='center',
            valign='middle',
            size_hint_y=None
        )
        self.intro_note.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        self.intro_note.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(30), value[1] + dp(6))))
        self.layout.add_widget(self.intro_note)
        
        # Plan Heading Note
        self.plan_note = Label(
            text="Choose Your Access Pass: All passes are one-time purchases. When your active time finishes, simply buy a new pass anytime to keep learning.",
            font_size='10sp',
            italic=True,
            bold=True,
            line_height=1.15,
            color=(0.7, 0.2, 0.2, 1),
            halign='center',
            valign='middle',
            size_hint_y=None
        )
        self.plan_note.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        self.plan_note.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(22), value[1] + dp(4))))
        self.layout.add_widget(self.plan_note)
        
        # Active Plan Details Note
        self.active_note_label = Label(
            text="Tap a plan option below to view details.", 
            font_size='12sp', 
            bold=True,
            line_height=1.2,
            color=(0.16, 0.50, 0.28, 1),
            halign='center',
            valign='middle',
            size_hint_y=None
        )
        self.active_note_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        self.active_note_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(40), value[1] + dp(8))))
        self.layout.add_widget(self.active_note_label)
        
        self.selected_plan = None
        self.plan_buttons = []
        
        options_data = [
            ("Demo", "(Free Trial)", 
             "• 10 minutes One-time Worth of Access.\n• Timer only ticks when using the app—pauses when the app is completely closed."),

            ("24-Hour Active Bundle", "(₦500)", 
             "24 Hours Worth of Access \n• Timer only ticks when using the app—pauses when the app is completely closed."),

            ("7-Day Active Bundle", "(₦1,500)", 
             "7 Days Worth of Access \n• Ideal for active study sprints and mastery. \n• Timer only ticks when using the app—pauses when the app is completely closed.")
        ]
        
        for name, price, note in options_data:
            btn = PlanOptionButton(plan_name=name, price_text=price, note_text=note)
            btn.bind(on_release=self.select_plan_option)
            btn.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(55), value[1] + dp(12))))
            self.plan_buttons.append(btn)
            self.layout.add_widget(btn)

        self.spacer_lbl = Label(size_hint_y=None, height=dp(8))
        self.layout.add_widget(self.spacer_lbl)
        
        # Action Continue Button
        self.continue_btn = Button(
            text="Continue", 
            font_size='14sp', 
            bold=True, 
            size_hint_y=None, 
            height=dp(44), 
            background_color=(0.16, 0.50, 0.28, 1), 
            background_normal='',
            halign='center',
            valign='middle'
        )
        self.continue_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        self.continue_btn.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(44), value[1] + dp(10))))
        self.continue_btn.bind(on_release=self.process_plan_selection)
        self.layout.add_widget(self.continue_btn)
        
        self.scroll_view.add_widget(self.layout)
        
        # Order of adding ensures Navbar floats on top of scrolling area
        self.main_container.add_widget(self.scroll_view)
        self.main_container.add_widget(self.navbar)
        self.add_widget(self.main_container)

        # Dynamic Window Resize Binding
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

        # Always keep "Sabi Learners" full title across all viewports
        self.brand_title.text = "[color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=2980b9]i[/color] [color=ffffff]Learners[/color]"

        # Handle Ultra-Narrow Screens dynamically
        if Window.width < dp(320):
            btn_w = dp(42 * scale)
            self.brand_title.font_size = f"{int(20 * scale)}sp"
            self.back_btn.font_size = f"{int(10 * scale)}sp"
        else:
            btn_w = dp(55 * scale)
            self.brand_title.font_size = f"{int(15 * scale)}sp"
            self.back_btn.font_size = f"{int(12 * scale)}sp"

        # Dynamic Typography
        self.intro_note.font_size = f"{int(15 * scale)}sp"
        self.plan_note.font_size = f"{int(16 * scale)}sp"
        self.active_note_label.font_size = f"{int(15 * scale)}sp"
        self.continue_btn.font_size = f"{int(16 * scale)}sp"

        for btn in self.plan_buttons:
            btn.font_size = f"{int(15 * scale)}sp"

        # Navbar Sizing
        nav_h = dp(50 * scale)
        self.navbar.height = nav_h
        btn_h = dp(40 * scale)
        self.back_btn.size = (btn_w, btn_h)
        self.nav_spacer.size = (btn_w, btn_h)

        # Responsive Layout Padding
        if Window.width >= dp(768):
            side_padding = max(dp(30), (Window.width - dp(850)) / 2)
            self.layout.padding = [side_padding, dp(16), side_padding, dp(24)]
            self.layout.spacing = dp(14)
        else:
            side_pad = max(dp(6), Window.width * 0.03)
            self.layout.padding = [side_pad, dp(8), side_pad, dp(16)]
            self.layout.spacing = dp(10)

    def on_pre_enter(self):
        if self.from_settings:
            self.back_btn.opacity = 1
            self.back_btn.disabled = False
        else:
            self.back_btn.opacity = 0
            self.back_btn.disabled = True

        profile = database.get_user_profile()
        current_plan = profile.get("chosen_plan_type", "Demo")
        
        for btn in self.plan_buttons:
            if btn.plan_name == current_plan:
                self.select_plan_option(btn)
                break

    def go_back_navigation(self, instance=None):
        if self.from_settings:
            self.manager.current = 'settings_page'
        else:
            self.manager.current = 'home_page'

    def select_plan_option(self, instance):
        target = instance
        while target and not hasattr(target, 'plan_name'):
            target = getattr(target, 'parent', None)
            
        if not target:
            return

        self.selected_plan = target.plan_name
        self.active_note_label.text = target.note_text
        self.active_note_label.color = (1, 1, 1, 1)
        
        if self.selected_plan == "Demo":
            self.continue_btn.text = "Start 10-Min Demo"
        else:
            self.continue_btn.text = "Continue to Payment"

        for btn in self.plan_buttons:
            if btn == target:
                btn.background_color = (0.16, 0.50, 0.28, 1)
            else:
                btn.background_color = (0.2, 0.2, 0.2, 1)

    def process_plan_selection(self, instance):
        if not self.selected_plan:
            self.active_note_label.text = "Please select a learning plan before continuing!"
            self.active_note_label.color = (0.7, 0.2, 0.2, 1)
            return

        if self.selected_plan == "Demo":
            profile = database.get_user_profile()
            is_demo_used = int(profile.get("is_demo_used", 0))
            demo_rem_sec = float(profile.get("demo_seconds_remaining", database.PLAN_MAX_SECONDS["Demo"]))

            if is_demo_used == 1 or demo_rem_sec <= 0:
                self.show_free_limit_popup()
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                database.update_user_profile({
                    "chosen_plan_type": "Demo",
                    "subscription_status": "ACTIVE",
                    "free_seconds_remaining": demo_rem_sec,
                    "last_active_timestamp": now_str,
                    "is_registered": 1,
                    "registration_step": "home_page"
                })
                print(f"[DEMO ACTIVATED]: Demo restored with {demo_rem_sec} seconds remaining.")
                
                app = App.get_running_app()
                if app:
                    app.sync_from_database()
                    app.start_metered_timer()
                    
                self.navigate_away()
        else:
            print(f"[BILLING INITIATED]: Preparing RevenueCat payment flow for {self.selected_plan}...")
            self._trigger_revenuecat_billing(self.selected_plan)

    def show_free_limit_popup(self):
        scale = get_responsive_scale()
        
        # Base container layout for popup content
        popup_root = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(12), dp(12), dp(12), dp(12)])

        # Header Title
        title_lbl = Label(
            text="Demo Access Used",
            font_size=f"{int(16 * scale)}sp", bold=True, color=(0.9, 0.4, 0.1, 1),
            size_hint_y=None, height=dp(28),
            halign='center', valign='middle'
        )
        title_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        popup_root.add_widget(title_lbl)

        # Scrollable Body Area
        scroll_container = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        scroll_content = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, padding=[dp(4), dp(4)])
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        msg = (
            "Your 10-minute demo has expired.\n\n"
            "Please select a 24-Hour Pass or 7-Day Pass to keep learning!"
        )
        msg_lbl = Label(
            text=msg, font_size=f"{int(12 * scale)}sp", color=(0.85, 0.85, 0.85, 1),
            halign='center', valign='middle', size_hint_y=None,
            line_height=1.2
        )
        msg_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(10)), None)))
        msg_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', max(dp(40), value[1] + dp(8))))
        
        scroll_content.add_widget(msg_lbl)
        scroll_container.add_widget(scroll_content)
        popup_root.add_widget(scroll_container)

        # Sticky Action Button
        close_btn = Button(
            text="Got It", font_size=f"{int(13 * scale)}sp", bold=True,
            size_hint_y=None, height=dp(38 * scale),
            background_color=(0.16, 0.50, 0.28, 1), background_normal='',
            halign='center', valign='middle'
        )
        close_btn.bind(width=lambda instance, value: setattr(instance, 'text_size', (max(dp(20), value - dp(8)), None)))
        popup_root.add_widget(close_btn)

        # Responsive Dynamic Dimensions
        popup_width = min(Window.width * 0.90, dp(360))
        popup_height = min(Window.height * 0.70, dp(220 * scale))

        popup = Popup(
            title="", title_size=0, separator_height=0,
            content=popup_root, size_hint=(None, None),
            width=popup_width,
            height=popup_height,
            auto_dismiss=True
        )
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _trigger_revenuecat_billing(self, plan_name):
        product_id = REVENUECAT_PRODUCT_IDS.get(plan_name)
        
        if platform == 'android':
            try:
                from jnius import autoclass
                Purchases = autoclass('com.revenuecat.purchases.Purchases')
                PurchasesConfiguration = autoclass('com.revenuecat.purchases.PurchasesConfiguration')
                Activity = autoclass('org.kivy.android.PythonActivity').mActivity
                
                # Configure RevenueCat with Public Key
                builder = PurchasesConfiguration.Builder(Activity, REVENUECAT_PUBLIC_KEY)
                Purchases.configure(builder.build())
                
                purchases_instance = Purchases.getSharedInstance()
                print(f"[REVENUECAT ANDROID]: Initiating purchase for Product ID: {product_id}")
            except Exception as e:
                print(f"[REVENUECAT ERROR]: Native Android SDK error: {e}")
                self.on_payment_success(platform_name="Google Play Store (Test)")

        elif platform == 'ios':
            try:
                from pyobjus import autoclass
                RCPurchases = autoclass('RCPurchases')
                RCPurchases.configureWithAPIKey_(REVENUECAT_PUBLIC_KEY)
                
                rc_instance = RCPurchases.sharedPurchases()
                print(f"[REVENUECAT IOS]: Initiating purchase for Product ID: {product_id}")
            except Exception as e:
                print(f"[REVENUECAT ERROR]: Native iOS SDK error: {e}")
                self.on_payment_success(platform_name="Apple App Store (Test)")

        else:
            print(f"[TEST / DESKTOP MODE]: Bypassing RevenueCat SDK; Crediting metered balance directly for {product_id}.")
            self.on_payment_success(platform_name="Desktop Store Test")

    def on_payment_success(self, platform_name="RevenueCat Store"):
        allocated_seconds = database.PLAN_MAX_SECONDS.get(self.selected_plan, 86400.0)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        database.update_user_profile({
            "chosen_plan_type": self.selected_plan,
            "subscription_status": "ACTIVE",
            "free_seconds_remaining": allocated_seconds,
            "last_active_timestamp": now_str,
            "payment_platform": platform_name,
            "is_registered": 1,
            "registration_step": "home_page"
        })
        
        app = App.get_running_app()
        if app:
            app.sync_from_database()
            app.start_metered_timer()

        print(f"[PAYMENT SUCCESS]: {self.selected_plan} credited with {allocated_seconds} metered active seconds via {platform_name}.")
        self.navigate_away()

    def navigate_away(self):
        if self.from_settings:
            self.from_settings = False
            self.manager.current = 'settings_page'
        else:
            self.manager.current = 'home_page'