import os
import sys
import keyboard
import time
import threading

from memory import Memory
from datatypes import *
from classes import Instance

from style import *

APP_DATA = os.getenv("LOCALAPPDATA")

class Overlay(QWidget):
    def __init__(self, app):
        super().__init__()

        self.app = app

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.CustomizeWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        self.setStyleSheet("background-color: transparent;")

        self.dots = {}
    
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

        for owner, dot in self.dots.items():
            coords = dot()

            painter.setPen(pen_red)
            painter.drawLine(round(coords[0]), round(coords[1]), round(coords[2]), round(coords[3]))
            painter.setPen(pen_blue)
            painter.drawEllipse(round(coords[0] - radius), round(coords[1] - radius), radius * 2, radius * 2)
    
    def setDot(self, owner, dot):
        if len(self.dots) == 1 and next(iter(self.dots.items()))[0] == owner:
            self.dots = {}
            return False
        else:
            self.dots = { owner: dot }
            return True
    
    def addDot(self, owner, dot):
        if owner in self.dots:
            del self.dots[owner]
        else:
            self.dots[owner] = dot

class Application(QWidget):
    signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.name = "Pyrblx"
        self.version = 1.1

        self.running = False
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

        self.handle_offsets()
    
    def init_path(self):
        self.path = os.path.join(APP_DATA, "PYRBLX")
        os.makedirs(self.path, exist_ok=True)
    
    def init_ui(self):
        self.setWindowTitle(f"{self.name} v{self.version}")
        self.setGeometry(100, 100, 800, 400)
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

        middlelayout = QHBoxLayout()
        middlelayout.setSpacing(10)

        leftlayout = QVBoxLayout()
        leftlayout.setSpacing(8)
        
        self.status = QLabel("Status:               Waiting...")
        self.status.setFixedWidth(400 - 15)
        self.status.setStyleSheet("background-color: #2d2d2d; border-radius: 5px;")
        leftlayout.addWidget(self.status)

        self.dmlabel = QLabel("DataModel:        0x0")
        self.dmlabel.setFixedWidth(400 - 15)
        self.dmlabel.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px;")
        leftlayout.addWidget(self.dmlabel)
        
        self.velabel = QLabel("VisualEngine:     0x0")
        self.velabel.setFixedWidth(400 - 15)
        self.velabel.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px;")
        leftlayout.addWidget(self.velabel)

        middlelayout.addLayout(leftlayout)

        rightLayout = QVBoxLayout()
        rightLayout.setSpacing(4)

        self.searchbox = QLineEdit()
        self.searchbox.setPlaceholderText("Search for an instance here...")
        self.searchbox.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px;")
        rightLayout.addWidget(self.searchbox)

        dtscroll = QScrollArea(self)
        dtscroll.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 0px;")
        dtscroll.setWidgetResizable(True)

        dtwidget = QWidget()
        dtwidget.setStyleSheet("background-color: #2d2d2d;")

        self.dtframe = QVBoxLayout(dtwidget)
        self.dtframe.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.dtframe.setSpacing(5)

        dtscroll.setWidget(dtwidget)
        rightLayout.addWidget(dtscroll)

        vrscroll = QScrollArea(self)
        vrscroll.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 0px;")
        vrscroll.setWidgetResizable(True)

        vrwidget = QWidget()
        vrwidget.setStyleSheet("background-color: #2d2d2d;")

        self.vrframe = QVBoxLayout(vrwidget)
        self.vrframe.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.vrframe.setSpacing(5)

        vrscroll.setWidget(vrwidget)
        rightLayout.addWidget(vrscroll)

        middlelayout.addLayout(rightLayout)

        mainlayout.addLayout(middlelayout)

        self.filechoose = QPushButton("Choose offset file")

        self.filechoose.clicked.connect(self.choose_offsets)
        mainlayout.addWidget(self.filechoose)
        
        self.exitbtn = QPushButton("Start")
        self.exitbtn.clicked.connect(self.enable)
        self.exitbtn.setStyleSheet("background-color: #34d141; border: 1px solid #63ff70; color: white; font-weight: 600;")
        mainlayout.addWidget(self.exitbtn)

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
        if self.registered:
            keyboard.unhook_all_hotkeys()
        
        if self.overlay:
            self.overlay.maintimer.stop()
            self.overlay.close()
        
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

        self.exitbtn.setText("Exit")
        self.exitbtn.setStyleSheet("background-color: #d13438; border: 1px solid #b12a2e; color: white; font-weight: 600;")
        self.exitbtn.clicked.disconnect()
        self.exitbtn.clicked.connect(self.closeEvent)

        self.status.setText("Status:               Connecting...")
        self.status.setStyleSheet("color: #ffa500; background-color: #2d2d2d; border-radius: 5px;")

        self.filechoose.clicked.disconnect()
    
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

        if self.datamodel :
            if not self.initialized:
                self.onInit()
                self.initialized = True

            self.onStep()
        
    def onInit(self):
        self.instance_buttons = {}
        self.instance_buttons_rev = {}

        self.selected_instance = None
        self.selected_variables = {}
        self.base_variables = BASE_VARIABLES
        self.base_actions = BASE_ACTIONS

        self.current_searches = []
        
        def loadButton(obj, parent, strictchildren=None):
            objname = obj.get_name()
            objclass = obj.get_class()
            objchildren = strictchildren if strictchildren != None else obj.get_children()

            main_widget = QWidget()
            main_layout = QVBoxLayout(main_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            info_widget = QWidget()
            info_widget.setFixedWidth(400)
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
        
        def testSearch(text, obj):
            stext = text.lower().split(" ")
            cname = f"{obj.get_name().lower()} {obj.get_class().lower()} {obj.get_address()}"
            return any([part in cname for part in stext])
        
        def findSearch(parent, text, current=[]):
            pcount = parent.count()

            for c in range(pcount):
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

                    while cur and cur in self.instance_buttons_rev:
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
                        QApplication.processEvents()
                else:
                    childwidget.hide()
                    childcontainer.hide()
                    if childopen.text() == "▼": childopen.setText("►")
                
                findSearch(childcontainerlayout, text, current)
                QApplication.processEvents()
            
            return current
        
        def filterSearch(text):
            searchid = time.perf_counter_ns()
            self.current_searches.append(searchid)
            
            found = findSearch(self.dtframe, text, [])

            self.current_searches.remove(searchid)
            return found
        
        self.loadButton = loadButton
        self.showButton = showButton
        self.updateButton = updateButton

        self.updateVariable = updateVariable

        self.clearLayout = clearLayout

        self.searchbox.textChanged.connect(filterSearch)
        self.searchbox.returnPressed.connect(lambda : filterSearch(self.searchbox.text()))

        self.players = self.datamodel.get_service("Players")
        self.workspace = self.datamodel.get_service("Workspace")
        self.replicatedstorage = self.datamodel.get_service("ReplicatedStorage")

        loadButton(self.datamodel, self.dtframe, [self.players, self.workspace, self.replicatedstorage])

        self.workspace_prevchildren = get_descendants_fast(self.workspace)
        self.replicatedstorage_prevchildren = get_descendants_fast(self.replicatedstorage)
        self.players_prevchildren = get_descendants_fast(self.players)

    def onStep(self):
        self.players_prevchildren = self.updateButton(self.players, self.players_prevchildren)
        self.workspace_prevchildren = self.updateButton(self.workspace, self.workspace_prevchildren)
        self.replicatedstorage_prevchildren = self.updateButton(self.replicatedstorage, self.replicatedstorage_prevchildren)

        if self.selected_instance != None:
            if not self.selected_instance.get_parent():
                self.clearLayout(self.vrframe)
                self.selected_instance = None
                self.selected_variables = {}
            else:
                for methodname, varwidget in self.selected_variables.items():
                    self.updateVariable(methodname, varwidget)