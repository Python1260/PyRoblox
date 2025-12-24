import os
import sys
import keyboard
import time
import threading

from memory import Memory
from style import *

APP_DATA = os.getenv("LOCALAPPDATA")

class Overlay(QWidget):
    def __init__(self, app):
        super().__init__()

        self.app = app

        self.maintimer = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.CustomizeWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        self.setStyleSheet("background-color: transparent;")

        self.sections = {}
    
    def init_timer(self):
        self.maintimer = QTimer()
        self.maintimer.timeout.connect(self.update)
        self.maintimer.start(round((1 / self.app.fps) * 1000))
    
    def run(self):
        self.init_timer()
        self.show()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        pen_red = QPen(Qt.red, 10, Qt.SolidLine)
        pen_blue = QPen(Qt.blue, 10, Qt.SolidLine)

        radius = 3

        for section, dots in self.sections.items():
            copydots = dots.copy()

            for owner, dot in copydots.items():
                coords = dot()
                if coords[0] < 0 or coords[1] < 0: continue

                painter.setPen(pen_red)
                painter.drawLine(round(coords[0]), round(coords[1]), round(coords[2]), round(coords[3]))
                painter.setPen(pen_blue)
                painter.drawEllipse(round(coords[0] - radius), round(coords[1] - radius), radius * 2, radius * 2)
        
        painter.end()
    
    def addSection(self):
        sectionid = len(self.sections)
        self.sections[sectionid] = {}

        return sectionid
    
    def setDot(self, sectionid, owner, dot):
        dots = self.sections[sectionid]

        prevowner = next(iter(dots.items()))[0] if len(dots) == 1 else None

        if len(dots) == 1 and prevowner == owner:
            self.sections[sectionid] = {}
            return None, prevowner
        else:
            self.sections[sectionid] = { owner: dot }
            return owner, prevowner
    
    def addDot(self, sectionid, owner, dot):
        dots = self.sections[sectionid]

        if owner in dots:
            del dots[owner]
        else:
            dots[owner] = dot
    
    def clear(self):
        self.sections.clear()

class Application(QWidget):
    signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.name = "Application"
        self.version = 1.0

        self.maintimer = None

        self.running = True
        self.enabled = False
        self.initialization = False
        self.initialization_finished = False
        self.timer = 0
        self.fps = 60

        self.attempts = 0
        self.retry = 0

        self.datamodel = None
        self.visualengine = None

        self.visible = True
        self.registered = False
        self.dragging = False
        self.position = None

        self.signal.connect(self.toggle)

        self.init_path()
        self.init_ui()
        self.init_hotkeys()

        self.overlay = Overlay(self)
        self.memory = Memory(self)
        self.overlay_section_part = self.overlay.addSection()
        self.overlay_section_esp = self.overlay.addSection()

        self.handle_offsets()
    
    def init_path(self):
        self.path = os.path.join(APP_DATA, "PYRBLX")
        os.makedirs(self.path, exist_ok=True)
    
    def init_ui(self):
        self.setWindowTitle(f"{self.name} v{self.version}")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
                font-size: 10pt;
            }
            QLabel {
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #505050;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
        """)

        mainlayout = QVBoxLayout()
        mainlayout.setSpacing(8)
        mainlayout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel(f"{self.name} v{self.version}")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #ffffff; font-weight: 600; margin-bottom: 10px;")
        mainlayout.addWidget(title)

        self.warning = QLabel("---")
        self.warning.setAlignment(Qt.AlignCenter)
        self.warning.setStyleSheet("color: #b0b0b0;")
        mainlayout.addWidget(self.warning)

        self.tabslayout = QTabWidget()
        self.tabslayout.setStyleSheet("""
            QTabWidget::pane {
                background: #222;
            }

            QTabBar::tab {
                background: #444;
                color: white;
                padding: 8px 15px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
                                 
            QTabBar::tab:selected {
                background: #666;
            }
                                 
            QTabBar::tab:hover {
                background: #555;
            }
        """)

        leftlayout = QVBoxLayout()
        leftlayout.setSpacing(8)
        leftwidget = QWidget()
        leftwidget.setLayout(leftlayout)
        
        self.status = QLabel("Status:               Waiting...")
        self.status.setStyleSheet("background-color: #2d2d2d; border-radius: 5px;")
        leftlayout.addWidget(self.status)

        self.dmlabel = QLabel("DataModel:        0x0")
        self.dmlabel.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px;")
        leftlayout.addWidget(self.dmlabel)
        
        self.velabel = QLabel("VisualEngine:     0x0")
        self.velabel.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px;")
        leftlayout.addWidget(self.velabel)

        self.tabslayout.addTab(leftwidget, "Main")

        mainlayout.addWidget(self.tabslayout)

        self.filechoose = QPushButton("Choose offset file (JSON)")

        self.filechoose.clicked.connect(self.choose_offsets)
        mainlayout.addWidget(self.filechoose)
        
        self.exitbtn = QPushButton("Start")
        self.exitbtn.clicked.connect(self.enable)
        self.exitbtn.setStyleSheet("background-color: #34d141; border: 1px solid #63ff70; color: white; font-weight: 600;")
        mainlayout.addWidget(self.exitbtn)

        self.messagelabel = QLabel("")
        self.messagelabel.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        mainlayout.addWidget(self.messagelabel)

        self.messagetexts = []
        self.messagetext_current = 0
        self.messagetext_delay = 0.5
        def message_set(msg, delay=0.5):
            self.messagetexts = msg
            self.messagetext_current = 0
            self.messagetext_delay = delay
        def message_update():
            while self.running:
                if len(self.messagetexts) != 0:
                    if self.messagetext_current > (len(self.messagetexts) - 1):
                        self.messagetext_current = 0

                    self.messagelabel.setText(self.messagetexts[self.messagetext_current])
                    self.messagetext_current += 1
                
                time.sleep(self.messagetext_delay)
        
        self.message_set = message_set
        self.message_update = message_update
        threading.Thread(target=self.message_update).start()

        self.message_set(["✦ Welcome", "✧ Welcome"])

        self.setLayout(mainlayout)
    
    def init_timer(self):
        self.maintimer = QTimer()
        self.maintimer.timeout.connect(self.update)
        self.maintimer.start(round((1 / self.fps) * 1000))
    
    def init_hotkeys(self):
        if not self.registered:
            keyboard.add_hotkey('tab', self.toggle_safe)

            self.registered = True
    
    def toggle(self):
        self.visible = not self.visible

        if self.visible:
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self.hide()
    
    def toggle_safe(self):
        self.signal.emit()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.position = event.globalPos() - self.frameGeometry().topLeft()

            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.position)

            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

            event.accept()
    
    def closeEvent(self, event):
        self.running = False
        self.enabled = False

        self.initialization = False
        self.initialization_finished = False

        self.attempts = 0
        self.retry = 0

        self.datamodel = None
        self.visualengine = None

        if self.registered:
            keyboard.unhook_all_hotkeys()
        
        if self.overlay:
            self.overlay.maintimer.stop()
            self.overlay.close()
        
        if self.memory:
            self.memory.close()
        
        self.maintimer.stop()
        QApplication.quit()

        if event:
            event.accept()
        
        sys.exit()
    
    def choose_offsets(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select a file",
            "",
            "JSON Files (*.json)"
        )

        if file:
            try:
                self.memory.offsets = {}
                self.memory.load_offsets(file)
                self.handle_offsets()
                self.filechoose.setText(f"Offset file: {os.path.basename(file)}")
            except Exception as e:
                self.filechoose.setText("Please choose a valid .json file!")
    
    def handle_offsets(self):
        if self.memory.process_find() != None:
            path = self.memory.process_find_path()

            if path:
                if "RobloxVersion" in self.memory.offsets:
                    version = os.path.basename(os.path.dirname(path))

                    if not version in self.memory.offsets["RobloxVersion"]:
                        self.warning.setText("WARNING: OFFSET AND ROBLOX VERSIONS DO NOT MATCH!")
                        self.warning.setStyleSheet("color: #b74b4b;")
                    else:
                        self.warning.setText("You are up to date!")
                        self.warning.setStyleSheet("color: #b0b0b0;")
                else:
                    self.warning.setText("WARNING: OFFSET VERSION NOT FOUND!")
                    self.warning.setStyleSheet("color: #b74b4b;")
            else:
                self.warning.setText("---")
                self.warning.setStyleSheet("color: #b0b0b0;")
        else:
            self.warning.setText("---")
            self.warning.setStyleSheet("color: #b0b0b0;")
    
    def enable_worker(self):
        self.exitbtn.setText("Stop")
        self.exitbtn.setStyleSheet("background-color: #d13438; border: 1px solid #b12a2e; color: white; font-weight: 600;")
        self.exitbtn.clicked.disconnect()
        self.exitbtn.clicked.connect(self.disable)

        self.status.setText("Status:               Connecting...")
        self.status.setStyleSheet("color: #ffa500; background-color: #2d2d2d; border-radius: 5px;")

        hide = QGraphicsOpacityEffect()
        hide.setOpacity(0)
        self.filechoose.setDisabled(True)
        self.filechoose.setGraphicsEffect(hide)
    
    def enable(self):
        if self.enabled: return

        self.message_set(["Loading", "▹ Loading", "▹▹ Loading..", "▹▹▻ Loading..."], 0.25)

        self.enabled = True

        self.enable_worker()
    
    def disable_worker(self):
        self.initialization = False
        self.initialization_finished = False

        self.attempts = 0
        self.retry = 0

        self.datamodel = None
        self.visualengine = None

        if self.overlay:
            self.overlay.clear()

        if self.memory:
            self.memory.close()
        self.memory = Memory(self)

        self.overlay_section_part = self.overlay.addSection()
        self.overlay_section_esp = self.overlay.addSection()

        self.exitbtn.setText("Start")
        self.exitbtn.clicked.disconnect()
        self.exitbtn.clicked.connect(self.enable)
        self.exitbtn.setStyleSheet("background-color: #34d141; border: 1px solid #63ff70; color: white; font-weight: 600;")

        self.status.setText("Status:               Waiting...")
        self.status.setStyleSheet("color: #ffffff; background-color: #2d2d2d; border-radius: 5px;")

        self.dmlabel.setText("DataModel:        0x0")
        self.velabel.setText("VisualEngine:     0x0")

        show = QGraphicsOpacityEffect()
        show.setOpacity(1)
        self.filechoose.setDisabled(False)
        self.filechoose.setGraphicsEffect(show)
    
    def disable(self):
        if not self.enabled: return

        self.message_set(["Loading", "▹ Loading", "▹▹ Loading..", "▹▹▻ Loading..."], 0.25)

        self.enabled = False

        self.disable_worker()

        self.message_set(["▣ Stopped"])
    
    def run(self):
        self.init_timer()
        self.show()
        self.overlay.run()
    
    def connect(self):
        if self.memory.process_attach():
            self.status.setText("Status:               Connected")
            self.status.setStyleSheet("color: #00ff00; background-color: #2d2d2d; border-radius: 5px;")
            return True
        else:
            return False
    
    def update(self):
        if not self.enabled: return

        if not self.memory.process_is_open():
            self.retry += 1

            if self.retry >= self.fps:
                self.retry = 0
                self.attempts += 1

                self.status.setText(f"Status:               Connecting... (attempt {self.attempts})")
                self.status.setStyleSheet("color: #ffa500; background-color: #2d2d2d; border-radius: 5px;")

                if self.connect():
                    self.attempts = 0
                elif self.attempts >= 10:
                    self.status.setText("Status:               Connection failed")
                    self.status.setStyleSheet("color: #ff4444; background-color: #2d2d2d; border-radius: 5px;")

                    self.message_set(["✖ Failed"])
            return
        
        self.datamodel = self.memory.get_datamodel()
        self.visualengine = self.memory.get_visualengine()

        self.dmlabel.setText(f"DataModel:        0x{self.datamodel.address:X}    {"" if self.datamodel else "(NOT FOUND)"}")
        self.velabel.setText(f"VisualEngine:     0x{self.visualengine.address:X}    {"" if self.visualengine else "(NOT FOUND)"}")

        if self.datamodel and self.visualengine:
            try:
                if not self.initialization:
                    self.initialization = True
                    self.message_set(["›  Running", "➤ Running"])
                
                if self.initialization and not self.initialization_finished:
                    self.onInit()
                else:
                    self.onStep()
            except Exception as e:
                raise e
                self.disable()
        
    def onInit(self):
        self.initialization_finished = True

    def onStep(self):
        pass