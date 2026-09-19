from collections import deque
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import time
import math
import struct
import random
import os
import sys
import shutil


# --- Автоматическая привязка иконки к файлам .red ---
def auto_register_file_type():
    if sys.platform != "win32":
        return
    try:
        import winreg
        import ctypes

        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
        src_icon = os.path.join(bundle_dir, "icon.ico")

        if not os.path.exists(src_icon):
            return

        app_dir = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "RedSimulation")
        os.makedirs(app_dir, exist_ok=True)
        perm_icon = os.path.join(app_dir, "icon.ico")
        
        if not os.path.exists(perm_icon):
            shutil.copyfile(src_icon, perm_icon)

        exe_path = sys.executable

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.red") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "RedstoneCircuitFile")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\RedstoneCircuitFile\DefaultIcon") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, perm_icon)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\RedstoneCircuitFile\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')

        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass

auto_register_file_type()
# --- Инициализация звуков и музыки (Встроенный синтезатор) ---
try:
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    SOUNDS_ENABLED = True

    def make_sfx(freq, duration=0.1, vol=0.1, wave_type='square'):
        sr = 22050
        n_samples = int(sr * duration)
        buf = bytearray()
        for i in range(n_samples):
            t = float(i) / sr
            if wave_type == 'square': val = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
            elif wave_type == 'sine': val = math.sin(2 * math.pi * freq * t)
            else: val = 2.0 * abs(2.0 * (t * freq - math.floor(t * freq + 0.5))) - 1.0
            
            env = max(0, 1.0 - (i / n_samples))
            sample = int(max(-1.0, min(1.0, val * env * vol)) * 32767)
            buf.extend(struct.pack('<hh', sample, sample))
        return pygame.mixer.Sound(buffer=bytes(buf))

    def make_bgm(is_menu):
        sr = 22050
        seq = [261.63, 329.63, 392.00, 523.25] if is_menu else [130.81, 164.81, 196.00, 261.63]
        speed = 6.0 if is_menu else 1.5
        cycles = 16 if is_menu else 8
            
        dur = (len(seq) / speed) * cycles
        n_samples = int(sr * dur)
        buf = bytearray()
        for i in range(n_samples):
            t = float(i) / sr
            idx = int(t * speed) % len(seq)
            f = seq[idx]
            nt = t * speed - math.floor(t * speed)
            env = math.exp(-1.5 * nt) if is_menu else math.exp(-0.8 * nt)
            
            v1 = math.sin(2 * math.pi * f * t)
            v2 = math.sin(2 * math.pi * (f * 0.5) * t)
            
            val = (v1 * 0.6 + v2 * 0.4) * env * (0.1 if is_menu else 0.05)
            
            if i < sr * 0.5: val *= (i / (sr * 0.5))
            elif i > n_samples - sr * 0.5: val *= ((n_samples - i) / (sr * 0.5))

            sample = int(max(-1.0, min(1.0, val)) * 32767)
            buf.extend(struct.pack('<hh', sample, sample))
        return pygame.mixer.Sound(buffer=bytes(buf))

    snd_hover = make_sfx(880, 0.03, 0.015, 'triangle')
    snd_click = make_sfx(440, 0.06, 0.04, 'square')
    snd_select_arr = [make_sfx(440 * (2**(i/12.0)), 0.1, 0.03, 'sine') for i in range(16)]

    bgm_menu_track = make_bgm(True)
    bgm_game_track = make_bgm(False)
    bgm_channel = pygame.mixer.Channel(0)

except Exception:
    SOUNDS_ENABLED = False

BASE_CELL_SIZE = 56
TOP_PANEL_HEIGHT = 45
BOTTOM_PANEL_HEIGHT = 125
LOGIC_TICK_MS = 100
UI_TICK_MS = 16
SIGNAL_POWER = 12

DIR_OFFSETS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
DIR_NAMES = ["Вправо", "Вниз", "Влево", "Вверх"]

TABS_IDS = {
    "mechanisms": ["wire", "delayer", "switch", "button", "inverter", "generator", "comparator", "screen", "light"],
    "blocks": ["wood", "bridge", "stone", "piston", "sticky_piston", "tnt", "c4"]
}

LANG = {
    "ru": {
        "play": "ВЫБРАТЬ СИМУЛЯЦИЮ", "settings": "НАСТРОЙКИ", "exit": "ВЫХОД",
        "new": "НАЧАТЬ НОВУЮ", "load": "ЗАГРУЗИТЬ", "back": "НАЗАД В МЕНЮ", "resume": "ПРОДОЛЖИТЬ ИГРУ",
        "pause_title": "СИМУЛЯЦИЯ НА ПАУЗЕ", "exit_to_menu": "ВЫЙТИ В ГЛАВНОЕ МЕНЮ",
        "bg": "ЦВЕТ ФОНА", "dark": "ТЁМНЫЙ", "light": "СВЕТЛЫЙ", 
        "size": "РАЗМЕР ИНТЕРФЕЙСА:", "lang": "ЯЗЫК", "lang_name": "РУССКИЙ",
        "sfx_vol": "ГРОМКОСТЬ ЗВУКОВ.", "bgm_vol": "ГРОМКОСТЬ МУЗЫКИ.",
        "mech": "⚙ МЕХАНИЗМЫ", "blocks": "🧱 БЛОКИ", "save": "💾 СОХРАНИТЬ", "load_btn": "📂 ЗАГРУЗИТЬ", "clear": "ОЧИСТИТЬ",
        "select": "ВЫДЕЛЕНИЕ", "eraser": "ЛАСТИК",
        "tools": {"wire": "ПРОВОД", "delayer": "ЗАДЕРЖКА", "switch": "ТУМБЛЕР", "button": "КНОПКА", "inverter": "ИНВЕРТОР", "generator": "ГЕНЕРАТОР", "comparator": "КОМПАР.", "screen": "ЭКРАН", "light": "ЛАМПА", "wood": "ДЕРЕВО", "bridge": "МОСТ", "stone": "КАМЕНЬ", "piston": "ПОРШЕНЬ", "sticky_piston": "ЛИПКИЙ", "tnt": "ТНТ", "c4": "C4"}
    },
    "en": {
        "play": "SELECT SIMULATION", "settings": "SETTINGS", "exit": "EXIT",
        "new": "NEW SIMULATION", "load": "LOAD SIMULATION", "back": "BACK TO MENU", "resume": "RESUME GAME",
        "pause_title": "SIMULATION PAUSED", "exit_to_menu": "RETURN TO MAIN MENU",
        "bg": "BACKGROUND", "dark": "DARK", "light": "LIGHT", 
        "size": "UI SIZE:", "lang": "LANGUAGE", "lang_name": "ENGLISH",
        "sfx_vol": "SFX VOLUME.", "bgm_vol": "MUSIC VOLUME.",
        "mech": "⚙ MECHANISMS", "blocks": "🧱 BLOCKS", "save": "💾 SAVE", "load_btn": "📂 LOAD", "clear": "CLEAR ALL",
        "select": "SELECT", "eraser": "ERASER",
        "tools": {"wire": "WIRE", "delayer": "DELAYER", "switch": "SWITCH", "button": "BUTTON", "inverter": "INVERTER", "generator": "GENERATOR", "comparator": "COMPAR.", "screen": "SCREEN", "light": "LIGHT", "wood": "WOOD", "bridge": "BRIDGE", "stone": "STONE", "piston": "PISTON", "sticky_piston": "STICKY", "tnt": "TNT", "c4": "C4"}
    },
    "zh": {
        "play": "选择模拟", "settings": "设置", "exit": "退出",
        "new": "新模拟", "load": "加载模拟", "back": "返回菜单", "resume": "继续游戏",
        "pause_title": "模拟暂停", "exit_to_menu": "返回主菜单",
        "bg": "背景颜色", "dark": "深色", "light": "浅色", 
        "size": "界面大小:", "lang": "语言", "lang_name": "中文",
        "sfx_vol": "音效音量.", "bgm_vol": "音乐音量.",
        "mech": "⚙ 机械", "blocks": "🧱 方块", "save": "💾 保存", "load_btn": "📂 加载", "clear": "清空",
        "select": "选择", "eraser": "橡皮擦",
        "tools": {"wire": "电线", "delayer": "延迟器", "switch": "开关", "button": "按钮", "inverter": "反相器", "generator": "发电机", "comparator": "比较器", "screen": "屏幕", "light": "灯", "wood": "木头", "bridge": "桥", "stone": "石头", "piston": "活塞", "sticky_piston": "粘性", "tnt": "TNT", "c4": "C4"}
    }
}
LANG_ORDER = ["ru", "en", "zh"]

class LogicSim:
  def __init__(self, root):
    self.root = root
    self.root.title("RED: REDTEDACVHSVAEEHFID")
    self.root.resizable(True, True)

    try: self.root.state('zoomed')
    except: self.root.attributes('-zoomed', True)

    self.win_width = self.root.winfo_screenwidth()
    self.win_height = self.root.winfo_screenheight()

    self.canvas = tk.Canvas(root, width=self.win_width, height=self.win_height, bg="#000000", highlightthickness=0)
    self.canvas.pack(fill=tk.BOTH, expand=True)

    self.app_state = "menu"
    self.prev_state = None
    self.has_active_game = False
    self.is_dark_mode = True
    self.ui_scale_val = 100
    self.ui_scale_str = "100"
    self.lang_idx = 0

    self.vol_sfx = 50
    self.vol_bgm = 30
    self.active_slider = None
    self.is_focused = True

    self.hovered_btn = None
    self.current_hover = None

    self.btn_scales = {}
    self.hitboxes = {}
    self.trans = {"active": False, "phase": 0, "prog": 0.0, "next": None, "action": None}
    self.lang_slide = {"active": False, "prog": 0.0, "dir": 1, "old_txt": "", "new_txt": ""}

    self.world = {}
    self.explosions = []
    self.is_fullscreen = False
    self.current_bgm_state = None

    self.zoom = 1.0
    self.cell_size = BASE_CELL_SIZE
    self.cam_x, self.cam_y = 80, 80
    self.drag_start_x, self.drag_start_y = 0, 0
    self.is_panning = False
    self.mouse_x, self.mouse_y = self.win_width // 2, self.win_height // 2

    self.selection_rect = None
    self.selection_origin = None
    self.clipboard = None
    self.is_selecting = False

    self.overlay_x = self.win_width - 260
    self.overlay_y = TOP_PANEL_HEIGHT + 15
    self.is_dragging_overlay = False
    self.is_interacting_overlay = False
    self.drag_overlay_offset_x, self.drag_overlay_offset_y = 0, 0

    self.active_tab = "mechanisms"
    self.selected_tool = "wire"
    self.selected_cell = None
    self.is_lmb_pressed = False
    self.last_dragged_grid = None
    self.last_dirs = {"delayer": 0, "inverter": 0, "comparator": 0, "piston": 0, "sticky_piston": 0}
    self.typing_target = None

    self.canvas.bind("<Motion>", self.on_mouse_move)
    self.canvas.bind("<Button-1>", self.on_left_down)
    self.canvas.bind("<B1-Motion>", self.on_left_drag)
    self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
    self.canvas.bind("<Button-2>", self.start_pan)
    self.canvas.bind("<B2-Motion>", self.do_pan)
    self.canvas.bind("<MouseWheel>", self.on_zoom)
    self.canvas.bind("<Button-4>", lambda e: self.zoom_step(1.15, e.x, e.y))
    self.canvas.bind("<Button-5>", lambda e: self.zoom_step(0.85, e.x, e.y))
    self.canvas.bind("<Button-3>", self.on_right_click)
    self.canvas.bind("<B3-Motion>", self.on_right_drag)
    self.root.bind("<Key>", self.on_key_press)
    self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
    self.root.bind("<Escape>", self.on_escape)
    self.root.bind("<Control-s>", lambda e: self.save_circuit())
    self.root.bind("<Control-S>", lambda e: self.save_circuit())
    self.root.bind("<Control-o>", lambda e: self.load_circuit())
    self.root.bind("<Control-O>", lambda e: self.load_circuit())
    self.root.bind("<Control-c>", lambda e: self.copy_selection())
    self.root.bind("<Control-C>", lambda e: self.copy_selection())
    self.root.bind("<Control-v>", lambda e: self.paste_selection())
    self.root.bind("<Control-V>", lambda e: self.paste_selection())
    self.root.bind("<Configure>", self.on_window_resize)
    
    self.root.bind("<FocusIn>", lambda e: self.on_focus(True))
    self.root.bind("<FocusOut>", lambda e: self.on_focus(False))

    self.setup_demo()
    self.update_audio_volumes()
    self.ui_tick()
    self.logic_tick()

  def on_focus(self, focused):
    self.is_focused = focused
    self.update_audio_volumes()

  def update_audio_volumes(self):
    if SOUNDS_ENABLED:
        focus_mult = 1.0 if self.is_focused else 0.15
        sfx_v = (self.vol_sfx / 100.0) * focus_mult
        bgm_v = (self.vol_bgm / 100.0) * focus_mult
        snd_hover.set_volume(sfx_v)
        snd_click.set_volume(sfx_v)
        for s in snd_select_arr: s.set_volume(sfx_v)
        bgm_channel.set_volume(bgm_v)

  def play_click_sound(self):
    if SOUNDS_ENABLED: snd_click.play()

  def trigger_transition(self, next_state, action=None):
    if self.trans["active"]: return
    self.trans = {"active": True, "phase": 1, "prog": 0.0, "next": next_state, "action": action}

  def loc(self, key): return LANG[LANG_ORDER[self.lang_idx]][key]

  def ui_tick(self):
    if self.trans["active"]:
      self.trans["prog"] += 0.08
      if self.trans["phase"] == 1:
        if self.trans["prog"] >= 1.0:
          self.app_state = self.trans["next"]
          action = self.trans["action"]
          self.trans["action"] = None
          if action: action()
          self.trans["phase"] = 2
          self.trans["prog"] = 0.0
      elif self.trans["phase"] == 2:
        if self.trans["prog"] >= 1.0:
          self.trans["active"] = False
          self.trans["phase"] = 0
          self.trans["prog"] = 0.0

    if self.lang_slide["active"]:
      self.lang_slide["prog"] += 0.08
      if self.lang_slide["prog"] >= 1.0: self.lang_slide["active"] = False

    if SOUNDS_ENABLED:
        target_state = "game" if self.app_state in ("game", "pause") else "menu"
        if self.current_bgm_state != target_state:
            self.current_bgm_state = target_state
            bgm_channel.play(bgm_game_track if target_state == "game" else bgm_menu_track, loops=-1)

    self.draw()
    self.root.after(UI_TICK_MS, self.ui_tick)

  def logic_tick(self):
    if self.app_state == "game" and not self.trans["active"]: self.tick()
    self.root.after(LOGIC_TICK_MS, self.logic_tick)

  def on_mouse_move(self, event):
    self.mouse_x, self.mouse_y = event.x, event.y

  def on_escape(self, event):
    if self.trans["active"]: return
    if self.typing_target:
      if self.typing_target == "ui_scale":
        val = int(self.ui_scale_str) if self.ui_scale_str and self.ui_scale_str.lstrip('-').isdigit() else 100
        self.ui_scale_val = max(10, min(200, val))
      else: self.apply_typing()
      self.typing_target = None
      return
      
    if self.app_state == "game":
      self.trigger_transition("pause")
    elif self.app_state == "pause":
      self.trigger_transition("game")
    elif self.app_state == "settings":
      self.trigger_transition(self.prev_state if self.prev_state else "menu")
      self.prev_state = None
    elif self.app_state == "select_sim":
      self.trigger_transition("menu")

  def toggle_fullscreen(self):
    self.is_fullscreen = not self.is_fullscreen
    self.root.attributes("-fullscreen", self.is_fullscreen)

  def exit_fullscreen(self):
    if self.is_fullscreen:
      self.is_fullscreen = False
      self.root.attributes("-fullscreen", False)

  def on_window_resize(self, event):
    if event.widget == self.root and event.width > 200:
      if event.width != self.win_width or event.height != self.win_height:
        self.win_width, self.win_height = event.width, event.height
        self.canvas.config(width=self.win_width, height=self.win_height)

  def screen_to_grid(self, sx, sy):
    return int((sx - self.cam_x) // max(1, self.cell_size)), int((sy - self.cam_y) // max(1, self.cell_size))

  def on_zoom(self, event):
    if self.app_state != "game": return
    factor = 1.15 if event.delta > 0 else 0.85
    self.zoom_step(factor, event.x, event.y)

  def zoom_step(self, factor, mx, my):
    top_h = int(TOP_PANEL_HEIGHT * (self.ui_scale_val / 100.0))
    bot_h = int(BOTTOM_PANEL_HEIGHT * (self.ui_scale_val / 100.0))
    if my < top_h or my > self.win_height - bot_h: return
    
    old_s = max(1, self.cell_size)
    new_s = max(20, int(BASE_CELL_SIZE * max(0.35, min(2.5, self.zoom * factor))))
    self.cam_x = mx - (mx - self.cam_x) * (new_s / old_s)
    self.cam_y = my - (my - self.cam_y) * (new_s / old_s)
    self.zoom = new_s / BASE_CELL_SIZE; self.cell_size = new_s

  def start_pan(self, event):
    if self.app_state == "game":
      self.is_panning = True; self.drag_start_x, self.drag_start_y = event.x, event.y

  def do_pan(self, event):
    if self.is_panning and self.app_state == "game":
      self.cam_x += event.x - self.drag_start_x; self.cam_y += event.y - self.drag_start_y
      self.drag_start_x, self.drag_start_y = event.x, event.y

  def setup_demo(self):
    self.world.clear()
    self.world[(5, 5)] = {"type": "switch", "active": True}
    self.world[(6, 5)] = {"type": "wire", "signal": 0}
    self.world[(7, 5)] = {"type": "sticky_piston", "direction": 0, "extended": False}
    self.world[(8, 5)] = {"type": "wood", "signal": 0, "powered_sides": 0}
    self.world[(9, 5)] = {"type": "light", "color": "green", "delay": 0, "counter": 0, "lit": False}
    self.selected_cell = None

  def copy_selection(self):
    if not self.selection_rect or self.app_state != "game": return
    x1, y1, x2, y2 = self.selection_rect
    min_x, max_x, min_y, max_y = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
    self.clipboard = {}
    for (gx, gy), comp in self.world.items():
      if min_x <= gx <= max_x and min_y <= gy <= max_y:
        self.clipboard[(gx - min_x, gy - min_y)] = json.loads(json.dumps(comp))

  def paste_selection(self):
    if not self.clipboard or self.app_state != "game": return
    target_gx, target_gy = self.screen_to_grid(self.mouse_x, self.mouse_y)
    for (rel_x, rel_y), comp in self.clipboard.items():
      self.world[(target_gx + rel_x, target_gy + rel_y)] = json.loads(json.dumps(comp))

  def save_circuit(self):
    filepath = filedialog.asksaveasfilename(title="Сохранить схему Redstone", defaultextension=".red", filetypes=[("Redstone Circuit File", "*.red"), ("All Files", "*.*")])
    if not filepath: return
    try:
      with open(filepath, "w", encoding="utf-8") as f:
        json.dump({f"{k[0]},{k[1]}": v for k, v in self.world.items()}, f, ensure_ascii=False, indent=2)
    except: pass

  def load_circuit(self):
    filepath = filedialog.askopenfilename(title="Загрузить схему Redstone", filetypes=[("Redstone Circuit File", "*.red"), ("All Files", "*.*")])
    if filepath:
      def do_load():
        try:
          with open(filepath, "r", encoding="utf-8") as f: data = json.load(f)
          self.world = {tuple(map(int, k.split(","))): v for k, v in data.items()}
          self.selected_cell, self.selection_rect = None, None
          self.has_active_game = True
        except: pass
      self.trigger_transition("game", do_load)

  def check_ui_click(self):
    for btn_id, rect in self.hitboxes.items():
      if rect[0] <= self.mouse_x <= rect[2] and rect[1] <= self.mouse_y <= rect[3]:
        return btn_id
    return None

  def handle_btn_click(self, btn_id):
    if btn_id == "btn_play": self.trigger_transition("select_sim")
    elif btn_id == "btn_resume": self.trigger_transition("game")
    elif btn_id == "btn_settings": 
      self.prev_state = self.app_state
      self.trigger_transition("settings")
    elif btn_id == "btn_exit": self.root.quit()
    elif btn_id == "btn_exit_to_menu":
      self.has_active_game = True
      self.trigger_transition("menu")
    elif btn_id == "btn_new":
      def start_new():
        self.cam_x, self.cam_y = 80, 80
        self.setup_demo()
        self.has_active_game = True
      self.trigger_transition("game", start_new)
    elif btn_id == "btn_load": self.load_circuit()
    elif btn_id == "btn_back":
      self.trigger_transition(self.prev_state if self.prev_state else "menu")
      self.prev_state = None
    elif btn_id == "set_theme": self.is_dark_mode = not self.is_dark_mode
    elif btn_id == "set_size_input":
      self.typing_target = "ui_scale"
      self.ui_scale_str = str(self.ui_scale_val)
    elif btn_id == "set_lang_left":
      self.lang_slide = {"active": True, "prog": 0.0, "dir": 1, "old_txt": self.loc("lang_name"), "new_txt": ""}
      self.lang_idx = (self.lang_idx - 1) % 3
      self.lang_slide["new_txt"] = self.loc("lang_name")
    elif btn_id == "set_lang_right":
      self.lang_slide = {"active": True, "prog": 0.0, "dir": -1, "old_txt": self.loc("lang_name"), "new_txt": ""}
      self.lang_idx = (self.lang_idx + 1) % 3
      self.lang_slide["new_txt"] = self.loc("lang_name")

  def update_slider(self, x, btn_id):
    rect = self.hitboxes.get(btn_id)
    if not rect: return
    track_x1, track_x2 = rect[0], rect[2]
    w = track_x2 - track_x1
    if w <= 0: return
    p = max(0.0, min(1.0, (x - track_x1) / w))
    if "vol_sfx" in btn_id: self.vol_sfx = int(p * 100)
    elif "vol_bgm" in btn_id: self.vol_bgm = int(p * 100)
    self.update_audio_volumes()

  def on_left_down(self, event):
    if self.trans["active"]: return
    self.is_lmb_pressed = True
    x, y = event.x, event.y

    if self.typing_target == "ui_scale" and self.check_ui_click() != "set_size_input":
        val = int(self.ui_scale_str) if self.ui_scale_str and self.ui_scale_str.lstrip('-').isdigit() else 100
        self.ui_scale_val = max(10, min(200, val))
        self.typing_target = None

    clicked_btn = self.check_ui_click()
    if clicked_btn:
      if "vol_sfx" in clicked_btn or "vol_bgm" in clicked_btn:
          self.active_slider = clicked_btn
          self.update_slider(x, clicked_btn)
      else:
          self.play_click_sound()
          self.handle_btn_click(clicked_btn)
      return

    if self.app_state == "game":
      scale = self.ui_scale_val / 100.0
      top_h = int(TOP_PANEL_HEIGHT * scale)
      bot_h = int(BOTTOM_PANEL_HEIGHT * scale)
      
      if y <= top_h:
        self.play_click_sound()
        self.handle_top_click(x, y); return
      if y >= self.win_height - bot_h:
        self.handle_bottom_click(x, y); return

      if self.selected_cell:
        c = self.world.get(self.selected_cell)
        if c and c.get("type") in ("delayer", "comparator", "generator", "c4", "light", "screen", "inverter", "piston", "sticky_piston"):
          ox, oy = self.overlay_x, self.overlay_y
          if ox <= x <= ox + 240 and oy <= y <= oy + 250:
            self.is_interacting_overlay = True
            if oy <= y <= oy + 35:
              self.is_dragging_overlay = True
              self.drag_overlay_offset_x = x - ox
              self.drag_overlay_offset_y = y - oy
            else: self.handle_overlay_click(x, y)
            return

      if isinstance(self.typing_target, dict): self.apply_typing()

      gx, gy = self.screen_to_grid(x, y)
      if self.selected_tool == "select":
        self.is_selecting = True
        self.selection_origin = (gx, gy)
        self.selection_rect = (gx, gy, gx, gy)
        return
      else: self.selection_rect = None

      self.apply_tool(gx, gy)
      self.last_dragged_grid = (gx, gy)

  def on_left_drag(self, event):
    if not self.is_lmb_pressed: return

    if self.active_slider:
        self.update_slider(event.x, self.active_slider)
        return

    if self.is_interacting_overlay:
      if self.is_dragging_overlay:
        scale = self.ui_scale_val / 100.0
        self.overlay_x = max(10, min(self.win_width - 250, event.x - self.drag_overlay_offset_x))
        self.overlay_y = max(int(TOP_PANEL_HEIGHT * scale) + 5, min(self.win_height - int(BOTTOM_PANEL_HEIGHT * scale) - 250, event.y - self.drag_overlay_offset_y))
      return

    if self.app_state != "game": return
    scale = self.ui_scale_val / 100.0
    if event.y <= int(TOP_PANEL_HEIGHT * scale) or event.y >= self.win_height - int(BOTTOM_PANEL_HEIGHT * scale): return

    gx, gy = self.screen_to_grid(event.x, event.y)
    if self.is_selecting:
      self.selection_rect = (self.selection_origin[0], self.selection_origin[1], gx, gy)
      return

    if (gx, gy) != self.last_dragged_grid:
      shift_pressed = bool(event.state & 0x0001)
      if self.selected_tool in ("wire", "eraser") or shift_pressed:
        self.apply_tool(gx, gy)
        self.last_dragged_grid = (gx, gy)

  def on_left_up(self, event):
    self.is_lmb_pressed = False
    self.active_slider = None
    self.is_dragging_overlay, self.is_interacting_overlay = False, False
    self.last_dragged_grid = None
    if self.is_selecting: self.is_selecting = False

  def on_right_click(self, event):
    if self.app_state == "game":
      scale = self.ui_scale_val / 100.0
      if int(TOP_PANEL_HEIGHT * scale) < event.y < self.win_height - int(BOTTOM_PANEL_HEIGHT * scale):
        self.erase_cell(*self.screen_to_grid(event.x, event.y))

  def on_right_drag(self, event): self.on_right_click(event)

  def erase_cell(self, gx, gy):
    if (gx, gy) in self.world: del self.world[(gx, gy)]
    if self.selected_cell == (gx, gy):
      self.selected_cell = None
      if isinstance(self.typing_target, dict): self.apply_typing()

  def apply_tool(self, gx, gy):
    if self.selected_tool is None:
      cell = self.world.get((gx, gy))
      if cell:
        if cell.get("type") == "switch": cell["active"] = not cell.get("active", False)
        elif cell.get("type") == "button": cell["active"] = True; cell["timer"] = 6
        self.selected_cell = (gx, gy)
      else: self.selected_cell = None
      if isinstance(self.typing_target, dict): self.apply_typing()
      return

    if self.selected_tool == "eraser":
      self.erase_cell(gx, gy); return

    cell = self.world.get((gx, gy))
    if cell:
      if cell.get("type") == "switch": cell["active"] = not cell.get("active", False); self.selected_cell = (gx, gy); return
      if cell.get("type") == "button": cell["active"] = True; cell["timer"] = 6; self.selected_cell = (gx, gy); return
      if cell.get("type") == "wire" and self.selected_tool != "wire": self.place_component(gx, gy, self.selected_tool)
      self.selected_cell = (gx, gy)
    else:
      self.place_component(gx, gy, self.selected_tool)
      self.selected_cell = (gx, gy)
    if isinstance(self.typing_target, dict): self.apply_typing()

  def place_component(self, gx, gy, c_type):
    d = self.last_dirs.get(c_type, 0)
    if c_type == "wire": self.world[(gx, gy)] = {"type": "wire", "signal": 0, "boost_red": False}
    elif c_type == "switch": self.world[(gx, gy)] = {"type": "switch", "active": False}
    elif c_type == "button": self.world[(gx, gy)] = {"type": "button", "active": False, "timer": 0}
    elif c_type == "delayer": self.world[(gx, gy)] = {"type": "delayer", "delay": 2, "counter": 0, "out_timer": 0, "is_active": False, "direction": d}
    elif c_type == "inverter": self.world[(gx, gy)] = {"type": "inverter", "direction": d, "is_powered": True}
    elif c_type == "generator": self.world[(gx, gy)] = {"type": "generator", "charge_time": 6, "pulse_time": 2, "counter": 0, "is_active": False, "is_blocked": False}
    elif c_type == "comparator": self.world[(gx, gy)] = {"type": "comparator", "direction": d, "mode": "compare", "output_signal": 0, "next_output": 0, "rear_in": 0, "side_in": 0}
    elif c_type == "screen": self.world[(gx, gy)] = {"type": "screen", "mode": 1, "val": "0", "is_powered": False}
    elif c_type == "light": self.world[(gx, gy)] = {"type": "light", "color": "red", "delay": 0, "counter": 0, "lit": False}
    elif c_type == "wood": self.world[(gx, gy)] = {"type": "wood", "signal": 0, "powered_sides": 0}
    elif c_type == "bridge": self.world[(gx, gy)] = {"type": "bridge", "signal_h": 0, "signal_v": 0}
    elif c_type == "stone": self.world[(gx, gy)] = {"type": "stone"}
    elif c_type == "piston": self.world[(gx, gy)] = {"type": "piston", "direction": d, "extended": False}
    elif c_type == "sticky_piston": self.world[(gx, gy)] = {"type": "sticky_piston", "direction": d, "extended": False}
    elif c_type == "tnt": self.world[(gx, gy)] = {"type": "tnt", "fuse": 4, "primed": False}
    elif c_type == "c4": self.world[(gx, gy)] = {"type": "c4", "timer": 30, "countdown": 30, "primed": False}

  def handle_top_click(self, x, y):
    scale = self.ui_scale_val / 100.0
    if int(218*scale) <= x <= int(342*scale): self.save_circuit()
    elif int(348*scale) <= x <= int(472*scale): self.load_circuit()
    elif int(482*scale) <= x <= int(595*scale):
      if messagebox.askyesno(self.loc("clear"), "Удалить все компоненты?"):
        self.world.clear()
        self.selected_cell, self.selection_rect = None, None

  def handle_bottom_click(self, x, y):
    scale = self.ui_scale_val / 100.0
    field_h = self.win_height - int(BOTTOM_PANEL_HEIGHT * scale)
    btn_w = int(58 * scale)
    btn_gap = int(2 * scale)
    step = btn_w + btn_gap

    if field_h + int(5*scale) <= y <= field_h + int(30*scale):
      if int(10*scale) <= x <= int(150*scale):
        self.active_tab = "mechanisms"
      elif int(155*scale) <= x <= int(280*scale):
        self.active_tab = "blocks"
      return

    clicked_tool = None
    start_x = int(10 * scale)
    for i, t_id in enumerate(TABS_IDS[self.active_tab]):
      bx = start_x + i * step
      if bx <= x <= bx + btn_w and field_h + int(35*scale) <= y <= field_h + int(115*scale):
        clicked_tool = t_id
        if SOUNDS_ENABLED: snd_select_arr[i % 16].play()
        break

    ex = self.win_width - btn_w - int(10 * scale)
    qx = ex - btn_w - btn_gap
    if field_h + int(35*scale) <= y <= field_h + int(115*scale):
      if qx <= x <= qx + btn_w: clicked_tool = "select"
      elif ex <= x <= ex + btn_w: clicked_tool = "eraser"

    self.selected_tool = None if self.selected_tool == clicked_tool else clicked_tool

  def handle_overlay_click(self, x, y):
    if not self.selected_cell: return False
    gx, gy = self.selected_cell
    c = self.world.get((gx, gy))
    if not c: return False

    px = self.overlay_x + 15
    py = self.overlay_y + 10

    if px <= x <= px + 210 and py + 195 <= y <= py + 225:
      self.erase_cell(gx, gy); return True

    def rotate_component():
      c["direction"] = (c.get("direction", 0) + 1) % 4
      self.last_dirs[c["type"]] = c["direction"]
      return True

    if c.get("type") == "delayer":
      if px + 35 <= x <= px + 95 and py + 75 <= y <= py + 105: self.typing_target = {"cell": (gx, gy), "field": "delay", "min": 1, "max": 30}; return True
      elif px <= x <= px + 25 and py + 75 <= y <= py + 105: c["delay"] = max(1, c.get("delay", 2) - 1); c.pop("delay_str", None); return True
      elif px + 105 <= x <= px + 130 and py + 75 <= y <= py + 105: c["delay"] = min(30, c.get("delay", 2) + 1); c.pop("delay_str", None); return True
      elif px <= x <= px + 170 and py + 120 <= y <= py + 150: return rotate_component()
    elif c.get("type") == "comparator":
      if px <= x <= px + 200 and py + 65 <= y <= py + 95: c["mode"] = "subtract" if c.get("mode", "compare") == "compare" else "compare"; return True
      elif px <= x <= px + 170 and py + 110 <= y <= py + 140: return rotate_component()
    elif c.get("type") in ("piston", "sticky_piston") and px <= x <= px + 170 and py + 65 <= y <= py + 95: return rotate_component()
    elif c.get("type") == "inverter" and px <= x <= px + 170 and py + 70 <= y <= py + 100: return rotate_component()
    elif c.get("type") == "generator":
      if px + 35 <= x <= px + 95 and py + 55 <= y <= py + 85: self.typing_target = {"cell": (gx, gy), "field": "charge_time", "min": 1, "max": 60}; return True
      elif px <= x <= px + 25 and py + 55 <= y <= py + 85: c["charge_time"] = max(1, c.get("charge_time", 6) - 1); c.pop("charge_time_str", None); return True
      elif px + 105 <= x <= px + 130 and py + 55 <= y <= py + 85: c["charge_time"] = min(60, c.get("charge_time", 6) + 1); c.pop("charge_time_str", None); return True
      elif px + 35 <= x <= px + 95 and py + 105 <= y <= py + 135: self.typing_target = {"cell": (gx, gy), "field": "pulse_time", "min": 1, "max": 30}; return True
      elif px <= x <= px + 25 and py + 105 <= y <= py + 135: c["pulse_time"] = max(1, c.get("pulse_time", 2) - 1); c.pop("pulse_time_str", None); return True
      elif px + 105 <= x <= px + 130 and py + 105 <= y <= py + 135: c["pulse_time"] = min(30, c.get("pulse_time", 2) + 1); c.pop("pulse_time_str", None); return True
    elif c.get("type") == "c4":
      if px + 35 <= x <= px + 95 and py + 75 <= y <= py + 105: self.typing_target = {"cell": (gx, gy), "field": "timer", "min": 10, "max": 100}; return True
      elif px <= x <= px + 25 and py + 75 <= y <= py + 105:
        c["timer"] = max(10, c.get("timer", 30) - 5); c.pop("timer_str", None)
        if not c.get("primed", False): c["countdown"] = c.get("timer", 30)
        return True
      elif px + 105 <= x <= px + 130 and py + 75 <= y <= py + 105:
        c["timer"] = min(100, c.get("timer", 30) + 5); c.pop("timer_str", None)
        if not c.get("primed", False): c["countdown"] = c.get("timer", 30)
        return True
    elif c.get("type") == "light":
      if py + 65 <= y <= py + 95:
        if px <= x <= px + 45: c["color"] = "red"; return True
        elif px + 50 <= x <= px + 95: c["color"] = "green"; return True
        elif px + 100 <= x <= px + 145: c["color"] = "blue"; return True
      elif px + 35 <= x <= px + 95 and py + 130 <= y <= py + 160: self.typing_target = {"cell": (gx, gy), "field": "delay", "min": 0, "max": 20}; return True
      elif px <= x <= px + 25 and py + 130 <= y <= py + 160: c["delay"] = max(0, c.get("delay", 0) - 1); c.pop("delay_str", None); return True
      elif px + 105 <= x <= px + 130 and py + 130 <= y <= py + 160: c["delay"] = min(20, c.get("delay", 0) + 1); c.pop("delay_str", None); return True
    elif c.get("type") == "screen" and px <= x <= px + 180 and py + 70 <= y <= py + 105: c["mode"] = 1 if c.get("mode", 1) == 2 else 2; return True
    return False

  def apply_typing(self):
    if isinstance(self.typing_target, dict):
      c = self.world.get(self.typing_target["cell"])
      if c:
        f = self.typing_target["field"]
        val_str = c.get(f + "_str", str(c.get(f, 0)))
        c[f] = max(self.typing_target["min"], min(self.typing_target["max"], int(val_str) if val_str and val_str.lstrip('-').isdigit() else 0))
        c.pop(f + "_str", None)
      self.typing_target = None

  def on_key_press(self, event):
    if self.trans["active"]: return

    if event.keysym.lower() in ('r', 'k', 'к', 'л'):
      if self.app_state == "game" and self.selected_cell:
        c = self.world.get(self.selected_cell)
        if c and c.get("type") in ("delayer", "comparator", "inverter", "piston", "sticky_piston"):
          c["direction"] = (c.get("direction", 0) + 1) % 4
          self.last_dirs[c["type"]] = c["direction"]
      return

    if self.typing_target == "ui_scale":
      if event.keysym == "BackSpace": self.ui_scale_str = self.ui_scale_str[:-1]
      elif event.char.isdigit(): 
        if len(self.ui_scale_str) < 3: self.ui_scale_str += event.char
      elif event.keysym in ("Return", "Escape"):
        val = int(self.ui_scale_str) if self.ui_scale_str and self.ui_scale_str.lstrip('-').isdigit() else 100
        self.ui_scale_val = max(10, min(200, val))
        self.typing_target = None
      return

    if isinstance(self.typing_target, dict):
      gx, gy = self.typing_target["cell"]
      c = self.world.get((gx, gy))
      if not c: self.typing_target = None; return
      field = self.typing_target["field"]
      if event.keysym == "BackSpace":
        val_str = c.get(field + "_str", str(c.get(field, 0)))[:-1]
        c[field + "_str"] = val_str
        c[field] = int(val_str) if val_str and val_str.lstrip('-').isdigit() else 0
      elif event.char.isdigit():
        val_str = c.get(field + "_str", str(c.get(field, 0)))
        if val_str == "0": val_str = ""
        val_str += event.char
        if len(val_str) > 3: val_str = val_str[:3]
        c[field + "_str"] = val_str
        c[field] = int(val_str) if val_str and val_str.lstrip('-').isdigit() else 0
      elif event.keysym in ("Return", "Escape"):
        val_str = c.get(field + "_str", str(c.get(field, 0)))
        c[field] = max(self.typing_target["min"], min(self.typing_target["max"], int(val_str) if val_str and val_str.lstrip('-').isdigit() else 0))
        c.pop(field + "_str", None)
        self.typing_target = None
      return

    if event.keysym in ("Delete", "BackSpace") and self.selection_rect:
      if SOUNDS_ENABLED: snd_click.play()
      x1, y1, x2, y2 = self.selection_rect
      to_del = [pos for pos in self.world if min(x1, x2) <= pos[0] <= max(x1, x2) and min(y1, y2) <= pos[1] <= max(y1, y2)]
      for p in to_del:
        del self.world[p]
        if self.selected_cell == p: self.selected_cell = None
      self.selection_rect = None
      return

    if self.app_state == "game":
      if event.keysym == "Tab":
        self.active_tab = "blocks" if self.active_tab == "mechanisms" else "mechanisms"
        if SOUNDS_ENABLED: snd_click.play()
        return
      char_low = event.char.lower()
      if char_low in ("q", "й"):
        self.selected_tool = None if self.selected_tool == "select" else "select"
        if SOUNDS_ENABLED: snd_select_arr[0].play()
        return
      elif char_low in ("e", "у"):
        self.selected_tool = None if self.selected_tool == "eraser" else "eraser"
        if SOUNDS_ENABLED: snd_select_arr[1].play()
        return
      if event.char in "123456789":
        idx = int(event.char) - 1
        tools = TABS_IDS[self.active_tab]
        if idx < len(tools):
          t_id = tools[idx]
          self.selected_tool = None if self.selected_tool == t_id else t_id
          if SOUNDS_ENABLED: snd_select_arr[idx % 16].play()

  def get_cell_power(self, pos, into_direction):
    nb = self.world.get(pos)
    if not nb: return 0
    t = nb.get("type")
    if t in ("wire", "wood"): return nb.get("signal", 0)
    elif t in ("switch", "button"): return SIGNAL_POWER if nb.get("active", False) else 0
    elif t == "delayer" and DIR_OFFSETS[nb.get("direction", 0)] == into_direction: return SIGNAL_POWER if nb.get("is_active", False) else 0
    elif t == "inverter" and DIR_OFFSETS[nb.get("direction", 0)] == into_direction: return SIGNAL_POWER if nb.get("is_powered", False) else 0
    elif t == "generator": return SIGNAL_POWER if nb.get("is_active", False) else 0
    elif t == "comparator" and DIR_OFFSETS[nb.get("direction", 0)] == into_direction: return nb.get("output_signal", 0)
    elif t == "bridge":
      if into_direction[0] != 0: return nb.get("signal_h", 0)
      if into_direction[1] != 0: return nb.get("signal_v", 0)
    return 0

  def tick(self):
    for pos, c in self.world.items():
      if c.get("type") in ("wire", "wood"):
        c["signal"] = 0; c["boost_red"] = False
        if c.get("type") == "wood": c["powered_sides"] = 0
      elif c.get("type") == "bridge": c["signal_h"] = 0; c["signal_v"] = 0

    for pos, c in self.world.items():
      if c.get("type") == "button" and c.get("active", False):
        c["timer"] = c.get("timer", 0) - 1
        if c["timer"] <= 0: c["active"] = False

    queue = deque()
    parents = {}

    def inject_pulse(gx, gy, dx, dy, out_s):
      curr_x, curr_y = gx + dx, gy + dy
      loss = 0
      visited_bridges = set()
      while True:
        target = self.world.get((curr_x, curr_y))
        if not target: break
        if target.get("type") == "bridge":
          if (curr_x, curr_y) in visited_bridges: break
          visited_bridges.add((curr_x, curr_y))
          loss += 1
          if dx != 0: target["signal_h"] = max(target.get("signal_h", 0), max(1, out_s - loss + 1))
          else: target["signal_v"] = max(target.get("signal_v", 0), max(1, out_s - loss + 1))
          curr_x += dx; curr_y += dy
          continue
        if target.get("type") in ("wire", "wood"):
          sig = max(1, out_s - loss)
          if target.get("type") == "wood": sig = max(1, sig // 2)
          if target.get("signal", 0) < sig:
            target["signal"] = sig
            parents[(curr_x, curr_y)] = (curr_x - dx, curr_y - dy)
            queue.append((curr_x, curr_y, sig, 1 + loss))
        break

    for (gx, gy), c in self.world.items():
      if c.get("type") in ("switch", "button") and c.get("active", False):
        for dx, dy in DIR_OFFSETS: inject_pulse(gx, gy, dx, dy, SIGNAL_POWER)
      elif c.get("type") == "delayer" and c.get("is_active", False):
        dx, dy = DIR_OFFSETS[c.get("direction", 0)]; inject_pulse(gx, gy, dx, dy, SIGNAL_POWER)
      elif c.get("type") == "inverter" and c.get("is_powered", False):
        dx, dy = DIR_OFFSETS[c.get("direction", 0)]; inject_pulse(gx, gy, dx, dy, SIGNAL_POWER)
      elif c.get("type") == "comparator" and c.get("output_signal", 0) > 0:
        dx, dy = DIR_OFFSETS[c.get("direction", 0)]; inject_pulse(gx, gy, dx, dy, c.get("output_signal", 0))

    for (gx, gy), c in self.world.items():
      if c.get("type") == "generator":
        has_input = any(self.get_cell_power((gx + dx, gy + dy), (-dx, -dy)) > 0 for dx, dy in DIR_OFFSETS)
        if has_input:
          c["is_blocked"] = True; c["counter"] = 0; c["is_active"] = False
        else:
          c["is_blocked"] = False
          c["counter"] = (c.get("counter", 0) + 1) % max(1, c.get("charge_time", 6) + c.get("pulse_time", 2))
          c["is_active"] = c["counter"] >= c.get("charge_time", 6)
        if c.get("is_active", False):
          for dx, dy in DIR_OFFSETS: inject_pulse(gx, gy, dx, dy, SIGNAL_POWER)

    wire_dist = {}
    while queue:
      cx, cy, strength, dist = queue.popleft()
      wire_dist[(cx, cy)] = dist
      if strength <= 1: continue
      for dx, dy in DIR_OFFSETS:
        nx, ny = cx + dx, cy + dy
        target = self.world.get((nx, ny))
        if not target: continue
        if target.get("type") in ("wire", "wood"):
          n_str = strength - 1
          if target.get("type") == "wood": n_str = max(1, n_str // 2)
          if target.get("signal", 0) < n_str:
            target["signal"] = n_str
            parents[(nx, ny)] = (cx, cy)
            queue.append((nx, ny, n_str, dist + 1))
        elif target.get("type") == "bridge":
          curr_x, curr_y = nx, ny
          bridges = 0
          visited_bridges = set()
          while True:
            b_blk = self.world.get((curr_x, curr_y))
            if b_blk and b_blk.get("type") == "bridge":
              if (curr_x, curr_y) in visited_bridges: break
              visited_bridges.add((curr_x, curr_y))
              bridges += 1
              val = max(1, strength - bridges)
              if dx != 0: b_blk["signal_h"] = max(b_blk.get("signal_h", 0), val)
              else: b_blk["signal_v"] = max(b_blk.get("signal_v", 0), val)
              curr_x += dx; curr_y += dy
            else: break
          exit_blk = self.world.get((curr_x, curr_y))
          if exit_blk and exit_blk.get("type") in ("wire", "wood"):
            val_out = strength - bridges - 1
            if exit_blk.get("type") == "wood": val_out = max(1, val_out // 2)
            if val_out > 0 and exit_blk.get("signal", 0) < val_out:
              exit_blk["signal"] = val_out
              parents[(curr_x, curr_y)] = (curr_x - dx, curr_y - dy)
              queue.append((curr_x, curr_y, val_out, dist + bridges + 1))

    for (gx, gy), c in self.world.items():
      if c.get("type") == "delayer":
        in_dir = (c.get("direction", 0) + 2) % 4
        dx, dy = DIR_OFFSETS[in_dir]
        has_in = self.get_cell_power((gx + dx, gy + dy), (-dx, -dy)) > 0
        if has_in:
          if c.get("counter", 0) < c.get("delay", 2): c["counter"] = c.get("counter", 0) + 1
        elif c.get("counter", 0) > 0 and c.get("counter", 0) < c.get("delay", 2): c["counter"] = c.get("counter", 0) + 1

        if c.get("counter", 0) >= c.get("delay", 2):
          c["next_active"] = True
          c["out_timer"] = max(2, c.get("out_timer", 0))
          if not has_in: c["counter"] = 0
        elif c.get("out_timer", 0) > 0:
          c["out_timer"] = c.get("out_timer", 0) - 1; c["next_active"] = c.get("out_timer", 0) > 0
        else: c["next_active"] = False

    for pos, c in self.world.items():
      if c.get("type") == "delayer": c["is_active"] = c.get("next_active", False)

    for (gx, gy), c in self.world.items():
      if c.get("type") == "comparator":
        d = c.get("direction", 0)
        rear_dir = (d + 2) % 4
        dx_r, dy_r = DIR_OFFSETS[rear_dir]
        dx_s1, dy_s1 = DIR_OFFSETS[(d + 1) % 4]
        dx_s2, dy_s2 = DIR_OFFSETS[(d + 3) % 4]

        A = self.get_cell_power((gx + dx_r, gy + dy_r), (-dx_r, -dy_r))
        B1 = self.get_cell_power((gx + dx_s1, gy + dy_s1), (-dx_s1, -dy_s1))
        B2 = self.get_cell_power((gx + dx_s2, gy + dy_s2), (-dx_s2, -dy_s2))
        B = max(B1, B2)

        c["rear_in"] = A; c["side_in"] = B
        c["next_output"] = (A if A >= B else 0) if c.get("mode", "compare") == "compare" else max(0, A - B)

    for pos, c in self.world.items():
      if c.get("type") == "comparator": c["output_signal"] = c.get("next_output", 0)

    for (gx, gy), c in self.world.items():
      if c.get("type") == "inverter":
        in_dir = (c.get("direction", 0) + 2) % 4
        dx, dy = DIR_OFFSETS[in_dir]
        c["is_powered"] = not (self.get_cell_power((gx + dx, gy + dy), (-dx, -dy)) > 0)

    piston_pushes, piston_pulls = [], []
    for (gx, gy), c in self.world.items():
      if c.get("type") in ("piston", "sticky_piston"):
        powered = any(self.get_cell_power((gx + dx, gy + dy), (-dx, -dy)) > 0 for dx, dy in DIR_OFFSETS)
        if powered and not c.get("extended", False):
          dx, dy = DIR_OFFSETS[c.get("direction", 0)]
          curr_x, curr_y = gx + dx, gy + dy
          blocks_to_push = []
          can_push = True
          for _ in range(3):
            target = self.world.get((curr_x, curr_y))
            if not target: break
            if target.get("type") in ("stone", "piston", "sticky_piston"): can_push = False; break
            blocks_to_push.append((curr_x, curr_y))
            curr_x += dx; curr_y += dy
          else:
            if self.world.get((curr_x, curr_y)): can_push = False
          if can_push:
            c["extended"] = True
            if blocks_to_push: piston_pushes.append((blocks_to_push, dx, dy))
        elif not powered and c.get("extended", False):
          c["extended"] = False
          if c.get("type") == "sticky_piston":
            dx, dy = DIR_OFFSETS[c.get("direction", 0)]
            pull_src, pull_dst = (gx + dx * 2, gy + dy * 2), (gx + dx, gy + dy)
            target = self.world.get(pull_src)
            if target and target.get("type") not in ("stone", "piston", "sticky_piston"):
              piston_pulls.append((pull_src, pull_dst))

    for blocks, dx, dy in piston_pushes:
      for bx, by in reversed(blocks):
        if (bx, by) in self.world:
          target_pos = (bx + dx, by + dy)
          if target_pos not in self.world:
              self.world[target_pos] = self.world.pop((bx, by))
              if self.selected_cell == (bx, by): self.selected_cell = target_pos
    for src, dst in piston_pulls:
      if src in self.world and dst not in self.world:
        self.world[dst] = self.world.pop(src)
        if self.selected_cell == src: self.selected_cell = dst

    for (gx, gy), c in self.world.items():
      if c.get("type") == "delayer":
        in_dir = (c.get("direction", 0) + 2) % 4
        dx, dy = DIR_OFFSETS[in_dir]
        curr = (gx + dx, gy + dy)
        if self.world.get(curr, {}).get("type") == "wire" and self.world.get(curr, {}).get("signal", 0) > 0:
          while curr is not None and curr in self.world:
            if self.world[curr].get("type") == "wire": self.world[curr]["boost_red"] = True
            curr = parents.get(curr)

    burnt = []
    for pos, c in self.world.items():
      if c.get("type") == "wood":
        sides = sum(1 for dx, dy in DIR_OFFSETS if self.world.get((pos[0] + dx, pos[1] + dy), {}).get("signal", 0) > 0)
        if sides >= 3: burnt.append(pos)

    for (gx, gy), c in self.world.items():
      if c.get("type") in ("screen", "light", "tnt", "c4"):
        max_s = 0; min_d = 999
        for dx, dy in DIR_OFFSETS:
          pos = (gx + dx, gy + dy)
          if pos in burnt: continue
          p = self.get_cell_power(pos, (-dx, -dy))
          if p > max_s: max_s = p
          if pos in wire_dist: min_d = min(min_d, wire_dist[pos])
        if c.get("type") == "screen":
          c["is_powered"] = max_s > 0
          c["val"] = str(min_d) if (c.get("is_powered", False) and c.get("mode", 1) == 1) else ("1" if c.get("is_powered", False) else "0")
        elif c.get("type") == "light":
          if max_s > 0:
            if c.get("counter", 0) < c.get("delay", 0): c["counter"] = c.get("counter", 0) + 1
            if c.get("counter", 0) >= c.get("delay", 0): c["lit"] = True
          else: c["counter"] = 0; c["lit"] = False
        elif c.get("type") == "tnt":
          if max_s > 0 and not c.get("primed", False): c["primed"] = True
        elif c.get("type") == "c4":
          if max_s > 0 and not c.get("primed", False): c["primed"] = True

    det = []
    for pos, c in list(self.world.items()):
      if c.get("type") == "tnt" and c.get("primed", False):
        c["fuse"] = c.get("fuse", 4) - 1
        if c.get("fuse", 0) <= 0: det.append((pos[0], pos[1], 1, "tnt"))
      elif c.get("type") == "c4" and c.get("primed", False):
        c["countdown"] = c.get("countdown", 30) - 1
        if c.get("countdown", 0) <= 0: det.append((pos[0], pos[1], 2, "c4"))

    for cx, cy, rad, _ in det:
      for dx in range(-rad, rad + 1):
        for dy in range(-rad, rad + 1):
          t = (cx + dx, cy + dy)
          if t in self.world:
            del self.world[t]
            if self.selected_cell == t: self.selected_cell = None; self.apply_typing()
      self.explosions.append({"x": cx, "y": cy, "radius": rad + 0.5, "life": 5, "type": "bomb"})

    for b in burnt:
      if b in self.world:
        del self.world[b]
      self.explosions.append({"x": b[0], "y": b[1], "radius": 0.8, "life": 4, "type": "fire"})
      if self.selected_cell == b: self.selected_cell = None

    for exp in self.explosions[:]:
      exp["life"] -= 1
      if exp["life"] <= 0: self.explosions.remove(exp)

  def draw_animated_btn(self, b_id, cx, cy, w, h, text, norm_col, hov_col, font_size=22):
    if b_id not in self.btn_scales: self.btn_scales[b_id] = 1.0
    is_hov = (cx - w // 2 <= self.mouse_x <= cx + w // 2) and (cy - h // 2 <= self.mouse_y <= cy + h // 2)
    
    if is_hov: self.current_hover = b_id
      
    target = 1.08 if is_hov else 1.0
    self.btn_scales[b_id] += (target - self.btn_scales[b_id]) * 0.2
    sc = self.btn_scales[b_id]
    cw, ch = int(w * sc), int(h * sc)
    rect = (cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2)
    self.hitboxes[b_id] = rect
    self.canvas.create_rectangle(rect, fill=hov_col if is_hov else norm_col, outline="#555", width=3)
    self.canvas.create_text(cx, cy, text=text, font=("Impact", int(font_size * sc)), fill="#000")

  def draw_tilted_box(self, b_id, cx, cy, w, h, tilt_y, fill, outline, width=3):
    if b_id not in self.btn_scales: self.btn_scales[b_id] = 1.0
    is_hov = (cx - w // 2 <= self.mouse_x <= cx + w // 2) and (cy - h // 2 <= self.mouse_y <= cy + h // 2)
    
    if is_hov: self.current_hover = b_id
      
    target = 1.05 if is_hov else 1.0
    self.btn_scales[b_id] += (target - self.btn_scales[b_id]) * 0.2
    sc = self.btn_scales[b_id]
    cw, ch, cty = int(w * sc), int(h * sc), int(tilt_y * sc)
    pts = [cx - cw // 2, cy - ch // 2 + cty, cx + cw // 2, cy - ch // 2 - cty, cx + cw // 2, cy + ch // 2 - cty, cx - cw // 2, cy + ch // 2 + cty]
    self.canvas.create_polygon(pts, fill=fill, outline=outline, width=width)
    return sc

  def draw_flat_slider(self, b_id, cx, cy, w, h, text, val):
    if b_id not in self.btn_scales: self.btn_scales[b_id] = 1.0
    is_hov = (cx - w // 2 <= self.mouse_x <= cx + w // 2) and (cy - h // 2 <= self.mouse_y <= cy + h // 2)
    if is_hov: self.current_hover = b_id
      
    target = 1.05 if is_hov else 1.0
    self.btn_scales[b_id] += (target - self.btn_scales[b_id]) * 0.2
    sc = self.btn_scales[b_id]
    
    cw, ch = int(w * sc), int(h * sc)
    self.canvas.create_rectangle(cx - cw//2, cy - ch//2, cx + cw//2, cy + ch//2, fill="#e6e6e6", outline="#555", width=3)
    self.canvas.create_text(cx - cw//2 + int(15*sc), cy, text=text, font=("Impact", int(20*sc)), fill="#000", anchor=tk.W)
    
    track_w = cw * 0.45
    track_x1 = cx + cw//2 - track_w - int(15*sc)
    track_x2 = cx + cw//2 - int(15*sc)
    self.canvas.create_line(track_x1, cy, track_x2, cy, fill="#555", width=int(4*sc))
    
    knob_x = track_x1 + (track_x2 - track_x1) * (val / 100.0)
    self.canvas.create_rectangle(knob_x - int(8*sc), cy - int(15*sc), knob_x + int(8*sc), cy + int(15*sc), fill="#ff2222", outline="#222", width=2)
    
    self.hitboxes[b_id] = (track_x1 - 15, cy - 25, track_x2 + 15, cy + 25)

  def draw(self):
    self.current_hover = None
    self.canvas.delete("all")
    self.hitboxes.clear()

    w = self.canvas.winfo_width()
    h = self.canvas.winfo_height()
    if w > 200: self.win_width = w
    if h > 200: self.win_height = h

    bg_col = "#000000" if self.is_dark_mode else "#e0e0e0"
    grid_col = "#222222" if self.is_dark_mode else "#c0c0c0"

    self.canvas.create_rectangle(0, 0, self.win_width, self.win_height, fill=bg_col)
    s = BASE_CELL_SIZE

    if self.app_state != "game":
      offset = (time.time() * 30) % s
      for x in range(-s, self.win_width + s, s):
        self.canvas.create_line(x + offset, 0, x + offset, self.win_height, fill=grid_col)
      for y in range(-s, self.win_height + s, s):
        self.canvas.create_line(0, y + offset, self.win_width, y + offset, fill=grid_col)
    else:
      self.draw_game_world(grid_col)

    if self.app_state == "menu": self.draw_menu()
    elif self.app_state == "pause": self.draw_pause_menu()
    elif self.app_state == "select_sim": self.draw_select_sim()
    elif self.app_state == "settings": self.draw_settings()
    elif self.app_state == "game": self.draw_game_ui()

    if self.trans["active"]:
      p = min(1.0, max(0.0, self.trans["prog"]))
      ep = 1.0 - (1.0 - p) ** 3
      cur_h = self.win_height
      if self.trans["phase"] == 1:
        self.canvas.create_rectangle(0, 0, self.win_width, cur_h * ep, fill="#050505", outline="")
      elif self.trans["phase"] == 2:
        self.canvas.create_rectangle(0, cur_h * ep, self.win_width, cur_h, fill="#050505", outline="")

    if self.current_hover != self.hovered_btn:
        if self.current_hover is not None and SOUNDS_ENABLED and "vol_" not in self.current_hover:
            snd_hover.play()
        self.hovered_btn = self.current_hover

  def draw_menu(self):
    cx, cy = self.win_width // 2, self.win_height // 2
    bob_y = math.sin(time.time() * 2) * 12
    title_w, title_y = 480, int(self.win_height * 0.22) + bob_y

    beta_cx = cx - title_w - 70
    beta_cy = title_y - 80
    self.canvas.create_line(beta_cx+10, beta_cy+10, cx - title_w + 30, title_y, fill="#777", width=3, smooth=True)
    self.canvas.create_line(beta_cx, beta_cy+20, cx - title_w + 20, title_y - 15, fill="#777", width=3, smooth=True)

    self.canvas.create_polygon(beta_cx-85, beta_cy-35, beta_cx+85, beta_cy-35, beta_cx+85, beta_cy+35, beta_cx-85, beta_cy+35, fill="#1c1c1c", outline="#444", width=3)
    self.canvas.create_polygon(beta_cx-80, beta_cy-30, beta_cx+80, beta_cy-30, beta_cx+80, beta_cy+30, beta_cx-80, beta_cy+30, fill="#ffffff", outline="#000", width=2)
    self.canvas.create_oval(beta_cx-75, beta_cy-25, beta_cx-65, beta_cy-15, fill="#888", outline="#444")
    self.canvas.create_oval(beta_cx+65, beta_cy-25, beta_cx+75, beta_cy-15, fill="#888", outline="#444")
    
    self.canvas.create_text(beta_cx - 2, beta_cy, text="BETA 2.0", font=("Impact", 28), fill="#aaaaaa", angle=10)
    self.canvas.create_text(beta_cx, beta_cy, text="BETA 2.0", font=("Impact", 28), fill="#ff2222", angle=10)

    self.canvas.create_arc(cx - 250, title_y - 50, cx - 120, title_y + 30, start=0, extent=180, outline="#ff0000", width=3, style=tk.ARC)
    self.canvas.create_arc(cx - 180, title_y - 40, cx - 80, title_y + 20, start=0, extent=180, outline="#ff0000", width=3, style=tk.ARC)
    self.canvas.create_rectangle(cx - title_w, title_y - 55, cx + title_w, title_y + 55, fill="#ffffff", outline="#aaaaaa", width=3)
    self.canvas.create_rectangle(cx + title_w, title_y - 35, cx + title_w + 25, title_y + 35, fill="#666666", outline="")
    self.canvas.create_rectangle(cx + title_w + 5, title_y - 25, cx + title_w + 20, title_y - 10, fill="#ff0000", outline="")
    self.canvas.create_rectangle(cx + title_w + 5, title_y + 10, cx + title_w + 20, title_y + 25, fill="#00ff00", outline="")

    star_cx, star_cy = cx - title_w, title_y + 55
    angle = time.time() * 0.8
    star_pts = []
    for i in range(10):
        r = 38 if i % 2 == 0 else 16
        a = angle + i * math.pi / 5
        star_pts.extend([star_cx + r * math.cos(a), star_cy + r * math.sin(a)])
    self.canvas.create_polygon(star_pts, fill="#ffcc00", outline="#cc9900", width=2)

    txt, fnt = "RED: REDTEDACVHSVAEEHFID", ("Impact", 33)
    self.canvas.create_text(cx - 3, title_y, text=txt, font=fnt, fill="#ff0000")
    self.canvas.create_text(cx + 3, title_y, text=txt, font=fnt, fill="#00ffff")
    self.canvas.create_text(cx, title_y, text=txt, font=fnt, fill="#000000")

    sc = 1.0 + (self.ui_scale_val - 100) * 0.0015
    sy = int(self.win_height * 0.45)
    
    self.draw_animated_btn("btn_play", cx, sy + 37, int(460*sc), int(75*sc), self.loc("play"), "#99ff99", "#b3ffb3", 22*sc)
    self.draw_animated_btn("btn_settings", cx, sy + 137, int(380*sc), int(70*sc), self.loc("settings"), "#cccccc", "#e6e6e6", 22*sc)
    self.draw_animated_btn("btn_exit", cx, sy + 232, int(260*sc), int(65*sc), self.loc("exit"), "#ffcccc", "#ffb3b3", 22*sc)

    kunjst_y = title_y + 75
    self.canvas.create_text(cx + 2, kunjst_y + 2, text="KUNJST", font=("Impact", 22), fill="#222222")
    self.canvas.create_text(cx, kunjst_y, text="KUNJST", font=("Impact", 22), fill="#888888")

  def draw_pause_menu(self):
    cx, cy = self.win_width // 2, self.win_height // 2
    bob_y = math.sin(time.time() * 2) * 12
    title_w, title_y = 480, int(self.win_height * 0.22) + bob_y

    self.canvas.create_rectangle(cx - title_w, title_y - 55, cx + title_w, title_y + 55, fill="#ffffff", outline="#aaaaaa", width=3)
    self.canvas.create_rectangle(cx + title_w, title_y - 35, cx + title_w + 25, title_y + 35, fill="#666666", outline="")
    self.canvas.create_rectangle(cx + title_w + 5, title_y - 25, cx + title_w + 20, title_y - 10, fill="#ff0000", outline="")
    self.canvas.create_rectangle(cx + title_w + 5, title_y + 10, cx + title_w + 20, title_y + 25, fill="#00ff00", outline="")

    txt, fnt = self.loc("pause_title"), ("Impact", 33)
    self.canvas.create_text(cx - 3, title_y, text=txt, font=fnt, fill="#ff0000")
    self.canvas.create_text(cx + 3, title_y, text=txt, font=fnt, fill="#00ffff")
    self.canvas.create_text(cx, title_y, text=txt, font=fnt, fill="#000000")

    sc = 1.0 + (self.ui_scale_val - 100) * 0.0015
    sy = int(self.win_height * 0.45)
    self.draw_animated_btn("btn_resume", cx, sy + 37, int(460*sc), int(75*sc), self.loc("resume"), "#99ff99", "#b3ffb3", 22*sc)
    self.draw_animated_btn("btn_settings", cx, sy + 137, int(380*sc), int(70*sc), self.loc("settings"), "#cccccc", "#e6e6e6", 22*sc)
    self.draw_animated_btn("btn_exit_to_menu", cx, sy + 232, int(400*sc), int(65*sc), self.loc("exit_to_menu"), "#ffcccc", "#ffb3b3", 20*sc)

  def draw_select_sim(self):
    cx = self.win_width // 2
    sc = 1.0 + (self.ui_scale_val - 100) * 0.0015
    
    if self.has_active_game:
      sy = int(self.win_height * 0.25)
      self.draw_animated_btn("btn_resume", cx, sy, int(460*sc), int(75*sc), self.loc("resume"), "#99ff99", "#b3ffb3", 22*sc)
      self.draw_animated_btn("btn_new", cx, sy + int(100*sc), int(440*sc), int(75*sc), self.loc("new"), "#99ccff", "#b3d9ff", 22*sc)
      self.draw_animated_btn("btn_load", cx, sy + int(200*sc), int(440*sc), int(75*sc), self.loc("load"), "#ffcc99", "#ffd9b3", 22*sc)
      self.draw_animated_btn("btn_back", cx, sy + int(320*sc), int(300*sc), int(60*sc), self.loc("back"), "#cccccc", "#e6e6e6", 18*sc)
    else:
      sy = int(self.win_height * 0.35)
      self.draw_animated_btn("btn_new", cx, sy, int(440*sc), int(75*sc), self.loc("new"), "#99ccff", "#b3d9ff", 22*sc)
      self.draw_animated_btn("btn_load", cx, sy + int(100*sc), int(440*sc), int(75*sc), self.loc("load"), "#ffcc99", "#ffd9b3", 22*sc)
      self.draw_animated_btn("btn_back", cx, sy + int(220*sc), int(300*sc), int(60*sc), self.loc("back"), "#cccccc", "#e6e6e6", 18*sc)

  def draw_settings(self):
    W, H = self.win_width, self.win_height
    bob1 = math.sin(time.time() * 2) * 6
    bob2 = math.cos(time.time() * 2.3) * 6
    bob3 = math.sin(time.time() * 1.7 + 1) * 6

    tx, ty = int(W * 0.28), int(H * 0.2) + bob1
    self.canvas.create_line(tx - 60, -50, tx - 50, ty, fill="#ff1111", width=3, smooth=True)
    self.canvas.create_line(tx - 35, -50, tx - 25, ty, fill="#ff3333", width=2, smooth=True)
    sc_bg = self.draw_tilted_box("box_bg", tx, ty, 480, 90, 8, "#ffffff", "#555")
    bg_state_txt = self.loc("dark") if self.is_dark_mode else self.loc("light")
    self.canvas.create_text(tx - 40 * sc_bg, ty, text=f"{self.loc('bg')}: {bg_state_txt}", font=("Impact", int(24 * sc_bg)), fill="#000", angle=2)

    sw_x, sw_y = tx + 190 * sc_bg, ty - 5 * sc_bg
    if "set_theme" not in self.btn_scales: self.btn_scales["set_theme"] = 1.0
    is_hov_sw = (sw_x - 30 <= self.mouse_x <= sw_x + 60) and (sw_y - 45 <= self.mouse_y <= sw_y + 45)
    if is_hov_sw: self.current_hover = "set_theme"
    
    target_sw = 1.15 if is_hov_sw else 1.0
    self.btn_scales["set_theme"] += (target_sw - self.btn_scales["set_theme"]) * 0.2
    sc_sw = self.btn_scales["set_theme"]
    
    self.canvas.create_rectangle(sw_x - 10 * (sc_sw - 1), sw_y - 35 * sc_sw, sw_x + 45 * sc_sw, sw_y + 35 * sc_sw, fill="#888", outline="#555", width=2)
    if self.is_dark_mode: 
      self.canvas.create_rectangle(sw_x + 5 * sc_sw, sw_y - 30 * sc_sw, sw_x + 40 * sc_sw, sw_y, fill="#00cc44", outline="")
    else: 
      self.canvas.create_rectangle(sw_x + 5 * sc_sw, sw_y, sw_x + 40 * sc_sw, sw_y + 30 * sc_sw, fill="#ee2222", outline="")
    self.hitboxes["set_theme"] = (sw_x - 10, sw_y - 45, sw_x + 60, sw_y + 45)

    vx, vy1 = int(W * 0.28), int(H * 0.42)
    self.draw_flat_slider("vol_sfx", vx, vy1, 480, 50, self.loc("sfx_vol"), self.vol_sfx)
    vy2 = int(H * 0.52)
    self.draw_flat_slider("vol_bgm", vx, vy2, 480, 50, self.loc("bgm_vol"), self.vol_bgm)

    sx, sy = int(W * 0.72), int(H * 0.3) + bob2
    sc_sz = self.draw_tilted_box("box_size", sx, sy, 520, 100, -8, "#ffffff", "#555")
    self.canvas.create_text(sx - 80 * sc_sz, sy, text=self.loc("size"), font=("Impact", int(28 * sc_sz)), fill="#000", angle=-2)
    
    st_x, st_y = sx + 190 * sc_sz, sy
    if "set_size_input" not in self.btn_scales: self.btn_scales["set_size_input"] = 1.0
    is_hov_st = (st_x - 60 <= self.mouse_x <= st_x + 70) and (st_y - 60 <= self.mouse_y <= st_y + 60)
    if is_hov_st: self.current_hover = "set_size_input"
    
    target_st = 1.1 if is_hov_st else 1.0
    self.btn_scales["set_size_input"] += (target_st - self.btn_scales["set_size_input"]) * 0.2
    sc_st = self.btn_scales["set_size_input"]

    self.canvas.create_polygon(st_x - 50 * sc_st, st_y - 50 * sc_st, st_x + 50 * sc_st, st_y - 60 * sc_st, st_x + 60 * sc_st, st_y + 50 * sc_st, st_x - 40 * sc_st, st_y + 60 * sc_st, fill="#b5b5b5", outline="#777")
    self.canvas.create_polygon(st_x - 55 * sc_st, st_y - 60 * sc_st, st_x - 35 * sc_st, st_y - 40 * sc_st, st_x - 25 * sc_st, st_y - 50 * sc_st, st_x - 45 * sc_st, st_y - 70 * sc_st, fill="#eeeeb8", outline="")
    self.canvas.create_polygon(st_x + 45 * sc_st, st_y + 50 * sc_st, st_x + 65 * sc_st, st_y + 70 * sc_st, st_x + 75 * sc_st, st_y + 60 * sc_st, st_x + 55 * sc_st, st_y + 40 * sc_st, fill="#eeeeb8", outline="")
    self.canvas.create_polygon(st_x - 35 * sc_st, st_y + 45 * sc_st, st_x - 15 * sc_st, st_y + 65 * sc_st, st_x - 5 * sc_st, st_y + 55 * sc_st, st_x - 25 * sc_st, st_y + 35 * sc_st, fill="#eeeeb8", outline="")
    
    is_typ = self.typing_target == "ui_scale"
    blink = "|" if is_typ and int(time.time() * 2) % 2 == 0 else ""
    v_str = (self.ui_scale_str + blink) if is_typ else f"{self.ui_scale_val}%"
    self.canvas.create_text(st_x + 10 * sc_st, sy, text=v_str, font=("Impact", int(24 * sc_st)), fill="#000" if is_typ else "#444", angle=-4)
    self.hitboxes["set_size_input"] = (st_x - 60, st_y - 60, st_x + 70, st_y + 60)

    lx, ly = int(W * 0.32), int(H * 0.75) + bob3
    self.canvas.create_rectangle(lx - 80, ly - 110, lx + 80, ly - 50, fill="#ccc", outline="#555", width=3)
    self.canvas.create_text(lx, ly - 80, text=self.loc("lang"), font=("Impact", 18), fill="#000")
    self.canvas.create_line(lx + 60, ly - 50, lx + 60, ly, smooth=True, fill="red", width=2)
    self.canvas.create_line(lx + 70, ly - 50, lx + 70, ly, smooth=True, fill="red", width=2)
    sc_lang = self.draw_tilted_box("box_lang", lx, ly, 520, 110, 12, "#ffffff", "#555")

    prog, dir_val = self.lang_slide["prog"], self.lang_slide["dir"]
    if self.lang_slide["active"]:
      ep = 1 - (1 - prog) ** 3
      off_old = ep * 180 * dir_val
      off_new = -180 * dir_val + (ep * 180 * dir_val)
      self.canvas.create_text(lx + off_old, ly, text=self.lang_slide["old_txt"], font=("Impact", int(36 * sc_lang)), fill="#cccccc", angle=2)
      self.canvas.create_text(lx + off_new, ly, text=self.lang_slide["new_txt"], font=("Impact", int(36 * sc_lang)), fill="#000000", angle=2)
    else:
      self.canvas.create_text(lx, ly, text=self.loc("lang_name"), font=("Impact", int(36 * sc_lang)), fill="#000000", angle=2)

    lcx, lcy = lx - 270 * sc_lang, ly - 20 * sc_lang
    if "set_lang_left" not in self.btn_scales: self.btn_scales["set_lang_left"] = 1.0
    is_hov_ll = (lcx - 50 <= self.mouse_x <= lcx + 50) and (lcy - 50 <= self.mouse_y <= lcy + 50)
    if is_hov_ll: self.current_hover = "set_lang_left"
    
    target_ll = 1.15 if is_hov_ll else 1.0
    self.btn_scales["set_lang_left"] += (target_ll - self.btn_scales["set_lang_left"]) * 0.2
    scl = self.btn_scales["set_lang_left"]
    
    self.canvas.create_polygon(lcx - 40 * scl, lcy - 50 * scl, lcx + 50 * scl, lcy - 40 * scl, lcx + 40 * scl, lcy + 50 * scl, lcx - 50 * scl, lcy + 40 * scl, fill="#ccc", outline="#555", width=2)
    self.canvas.create_polygon(lcx + 10 * scl, lcy - 20 * scl, lcx - 20 * scl, lcy, lcx + 10 * scl, lcy + 20 * scl, fill="#777", outline="")
    self.canvas.create_rectangle(lcx + 10 * scl, lcy - 10 * scl, lcx + 35 * scl, lcy + 10 * scl, fill="#777", outline="")
    self.hitboxes["set_lang_left"] = (lcx - 50, lcy - 50, lcx + 50, lcy + 50)

    rcx, rcy = lx + 260 * sc_lang, ly + 10 * sc_lang
    if "set_lang_right" not in self.btn_scales: self.btn_scales["set_lang_right"] = 1.0
    is_hov_lr = (rcx - 50 <= self.mouse_x <= rcx + 50) and (rcy - 50 <= self.mouse_y <= rcy + 50)
    if is_hov_lr: self.current_hover = "set_lang_right"
    
    target_lr = 1.15 if is_hov_lr else 1.0
    self.btn_scales["set_lang_right"] += (target_lr - self.btn_scales["set_lang_right"]) * 0.2
    scr = self.btn_scales["set_lang_right"]
    
    self.canvas.create_polygon(rcx - 40 * scr, rcy - 50 * scr, rcx + 50 * scr, rcy - 40 * scr, rcx + 40 * scr, rcy + 50 * scr, rcx - 50 * scr, rcy + 40 * scr, fill="#ccc", outline="#555", width=2)
    self.canvas.create_polygon(rcx - 10 * scr, rcy - 20 * scr, rcx + 20 * scr, rcy, rcx - 10 * scr, rcy + 20 * scr, fill="#777", outline="")
    self.canvas.create_rectangle(rcx - 10 * scr, rcy - 10 * scr, rcx - 35 * scr, rcy + 10 * scr, fill="#777", outline="")
    self.hitboxes["set_lang_right"] = (rcx - 50, rcy - 50, rcx + 50, rcy + 50)

    bx, by = int(W * 0.72), int(H * 0.8)
    self.draw_animated_btn("btn_back", bx, by, 340, 80, self.loc("back"), "#cccccc", "#e6e6e6", 24)

  def draw_game_world(self, grid_col):
    scale = self.ui_scale_val / 100.0
    top_h = int(TOP_PANEL_HEIGHT * scale)
    bot_h = int(BOTTOM_PANEL_HEIGHT * scale)
    field_w, field_h, s = self.win_width, self.win_height - bot_h, max(1, self.cell_size)
    
    start_col, end_col = int(-(self.cam_x // s) - 1), int(-(self.cam_x // s) - 1) + int(field_w // s) + 3
    start_row, end_row = int(-(self.cam_y // s) - 1), int(-(self.cam_y // s) - 1) + int(field_h // s) + 3
    for col in range(start_col, end_col):
      sx = col * s + self.cam_x
      if 0 <= sx <= field_w: self.canvas.create_line(sx, top_h, sx, field_h, fill=grid_col, width=1)
    for row in range(start_row, end_row):
      sy = row * s + self.cam_y
      if top_h <= sy <= field_h: self.canvas.create_line(0, sy, field_w, sy, fill=grid_col, width=1)

    for (gx, gy), c in self.world.items():
      sx, sy = gx * s + self.cam_x, gy * s + self.cam_y
      if sx + s < 0 or sx > field_w or sy + s < top_h or sy > field_h: continue

      if c.get("type") == "wire":
        col = "#ff1e1e" if c.get("boost_red") or c.get("signal", 0) >= 4 else ("#d61a1a" if c.get("signal", 0) == 3 else ("#941010" if c.get("signal", 0) == 2 else "#5e0808" if c.get("signal", 0) == 1 else "#380505"))
        w = max(2, int(4 * self.zoom)) if c.get("signal", 0) > 0 else max(1, int(3 * self.zoom))
        r = int(s * 0.1)
        cx, cy = sx + s // 2, sy + s // 2
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")
        for dx, dy in DIR_OFFSETS:
          if self.world.get((gx + dx, gy + dy)) is not None: self.canvas.create_line(cx, cy, cx + dx * (s // 2), cy + dy * (s // 2), fill=col, width=w)
      elif c.get("type") == "wood":
        self.canvas.create_rectangle(sx + 3, sy + 3, sx + s - 3, sy + s - 3, fill="#8B5A2B" if c.get("signal", 0) == 0 else "#b06c33", outline="#5C3A1E" if c.get("signal", 0) == 0 else "#ff9900", width=max(1, int(2 * self.zoom)))
        self.canvas.create_line(sx + 3, sy + s // 3, sx + s - 3, sy + s // 3, fill="#5C3A1E")
        self.canvas.create_line(sx + 3, sy + 2 * (s // 3), sx + s - 3, sy + 2 * (s // 3), fill="#5C3A1E")
        if c.get("signal", 0) > 0: self.canvas.create_text(sx + s // 2, sy + s // 2, text=f"½ ({c.get('signal', 0)})", fill="#ffff55", font=("Arial", max(6, int(8 * self.zoom)), "bold"))
      elif c.get("type") == "bridge":
        self.canvas.create_rectangle(sx + 2, sy + 2, sx + s - 2, sy + s - 2, fill="#555", outline="#777")
        col_v = "#ff1e1e" if c.get("signal_v", 0) >= 4 else ("#d61a1a" if c.get("signal_v", 0) == 3 else ("#941010" if c.get("signal_v", 0) == 2 else "#5e0808" if c.get("signal_v", 0) == 1 else "#380505"))
        col_h = "#ff1e1e" if c.get("signal_h", 0) >= 4 else ("#d61a1a" if c.get("signal_h", 0) == 3 else ("#941010" if c.get("signal_h", 0) == 2 else "#5e0808" if c.get("signal_h", 0) == 1 else "#380505"))
        self.canvas.create_rectangle(sx + int(s * 0.35), sy, sx + int(s * 0.65), sy + s, fill="#444", outline="")
        if c.get("signal_v", 0) > 0: self.canvas.create_line(sx + s // 2, sy, sx + s // 2, sy + s, fill=col_v, width=max(2, int(4 * self.zoom)))
        self.canvas.create_rectangle(sx, sy + int(s * 0.35), sx + s, sy + int(s * 0.65), fill="#666", outline="")
        if c.get("signal_h", 0) > 0: self.canvas.create_line(sx, sy + s // 2, sx + s, sy + s // 2, fill=col_h, width=max(2, int(4 * self.zoom)))
      elif c.get("type") == "stone":
        self.canvas.create_rectangle(sx + 2, sy + 2, sx + s - 2, sy + s - 2, fill="#4a4d52", outline="#2a2c30", width=max(1, int(1.5 * self.zoom)))
        self.canvas.create_line(sx + 2, sy + s // 2, sx + s - 2, sy + s // 2, fill="#2a2c30", width=2)
        self.canvas.create_line(sx + s // 2, sy + 2, sx + s // 2, sy + s // 2, fill="#2a2c30", width=2)
      elif c.get("type") in ("piston", "sticky_piston"):
        self.draw_piston(sx, sy, s, c)
      elif c.get("type") == "tnt":
        self.canvas.create_rectangle(sx + 3, sy + 3, sx + s - 3, sy + s - 3, fill="#fff" if c.get("primed", False) and c.get("fuse", 4) % 2 == 0 else "#cc2222", outline="#fff")
        self.canvas.create_rectangle(sx + 3, sy + int(s * 0.35), sx + s - 3, sy + int(s * 0.65), fill="#fff", outline="")
        self.canvas.create_text(sx + s // 2, sy + s // 2, text="TNT", fill="#000", font=("Impact", max(7, int(11 * self.zoom))))
      elif c.get("type") == "c4":
        self.canvas.create_rectangle(sx + 4, sy + 4, sx + s - 4, sy + s - 4, fill="#303828", outline="#ff4400" if c.get("primed", False) else "#667755", width=max(1, int(2 * self.zoom)))
        self.canvas.create_rectangle(sx + int(s * 0.2), sy + int(s * 0.3), sx + int(s * 0.8), sy + int(s * 0.7), fill="#111", outline="#333")
        self.canvas.create_text(sx + s // 2, sy + s // 2, text=str(c.get("countdown", 30)) if c.get("primed", False) else f"[{c.get('timer', 30)}]", fill="#ff1111" if c.get("primed", False) else "#00ffcc", font=("Arial", max(6, int(8 * self.zoom)), "bold"))
      elif c.get("type") == "switch":
        self.canvas.create_rectangle(sx + int(s * 0.2), sy + int(s * 0.15), sx + int(s * 0.8), sy + int(s * 0.85), fill="#808080", outline="#fff")
        self.canvas.create_rectangle(sx + int(s * 0.3), sy + int(s * 0.22), sx + int(s * 0.7), sy + int(s * 0.78), fill="#333", outline="")
        if c.get("active", False): self.canvas.create_rectangle(sx + int(s * 0.3), sy + int(s * 0.22), sx + int(s * 0.7), sy + int(s * 0.5), fill="#00cc44", outline="")
        else: self.canvas.create_rectangle(sx + int(s * 0.3), sy + int(s * 0.5), sx + int(s * 0.7), sy + int(s * 0.78), fill="#ee2222", outline="")
      elif c.get("type") == "button":
        self.canvas.create_rectangle(sx + int(s * 0.15), sy + int(s * 0.3), sx + int(s * 0.85), sy + int(s * 0.7), fill="#fff" if c.get("active", False) else "#666", outline="#aaa")
        self.canvas.create_text(sx + s // 2, sy + s // 2, text="BTN", fill="#000", font=("Arial", max(6, int(8 * self.zoom)), "bold"))
      elif c.get("type") == "delayer":
        p = int(s * 0.2); m = s // 2; d = c.get("direction", 0)
        pts = ([sx + p, sy + p, sx + p, sy + s - p, sx + s - p, sy + m] if d == 0 else ([sx + p, sy + p, sx + s - p, sy + p, sx + m, sy + s - p] if d == 1 else ([sx + s - p, sy + p, sx + s - p, sy + s - p, sx + p, sy + m] if d == 2 else [sx + p, sy + s - p, sx + s - p, sy + s - p, sx + m, sy + p])))
        self.canvas.create_polygon(pts, fill="#ff4444" if c.get("is_active", False) else "#888", outline="#fff", width=max(1, int(2 * self.zoom)))
        if c.get("counter", 0) > 0:
          prog = c.get("counter", 0) / max(1, c.get("delay", 2))
          self.canvas.create_rectangle(sx + int(s * 0.15), sy + int(s * 0.82), sx + int(s * 0.15) + int(s * 0.7 * prog), sy + int(s * 0.88), fill="#ffff00", outline="")
      elif c.get("type") == "comparator": self.draw_comparator(sx, sy, s, c)
      elif c.get("type") == "inverter":
        cx, cy = sx + s // 2, sy + s // 2; d = c.get("direction", 0)
        rot = (lambda rx, ry: (cx + int(rx * s), cy + int(ry * s)) if d == 1 else ((cx + int(ry * s), cy - int(rx * s)) if d == 0 else ((cx - int(rx * s), cy - int(ry * s)) if d == 3 else (cx - int(ry * s), cy + int(rx * s)))))
        r_pts = lambda pts: [p for pt in pts for p in rot(*pt)]
        self.canvas.create_polygon(r_pts([(-0.28, -0.4), (0.28, -0.4), (0.28, 0.4), (-0.28, 0.4)]), fill="#a6a6a6", outline="#fff")
        self.canvas.create_polygon(r_pts([(-0.28, -0.4), (0.28, -0.4), (0.28, -0.25), (-0.28, -0.25)]), fill="#00cc44", outline="")
        self.canvas.create_polygon(r_pts([(-0.28, 0.25), (0.28, 0.25), (0.28, 0.4), (-0.28, 0.4)]), fill="#ee2222", outline="")
        p1, p2, p3 = rot(-0.28, -0.15), rot(-0.4, -0.06), rot(-0.28, 0.04)
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], fill="#ff2222", width=max(1, int(2 * self.zoom)), smooth=True)
        p4, p5, p6 = rot(-0.28, -0.04), rot(-0.4, 0.08), rot(-0.28, 0.18)
        self.canvas.create_line(p4[0], p4[1], p5[0], p5[1], p6[0], p6[1], fill="#ff2222", width=max(1, int(2 * self.zoom)), smooth=True)
        self.canvas.create_polygon(r_pts([(0.04, -0.14), (-0.07, 0.01), (0.01, 0.01), (-0.04, 0.15), (0.08, -0.02), (0.01, -0.02)]), fill="#ffee00", outline="")
      elif c.get("type") == "generator":
        self.canvas.create_rectangle(sx + int(s * 0.15), sy + int(s * 0.1), sx + int(s * 0.85), sy + int(s * 0.9), fill="#262626", outline="#ff3333" if c.get("is_blocked", False) else "#888")
        bar_h = int(s * 0.65); bx = sx + int(s * 0.72); by_bot = sy + int(s * 0.8)
        self.canvas.create_rectangle(bx, by_bot - bar_h, bx + int(s * 0.08), by_bot, fill="#441111", outline="#555")
        if not c.get("is_blocked", False):
          if c.get("is_active", False): self.canvas.create_rectangle(bx, by_bot - bar_h, bx + int(s * 0.08), by_bot, fill="#ffff00", outline="")
          else: self.canvas.create_rectangle(bx, by_bot - int(bar_h * (c.get("counter", 0) / max(1, c.get("charge_time", 6)))), bx + int(s * 0.08), by_bot, fill="#ff2222", outline="")
        lt_size = int(s * 0.3); cx, cy = sx + int(s * 0.45), sy + int(s * 0.55)
        lt_pts = [cx + int(lt_size * 0.1), cy - lt_size // 2, cx - int(lt_size * 0.3), cy + int(lt_size * 0.05), cx, cy + int(lt_size * 0.05), cx - int(lt_size * 0.1), cy + lt_size // 2, cx + int(lt_size * 0.35), cy - int(lt_size * 0.1), cx + int(lt_size * 0.05), cy - int(lt_size * 0.1)]
        self.canvas.create_polygon(lt_pts, fill="#555" if c.get("is_blocked", False) else "#ff0", outline="")
      elif c.get("type") == "screen":
        is_lit = c.get("is_powered", False)
        self.canvas.create_rectangle(sx + int(s * 0.1), sy + int(s * 0.1), sx + int(s * 0.9), sy + int(s * 0.9), fill="#fff", outline="#00ff44" if is_lit else "#aaa", width=max(1, int(2 * self.zoom)))
        self.canvas.create_text(sx + s // 2, sy + s // 2, text=c.get("val", "0"), fill="#00aa00" if is_lit else "#222", font=("Arial", max(7, int(18 * self.zoom)), "bold"))
      elif c.get("type") == "light":
        on_c, off_c = {"red": ("#ff2222", "#551111"), "green": ("#00ff22", "#115511"), "blue": ("#2277ff", "#112255")}.get(c.get("color", "red"), ("#ff2222", "#551111"))
        self.canvas.create_polygon(sx + int(s * 0.3), sy + int(s * 0.8), sx + int(s * 0.7), sy + int(s * 0.8), sx + int(s * 0.65), sy + s, sx + int(s * 0.35), sy + s, fill="#555", outline="#333")
        self.canvas.create_oval(sx + int(s * 0.2), sy + int(s * 0.1), sx + int(s * 0.8), sy + int(s * 0.8), fill=on_c if c.get("lit", False) else off_c, outline="#fff" if c.get("lit", False) else "#555", width=max(1, int(2 * self.zoom)))
        if c.get("lit", False): self.canvas.create_oval(sx + int(s * 0.3), sy + int(s * 0.2), sx + int(s * 0.7), sy + int(s * 0.7), fill="#fff", outline="")

    if self.selection_rect:
      x1, y1, x2, y2 = self.selection_rect
      self.canvas.create_rectangle(min(x1, x2) * s + self.cam_x, min(y1, y2) * s + self.cam_y, (max(x1, x2) + 1) * s + self.cam_x, (max(y1, y2) + 1) * s + self.cam_y, outline="#00aaff", width=2, dash=(4, 4))

    for exp in self.explosions:
      ex, ey = exp["x"] * s + self.cam_x + s // 2, exp["y"] * s + self.cam_y + s // 2
      r_px = int(exp["radius"] * s * (1.0 + (5 - exp["life"]) * 0.15))
      self.canvas.create_oval(ex - r_px, ey - r_px, ex + r_px, ey + r_px, fill="#ff6600" if exp.get("type") == "bomb" else "#ff3300", outline="#ff0", width=3)

    if self.selected_cell:
      gx, gy = self.selected_cell
      self.canvas.create_rectangle(gx * s + self.cam_x + 1, gy * s + self.cam_y + 1, gx * s + self.cam_x + s - 1, gy * s + self.cam_y + s - 1, outline="#ffffff", width=2)

  def draw_piston(self, sx, sy, s, c):
    cx, cy = sx + s // 2, sy + s // 2
    d = c.get("direction", 0)
    rot = (lambda rx, ry: (cx + int(rx * s), cy + int(ry * s)) if d == 3 else ((cx - int(rx * s), cy - int(ry * s)) if d == 1 else ((cx - int(ry * s), cy + int(rx * s)) if d == 0 else (cx + int(ry * s), cy - int(rx * s)))))
    base_pts = [rot(-0.45, -0.1), rot(0.45, -0.1), rot(0.45, 0.45), rot(-0.45, 0.45)]
    self.canvas.create_polygon([p for pt in base_pts for p in pt], fill="#505050", outline="#777", width=max(1, int(1.5 * self.zoom)))
    ext = c.get("extended", False); y_off = -1.0 if ext else 0.0
    if ext:
      rod_pts = [rot(-0.1, -0.1), rot(0.1, -0.1), rot(0.1, -1.1), rot(-0.1, -1.1)]
      self.canvas.create_polygon([p for pt in rod_pts for p in pt], fill="#888", outline="#555")
    head_pts = [rot(-0.45, -0.5 + y_off), rot(0.45, -0.5 + y_off), rot(0.45, -0.1 + y_off), rot(-0.45, -0.1 + y_off)]
    self.canvas.create_polygon([p for pt in head_pts for p in pt], fill="#8B5A2B", outline="#4a2c11", width=max(1, int(1.5 * self.zoom)))
    if c.get("type") == "sticky_piston":
      slime_pts = [rot(-0.45, -0.5 + y_off), rot(0.45, -0.5 + y_off), rot(0.45, -0.35 + y_off), rot(-0.45, -0.35 + y_off)]
      self.canvas.create_polygon([p for pt in slime_pts for p in pt], fill="#00ff44", outline="")

  def draw_comparator(self, sx, sy, s, c):
    cx, cy = sx + s // 2, sy + s // 2
    d = c.get("direction", 0)
    rot = (lambda rx, ry: (cx + int(rx * s), cy + int(ry * s)) if d == 1 else ((cx + int(ry * s), cy - int(rx * s)) if d == 0 else ((cx - int(rx * s), cy - int(ry * s)) if d == 3 else (cx - int(ry * s), cy + int(rx * s)))))
    pts = [rot(-0.35, -0.35), rot(0.35, -0.35), rot(0.35, 0.35), rot(-0.35, 0.35)]
    self.canvas.create_polygon([p for pt in pts for p in pt], fill="#505050", outline="#aaaaaa", width=max(1, int(1.5 * self.zoom)))
    rear_lit = c.get("rear_in", 0) > 0
    t_col = "#ff2222" if rear_lit else "#440000"
    r_r = max(2, int(3 * self.zoom))
    for t_pos in [rot(-0.2, -0.2), rot(0.2, -0.2)]:
      self.canvas.create_oval(t_pos[0] - r_r, t_pos[1] - r_r, t_pos[0] + r_r, t_pos[1] + r_r, fill=t_col, outline="#fff" if rear_lit else "#222")
    front_pos = rot(0.0, 0.2)
    is_sub = c.get("mode", "compare") == "subtract"
    out_active = c.get("output_signal", 0) > 0
    f_col = ("#ffaa00" if out_active else "#664400") if is_sub else ("#ff2222" if out_active else "#440000")
    self.canvas.create_oval(front_pos[0] - r_r, front_pos[1] - r_r, front_pos[0] + r_r, front_pos[1] + r_r, fill=f_col, outline="#fff" if out_active else "#222")
    self.canvas.create_text(cx, cy, text="-" if is_sub else "=", fill="#ffffff" if out_active else "#888888", font=("Arial", max(7, int(10 * self.zoom)), "bold"))

  def draw_game_ui(self):
    scale = self.ui_scale_val / 100.0
    top_h = int(TOP_PANEL_HEIGHT * scale)
    bot_h = int(BOTTOM_PANEL_HEIGHT * scale)
    field_h = self.win_height - bot_h
    bg_pan = "#121212" if self.is_dark_mode else "#d0d0d0"
    bg_bot = "#0c0c0c" if self.is_dark_mode else "#c0c0c0"
    t_col = "#ffffff" if self.is_dark_mode else "#000000"

    f_13 = ("Impact", max(8, int(13 * scale)))
    f_10 = ("Impact", max(7, int(10 * scale)))
    f_9 = ("Impact", max(6, int(9 * scale)))
    f_8 = ("Impact", max(6, int(8 * scale)))
    f_b8 = ("Arial", max(6, int(8 * scale)), "bold")

    self.canvas.create_rectangle(0, 0, self.win_width, top_h, fill=bg_pan, outline="#282828")
    self.canvas.create_text(int(16*scale), int(22*scale), text="RED: REDTEDACVHSVAEEHFID", fill=t_col, anchor=tk.W, font=f_13)
    
    self.canvas.create_rectangle(int(218*scale), int(8*scale), int(342*scale), int(38*scale), fill="#0d2233", outline="#00d2ff", width=2)
    self.canvas.create_text(int(280*scale), int(23*scale), text=self.loc("save"), fill="#ffffff", font=f_9)
    
    self.canvas.create_rectangle(int(348*scale), int(8*scale), int(472*scale), int(38*scale), fill="#281a38", outline="#c471ed", width=2)
    self.canvas.create_text(int(410*scale), int(23*scale), text=self.loc("load_btn"), fill="#ffffff", font=f_9)
    
    self.canvas.create_rectangle(int(482*scale), int(8*scale), int(595*scale), int(38*scale), fill="#cc2222", outline="#ff4444", width=2)
    self.canvas.create_text(int(538*scale), int(23*scale), text=self.loc("clear"), fill="#ffffff", font=f_10)

    self.canvas.create_rectangle(0, field_h, self.win_width, self.win_height, fill=bg_bot, outline="#282828")

    is_m = self.active_tab == "mechanisms"
    self.canvas.create_rectangle(int(10*scale), field_h + int(5*scale), int(150*scale), field_h + int(30*scale), fill="#252525" if is_m else "#111111", outline="#00ffcc" if is_m else "#555", width=2 if is_m else 1)
    self.canvas.create_text(int(80*scale), field_h + int(17*scale), text=self.loc("mech"), fill="#ffffff" if is_m else "#888", font=f_10)

    is_b = self.active_tab == "blocks"
    self.canvas.create_rectangle(int(155*scale), field_h + int(5*scale), int(280*scale), field_h + int(30*scale), fill="#252525" if is_b else "#111111", outline="#00ffcc" if is_b else "#555", width=2 if is_b else 1)
    self.canvas.create_text(int(217*scale), field_h + int(17*scale), text=self.loc("blocks"), fill="#ffffff" if is_b else "#888", font=f_10)

    btn_w = int(58 * scale)
    btn_gap = int(2 * scale)
    step = btn_w + btn_gap
    start_x = int(10 * scale)

    tool_dict = self.loc("tools")
    for i, t_id in enumerate(TABS_IDS[self.active_tab]):
      t_name = tool_dict.get(t_id, t_id)
      bx = start_x + i * step
      by = field_h + int(35*scale)
      is_sel = self.selected_tool == t_id
      self.canvas.create_rectangle(bx, by, bx + btn_w, by + int(80*scale), outline="#00ffcc" if is_sel else "#444444", fill="#1c1c1c", width=2 if is_sel else 1)
      self.canvas.create_text(bx + int(8*scale), by + int(9*scale), text=f"[{i + 1}]", fill="#ffff55" if is_sel else "#777777", font=f_b8)

      cbx = bx + btn_w // 2
      cby = by + int(38 * scale)

      if t_id == "wire": self.canvas.create_line(cbx-int(18*scale), cby, cbx+int(18*scale), cby, fill="#ff2222", width=max(2, int(4*scale)))
      elif t_id == "delayer": self.canvas.create_polygon([cbx-int(15*scale), cby-int(15*scale), cbx-int(15*scale), cby+int(15*scale), cbx+int(15*scale), cby], fill="#888", outline="#fff")
      elif t_id == "switch":
        self.canvas.create_rectangle(cbx-int(10*scale), cby-int(16*scale), cbx+int(10*scale), cby+int(16*scale), fill="#888", outline="#fff")
        self.canvas.create_rectangle(cbx-int(7*scale), cby-int(13*scale), cbx+int(7*scale), cby, fill="#00cc44", outline="")
      elif t_id == "button": self.canvas.create_rectangle(cbx-int(18*scale), cby-int(10*scale), cbx+int(18*scale), cby+int(10*scale), fill="#888", outline="#fff")
      elif t_id == "inverter":
        self.canvas.create_rectangle(cbx-int(10*scale), cby-int(16*scale), cbx+int(10*scale), cby+int(16*scale), fill="#aaa", outline="#fff")
        self.canvas.create_rectangle(cbx-int(10*scale), cby-int(16*scale), cbx+int(10*scale), cby-int(8*scale), fill="#00cc44", outline="")
        self.canvas.create_rectangle(cbx-int(10*scale), cby+int(8*scale), cbx+int(10*scale), cby+int(16*scale), fill="#ee2222", outline="")
      elif t_id == "generator":
        self.canvas.create_rectangle(cbx-int(14*scale), cby-int(16*scale), cbx+int(14*scale), cby+int(16*scale), fill="#222", outline="#888")
        self.canvas.create_line(cbx+int(10*scale), cby-int(10*scale), cbx+int(10*scale), cby+int(10*scale), fill="#ff2222", width=max(1, int(2*scale)))
      elif t_id == "comparator":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#505050", outline="#fff")
        self.canvas.create_oval(cbx-int(10*scale), cby+int(3*scale), cbx-int(4*scale), cby+int(9*scale), fill="#ff2222", outline="")
        self.canvas.create_oval(cbx+int(4*scale), cby+int(3*scale), cbx+int(10*scale), cby+int(9*scale), fill="#ff2222", outline="")
        self.canvas.create_oval(cbx-int(3*scale), cby-int(11*scale), cbx+int(3*scale), cby-int(5*scale), fill="#ffaa00", outline="")
      elif t_id == "screen":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#fff")
        self.canvas.create_text(cbx, cby, text="1", fill="#00aa00", font=("Arial", max(7, int(11*scale)), "bold"))
      elif t_id == "light":
        self.canvas.create_polygon(cbx-int(8*scale), cby+int(4*scale), cbx+int(8*scale), cby+int(4*scale), cbx+int(5*scale), cby+int(13*scale), cbx-int(5*scale), cby+int(13*scale), fill="#555", outline="#333")
        self.canvas.create_oval(cbx-int(13*scale), cby-int(15*scale), cbx+int(13*scale), cby+int(8*scale), fill="#ff2222", outline="#fff", width=max(1, int(2*scale)))
      elif t_id == "wood":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#8B5A2B", outline="#5C3A1E", width=max(1, int(2*scale)))
        self.canvas.create_line(cbx-int(15*scale), cby-int(5*scale), cbx+int(15*scale), cby-int(5*scale), fill="#5C3A1E")
        self.canvas.create_line(cbx-int(15*scale), cby+int(5*scale), cbx+int(15*scale), cby+int(5*scale), fill="#5C3A1E")
      elif t_id == "bridge":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#555", outline="#777")
        self.canvas.create_rectangle(cbx-int(5*scale), cby-int(15*scale), cbx+int(5*scale), cby+int(15*scale), fill="#444", outline="")
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(5*scale), cbx+int(15*scale), cby+int(5*scale), fill="#666", outline="")
      elif t_id == "stone":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#4a4d52", outline="#2a2c30", width=max(1, int(2*scale)))
        self.canvas.create_line(cbx-int(15*scale), cby, cbx+int(15*scale), cby, fill="#2a2c30", width=max(1, int(2*scale)))
        self.canvas.create_line(cbx, cby-int(15*scale), cbx, cby, fill="#2a2c30", width=max(1, int(2*scale)))
      elif t_id == "piston":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(6*scale), cbx+int(15*scale), cby+int(14*scale), fill="#555", outline="#777")
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(14*scale), cbx+int(15*scale), cby-int(6*scale), fill="#8B5A2B", outline="#4a2c11")
      elif t_id == "sticky_piston":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(6*scale), cbx+int(15*scale), cby+int(14*scale), fill="#555", outline="#777")
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(14*scale), cbx+int(15*scale), cby-int(6*scale), fill="#8B5A2B", outline="#4a2c11")
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(17*scale), cbx+int(15*scale), cby-int(14*scale), fill="#00ff44", outline="")
      elif t_id == "tnt":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#cc2222", outline="#fff")
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(5*scale), cbx+int(15*scale), cby+int(5*scale), fill="#fff", outline="")
        self.canvas.create_text(cbx, cby, text="TNT", fill="#000", font=f_10)
      elif t_id == "c4":
        self.canvas.create_rectangle(cbx-int(15*scale), cby-int(15*scale), cbx+int(15*scale), cby+int(15*scale), fill="#303828", outline="#ff4400")
        self.canvas.create_rectangle(cbx-int(11*scale), cby-int(7*scale), cbx+int(11*scale), cby+int(7*scale), fill="#111", outline="#333")
        self.canvas.create_text(cbx, cby, text="30", fill="#00ffcc", font=f_b8)

      self.canvas.create_text(cbx, by + int(68*scale), text=t_name, fill="#ffffff", font=f_8)

    by = field_h + int(35*scale)
    ex = self.win_width - btn_w - int(10 * scale)
    qx = ex - btn_w - btn_gap

    is_sel_select = self.selected_tool == "select"
    self.canvas.create_rectangle(qx, by, qx + btn_w, by + int(80*scale), outline="#00aaff" if is_sel_select else "#444444", fill="#1c1c1c", width=2 if is_sel_select else 1)
    self.canvas.create_text(qx + int(8*scale), by + int(9*scale), text="[Q]", fill="#ffff55" if is_sel_select else "#777777", font=f_b8)
    q_cbx = qx + btn_w // 2
    q_cby = by + int(38 * scale)
    self.canvas.create_rectangle(q_cbx-int(16*scale), q_cby-int(16*scale), q_cbx+int(16*scale), q_cby+int(16*scale), outline="#00aaff", width=2, dash=(2, 2))
    self.canvas.create_line(q_cbx-int(16*scale), q_cby-int(16*scale), q_cbx-int(6*scale), q_cby-int(16*scale), fill="#00aaff", width=2)
    self.canvas.create_text(q_cbx, by + int(68*scale), text=self.loc("select"), fill="#00aaff" if is_sel_select else "#ffffff", font=f_8)

    is_sel_eraser = self.selected_tool == "eraser"
    self.canvas.create_rectangle(ex, by, ex + btn_w, by + int(80*scale), outline="#ff4444" if is_sel_eraser else "#444444", fill="#1c1c1c", width=2 if is_sel_eraser else 1)
    self.canvas.create_text(ex + int(8*scale), by + int(9*scale), text="[E]", fill="#ffff55" if is_sel_eraser else "#777777", font=f_b8)
    e_cbx = ex + btn_w // 2
    e_cby = by + int(38 * scale)
    self.canvas.create_line(e_cbx-int(13*scale), e_cby-int(13*scale), e_cbx+int(13*scale), e_cby+int(13*scale), fill="#ff4444", width=max(1, int(3*scale)))
    self.canvas.create_line(e_cbx+int(13*scale), e_cby-int(13*scale), e_cbx-int(13*scale), e_cby+int(13*scale), fill="#ff4444", width=max(1, int(3*scale)))
    self.canvas.create_text(e_cbx, by + int(68*scale), text=self.loc("eraser"), fill="#ff4444", font=f_8)

    if self.selected_cell:
      c = self.world.get(self.selected_cell)
      if c and c.get("type") in ("delayer", "comparator", "generator", "c4", "light", "screen", "inverter", "piston", "sticky_piston"):
        ox, oy = self.overlay_x, self.overlay_y
        px, py = ox + 15, oy + 10
        self.canvas.create_rectangle(ox, oy, ox + 240, oy + 245, fill="#161616", outline="#3a3a3a", width=2)
        self.canvas.create_rectangle(ox, oy, ox + 240, oy + 32, fill="#222222", outline="")
        names = {"delayer": "Задержатель", "comparator": "Компаратор", "generator": "Генератор", "c4": "C4 Взрывчатка", "light": "Лампочка", "screen": "Экран", "inverter": "Инвертор", "piston": "Поршень", "sticky_piston": "Липкий поршень"}
        self.canvas.create_text(px, py + 6, text=f"≡ {names.get(c.get('type'))}:", fill="#ffffff", anchor=tk.W, font=("Impact", 13))

        def draw_box(y_p, f_name):
          self.canvas.create_rectangle(px, y_p, px + 25, y_p + 25, fill="#2a2a2a", outline="#fff")
          self.canvas.create_text(px + 12, y_p + 12, text="-", fill="#fff", font=("Arial", 12, "bold"))
          is_typ = isinstance(self.typing_target, dict) and self.typing_target["cell"] == self.selected_cell and self.typing_target["field"] == f_name
          self.canvas.create_rectangle(px + 35, y_p, px + 95, y_p + 25, fill="#383838" if is_typ else "#1c1c1c", outline="#00ffcc" if is_typ else "#fff")
          raw_val = c.get(f_name, 0)
          v_str = c.get(f_name + "_str", str(raw_val)) if is_typ else str(raw_val)
          self.canvas.create_text(px + 65, y_p + 12, text=v_str + ("|" if is_typ else ""), fill="#00ffcc", font=("Arial", 11, "bold"))
          self.canvas.create_rectangle(px + 105, y_p, px + 130, y_p + 25, fill="#2a2a2a", outline="#fff")
          self.canvas.create_text(px + 117, y_p + 12, text="+", fill="#fff", font=("Arial", 12, "bold"))

        if c.get("type") == "delayer":
          self.canvas.create_text(px, py + 50, text="Задержка (тиков):", fill="#aaa", anchor=tk.W, font=("Arial", 9))
          draw_box(py + 75, "delay")
          self.canvas.create_rectangle(px, py + 120, px + 170, py + 150, fill="#252525", outline="#fff")
          self.canvas.create_text(px + 85, py + 135, text=f"Выход: {DIR_NAMES[c.get('direction', 0)]}", fill="#fff", font=("Arial", 9, "bold"))
        elif c.get("type") == "comparator":
          mode_txt = "Режим: Сравнение (A >= B)" if c.get("mode", "compare") == "compare" else "Режим: Вычитание (A - B)"
          mode_col = "#00ffcc" if c.get("mode", "compare") == "compare" else "#ffaa00"
          self.canvas.create_rectangle(px, py + 65, px + 200, py + 95, fill="#252525", outline=mode_col, width=2)
          self.canvas.create_text(px + 100, py + 80, text=mode_txt, fill=mode_col, font=("Arial", 8, "bold"))
          self.canvas.create_rectangle(px, py + 110, px + 170, py + 140, fill="#252525", outline="#fff")
          self.canvas.create_text(px + 85, py + 125, text=f"Выход: {DIR_NAMES[c.get('direction', 0)]}", fill="#fff", font=("Arial", 9, "bold"))
          self.canvas.create_text(px, py + 160, text=f"Вход A: {c.get('rear_in', 0)} | Бок B: {c.get('side_in', 0)}", fill="#aaa", anchor=tk.W, font=("Arial", 9))
        elif c.get("type") in ("piston", "sticky_piston"):
          self.canvas.create_text(px, py + 45, text="Направление толкания:", fill="#aaa", anchor=tk.W, font=("Arial", 9))
          self.canvas.create_rectangle(px, py + 65, px + 170, py + 95, fill="#252525", outline="#fff")
          self.canvas.create_text(px + 85, py + 80, text=f"Вперёд: {DIR_NAMES[c.get('direction', 0)]}", fill="#00ffcc", font=("Arial", 9, "bold"))
        elif c.get("type") == "generator":
          self.canvas.create_text(px, py + 40, text="Время зарядки:", fill="#aaa", anchor=tk.W, font=("Arial", 8))
          draw_box(py + 55, "charge_time")
          self.canvas.create_text(px, py + 90, text="Время подачи:", fill="#aaa", anchor=tk.W, font=("Arial", 8))
          draw_box(py + 105, "pulse_time")
        elif c.get("type") == "c4":
          self.canvas.create_text(px, py + 50, text="Таймер взрыва (10-100):", fill="#aaa", anchor=tk.W, font=("Arial", 9))
          draw_box(py + 75, "timer")
        elif c.get("type") == "light":
          colors = [("red", "#ff2222"), ("green", "#00aa22"), ("blue", "#2266ff")]
          for i, (col_id, col_hex) in enumerate(colors):
            self.canvas.create_rectangle(px + i * 50, py + 55, px + i * 50 + 40, py + 85, fill=col_hex, outline="#fff" if c.get("color", "red") == col_id else "#333", width=2 if c.get("color", "red") == col_id else 1)
          self.canvas.create_text(px, py + 105, text="Задержка включения:", fill="#aaa", anchor=tk.W, font=("Arial", 8))
          draw_box(py + 125, "delay")
        elif c.get("type") == "screen":
          mode_str = "Режим: 1: Длина сигнала" if c.get("mode", 1) == 1 else "Режим: 2: Логический (0/1)"
          self.canvas.create_rectangle(px, py + 65, px + 180, py + 95, fill="#252525", outline="#00ffcc")
          self.canvas.create_text(px + 90, py + 80, text=mode_str, fill="#00ffcc", font=("Arial", 8, "bold"))
        
        self.canvas.create_rectangle(px, py + 195, px + 210, py + 225, fill="#881111", outline="#ff4444", width=2)
        self.canvas.create_text(px + 105, py + 210, text="УДАЛИТЬ ЭЛЕМЕНТ", fill="#ffffff", font=("Impact", 10))

if __name__ == "__main__":
  root = tk.Tk()
  app = LogicSim(root)
  root.mainloop()