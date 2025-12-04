import os
import sys
import keyboard
import time
import threading

from memory import Memory
from datatypes import *
from classes import Instance, BasePart

from style import *

APP_DATA = os.getenv("LOCALAPPDATA")

def clearLayout(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        else:
            sub_layout = item.layout()
            if sub_layout is not None:
                clearLayout(sub_layout)

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

class Application(QWidget):
    signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.name = "Pyrblx"
        self.version = 1.1

        self.maintimer = None

        self.running = True
        self.enabled = False
        self.initialized = False
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

        tabslayout = QTabWidget()
        tabslayout.setStyleSheet("""
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

        tabslayout.addTab(leftwidget, "Main")

        rightlayout = QVBoxLayout()
        rightlayout.setSpacing(4)
        rightwidget = QWidget()
        rightwidget.setLayout(rightlayout)

        self.searchbox = QLineEdit()
        self.searchbox.setPlaceholderText("Search for an instance here...")
        self.searchbox.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        rightlayout.addWidget(self.searchbox)

        dtscroll = QScrollArea(self)
        dtscroll.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 0px;")
        dtscroll.setWidgetResizable(True)

        dtwidget = QWidget()
        dtwidget.setStyleSheet("background-color: #2d2d2d;")

        self.dtframe = QVBoxLayout(dtwidget)
        self.dtframe.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.dtframe.setSpacing(5)

        dtscroll.setWidget(dtwidget)
        rightlayout.addWidget(dtscroll)

        vrscroll = QScrollArea(self)
        vrscroll.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 0px;")
        vrscroll.setWidgetResizable(True)

        vrwidget = QWidget()
        vrwidget.setStyleSheet("background-color: #2d2d2d;")

        self.vrframe = QVBoxLayout(vrwidget)
        self.vrframe.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.vrframe.setSpacing(5)

        vrscroll.setWidget(vrwidget)
        rightlayout.addWidget(vrscroll)

        tabslayout.addTab(rightwidget, "Instances")

        toplayout = QVBoxLayout()
        topwidget = QWidget()
        topwidget.setLayout(toplayout)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.executebox = QLineEdit()
        self.executebox.setPlaceholderText("Code to execute…")
        self.executebox.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")

        self.executebutton = QPushButton("Run")
        self.executebutton.setStyleSheet("color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px;")

        row.addWidget(self.executebox)
        row.addWidget(self.executebutton)

        toplayout.addLayout(row)

        self.executeresult = QTextEdit("> Pyrblx is running...")
        self.executeresult.setReadOnly(True)
        self.executeresult.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.executeresult.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        toplayout.addWidget(self.executeresult)

        tabslayout.addTab(topwidget, "Execute")

        downlayout = QVBoxLayout()
        downwidget = QWidget()
        downwidget.setLayout(downlayout)

        esplayout = QHBoxLayout()
        espwidget = QWidget()
        espwidget.setLayout(esplayout)
        self.espbox = QCheckBox("Enable ESP")
        esplayout.addWidget(self.espbox)
        downlayout.addWidget(espwidget)

        flylayout = QHBoxLayout()
        flywidget = QWidget()
        flywidget.setLayout(flylayout)
        self.flybox = QCheckBox("Enable FLY")
        flylayout.addWidget(self.flybox)
        downlayout.addWidget(flywidget)

        spdlayout = QHBoxLayout()
        spdwidget = QWidget()
        spdwidget.setLayout(spdlayout)
        spdlabel = QLabel("Player WalkSpeed: ")
        self.spdtextbox = QLineEdit("16")
        self.spdtextbox.setValidator(QIntValidator(bottom=0))
        self.spdtextbox.setPlaceholderText("Input value here")
        self.spdtextbox.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.spdbutton = QPushButton("Ok")
        self.spdbutton.setStyleSheet("color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px;")
        spdlayout.addWidget(spdlabel)
        spdlayout.addWidget(self.spdtextbox)
        spdlayout.addWidget(self.spdbutton)
        downlayout.addWidget(spdwidget)

        jumplayout = QHBoxLayout()
        jumpwidget = QWidget()
        jumpwidget.setLayout(jumplayout)
        jumplabel = QLabel("Player JumpPower: ")
        self.jumptextbox = QLineEdit("50")
        self.jumptextbox.setValidator(QIntValidator(bottom=0))
        self.jumptextbox.setPlaceholderText("Input value here")
        self.jumptextbox.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.jumpbutton = QPushButton("Ok")
        self.jumpbutton.setStyleSheet("color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px;")
        jumplayout.addWidget(jumplabel)
        jumplayout.addWidget(self.jumptextbox)
        jumplayout.addWidget(self.jumpbutton)
        downlayout.addWidget(jumpwidget)

        teleportlayout = QHBoxLayout()
        teleportwidget = QWidget()
        teleportwidget.setLayout(teleportlayout)
        teleportlabel = QLabel("Teleport to position: ")
        self.teleporttextboxX = QLineEdit("0")
        self.teleporttextboxX.setValidator(QIntValidator())
        self.teleporttextboxX.setPlaceholderText("X")
        self.teleporttextboxX.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.teleporttextboxY = QLineEdit("0")
        self.teleporttextboxY.setValidator(QIntValidator())
        self.teleporttextboxY.setPlaceholderText("Y")
        self.teleporttextboxY.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.teleporttextboxZ = QLineEdit("0")
        self.teleporttextboxZ.setValidator(QIntValidator())
        self.teleporttextboxZ.setPlaceholderText("Z")
        self.teleporttextboxZ.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.teleportbutton = QPushButton("Go")
        self.teleportbutton.setStyleSheet("color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px;")
        teleportlayout.addWidget(teleportlabel)
        teleportlayout.addWidget(self.teleporttextboxX)
        teleportlayout.addWidget(self.teleporttextboxY)
        teleportlayout.addWidget(self.teleporttextboxZ)
        teleportlayout.addWidget(self.teleportbutton)
        downlayout.addWidget(teleportwidget)

        teleportplayerlayout = QHBoxLayout()
        teleportplayerwidget = QWidget()
        teleportplayerwidget.setLayout(teleportplayerlayout)
        teleportplayerlabel = QLabel("Teleport to player:    ")
        self.teleportplayertextbox = QLineEdit("")
        self.teleportplayertextbox.setPlaceholderText("Player name")
        self.teleportplayertextbox.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        self.teleportplayerbutton = QPushButton("Go")
        self.teleportplayerbutton.setStyleSheet("color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px;")
        teleportplayerlayout.addWidget(teleportplayerlabel)
        teleportplayerlayout.addWidget(self.teleportplayertextbox)
        teleportplayerlayout.addWidget(self.teleportplayerbutton)
        downlayout.addWidget(teleportplayerwidget)

        nocliplayout = QHBoxLayout()
        noclipwidget = QWidget()
        noclipwidget.setLayout(nocliplayout)
        self.noclipbutton = QPushButton("Disable collision")
        nocliplayout.addWidget(self.noclipbutton)
        downlayout.addWidget(noclipwidget)

        invislayout = QHBoxLayout()
        inviswidget = QWidget()
        inviswidget.setLayout(invislayout)
        self.invisbutton = QPushButton("Disable visibility")
        invislayout.addWidget(self.invisbutton)
        downlayout.addWidget(inviswidget)

        tabslayout.addTab(downwidget, "Utilities")

        mainlayout.addWidget(tabslayout)

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
        thread = threading.Thread(target=self.message_update)
        thread.start()

        self.message_set(["✦ Welcome", "✧ Welcome"])

        self.setLayout(mainlayout)
    
    def init_timer(self):
        self.maintimer = QTimer()
        self.maintimer.timeout.connect(self.update)
        self.maintimer.start(round((1 / self.fps) * 1000))
    
    def init_hotkeys(self):
        if not self.registered:
            def history_up():
                if hasattr(self, "execute_history") and len(self.execute_history) > 0:
                    self.executebox.setText(self.execute_history[self.execute_history_current])
                    self.execute_history_current = min(self.execute_history_current + 1, len(self.execute_history) - 1)
            def history_down():
                if hasattr(self, "execute_history") and len(self.execute_history) > 0:
                    self.executebox.setText(self.execute_history[self.execute_history_current])
                    self.execute_history_current = max(self.execute_history_current - 1, 0)

            keyboard.add_hotkey('tab', self.toggle_safe)
            keyboard.add_hotkey('up', history_up)
            keyboard.add_hotkey('down', history_down)

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

        self.initialized = False

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
                self.memory.load_offsets(file)
                self.handle_offsets()
                self.filechoose.setText(f"Offset file: {os.path.basename(file)}")
            except Exception as e:
                self.filechoose.setText("Please choose a valid .json file!")
    
    def handle_offsets(self):
        if self.memory.process_find() == None: return

        if "RobloxVersion" in self.memory.offsets:
            version = os.path.basename(os.path.dirname(self.memory.process_find_path()))

            if not version in self.memory.offsets["RobloxVersion"]:
                self.warning.setText("WARNING: OFFSET AND ROBLOX VERSIONS DO NOT MATCH!")
                self.warning.setStyleSheet("color: #b74b4b;")
            else:
                self.warning.setText("You are up to date!")
                self.warning.setStyleSheet("color: #b0b0b0;")
        else:
            self.warning.setText("WARNING: OFFSET VERSION NOT FOUND!")
            self.warning.setStyleSheet("color: #b74b4b;")
    
    def enable(self):
        self.enabled = True

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

        self.message_set(["Loading", "▹ Loading", "▹▹ Loading..", "▹▹▻ Loading..."], 0.25)
    
    def disable(self):
        self.message_set(["Loading", "▹ Loading", "▹▹ Loading..", "▹▹▻ Loading..."], 0.25)

        self.enabled = False

        self.initialized = False

        self.attempts = 0
        self.retry = 0

        self.datamodel = None
        self.visualengine = None

        if self.overlay:
            if self.overlay.maintimer: self.overlay.maintimer.stop()
            self.overlay.close()
        self.overlay = Overlay(self)
        self.overlay.run()

        if self.memory:
            self.memory.close()
        self.memory = Memory(self)

        self.overlay_section_part = self.overlay.addSection()
        self.overlay_section_esp = self.overlay.addSection()

        try:
            self.searchbox.textChanged.disconnect()
            self.searchbox.returnPressed.disconnect()
        except Exception:
            pass
        try:
            self.executebox.textChanged.disconnect()
            self.executebox.returnPressed.disconnect()
        except Exception:
            pass
        try:
            self.executebutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.spdtextbox.returnPressed.disconnect()
            self.spdbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.jumptextbox.returnPressed.disconnect()
            self.jumpbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.teleportbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.teleportplayerbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.noclipbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.invisbutton.clicked.disconnect()
        except Exception:
            pass

        self.exitbtn.setText("Start")
        self.exitbtn.clicked.disconnect()
        self.exitbtn.clicked.connect(self.enable)
        self.exitbtn.setStyleSheet("background-color: #34d141; border: 1px solid #63ff70; color: white; font-weight: 600;")

        self.status.setText("Status:               Waiting...")
        self.status.setStyleSheet("color: #ffffff; background-color: #2d2d2d; border-radius: 5px;")

        self.dmlabel.setText("DataModel:        0x0")
        self.velabel.setText("VisualEngine:     0x0")

        clearLayout(self.vrframe)
        clearLayout(self.dtframe)

        show = QGraphicsOpacityEffect()
        show.setOpacity(1)
        self.filechoose.setDisabled(False)
        self.filechoose.setGraphicsEffect(show)

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
            return
        
        self.datamodel = self.memory.get_datamodel()
        self.visualengine = self.memory.get_visualengine()

        self.dmlabel.setText(f"DataModel:        0x{self.datamodel.address:X}    {"" if self.datamodel else "(NOT FOUND)"}")
        self.velabel.setText(f"VisualEngine:     0x{self.visualengine.address:X}    {"" if self.visualengine else "(NOT FOUND)"}")

        if self.datamodel and self.visualengine:
            try:
                if not self.initialized:
                    self.initialized = True
                    self.message_set(["›  Running", "➤ Running"])
                    self.onInit()

                self.onStep()
            except Exception as e:
                self.disable()
        
    def onInit(self):
        self.instance_buttons = {}
        self.instance_buttons_rev = {}

        self.selected_instance = None
        self.selected_variables = {}
        self.base_variables = BASE_VARIABLES
        self.base_actions = BASE_ACTIONS

        self.searches_current = []
        self.searches_closedbuttons = []
        
        def loadButton(obj, parent, strictchildren=None):
            objname = obj.get_name()
            objclass = obj.get_class()
            objchildren = strictchildren if strictchildren != None else obj.get_children()

            main_widget = QWidget()
            main_layout = QVBoxLayout(main_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            info_widget = QWidget()
            info_layout = QHBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(0)

            name = QPushButton()
            name.setText(f"{objname} ({objclass})    LOADING...")
            name.setStyleSheet("color: #FFB74D; background-color: #2d2d2d; border-radius: 3px; padding: 5px; text-align: left;")
            info_layout.addWidget(name)

            name.clicked.connect(lambda : selectVariable(obj))

            container_widget = QWidget()
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(32, 0, 0, 0)
            container_layout.setSpacing(0)

            button = None

            if len(objchildren) > 0:
                button = QPushButton(f"►")
                button.setFixedWidth(32)
                button.setStyleSheet("color: #c0c0c0; background-color: #3d3d3d; border-color: #c0c0c0; border-radius: 3px; padding: 5px; text-align: left;")
                info_layout.insertWidget(0, button)

                button.clicked.connect(lambda : showButton(button, container_widget, "►" in button.text()))
                showButton(button, container_widget, False)
            else:
                info_widget.setContentsMargins(32, 0, 0, 0)

            main_layout.addWidget(info_widget)
            main_layout.addWidget(container_widget)

            parent.addWidget(main_widget)

            self.instance_buttons[obj] = main_widget
            self.instance_buttons_rev[main_widget] = obj

            for idx, child in enumerate(objchildren):
                name.setText(f"{objname} ({objclass})    LOADING {(idx + 1)}/{len(objchildren)}")
                loadButton(child, container_layout)
                QApplication.processEvents()
            
            name.setText(f"{objname} ({objclass})")
            name.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px; padding: 5px; text-align: left;")

            if not testSearch(self.searchbox.text(), obj):
                main_widget.hide()
                container_widget.hide()
                if button and button.text() == "▼": button.setText("►")
                
            return main_widget
        
        def deleteButton(obj):
            if obj in self.instance_buttons:
                button = self.instance_buttons[obj]
                
                if not sip.isdeleted(button):
                    button.deleteLater()

                del self.instance_buttons[obj]
                del self.instance_buttons_rev[button]
        
        def updateButton(obj, prev_list):
            objdescendants = get_descendants_fast(obj)

            for child in objdescendants:
                if not child in prev_list:
                    childparent = child.get_parent()

                    if childparent in self.instance_buttons:
                        parentbutton = self.instance_buttons[childparent]

                        if not sip.isdeleted(parentbutton):
                            parentbuttonlayout = parentbutton.layout()
                            parentcontainer = parentbuttonlayout.itemAt(1).widget()
                            parentcontainerlayout = parentcontainer.layout()
                            
                            loadButton(child, parentcontainerlayout)
                else:
                    if child in self.instance_buttons:
                        childbutton = self.instance_buttons[child]

                        if not sip.isdeleted(childbutton):
                            childbuttonlayout = childbutton.layout()
                            childinfo = childbuttonlayout.itemAt(0).widget()
                            childinfolayout = childinfo.layout()
                            childname = childinfolayout.itemAt(childinfolayout.count() - 1).widget()
                            
                            childname.setText(f"{child.get_name()} ({child.get_class()})")

                QApplication.processEvents()
            
            for child in prev_list:
                if not child in objdescendants:
                    deleteButton(child)
                QApplication.processEvents()

            return objdescendants
        
        def showButton(button, container, visible):
            if isinstance(button, QPushButton):
                if visible:
                    button.setText("▼")
                    container.show()
                else:
                    button.setText("►")
                    container.hide()
            else:
                if visible:
                    button.show()
                    container.show()
                else:
                    button.hide()
                    container.hide()
            
            if not visible:
                parentwidget = button.parent().parent()
                self.searches_closedbuttons.append(parentwidget)
        
        def selectVariable(obj):
            self.selected_instance = obj

            objname = obj.get_name
            objclass = obj.get_class
            objaddress = obj.get_address
            objparent = obj.get_parent

            classvalue = objclass()

            clearLayout(self.vrframe)
            self.selected_variables = {}

            self.selected_variables["get_name"] = loadVariable("Name: ", objname)
            self.selected_variables["get_class"] = loadVariable("Class: ", objclass)
            self.selected_variables["get_address"] = loadVariable("Address: ", objaddress)
            self.selected_variables["get_parent"] = loadVariable("Parent: ", objparent)

            if classvalue in self.base_actions:
                classaction = self.base_actions[classvalue]
                classaction(self, obj)

            if classvalue in self.base_variables:
                classvars = self.base_variables[classvalue]

                for varname, methodname in classvars.items():
                    self.selected_variables[methodname] = loadVariable(f"{varname}: ", getattr(obj, methodname))

        def loadVariable(varname, varvalue):
            result = varvalue()

            main_widget = QWidget()
            main_layout = QHBoxLayout(main_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            name = QLabel(varname)
            name.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px; padding: 5px; text-align: left;")
            
            main_layout.addWidget(name, 0)

            button = QPushButton(str(result))
            button.setStyleSheet("color: #c0c0c0; background-color: #3d3d3d; border-color: #c0c0c0; border-radius: 3px; padding: 5px; text-align: left;")
            main_layout.addWidget(button, 0)

            if isinstance(result, Instance):
                button.clicked.connect(lambda : selectVariable(varvalue()))
            elif isinstance(result, str):
                button.clicked.connect(lambda : QApplication.clipboard().setText(varvalue()))
            elif isinstance(result, bytes):
                button.clicked.connect(lambda : QApplication.clipboard().setText(str(varvalue())))

            main_layout.addStretch()
            self.vrframe.addWidget(main_widget)

            return main_widget
        
        def updateVariable(mname, mwidget):
            value = getattr(self.selected_instance, mname)()

            mlayout = mwidget.layout()
            mbutton = mlayout.itemAt(1).widget()

            mbutton.setText(str(value))
        
        def get_descendants_fast(obj):
            descendants = []

            objchildren = obj.get_children()

            for child in objchildren:
                descendants.append(child)
                descendants += get_descendants_fast(child)
                QApplication.processEvents()

            return descendants
        
        def testSearch(text, obj):
            stext = text.lower().split(" ")
            cname = f"{obj.get_name().lower()} {obj.get_class().lower()} {obj.get_address()}"
            return text == "" or any([part in cname for part in stext])
        
        def findSearch(parent, text, current=[], sid= -1):
            pcount = parent.count()

            for c in range(pcount):
                if (len(self.searches_current) and min(self.searches_current) == sid) > 1 or not self.enabled:
                    break

                childwidget = parent.itemAt(c).widget()
                childlayout = childwidget.layout()
                childinfo = childlayout.itemAt(0).widget()
                childinfolayout = childinfo.layout()
                childname = childinfolayout.itemAt(childinfolayout.count() - 1).widget()
                childopen = childinfolayout.itemAt(0).widget()
                childcontainer = childlayout.itemAt(1).widget()
                childcontainerlayout = childcontainer.layout()

                obj = self.instance_buttons_rev[childwidget]

                if text == "" or testSearch(text, obj):
                    cur = childwidget
                    parented = False

                    while cur and cur in self.instance_buttons_rev and (not cur in self.searches_closedbuttons) and (not sip.isdeleted(cur)):
                        curlayout = cur.layout()
                        curinfo = curlayout.itemAt(0).widget()
                        curinfolayout = curinfo.layout()
                        curopen = curinfolayout.itemAt(0).widget()
                        curcontainer = curlayout.itemAt(1).widget()

                        if not (parented and "►" in curopen.text() and text == ""):
                            cur.show()
                            curcontainer.show()
                            if curopen.text() == "►": curopen.setText("▼")

                        cur = cur.parent().parent()
                        parented = True
                else:
                    childwidget.hide()
                    childcontainer.hide()
                    if childopen.text() == "▼": childopen.setText("►")
                
                findSearch(childcontainerlayout, text, current, sid=sid)
            
            return current
        
        def filterSearch(text):
            def search():
                searchid = time.perf_counter_ns()
                self.searches_current.append(searchid)
                self.searches_closedbuttons = []

                findSearch(self.dtframe, text, [], sid=searchid)

                self.searches_current.remove(searchid)
            
            thread = threading.Thread(target=search)
            thread.start()
        
        self.execute_globals = { "game": self.datamodel, "Vector3": Vector3, "Vector2": Vector2, "CFrame": CFrame }
        self.execute_locals = {}

        self.execute_history = []
        self.execute_history_current = 0
        
        def executeCode(text):
            if text == "": return

            self.execute_history = self.execute_history[self.execute_history_current:len(self.execute_history)]
            self.execute_history.insert(0, text)
            self.execute_history_current = 0

            try:
                value = str(eval(text, self.execute_globals, self.execute_locals))
            except Exception:
                try:
                    value = str(exec(text, self.execute_globals, self.execute_locals))
                except Exception as error:
                    value = str(error)

            self.executebox.setText("")
            self.executeresult.setText(f"> {value}\n{self.executeresult.toPlainText()}")
            return value
        
        def updateEspDots():
            try:
                while self.enabled:
                    if self.espbox.isChecked():
                        localplayer = self.players.get_localplayer()
                        if not localplayer: continue
                        playerchildren = self.players.get_children()
                        espdots = self.overlay.sections[self.overlay_section_esp].copy()

                        for owner, dot in espdots.items():
                            if not owner in playerchildren:
                                self.overlay.addDot(self.overlay_section_esp, owner, False)

                        for child in playerchildren:
                            if child == localplayer: continue

                            if not child in espdots:
                                character = child.get_character()
                                if not character: continue
                                root = character.find_first_child("HumanoidRootPart")
                                if not root: continue

                                self.overlay.addDot(self.overlay_section_esp, child, lambda r=root: getCFrame(self, r))
                    else:
                        self.overlay.sections[self.overlay_section_esp] = {}

                    time.sleep(0)
            except:
                self.overlay.sections[self.overlay_section_esp] = {}
        
        def updateFlyVelocity():
            try:
                while self.enabled:
                    if self.flybox.isChecked():
                        localplayer = self.players.get_localplayer()
                        if not localplayer: continue
                        character = localplayer.get_character()
                        if not character: continue
                        root = character.find_first_child("HumanoidRootPart")
                        if not root: continue

                        vel = Vector3(0.0, 500.0, 0.0)
                        root.set_velocity(vel)
                    
                    time.sleep(0)
            except:
                pass
        
        def updateSpdWalkSpeed(text):
            if text == "": return

            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return
                humanoid = character.find_first_child("Humanoid")
                if not humanoid: return

                humanoid.set_walkspeed(float(text))
            except:
                pass
        
        def updateJumpJumpPower(text):
            if text == "": return

            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return
                humanoid = character.find_first_child("Humanoid")
                if not humanoid: return

                humanoid.set_jumppower(float(text))
            except:
                pass
        
        def updateTeleportPosition(tx, ty, tz):
            if tx == "" or ty == "" or tz == "": return

            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return
                root = character.find_first_child("HumanoidRootPart")
                if not root: return

                newpos = Vector3(float(tx), float(ty), float(tz))
                newcframe = CFrame(newpos)
                newvel = Vector3(0.0, 0.0, 0.0)

                for i in range(self.fps):
                    root.set_cframe(newcframe)
                    root.set_position(newpos)
                    root.set_velocity(newvel)
                    time.sleep(0)
            except:
                pass
        
        def updateTeleportplayerPosition(tname):
            if tname == "": return

            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return
                root = character.find_first_child("HumanoidRootPart")
                if not root: return

                tplayer = self.players.find_first_child(tname)
                if not tplayer: return
                tcharacter = tplayer.get_character()
                if not tcharacter: return
                troot = tcharacter.find_first_child("HumanoidRootPart")
                if not troot: return

                newpos = troot.get_position()
                newcframe = CFrame(newpos)
                newvel = Vector3(0.0, 0.0, 0.0)

                for i in range(self.fps):
                    root.set_cframe(newcframe)
                    root.set_position(newpos)
                    root.set_velocity(newvel)
                    time.sleep(0)
            except:
                pass
        
        def updateNoclipCollision():
            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return

                for child in character.get_descendants():
                    if isinstance(child, BasePart):
                        child.set_cancollide(False)
            except:
                pass
        
        def updateInvisTransparency():
            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return

                for child in character.get_descendants():
                    if isinstance(child, BasePart):
                        child.set_transparency(1.0)
            except:
                pass
        
        self.loadButton = loadButton
        self.showButton = showButton
        self.updateButton = updateButton

        self.updateVariable = updateVariable

        self.searchbox.textChanged.connect(filterSearch)
        self.searchbox.returnPressed.connect(lambda : filterSearch(self.searchbox.text()))

        self.executebox.returnPressed.connect(lambda : executeCode(self.executebox.text()))
        self.executebutton.clicked.connect(lambda : executeCode(self.executebox.text()))

        self.spdtextbox.returnPressed.connect(lambda : updateSpdWalkSpeed(self.spdtextbox.text()))
        self.spdbutton.clicked.connect(lambda : updateSpdWalkSpeed(self.spdtextbox.text()))
        self.jumptextbox.returnPressed.connect(lambda : updateJumpJumpPower(self.jumptextbox.text()))
        self.jumpbutton.clicked.connect(lambda : updateJumpJumpPower(self.jumptextbox.text()))
        self.teleportbutton.clicked.connect(lambda : updateTeleportPosition(self.teleporttextboxX.text(), self.teleporttextboxY.text(), self.teleporttextboxZ.text()))
        self.teleportplayerbutton.clicked.connect(lambda : updateTeleportplayerPosition(self.teleportplayertextbox.text()))
        self.noclipbutton.clicked.connect(updateNoclipCollision)
        self.invisbutton.clicked.connect(updateInvisTransparency)

        self.players = self.datamodel.get_service("Players")
        self.workspace = self.datamodel.get_service("Workspace")
        self.replicatedstorage = self.datamodel.get_service("ReplicatedStorage")

        espdotsthread = threading.Thread(target=updateEspDots)
        espdotsthread.start()
        flyvelocitythread = threading.Thread(target=updateFlyVelocity)
        flyvelocitythread.start()

        loadButton(self.datamodel, self.dtframe, [self.datamodel.get_service("Stats"), self.players, self.workspace, self.replicatedstorage])

        self.workspace_prevchildren = get_descendants_fast(self.workspace)
        self.replicatedstorage_prevchildren = get_descendants_fast(self.replicatedstorage)
        self.players_prevchildren = get_descendants_fast(self.players)

    def onStep(self):
        self.players_prevchildren = self.updateButton(self.players, self.players_prevchildren)
        self.workspace_prevchildren = self.updateButton(self.workspace, self.workspace_prevchildren)
        self.replicatedstorage_prevchildren = self.updateButton(self.replicatedstorage, self.replicatedstorage_prevchildren)

        if self.selected_instance != None:
            if not self.selected_instance.get_parent():
                clearLayout(self.vrframe)
                self.selected_instance = None
                self.selected_variables = {}
            else:
                for methodname, varwidget in self.selected_variables.items():
                    self.updateVariable(methodname, varwidget)