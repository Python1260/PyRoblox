import os
import sys

PACKAGES = [
    "pymem==1.13.0",
    "psutil==5.9.6",
    "keyboard==0.13.5",
    "mouse==0.7.1",
    "PyQt5==5.15.10",
    "pyautogui==0.9.54",
    "xxhash==3.6.0",
    "zstandard==0.25.0",
    "sip==6.13.1",
    "dirtyjson==1.0.8",
    "websockets==15.0.1"
]

environment = os.path.dirname(os.path.abspath(__file__))

os.chdir(environment)
os.system(f"pip install {' '.join(pckg for pckg in PACKAGES)}")

from app import *
from classes import Instance, BasePart
from datatypes import *

from Luau.compiler import Compiler
from Luau.input import focus_until, send_keys, VK_ESCAPE
from Luau.websocket import WebSocket, asyncio

class Main(Application):
    def __init__(self):
        super().__init__()

        self.name = "Pyrblx"
        self.version = 2.0

        self.instance_buttons = {}
        self.instance_buttons_rev = {}

        self.selected_instance = None
        self.selected_variables = {}
        self.base_variables = BASE_VARIABLES
        self.base_actions = BASE_ACTIONS

        self.searches_current = []
        self.searches_closedbuttons = []

        self.websocket = WebSocket()
        self.injecting = False

        self.execute_globals = { "game": self.datamodel, "Vector3": Vector3, "Vector2": Vector2, "CFrame": CFrame }
        self.execute_locals = {}

        self.execute_history = []
        self.execute_history_current = 0
    
    def init_ui(self):
        self.name = "Pyrblx"
        self.version = 2.0

        super().init_ui()

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

        self.tabslayout.addTab(rightwidget, "Instances")

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
        self.spdbutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px; } QPushButton:hover { background-color: #66d9ff; } QPushButton:pressed { background-color: #00a6e6; }")
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
        self.jumpbutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px; } QPushButton:hover { background-color: #66d9ff; } QPushButton:pressed { background-color: #00a6e6; }")
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
        self.teleportbutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px; } QPushButton:hover { background-color: #66d9ff; } QPushButton:pressed { background-color: #00a6e6; }")
        self.teleportcurrentbutton = QPushButton("Current")
        self.teleportcurrentbutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #ff9800; border-color: #ff9800; border-radius: 3px; } QPushButton:hover { background-color: #ffb84d; } QPushButton:pressed { background-color: #e68a00; }")
        teleportlayout.addWidget(teleportlabel)
        teleportlayout.addWidget(self.teleporttextboxX)
        teleportlayout.addWidget(self.teleporttextboxY)
        teleportlayout.addWidget(self.teleporttextboxZ)
        teleportlayout.addWidget(self.teleportcurrentbutton)
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
        self.teleportplayerbutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px; } QPushButton:hover { background-color: #66d9ff; } QPushButton:pressed { background-color: #00a6e6; }")
        teleportplayerlayout.addWidget(teleportplayerlabel)
        teleportplayerlayout.addWidget(self.teleportplayertextbox)
        teleportplayerlayout.addWidget(self.teleportplayerbutton)
        downlayout.addWidget(teleportplayerwidget)

        nocliplayout = QHBoxLayout()
        noclipwidget = QWidget()
        noclipwidget.setLayout(nocliplayout)
        self.noclipbutton = QPushButton("Disable collision")
        self.notouchbutton = QPushButton("Disable touch")
        nocliplayout.addWidget(self.noclipbutton)
        nocliplayout.addWidget(self.notouchbutton)
        downlayout.addWidget(noclipwidget)

        invislayout = QHBoxLayout()
        inviswidget = QWidget()
        inviswidget.setLayout(invislayout)
        self.invisbutton = QPushButton("Disable visibility")
        invislayout.addWidget(self.invisbutton)
        downlayout.addWidget(inviswidget)

        self.tabslayout.addTab(downwidget, "Utilities")

        uplayout = QVBoxLayout()
        upwidget = QWidget()
        upwidget.setLayout(uplayout)

        injectrow = QVBoxLayout()
        injectrow.setContentsMargins(0, 0, 0, 0)
        injectrow.setSpacing(4)
        self.injectbox = QTextEdit()
        self.injectbox.setPlaceholderText("Luau to inject...")
        self.injectbox.setStyleSheet("QTextEdit { font-family: Consolas, 'JetBrains Mono', monospace; color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px; }")
        self.injectcopybutton = QPushButton("Load from file")
        
        injectrow.addWidget(self.injectbox)
        injectrow.addWidget(self.injectcopybutton)

        self.injectbutton = QPushButton("Run")
        self.injectbutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px; } QPushButton:hover { background-color: #66d9ff; } QPushButton:pressed { background-color: #00a6e6; }")
        self.injectstatus = QLabel("---")
        self.injectstatus.setAlignment(Qt.AlignCenter)

        uplayout.addLayout(injectrow)
        uplayout.addWidget(self.injectbutton)
        uplayout.addWidget(self.injectstatus)

        self.tabslayout.addTab(upwidget, "Inject")

        toplayout = QVBoxLayout()
        topwidget = QWidget()
        topwidget.setLayout(toplayout)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.executebox = QLineEdit()
        self.executebox.setPlaceholderText("Code to execute…")
        self.executebox.setStyleSheet("QLineEdit { font-family: Consolas, 'JetBrains Mono', monospace; color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px; }")

        self.executebutton = QPushButton("Run")
        self.executebutton.setStyleSheet("QPushButton { color: #ffffff; background-color: #00bfff; border-color: #00bfff; border-radius: 3px; } QPushButton:hover { background-color: #66d9ff; } QPushButton:pressed { background-color: #00a6e6; }")

        row.addWidget(self.executebox)
        row.addWidget(self.executebutton)

        toplayout.addLayout(row)

        self.executeresult = QTextEdit("> Pyrblx is running...")
        self.executeresult.setReadOnly(True)
        self.executeresult.setStyleSheet("QTextEdit { font-family: Consolas, 'JetBrains Mono', monospace; color: #b0b0b0; background-color: #2d2d2d; border-color: #b0b0b0; border-radius: 3px; }")
        self.executeresult.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        toplayout.addWidget(self.executeresult)

        self.tabslayout.addTab(topwidget, "Execute")
    
    def init_hotkeys(self):
        if not self.registered:
            def history_up():
                if len(self.execute_history) > 0:
                    self.executebox.setText(self.execute_history[self.execute_history_current])
                    self.execute_history_current = min(self.execute_history_current + 1, len(self.execute_history) - 1)
            def history_down():
                if len(self.execute_history) > 0:
                    self.executebox.setText(self.execute_history[self.execute_history_current])
                    self.execute_history_current = max(self.execute_history_current - 1, 0)
            
            keyboard.add_hotkey('up', history_up)
            keyboard.add_hotkey('down', history_down)

            super().init_hotkeys()
    
    def closeEvent(self, event):
        threading.Thread(target=self.websocket.stop, daemon=False).start()

        super().closeEvent(event)
    
    def enable_worker(self):
        super().enable_worker()

        threading.Thread(target=self.websocket.start, daemon=False).start()

    def disable_worker(self):
        super().disable_worker()

        clearLayout(self.vrframe)
        clearLayout(self.dtframe)

        try:
            self.searchbox.textChanged.disconnect()
            self.searchbox.returnPressed.disconnect()
        except Exception:
            pass
        try:
            self.spdtextbox.returnPressed.disconnect()
            self.spdbutton.clicked.disconnect()
            self.jumptextbox.returnPressed.disconnect()
            self.jumpbutton.clicked.disconnect()
            self.teleportcurrentbutton.clicked.disconnect()
            self.teleporttextboxX.returnPressed.disconnect()
            self.teleporttextboxY.returnPressed.disconnect()
            self.teleporttextboxZ.returnPressed.disconnect()
            self.teleportbutton.clicked.disconnect()
            self.teleportplayertextbox.returnPressed.disconnect()
            self.teleportplayerbutton.clicked.disconnect()
            self.noclipbutton.clicked.disconnect()
            self.notouchbutton.clicked.disconnect()
            self.invisbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.injectcopybutton.clicked.disconnect()
            self.injectbutton.clicked.disconnect()
        except Exception:
            pass
        try:
            self.executebox.returnPressed.disconnect()
            self.executebutton.clicked.disconnect()
        except Exception:
            pass
    
        threading.Thread(target=self.websocket.stop, daemon=False).start()
        
    def loadButton(self, obj, parent, strictchildren=None):
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

        name.clicked.connect(lambda : self.selectVariable(obj))

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

            button.clicked.connect(lambda : self.showButton(button, container_widget, "►" in button.text()))
            self.showButton(button, container_widget, False)
        else:
            info_widget.setContentsMargins(32, 0, 0, 0)

        main_layout.addWidget(info_widget)
        main_layout.addWidget(container_widget)

        parent.addWidget(main_widget)

        self.instance_buttons[obj] = main_widget
        self.instance_buttons_rev[main_widget] = obj

        for idx, child in enumerate(objchildren):
            if not self.enabled: break

            name.setText(f"{objname} ({objclass})    LOADING {(idx + 1)}/{len(objchildren)}")
            self.loadButton(child, container_layout)
            QApplication.processEvents()
            
        name.setText(f"{objname} ({objclass})")
        name.setStyleSheet("color: #b0b0b0; background-color: #2d2d2d; border-radius: 3px; padding: 5px; text-align: left;")

        if not self.testSearch(self.searchbox.text(), obj):
            main_widget.hide()
            container_widget.hide()
            if button and button.text() == "▼": button.setText("►")
                
            return main_widget
        
    def deleteButton(self, obj):
        if obj in self.instance_buttons:
            button = self.instance_buttons[obj]
                
            if not sip.isdeleted(button):
                button.deleteLater()

            del self.instance_buttons[obj]
            del self.instance_buttons_rev[button]
        
    def updateButton(self, obj, prev_list):
        objdescendants = self.get_descendants_fast(obj)

        for child in objdescendants:
            if not self.enabled: break
            
            if not child in prev_list:
                childparent = child.get_parent()

                if childparent in self.instance_buttons:
                    parentbutton = self.instance_buttons[childparent]

                    if not sip.isdeleted(parentbutton):
                        parentbuttonlayout = parentbutton.layout()
                        parentcontainer = parentbuttonlayout.itemAt(1).widget()
                        parentcontainerlayout = parentcontainer.layout()
                            
                        self.loadButton(child, parentcontainerlayout)
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
                self.deleteButton(child)
            QApplication.processEvents()

        return objdescendants
        
    def showButton(self, button, container, visible):
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
        
    def selectVariable(self, obj):
        self.selected_instance = obj

        objname = obj.get_name
        objclass = obj.get_class
        objaddress = obj.get_address
        objparent = obj.get_parent

        classvalue = objclass()

        clearLayout(self.vrframe)
        self.selected_variables = {}

        self.selected_variables["get_name"] = self.loadVariable("Name: ", objname)
        self.selected_variables["get_class"] = self.loadVariable("Class: ", objclass)
        self.selected_variables["get_address"] = self.loadVariable("Address: ", objaddress)
        self.selected_variables["get_parent"] = self.loadVariable("Parent: ", objparent)

        if classvalue in self.base_actions:
            classaction = self.base_actions[classvalue]
            classaction(self, obj)

        if classvalue in self.base_variables:
            classvars = self.base_variables[classvalue]

            for varname, methodname in classvars.items():
                self.selected_variables[methodname] = self.loadVariable(f"{varname}: ", getattr(obj, methodname))

    def loadVariable(self, varname, varvalue):
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
            button.clicked.connect(lambda : self.selectVariable(varvalue()))
        elif isinstance(result, str):
            button.clicked.connect(lambda : QApplication.clipboard().setText(varvalue()))
        elif isinstance(result, bytes):
            button.clicked.connect(lambda : QApplication.clipboard().setText(str(varvalue())))

        main_layout.addStretch()
        self.vrframe.addWidget(main_widget)

        return main_widget
        
    def updateVariable(self, mname, mwidget):
        value = getattr(self.selected_instance, mname)()

        mlayout = mwidget.layout()
        mbutton = mlayout.itemAt(1).widget()

        mbutton.setText(str(value))
        
    def get_descendants_fast(self, obj):
        descendants = []

        objchildren = obj.get_children()

        for child in objchildren:
            descendants.append(child)
            descendants += self.get_descendants_fast(child)
            QApplication.processEvents()

        return descendants
        
    def testSearch(self, text, obj):
        stext = text.lower().split(" ")
        cname = f"{obj.get_name().lower()} {obj.get_class().lower()} {obj.get_address()}"
        return text == "" or any([part in cname for part in stext])
        
    def findSearch(self, parent, text, current=[], sid= -1):
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

            if text == "" or self.testSearch(text, obj):
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
                
            self.findSearch(childcontainerlayout, text, current, sid=sid)
            
        return current
        
    def filterSearch(self, text):
        def search():
            searchid = time.perf_counter_ns()
            self.searches_current.append(searchid)
            self.searches_closedbuttons = []

            self.findSearch(self.dtframe, text, [], sid=searchid)

            self.searches_current.remove(searchid)
            
        threading.Thread(target=search).start()
    
    def onInit(self):
        self.instance_buttons = {}
        self.instance_buttons_rev = {}

        self.selected_instance = None
        self.selected_variables = {}

        self.searches_current = []
        self.searches_closedbuttons = []

        self.injecting = False

        self.execute_globals = { "game": self.datamodel, "Vector3": Vector3, "Vector2": Vector2, "CFrame": CFrame }
        self.execute_locals = {}

        self.execute_history = []
        self.execute_history_current = 0
        
        def updateEspDots():
                while self.enabled:
                    section = self.overlay.sections[self.overlay_section_esp]

                    if self.espbox.isChecked():
                        try:
                            localplayer = self.players.get_localplayer()
                            if not localplayer: continue
                            playerchildren = self.players.get_children()
                            espdots = section.copy()

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
                        except:
                            self.overlay.sections[self.overlay_section_esp] = {}
                    else:
                        if len(section) > 0:
                            self.overlay.sections[self.overlay_section_esp] = {}

                    time.sleep(0)
        
        def updateFlyVelocity():
                while self.enabled:
                    if self.flybox.isChecked():
                        try:
                            localplayer = self.players.get_localplayer()
                            if not localplayer: continue
                            character = localplayer.get_character()
                            if not character: continue
                            root = character.find_first_child("HumanoidRootPart")
                            if not root: continue

                            vel = Vector3(0.0, 500.0, 0.0)
                            root.set_velocity(vel)
                        except:
                            pass
                    
                    time.sleep(0)
        
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
        
        def updateTeleportCurrentposition():
            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return
                root = character.find_first_child("HumanoidRootPart")
                if not root: return

                pos = root.get_position()

                self.teleporttextboxX.setText(f"{pos.x:.3f}")
                self.teleporttextboxY.setText(f"{pos.y:.3f}")
                self.teleporttextboxZ.setText(f"{pos.z:.3f}")
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
        
        def updateNoclipTouch():
            try:
                localplayer = self.players.get_localplayer()
                if not localplayer: return
                character = localplayer.get_character()
                if not character: return

                for child in character.get_descendants():
                    if isinstance(child, BasePart):
                        child.set_cantouch(False)
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
        
        def injectGetFromFile():
            if self.injecting: return

            file, _ = QFileDialog.getOpenFileName(
                self,
                "Select a file",
                "",
                "LUA Files (*.lua)"
            )

            if file:
                try:
                    with open(file) as f:
                        self.injectbox.setText(f.read())
                except Exception as e:
                    self.filechoose.setText("Please choose a valid .lua file!")

        def injectLuau(luau):
            if self.injecting: return
            if luau == "": return

            compiler = Compiler()

            async def inject():
                robloxreplicatedstorage = self.datamodel.get_service("RobloxReplicatedStorage")

                if not robloxreplicatedstorage.find_first_child(self.name):
                    hook = compiler.get_hook(self.name, self.version, self.memory.process.process_id)
                    script = "script.Parent=nil;task.spawn(function()" + hook + "\nend);while true do task.wait(9e9) end"

                    status, bytecode = compiler.compile(script)

                    if status:
                        self.injectstatus.setText("Injecting hook...")

                        try:
                            starterplayer = self.datamodel.get_service("StarterPlayer")
                            scriptcontext = self.datamodel.get_service("ScriptContext")
                            coregui = self.datamodel.get_service("CoreGui")

                            vrnavigation = starterplayer.find_first_child("StarterPlayerScripts").find_first_child("PlayerModule").find_first_child("ControlModule").find_first_child("VRNavigation")
                            playerlistmanager = coregui.find_first_child("RobloxGui").find_first_child("Modules").find_first_child("PlayerList").find_first_child("PlayerListManager")

                            self.memory.fastflags.set_fflag("WebSocketServiceEnableClientCreation", True)

                            if scriptcontext.requirebypass():
                                if vrnavigation.set_bytecode(bytecode):
                                    playerlistmanager.spoofwith(vrnavigation)
                                    time.sleep(0.5)
                                    focus_until(self.memory.process.process_id, lambda : send_keys(VK_ESCAPE, VK_ESCAPE))
                                    time.sleep(0.5)
                                    playerlistmanager.spoofwith(playerlistmanager)

                                    self.injectstatus.setText("Successfully injected hook into target script!")
                                else:
                                    self.injectstatus.setText("Failed to set bytecode of target script!")
                            else:
                                self.injectstatus.setText("Failed to require bypass!")
                        except Exception:
                            self.injectstatus.setText("Failed to inject hook into target script!")
                    else:
                        self.injectstatus.setText("Failed to compile hook!")
                
                self.injectstatus.setText("Connecting to hook...")

                responses = await self.websocket.broadcast(action="getModule")

                if len(responses) == 0:
                    self.injectstatus.setText("Failed connecting to hook!")
                else:
                    script = "script.Parent=nil;task.spawn(function()" + luau + "\nend);return {}"

                    status, bytecode = compiler.compile(script)

                    if status:
                        self.injectstatus.setText("Injecting...")

                        for ws, data in responses:
                            try:
                                module = robloxreplicatedstorage.find_first_child(self.name).find_first_child("Scripts").find_first_child(data)

                                if module:
                                    if module.set_bytecode(bytecode):
                                        self.injectstatus.setText("Sending require request...")

                                        responses2 = await self.websocket.broadcast(action="requireModule", data=module.get_name(), target=ws)

                                        for _, data in responses2:
                                            pass
                                                
                                        self.injectstatus.setText("Successfully injected luau into target script!")
                                    else:
                                        self.injectstatus.setText("Failed to set bytecode of target script!")
                                else:
                                    self.injectstatus.setText("Target script not found!")
                            except Exception:
                                self.injectstatus.setText("Failed to inject luau into target script!")
                    else:
                        self.injectstatus.setText("Failed to compile luau!")
                
                self.injecting = False
            
            def run_inject():
                asyncio.run(inject())

            self.injecting = True
            threading.Thread(target=run_inject, daemon=True).start()
            self.injectstatus.setText("Compiling...")
        
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

        self.searchbox.textChanged.connect(self.filterSearch)
        self.searchbox.returnPressed.connect(lambda : self.filterSearch(self.searchbox.text()))

        self.spdtextbox.returnPressed.connect(lambda : updateSpdWalkSpeed(self.spdtextbox.text()))
        self.spdbutton.clicked.connect(lambda : updateSpdWalkSpeed(self.spdtextbox.text()))
        self.jumptextbox.returnPressed.connect(lambda : updateJumpJumpPower(self.jumptextbox.text()))
        self.jumpbutton.clicked.connect(lambda : updateJumpJumpPower(self.jumptextbox.text()))
        self.teleportcurrentbutton.clicked.connect(updateTeleportCurrentposition)
        self.teleporttextboxX.returnPressed.connect(self.teleporttextboxY.setFocus)
        self.teleporttextboxY.returnPressed.connect(self.teleporttextboxZ.setFocus)
        self.teleporttextboxZ.returnPressed.connect(lambda : updateTeleportPosition(self.teleporttextboxX.text(), self.teleporttextboxY.text(), self.teleporttextboxZ.text()))
        self.teleportbutton.clicked.connect(lambda : updateTeleportPosition(self.teleporttextboxX.text(), self.teleporttextboxY.text(), self.teleporttextboxZ.text()))
        self.teleportplayertextbox.returnPressed.connect(lambda : updateTeleportplayerPosition(self.teleportplayertextbox.text()))
        self.teleportplayerbutton.clicked.connect(lambda : updateTeleportplayerPosition(self.teleportplayertextbox.text()))
        self.noclipbutton.clicked.connect(updateNoclipCollision)
        self.notouchbutton.clicked.connect(updateNoclipTouch)
        self.invisbutton.clicked.connect(updateInvisTransparency)

        self.injectcopybutton.clicked.connect(injectGetFromFile)
        self.injectbutton.clicked.connect(lambda : injectLuau(self.injectbox.toPlainText()))

        self.executebox.returnPressed.connect(lambda : executeCode(self.executebox.text()))
        self.executebutton.clicked.connect(lambda : executeCode(self.executebox.text()))

        self.players = self.datamodel.get_service("Players")
        self.workspace = self.datamodel.get_service("Workspace")
        self.replicatedstorage = self.datamodel.get_service("ReplicatedStorage")

        threading.Thread(target=updateEspDots).start()
        threading.Thread(target=updateFlyVelocity).start()

        self.loadButton(self.datamodel, self.dtframe, [self.players, self.workspace, self.replicatedstorage])

        self.workspace_prevchildren = self.get_descendants_fast(self.workspace)
        self.replicatedstorage_prevchildren = self.get_descendants_fast(self.replicatedstorage)
        self.players_prevchildren = self.get_descendants_fast(self.players)
    
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

if __name__ == '__main__':
    runner = QApplication(sys.argv)

    main = Main()
    main.run()

    runner.exec_()