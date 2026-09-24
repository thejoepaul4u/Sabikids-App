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
from utils.isabi_curriculum_manager import ISabiCurriculumManager
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock


# --- RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
  base_scale = Window.width / dp(320)
  return max(0.85, min(1.25, base_scale))


# 4 Dark Vibe Palette Colors in fixed repeating sequence
SUBJECT_CARD_COLORS = [
    (0.04, 0.22, 0.12, 1),  # Deep Forest Green
    (0.60, 0.20, 0.05, 1),  # Dark Orange
    (0.55, 0.42, 0.05, 1),  # Dark Yellow
    (0.05, 0.22, 0.38, 1),  # Dark Navy Blue
]


class SubjectCardButton(ButtonBehavior, BoxLayout):
  """Reusable card button for dynamically rendering subject items."""

  def __init__(self, title, subject_id, bg_color=None, **kwargs):
    super().__init__(**kwargs)
    self.orientation = 'vertical'
    self.size_hint_y = None
    self.padding = [dp(14), dp(12), dp(14), dp(12)]
    self.spacing = dp(6)
    self.subject_id = subject_id

    card_bg = bg_color if bg_color is not None else SUBJECT_CARD_COLORS[0]

    with self.canvas.before:
      Color(*card_bg)
      self.rect = RoundedRectangle(
          pos=self.pos, size=self.size, radius=[dp(8)]
      )
    self.bind(pos=self._update_rect, size=self._update_rect)

    self.display_title = title if title else 'Untitled Subject'

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

  def _update_card_height(self, *args):
    self.lbl_title.height = max(dp(22), self.lbl_title.texture_size[1])
    total_content = (
        self.lbl_title.height + self.padding[1] + self.padding[3] + self.spacing
    )
    self.height = max(dp(70), total_content)

  def apply_scale(self, scale):
    title_font_pt = int(17 * scale)
    self.lbl_title.font_size = f'{title_font_pt}sp'
    self._update_card_height()

  def _update_rect(self, instance, value):
    self.rect.pos = instance.pos
    self.rect.size = instance.size


class ISabiSubjectScreen(Screen):

  def __init__(self, **kwargs):
    kwargs.setdefault('name', 'isabi_subject')
    super().__init__(**kwargs)

    self.selected_level_id = None
    self.selected_level_title = 'Level'
    self._ticker_event = None

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
        text=' Levels',
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
    self.back_btn.bind(on_release=self.go_back_levels)
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

    # --- RECURRING INTERNET CONNECTIVITY REMINDER BANNER ---
    self.notice_box = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(36),
        padding=[dp(10), dp(6)],
        spacing=dp(6),
    )
    with self.notice_box.canvas.before:
      Color(0.12, 0.16, 0.22, 1)
      self.notice_rect = RoundedRectangle(
          pos=self.notice_box.pos,
          size=self.notice_box.size,
          radius=[dp(6)],
      )
    self.notice_box.bind(
        pos=lambda inst, val: setattr(self.notice_rect, 'pos', val),
        size=lambda inst, val: setattr(self.notice_rect, 'size', val),
    )

    self.notice_messages = [
        'Connect to the internet periodically to check for new Subject Challenges and updates.',
        'AI-Powered and Human Creativity & Compilation.',
    ]
    self.notice_index = 0

    self.notice_label = Label(
        text=(
            f'[color=f1c40f][b]Note:[/b][/color]'
            f' [color=dddddd]{self.notice_messages[0]}[/color]'
        ),
        markup=True,
        font_size='12sp',
        halign='left',
        valign='middle',
        size_hint=(1, None),
    )
    self.notice_label.bind(texture_size=self._on_notice_label_texture)
    self.notice_box.bind(width=self._update_notice_text_width)
    self.notice_box.add_widget(self.notice_label)
    self.layout.add_widget(self.notice_box)

    self.level_header_lbl = Label(
        text='[size=22sp][b]Level Name[/b][/size]',
        markup=True,
        font_size='20sp',
        halign='left',
        valign='middle',
        size_hint_y=None,
    )
    self.level_header_lbl.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(4)), None)
        ),
        texture_size=lambda inst, val: setattr(
            inst, 'height', max(dp(34), val[1] + dp(4))
        ),
    )
    self.layout.add_widget(self.level_header_lbl)

    self.sub_header = Label(
        text='Select a subject to start practice:',
        font_size='14sp',
        bold=True,
        color=(0.90, 0.90, 0.90, 1),
        halign='left',
        valign='middle',
        size_hint_y=None,
    )
    self.sub_header.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(4)), None)
        ),
        texture_size=lambda inst, val: setattr(
            inst, 'height', max(dp(22), val[1] + dp(2))
        ),
    )
    self.layout.add_widget(self.sub_header)

    self.cards_grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
    self.cards_grid.bind(minimum_height=self.cards_grid.setter('height'))
    self.layout.add_widget(self.cards_grid)

    self.scroll_view.add_widget(self.layout)
    self.main_container.add_widget(self.scroll_view)
    self.add_widget(self.main_container)

    Window.bind(on_resize=self._apply_responsive_structure)
    self._apply_responsive_structure()

  def _update_notice_text_width(self, instance, val):
    self.notice_label.text_size = (max(dp(20), val - dp(20)), None)

  def _on_notice_label_texture(self, instance, val):
    self.notice_label.height = val[1]
    self.notice_box.height = max(dp(36), val[1] + dp(12))

  def _rotate_notice_text(self, dt):
    self.notice_index = (self.notice_index + 1) % len(self.notice_messages)
    msg = self.notice_messages[self.notice_index]
    self.notice_label.text = (
        f'[color=f1c40f][b]Note:[/b][/color] [color=dddddd]{msg}[/color]'
    )

  def on_enter(self):
    if not self._ticker_event:
      self._ticker_event = Clock.schedule_interval(
          self._rotate_notice_text, 4.0
      )

  def on_leave(self):
    if self._ticker_event:
      self._ticker_event.cancel()
      self._ticker_event = None

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
      self.back_btn.text = 'Levels'
      self.back_btn.font_size = f'{int(11 * scale)}sp'
      self.brand_title.font_size = f'{int(18 * scale)}sp'
    else:
      btn_w = dp(75 * scale)
      self.back_btn.text = 'Levels'
      self.back_btn.font_size = f'{int(13 * scale)}sp'
      self.brand_title.font_size = f'{int(20 * scale)}sp'

    nav_h = dp(50 * scale)
    self.navbar.height = nav_h
    btn_h = dp(38 * scale)
    self.back_btn.size = (btn_w, btn_h)
    self.nav_spacer.size = (btn_w, btn_h)

    # Dynamic Notice Banner Sizing
    self.notice_label.font_size = f'{int(12 * scale)}sp'
    self._update_notice_text_width(self.notice_box, self.notice_box.width)

    self.level_header_lbl.font_size = f'{int(20 * scale)}sp'
    self.sub_header.font_size = f'{int(14 * scale)}sp'

    if Window.width >= dp(768):
      side_padding = max(dp(30), (Window.width - dp(850)) / 2)
      self.layout.padding = [side_padding, dp(16), side_padding, dp(24)]
      self.layout.spacing = dp(14)
    else:
      side_pad = max(dp(8), Window.width * 0.03)
      self.layout.padding = [side_pad, dp(10), side_pad, dp(16)]
      self.layout.spacing = dp(12)

    for child in self.cards_grid.children:
      if isinstance(child, SubjectCardButton):
        child.apply_scale(scale)

  def load_level_subjects(self, level_id, level_title, subjects_list=None):
    self.selected_level_id = level_id
    self.selected_level_title = level_title
    self.level_header_lbl.text = f'[size=22sp][b]{level_title}[/b][/size]'

    self.cards_grid.clear_widgets()

    if not subjects_list:
      subjects_list = ISabiCurriculumManager.get_subjects_for_level(level_id)

    if not subjects_list:
      subjects_registry = {
          'level_1': [
              {'title': 'Mathematics', 'subject_id': 'math'},
              {'title': 'English Language', 'subject_id': 'eng'},
          ],
          'level_2': [
              {'title': 'Mathematics', 'subject_id': 'math'},
              {'title': 'English Language', 'subject_id': 'eng'},
              {
                  'title': 'Nig Social & Cultural Education',
                  'subject_id': 'nig_social',
              },
          ],
          'level_3': [
              {'title': 'Quantitative Reasoning (QA)', 'subject_id': 'qa'},
              {'title': 'Verbal Reasoning (VR)', 'subject_id': 'vr'},
              {
                  'title': 'Nig Social & Cultural Education',
                  'subject_id': 'nig_social',
              },
              {'title': 'Constitution', 'subject_id': 'constitution'},
          ],
      }
      subjects_list = subjects_registry.get(level_id, [])

    for idx, subj in enumerate(subjects_list):
      selected_color = SUBJECT_CARD_COLORS[idx % len(SUBJECT_CARD_COLORS)]

      sub_title = subj.get('title', 'Subject')
      sub_id = subj.get('subject_id') or subj.get('id', 'math')

      btn = SubjectCardButton(
          title=sub_title, subject_id=sub_id, bg_color=selected_color
      )
      btn.bind(on_release=self.on_subject_selected)
      self.cards_grid.add_widget(btn)

    self._apply_responsive_structure()

  def on_subject_selected(self, instance):
    subject_id = getattr(instance, 'subject_id', None)
    level_id = self.selected_level_id or 'level_1'

    quizzes = ISabiCurriculumManager.get_quizzes(level_id, subject_id)

    if self.manager and self.manager.has_screen('isabi_mcq'):
      mcq_screen = self.manager.get_screen('isabi_mcq')
      clean_title = instance.display_title
      mcq_screen.load_mcq_data(
          subject_title=clean_title,
          questions=quizzes,
          level_id=level_id,
          subject_id=subject_id,
      )
      self.manager.current = 'isabi_mcq'

  def go_back_levels(self, instance):
    if self.manager and self.manager.has_screen('isabi_level'):
      self.manager.current = 'isabi_level'

  def on_pre_enter(self):
    self._apply_responsive_structure()