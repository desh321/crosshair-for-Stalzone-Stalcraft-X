import sys
import os
import json
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpinBox
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
import keyboard
import win32gui
import win32con

CONFIG_FILE = "crosshair_config.json"

class KeyboardSignals(QObject):
    trigger_menu = pyqtSignal()
    trigger_quit = pyqtSignal()

class CrosshairOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        # Дефолтные настройки, если файла конфигурации нет
        self.offset_x = 0  
        self.offset_y = 0  
        self.crosshair_size = 48
        self.image_path = "crosshair.png"
        
        self.settings_window = None 
        self.game_hwnd = None 
        
        self.load_settings() # Загружаем сохраненные настройки
        self.init_ui()
        
    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Размер контейнера делаем чуть больше максимального размера прицела
        self.resize(256, 256)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setGeometry(0, 0, 256, 256)
        
        self.load_crosshair()
        self.update_position()
        
        # Настройка сигналов
        self.signals = KeyboardSignals()
        self.signals.trigger_menu.connect(self.toggle_settings_ui)
        self.signals.trigger_quit.connect(self.close_app)

        keyboard.add_hotkey('ctrl+alt+m', lambda: self.signals.trigger_menu.emit())
        keyboard.add_hotkey('ctrl+alt+q', lambda: self.signals.trigger_quit.emit())

        self.loop_timer = QTimer(self)
        self.loop_timer.timeout.connect(self.force_window_positions)
        self.loop_timer.start(20)

    def force_window_positions(self):
        hwnd = int(self.winId())
        if hwnd:
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )

    def load_crosshair(self):
        if os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            scaled_pixmap = pixmap.scaled(
                self.crosshair_size, 
                self.crosshair_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.label.setPixmap(scaled_pixmap)
        else:
            self.label.setPixmap(QPixmap()) # Очищаем картинку
            self.label.setText("•")
            self.label.setStyleSheet("color: #00FF00; font-size: 30px; font-weight: bold;")

    def update_position(self):
        screen = QApplication.primaryScreen().geometry()
        center_x = int((screen.width() - self.width()) / 2)
        center_y = int((screen.height() - self.height()) / 2)
        self.move(center_x + self.offset_x, center_y + self.offset_y)

    def load_settings(self):
        """Загрузка конфигурации из JSON файла"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.offset_x = data.get("offset_x", 0)
                    self.offset_y = data.get("offset_y", 0)
                    self.crosshair_size = data.get("crosshair_size", 48)
                    self.image_path = data.get("image_path", "crosshair.png")
            except Exception as e:
                print(f"Ошибка загрузки конфига: {e}")

    def save_settings(self):
        """Сохранение конфигурации в JSON файл"""
        data = {
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "crosshair_size": self.crosshair_size,
            "image_path": self.image_path
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")

    def toggle_settings_ui(self):
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.close()
            if self.game_hwnd:
                try:
                    win32gui.SetForegroundWindow(self.game_hwnd)
                except Exception:
                    pass
            return

        self.game_hwnd = win32gui.GetForegroundWindow()

        self.settings_window = QWidget()
        self.settings_window.setWindowTitle("Настройка прицела")
        self.settings_window.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.settings_window.resize(280, 200)
        
        layout = QVBoxLayout()
        
        # Смещение X
        layout_x = QHBoxLayout()
        label_x = QLabel("Смещение X:")
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-1000, 1000)
        self.spin_x.setValue(self.offset_x)
        self.spin_x.valueChanged.connect(self.on_config_changed)
        layout_x.addWidget(label_x)
        layout_x.addWidget(self.spin_x)
        
        # Смещение Y
        layout_y = QHBoxLayout()
        label_y = QLabel("Смещение Y:")
        self.spin_y = QSpinBox()
        self.spin_y.setRange(-1000, 1000)
        self.spin_y.setValue(self.offset_y)
        self.spin_y.valueChanged.connect(self.on_config_changed)
        layout_y.addWidget(label_y)
        layout_y.addWidget(self.spin_y)

        # Размер прицела
        layout_size = QHBoxLayout()
        label_size = QLabel("Размер (px):")
        self.spin_size = QSpinBox()
        self.spin_size.setRange(8, 256)
        self.spin_size.setValue(self.crosshair_size)
        self.spin_size.valueChanged.connect(self.on_config_changed)
        layout_size.addWidget(label_size)
        layout_size.addWidget(self.spin_size)
        
        # Кнопка выбора файла
        btn_select_file = QPushButton("Выбрать файл прицела")
        btn_select_file.clicked.connect(self.change_image)

        # Кнопка сброса в центр
        btn_reset = QPushButton("Сбросить в центр (0, 0)")
        btn_reset.clicked.connect(self.reset_to_center)
        
        layout.addLayout(layout_x)
        layout.addLayout(layout_y)
        layout.addLayout(layout_size)
        layout.addWidget(btn_select_file)
        layout.addWidget(btn_reset)
        
        self.settings_window.setLayout(layout)
        self.settings_window.show()
        self.settings_window.activateWindow()

    def on_config_changed(self):
        self.offset_x = self.spin_x.value()
        self.offset_y = self.spin_y.value()
        self.crosshair_size = self.spin_size.value()
        self.update_position()
        self.load_crosshair()
        self.save_settings() # Сохраняем при каждом изменении ползунков

    def reset_to_center(self):
        self.offset_x = 0
        self.offset_y = 0
        if hasattr(self, 'spin_x'): self.spin_x.setValue(0)
        if hasattr(self, 'spin_y'): self.spin_y.setValue(0)
        self.update_position()
        self.save_settings()

    def change_image(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Выберите прицел", "", "Images (*.png *.jpg *.bmp)")
        if file_path:
            self.image_path = file_path
            self.load_crosshair()
            self.save_settings() # Сохраняем новый путь к файлу

    def close_app(self):
        if self.settings_window:
            self.settings_window.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = CrosshairOverlay()
    overlay.show()
    sys.exit(app.exec())
