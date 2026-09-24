import os
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from utils.isabi_curriculum_manager import ISabiCurriculumManager
from utils.update_popup import UpdateNotificationPopup


# --- RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
  base_scale = Window.width / dp(320)
  return max(0.85, min(1.25, base_scale))


class LevelCardButton(ButtonBehavior, BoxLayout):

  def __init__(self, title, subtitle, bg_color, level_id, **kwargs):
    super().__init__(**kwargs)
    self.orientation = 'vertical'
    self.size_hint_y = None
    self.padding = [dp(14), dp(12), dp(14), dp(12)]
    self.spacing = dp(6)
    self.level_id = level_id

    with self.canvas.before:
      Color(*bg_color)
      self.rect = RoundedRectangle(
          pos=self.pos, size=self.size, radius=[dp(8)]
      )
    self.bind(pos=self._update_rect, size=self._update_rect)

    self.display_title = title if title else 'Untitled Level'
    self.display_subtitle = subtitle if subtitle else ''

    self.lbl_title = Label(
        text=f'[b]{self.display_title}[/b]',
        font_size='16sp',
        markup=True,
        halign='left',
        valign='top',
        size_hint_y=None,
    )
    self.lbl_title.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(4)), None)
        ),
        texture_size=self._update_card_height,
    )
    self.add_widget(self.lbl_title)

    self.lbl_sub = Label(
        text=f'[b]{self.display_subtitle}[/b]',
        font_size='12sp',
        markup=True,
        color=(0.92, 0.92, 0.92, 1),
        halign='left',
        valign='top',
        size_hint_y=None,
    )
    self.lbl_sub.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(4)), None)
        ),
        texture_size=self._update_card_height,
    )
    self.add_widget(self.lbl_sub)

  def _update_card_height(self, *args):
    self.lbl_title.height = max(dp(22), self.lbl_title.texture_size[1])
    self.lbl_sub.height = max(dp(18), self.lbl_sub.texture_size[1])

    total_content = (
        self.lbl_title.height
        + self.lbl_sub.height
        + self.padding[1]
        + self.padding[3]
        + self.spacing
    )
    self.height = max(dp(80), total_content)

  def apply_scale(self, scale):
    title_font_pt = int(17 * scale)
    sub_font_pt = int(12.5 * scale)

    self.lbl_title.font_size = f'{title_font_pt}sp'
    self.lbl_sub.font_size = f'{sub_font_pt}sp'

    self._update_card_height()

  def _update_rect(self, instance, value):
    self.rect.pos = instance.pos
    self.rect.size = instance.size


class ISabiLevelScreen(Screen):

  def __init__(self, **kwargs):
    kwargs.setdefault('name', 'isabi_level')
    super().__init__(**kwargs)

    self.main_container = FloatLayout()

    # --- RESPONSIVE NAVBAR ---
    self.navbar = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(52),
        padding=[dp(2), dp(4)],
        spacing=dp(2),
        pos_hint={'top': 1},
    )

    self.back_btn = Button(
        text='Home',
        font_size='13sp',
        bold=True,
        size_hint=(None, None),
        size=(dp(85), dp(36)),
        pos_hint={'center_y': 0.5},
        background_color=(0.7, 0.2, 0.2, 1),
        background_normal='',
        halign='center',
        valign='middle',
    )
    self.back_btn.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(10), val - dp(2)), None)
        )
    )
    self.back_btn.bind(on_release=self.go_back_home)
    self.navbar.add_widget(self.back_btn)

    self.brand_title = Label(
        text=(
            '[color=ffffff]i-[/color][color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=38b6ff]i[/color]'
            ' [color=ffffff]Challenges[/color]'
        ),
        font_size='16sp',
        bold=True,
        markup=True,
        size_hint=(1, 1),
        halign='center',
        valign='middle',
    )
    self.brand_title.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(2)), None)
        )
    )
    self.navbar.add_widget(self.brand_title)

    self.nav_spacer = Label(size_hint=(None, None), size=(dp(85), dp(36)))
    self.navbar.add_widget(self.nav_spacer)

    self.main_container.add_widget(self.navbar)

    # --- RESPONSIVE SCROLLVIEW & CONTENT CONTAINER ---
    self.scroll_view = ScrollView(
        size_hint=(1, None),
        pos_hint={'x': 0, 'y': 0},
        do_scroll_x=False,
        do_scroll_y=True,
    )

    self.layout = BoxLayout(
        orientation='vertical',
        spacing=dp(12),
        padding=[dp(10), dp(10), dp(10), dp(15)],
        size_hint=(1, None),
    )
    self.layout.bind(minimum_height=self.layout.setter('height'))

    self.welcome_label = Label(
        text='[size=20sp][b]Select Challenge Group:[/b][/size]',
        markup=True,
        font_size='16sp',
        halign='left',
        valign='middle',
        size_hint_y=None,
    )
    self.welcome_label.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(4)), None)
        ),
        texture_size=lambda inst, val: setattr(
            inst, 'height', max(dp(30), val[1] + dp(4))
        ),
    )
    self.layout.add_widget(self.welcome_label)

    self.cards_grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
    self.cards_grid.bind(minimum_height=self.cards_grid.setter('height'))

    self.render_levels()

    self.layout.add_widget(self.cards_grid)
    self.scroll_view.add_widget(self.layout)
    self.main_container.add_widget(self.scroll_view)
    self.add_widget(self.main_container)

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

    self.cards_grid.cols = 1

    if Window.width < dp(360):
      btn_w = dp(55 * scale)
      self.back_btn.text = 'Home'
      self.back_btn.font_size = f'{int(11 * scale)}sp'
      self.brand_title.font_size = f'{int(18 * scale)}sp'
    else:
      btn_w = dp(75 * scale)
      self.back_btn.text = 'Home'
      self.back_btn.font_size = f'{int(13 * scale)}sp'
      self.brand_title.font_size = f'{int(20 * scale)}sp'

    nav_h = dp(50 * scale)
    self.navbar.height = nav_h
    btn_h = dp(38 * scale)
    self.back_btn.size = (btn_w, btn_h)
    self.nav_spacer.size = (btn_w, btn_h)

    self.welcome_label.font_size = f'{int(16 * scale)}sp'

    if Window.width >= dp(768):
      side_padding = max(dp(30), (Window.width - dp(850)) / 2)
      self.layout.padding = [side_padding, dp(16), side_padding, dp(24)]
      self.layout.spacing = dp(14)
    else:
      side_pad = max(dp(8), Window.width * 0.03)
      self.layout.padding = [side_pad, dp(10), side_pad, dp(16)]
      self.layout.spacing = dp(12)

    for child in self.cards_grid.children:
      if isinstance(child, LevelCardButton):
        child.apply_scale(scale)

  def render_levels(self):
    levels_data = [
        {
            'title': 'Primary Education General Challenges',
            'subtitle': 'Primary 1–6',
            'id': 'level_1',
            'color': (0.04, 0.22, 0.12, 1),
        },
        {
            'title': 'Junior Secondary Education General Challenges',
            'subtitle': 'JSS 1–3',
            'id': 'level_2',
            'color': (0.60, 0.20, 0.05, 1),
        },
        {
            'title': 'Senior Secondary Education General Challenges',
            'subtitle': 'SSS 1–3',
            'id': 'level_3',
            'color': (0.05, 0.22, 0.38, 1),
        },
    ]

    for item in levels_data:
      btn = LevelCardButton(
          title=item['title'],
          subtitle=item['subtitle'],
          bg_color=item['color'],
          level_id=item['id'],
      )
      btn.bind(on_release=self.on_level_selected)
      self.cards_grid.add_widget(btn)

    self._apply_responsive_structure()

  def on_level_selected(self, instance):
    ISabiCurriculumManager.check_level_update(
        level_id=instance.level_id,
        on_update_found_callback=self.prompt_isabi_update,
    )

    if self.manager and self.manager.has_screen('isabi_subject'):
      subject_screen = self.manager.get_screen('isabi_subject')
      level_title = instance.display_title
      subject_screen.load_level_subjects(
          level_id=instance.level_id, level_title=level_title
      )
      self.manager.current = 'isabi_subject'

  def prompt_isabi_update(self, level_id):
    """Shows update notification popup when new questions/options are found."""
    popup = UpdateNotificationPopup(
        on_confirm_callback=lambda: self.apply_isabi_update(level_id),
        update_type='isabi',
    )
    popup.open()

  def apply_isabi_update(self, level_id):
    """Saves target level data to local disk and reloads the cache."""
    success = ISabiCurriculumManager.apply_pending_update(
        target_level_id=level_id
    )
    if success:
      ISabiCurriculumManager.reload_data()

  def go_back_home(self, instance):
    if self.manager and self.manager.has_screen('home_page'):
      self.manager.current = 'home_page'

  def on_pre_enter(self):
    self._apply_responsive_structure()