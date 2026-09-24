import os
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage, Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView


# --- GLOBAL RESPONSIVE SCALE HELPER ---
def get_responsive_scale():
  base_scale = Window.width / dp(400)
  return max(0.95, min(1.30, base_scale))


class MCQOptionButton(ButtonBehavior, BoxLayout):
  """Reusable card button for MCQ options with dynamic color feedback."""

  def __init__(self, option_text, **kwargs):
    super().__init__(**kwargs)
    self.orientation = 'vertical'
    self.size_hint_y = None
    self.padding = [dp(16), dp(10), dp(16), dp(10)]
    self.spacing = dp(4)
    self.option_text = option_text

    with self.canvas.before:
      self.bg_color = Color(0.2, 0.25, 0.35, 1)
      self.rect = RoundedRectangle(
          pos=self.pos, size=self.size, radius=[dp(8)]
      )
    self.bind(pos=self._update_rect, size=self._update_rect)

    self.lbl_text = Label(
        text=f'{option_text}',
        font_size='15sp',
        color=(1, 1, 1, 1),
        bold=True,
        halign='center',
        valign='middle',
        size_hint_y=None,
    )
    self.lbl_text.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(10), val - dp(4)), None)
        ),
        texture_size=self._update_card_height,
    )
    self.add_widget(self.lbl_text)

  def _update_card_height(self, *args):
    self.lbl_text.height = max(dp(22), self.lbl_text.texture_size[1])
    total_content = (
        self.lbl_text.height + self.padding[1] + self.padding[3] + self.spacing
    )
    self.height = max(dp(52), total_content)

  def apply_scale(self, scale):
    self.lbl_text.font_size = f'{int(15 * scale)}sp'
    self._update_card_height()

  def _update_rect(self, instance, value):
    self.rect.pos = instance.pos
    self.rect.size = instance.size

  def set_feedback(self, is_correct):
    if is_correct:
      self.bg_color.rgba = (0.15, 0.68, 0.37, 1)  # Emerald Green
      self.lbl_text.text = f'{self.option_text}  -  [b]Correct![/b]'
    else:
      self.bg_color.rgba = (0.8, 0.2, 0.2, 1)  # Crimson Red
      self.lbl_text.text = f'{self.option_text}  -  [b]Wrong![/b]'
    self.lbl_text.markup = True


class QuestionView(Screen):
  """Isolated View exclusively for displaying questions and optional images."""

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.name = 'question_view'

    self.content = BoxLayout(
        orientation='vertical',
        spacing=dp(12),
        padding=[dp(10), dp(10), dp(10), dp(20)],
        size_hint=(1, None),
    )
    self.content.bind(minimum_height=self.content.setter('height'))

    self.progress_lbl = Label(
        text='Question 1 of X',
        font_size='14sp',
        bold=True,
        color=(0.65, 0.75, 0.9, 1),
        halign='left',
        valign='middle',
        size_hint_y=None,
    )
    self.progress_lbl.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(10), val - dp(4)), None)
        ),
        texture_size=lambda inst, val: setattr(
            inst, 'height', max(dp(22), val[1] + dp(2))
        ),
    )
    self.content.add_widget(self.progress_lbl)

    self.question_lbl = Label(
        text='',
        font_size='17sp',
        bold=True,
        color=(1, 1, 1, 1),
        halign='left',
        valign='middle',
        size_hint_y=None,
    )
    self.question_lbl.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(8)), None)
        ),
        texture_size=lambda inst, val: setattr(
            inst, 'height', max(dp(28), val[1] + dp(4))
        ),
    )
    self.content.add_widget(self.question_lbl)

    # Dynamic Container for Top Image Question Uploads
    self.image_container = BoxLayout(
        orientation='vertical',
        size_hint_y=None,
        height=dp(0),
        spacing=dp(4),
    )
    self.content.add_widget(self.image_container)

    self.options_grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
    self.options_grid.bind(minimum_height=self.options_grid.setter('height'))
    self.content.add_widget(self.options_grid)

    scroll = ScrollView(
        size_hint=(1, 1),
        pos_hint={'x': 0, 'y': 0},
        do_scroll_x=False,
        do_scroll_y=True,
    )
    scroll.add_widget(self.content)
    self.add_widget(scroll)


class ResultsView(Screen):
  """Isolated View exclusively for displaying summary card."""

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.name = 'results_view'

    self.scroll = ScrollView(
        size_hint=(1, 1),
        pos_hint={'x': 0, 'y': 0},
        do_scroll_x=False,
        do_scroll_y=True,
    )

    self.content = BoxLayout(
        orientation='vertical',
        spacing=dp(12),
        padding=[dp(10), dp(10), dp(10), dp(20)],
        size_hint=(1, None),
    )
    self.content.bind(minimum_height=self.content.setter('height'))

    self.result_header = Label(
        text='[b]Quiz Completed![/b]',
        font_size='19sp',
        bold=True,
        markup=True,
        halign='center',
        valign='middle',
        size_hint_y=None,
    )
    self.result_header.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(8)), None)
        ),
        texture_size=lambda inst, val: setattr(
            inst, 'height', max(dp(32), val[1] + dp(4))
        ),
    )
    self.content.add_widget(self.result_header)

    self.summary_card = BoxLayout(
        orientation='vertical',
        size_hint_y=None,
        padding=[dp(12), dp(10)],
        spacing=dp(4),
    )
    self.summary_card.bind(minimum_height=self.summary_card.setter('height'))
    with self.summary_card.canvas.before:
      Color(0.15, 0.20, 0.32, 1)
      self.card_rect = RoundedRectangle(
          pos=self.summary_card.pos,
          size=self.summary_card.size,
          radius=[dp(8)],
      )
    self.summary_card.bind(
        pos=self._update_card_rect, size=self._update_card_rect
    )

    self.lbl_acc = Label(
        font_size='15sp',
        bold=True,
        markup=True,
        halign='center',
        size_hint_y=None,
    )
    self.lbl_total = Label(
        font_size='14sp',
        bold=True,
        color=(0.85, 0.9, 0.95, 1),
        markup=True,
        halign='center',
        size_hint_y=None,
    )
    self.lbl_correct = Label(
        font_size='15sp',
        bold=True,
        color=(0.2, 0.85, 0.4, 1),
        markup=True,
        halign='center',
        size_hint_y=None,
    )
    self.lbl_missed = Label(
        font_size='15sp',
        bold=True,
        color=(0.9, 0.3, 0.3, 1),
        markup=True,
        halign='center',
        size_hint_y=None,
    )

    for lbl in (self.lbl_correct, self.lbl_missed, self.lbl_total, self.lbl_acc):
      lbl.bind(
          width=lambda inst, val: setattr(
              inst, 'text_size', (max(dp(20), val - dp(8)), None)
          ),
          texture_size=lambda inst, val: setattr(
              inst, 'height', max(dp(22), val[1] + dp(2))
          ),
      )
      self.summary_card.add_widget(lbl)

    self.content.add_widget(self.summary_card)

    self.retry_btn = Button(
        text='Try Again',
        size_hint_y=None,
        height=dp(48),
        background_color=(0.18, 0.80, 0.44, 1),
        background_normal='',
        bold=True,
        font_size='15sp',
        halign='center',
        valign='middle',
    )
    self.retry_btn.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(8)), None)
        )
    )

    self.back_btn = Button(
        text='Finish & Return',
        size_hint_y=None,
        height=dp(48),
        background_color=(0.2, 0.5, 0.8, 1),
        background_normal='',
        bold=True,
        font_size='15sp',
        halign='center',
        valign='middle',
    )
    self.back_btn.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(20), val - dp(8)), None)
        )
    )

    self.content.add_widget(self.retry_btn)
    self.content.add_widget(self.back_btn)

    self.scroll.add_widget(self.content)
    self.add_widget(self.scroll)

  def _update_card_rect(self, instance, value):
    self.card_rect.pos = instance.pos
    self.card_rect.size = instance.size


class ISabiMCQScreen(Screen):

  def __init__(self, **kwargs):
    kwargs.setdefault('name', 'isabi_mcq')
    super().__init__(**kwargs)

    self.current_question_index = 0
    self.questions_list = []
    self.correct_count = 0
    self.missed_count = 0
    self.is_answering_locked = False
    self.raw_subject_title = ''

    self.main_container = FloatLayout()

    # 1. TOP NAVBAR
    self.navbar = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(52),
        padding=[dp(4), dp(4)],
        spacing=dp(4),
        pos_hint={'top': 1},
    )

    with self.navbar.canvas.before:
      Color(0.08, 0.12, 0.22, 1)
      self.nav_bg = RoundedRectangle(
          pos=self.navbar.pos, size=self.navbar.size
      )
    self.navbar.bind(pos=self._update_nav_bg, size=self._update_nav_bg)

    self.nav_back_btn = Button(
        text='Back',
        font_size='13sp',
        bold=True,
        size_hint=(None, None),
        size=(dp(65), dp(38)),
        pos_hint={'center_y': 0.5},
        background_normal='',
        background_color=(0.7, 0.2, 0.2, 1),
        color=(1, 1, 1, 1),
        halign='center',
        valign='middle',
    )
    self.nav_back_btn.bind(
        width=lambda inst, val: setattr(
            inst, 'text_size', (max(dp(10), val - dp(2)), None)
        )
    )
    self.nav_back_btn.bind(on_release=self.go_back)
    self.navbar.add_widget(self.nav_back_btn)

    self.brand_title = Label(
        text=(
            '[color=ffffff]i-[/color][color=26a65b]S[/color][color=e67e22]a[/color][color=f1c40f]b[/color][color=38b6ff]i[/color]'
            ' [color=ffffff]Challenges[/color]'
        ),
        markup=True,
        font_size='16sp',
        bold=True,
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

    self.nav_spacer = Label(size_hint=(None, None), size=(dp(65), dp(38)))
    self.navbar.add_widget(self.nav_spacer)

    self.main_container.add_widget(self.navbar)

    # 2. SUB-VIEW MANAGER
    self.view_manager = ScreenManager(transition=FadeTransition(duration=0.15))
    self.view_manager.size_hint = (1, None)
    self.view_manager.pos_hint = {'x': 0, 'y': 0}

    self.q_view = QuestionView()
    self.r_view = ResultsView()

    self.r_view.retry_btn.bind(
        on_release=lambda x: self.load_mcq_data(
            self.raw_subject_title, self.questions_list
        )
    )
    self.r_view.back_btn.bind(on_release=self.go_back)

    self.view_manager.add_widget(self.q_view)
    self.view_manager.add_widget(self.r_view)

    self.main_container.add_widget(self.view_manager)
    self.add_widget(self.main_container)

    # Dynamic Window Resize Binding
    Window.bind(on_resize=self._apply_responsive_structure)
    self._apply_responsive_structure()

  def _update_nav_bg(self, instance, value):
    self.nav_bg.pos = instance.pos
    self.nav_bg.size = instance.size

  def _update_scroll_bounds(self, *args):
    fixed_header_height = self.navbar.height
    top_offset = fixed_header_height + dp(4)
    self.view_manager.y = 0
    self.view_manager.height = max(dp(80), Window.height - top_offset)

  def _apply_responsive_structure(self, *args):
    scale = get_responsive_scale()
    self._update_scroll_bounds()

    if Window.width < dp(340):
      btn_w = dp(50 * scale)
      self.brand_title.font_size = f'{int(15 * scale)}sp'
      self.nav_back_btn.font_size = f'{int(12 * scale)}sp'
      self.nav_back_btn.text = 'Back'
    else:
      btn_w = dp(72 * scale)
      self.brand_title.font_size = f'{int(17 * scale)}sp'
      self.nav_back_btn.font_size = f'{int(13 * scale)}sp'
      self.nav_back_btn.text = 'Back'

    nav_h = dp(54 * scale)
    self.navbar.height = nav_h
    btn_h = dp(38 * scale)
    self.nav_back_btn.size = (btn_w, btn_h)
    self.nav_spacer.size = (btn_w, btn_h)

    # Layout padding adjustments
    if Window.width >= dp(768):
      side_padding = max(dp(30), (Window.width - dp(850)) / 2)
      self.q_view.content.padding = [
          side_padding,
          dp(16),
          side_padding,
          dp(24),
      ]
      self.q_view.content.spacing = dp(14)
      self.r_view.content.padding = [
          side_padding,
          dp(16),
          side_padding,
          dp(24),
      ]
      self.r_view.content.spacing = dp(14)
    else:
      side_pad = max(dp(8), Window.width * 0.03)
      self.q_view.content.padding = [side_pad, dp(10), side_pad, dp(18)]
      self.q_view.content.spacing = dp(12)
      self.r_view.content.padding = [side_pad, dp(10), side_pad, dp(18)]
      self.r_view.content.spacing = dp(12)

    # Text size adjustments
    self.q_view.progress_lbl.font_size = f'{int(14 * scale)}sp'
    self.q_view.question_lbl.font_size = f'{int(17 * scale)}sp'

    for child in self.q_view.options_grid.children:
      if isinstance(child, MCQOptionButton):
        child.apply_scale(scale)

    self.r_view.result_header.font_size = f'{int(19 * scale)}sp'
    self.r_view.lbl_acc.font_size = f'{int(15 * scale)}sp'
    self.r_view.lbl_total.font_size = f'{int(14 * scale)}sp'
    self.r_view.lbl_correct.font_size = f'{int(15 * scale)}sp'
    self.r_view.lbl_missed.font_size = f'{int(15 * scale)}sp'
    self.r_view.retry_btn.font_size = f'{int(15 * scale)}sp'
    self.r_view.retry_btn.height = dp(48 * scale)
    self.r_view.back_btn.font_size = f'{int(15 * scale)}sp'
    self.r_view.back_btn.height = dp(48 * scale)

  def load_mcq_data(self, subject_title, questions, **kwargs):
    self.raw_subject_title = subject_title
    self.questions_list = questions or []
    self.current_question_index = 0
    self.correct_count = 0
    self.missed_count = 0
    self.is_answering_locked = False

    self.view_manager.current = 'question_view'
    self.render_current_question()

  def render_current_question(self):
    self.q_view.options_grid.clear_widgets()
    self.q_view.image_container.clear_widgets()
    self.q_view.image_container.height = dp(0)
    self.is_answering_locked = False

    scale = get_responsive_scale()

    if not self.questions_list:
      self.q_view.question_lbl.text = 'No questions available for this subject.'
      self.q_view.progress_lbl.text = ''
      return

    total_q = len(self.questions_list)
    q_data = self.questions_list[self.current_question_index]

    self.q_view.progress_lbl.text = (
        f'Question {self.current_question_index + 1} of {total_q}'
    )
    self.q_view.question_lbl.text = q_data.get('question', '')

    # Render image questions uploaded seamlessly
    top_img = (
        q_data.get('image_url')
        or q_data.get('image_path')
        or q_data.get('image')
    )
    if top_img:
      img_h = dp(190 * scale)
      if str(top_img).startswith('http://') or str(top_img).startswith(
          'https://'
      ):
        q_image_widget = AsyncImage(
            source=top_img,
            size_hint_y=None,
            height=img_h,
            fit_mode='contain',
        )
      elif os.path.exists(top_img):
        q_image_widget = Image(
            source=top_img,
            size_hint_y=None,
            height=img_h,
            fit_mode='contain',
        )
      else:
        q_image_widget = None

      if q_image_widget:
        self.q_view.image_container.height = img_h
        self.q_view.image_container.add_widget(q_image_widget)

    for opt in q_data.get('options', []):
      opt_str = opt.get('value', '') if isinstance(opt, dict) else str(opt)
      btn = MCQOptionButton(option_text=opt_str)
      btn.apply_scale(scale)
      btn.bind(on_release=self.on_option_selected)
      self.q_view.options_grid.add_widget(btn)

    self._apply_responsive_structure()

  def on_option_selected(self, instance):
    if self.is_answering_locked:
      return

    self.is_answering_locked = True
    q_data = self.questions_list[self.current_question_index]

    raw_answer = q_data.get('correct_answer') or q_data.get('answer', '')
    correct_answer = str(raw_answer).strip()
    selected_answer = str(instance.option_text).strip()

    is_correct = selected_answer == correct_answer

    if is_correct:
      self.correct_count += 1
      instance.set_feedback(is_correct=True)
    else:
      self.missed_count += 1
      instance.set_feedback(is_correct=False)

    Clock.schedule_once(self.advance_question, 0.8)

  def advance_question(self, dt):
    if self.current_question_index < len(self.questions_list) - 1:
      self.current_question_index += 1
      self.render_current_question()
    else:
      self.show_results()

  def show_results(self):
    total_questions = len(self.questions_list)
    score_percentage = (
        (self.correct_count / total_questions * 100)
        if total_questions > 0
        else 0
    )

    if score_percentage >= 70:
      header_text = 'OUTSTANDING JOB!'
      header_color = (0.2, 0.85, 0.4, 1)
    elif score_percentage >= 40:
      header_text = 'GOOD EFFORT!'
      header_color = (0.95, 0.77, 0.06, 1)
    else:
      header_text = 'KEEP TRYING!'
      header_color = (0.9, 0.4, 0.2, 1)

    self.r_view.result_header.text = header_text
    self.r_view.result_header.color = header_color

    self.r_view.lbl_acc.text = f'Accuracy Score: {int(score_percentage)}%'
    self.r_view.lbl_acc.color = header_color
    self.r_view.lbl_total.text = f'Total Questions: {total_questions}'
    self.r_view.lbl_correct.text = (
        f'Questions Correct: {self.correct_count}'
    )
    self.r_view.lbl_missed.text = f'Questions Missed: {self.missed_count}'

    self.view_manager.current = 'results_view'
    self._apply_responsive_structure()

  def go_back(self, instance=None):
    if self.manager and self.manager.has_screen('isabi_subject'):
      self.manager.current = 'isabi_subject'