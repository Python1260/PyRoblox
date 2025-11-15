from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QPushButton, QScrollArea, QSizePolicy, QLineEdit, QFileDialog
from PyQt5.QtCore import QTimer, Qt, QRect, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
import sip

def displayPosition(app, obj):
    def getCFrame():
        cframe = obj.get_cframe()
        cframe_adv = cframe + cframe.lookvector * 3

        pos = app.visualengine.world_to_screen(cframe.position)
        pos_adv = app.visualengine.world_to_screen(cframe_adv.position)

        return (pos.x, pos.y, pos_adv.x, pos_adv.y)

    if obj in app.instance_buttons:
        childbutton = app.instance_buttons[obj]

        if not sip.isdeleted(childbutton):
            selected, unselected = app.overlay.setDot(childbutton, getCFrame)

            if selected in app.instance_buttons_rev:
                selectedbuttonlayout = selected.layout()
                selectedinfo = selectedbuttonlayout.itemAt(0).widget()
                selectedinfolayout = selectedinfo.layout()
                selectedname = selectedinfolayout.itemAt(selectedinfolayout.count() - 1).widget()
                selectedname.setStyleSheet(f"color: {"#0000ff"}; background-color: #2d2d2d; border-radius: 3px; padding: 5px; text-align: left;")

            if unselected in app.instance_buttons_rev:
                unselectedbuttonlayout = unselected.layout()
                unselectedinfo = unselectedbuttonlayout.itemAt(0).widget()
                unselectedinfolayout = unselectedinfo.layout()
                unselectedname = unselectedinfolayout.itemAt(unselectedinfolayout.count() - 1).widget()
                unselectedname.setStyleSheet(f"color: {"#b0b0b0"}; background-color: #2d2d2d; border-radius: 3px; padding: 5px; text-align: left;")

BASE_VARIABLES = {
    "DataModel": {
        "CreatorId": "get_creatorid",
        "GameId": "get_gameid",
        "PlaceId": "get_placeid",
        "GameLoaded": "get_gameloaded"
    },
    "Workspace": {
        "Gravity": "get_gravity",
        "CurrentCamera": "get_currentcamera"
    },
    "Players": {
        "LocalPlayer": "get_localplayer"
    },
    "Player": {
        "Character": "get_character",
        "UserId": "get_userid"
    },
    "Humanoid": {
        "Health": "get_health",
        "MaxHealth": "get_maxhealth",
        "WalkSpeed": "get_walkspeed",
        "JumpPower": "get_jumppower"
    },
    "Camera": {
        "Position": "get_position",
        "Orientation": "get_rotation",
        "Subject": "get_subject"
    },
    "BasePart": {
        "Position": "get_position",
        "Orientation": "get_rotation",
        "Size": "get_size",
        "CFrame": "get_cframe",
        "Anchored": "get_anchored",
        "CanCollide": "get_cancollide",
        "CanTouch": "get_cantouch"
    },
    "Part": {
        "Position": "get_position",
        "Orientation": "get_rotation",
        "Size": "get_size",
        "CFrame": "get_cframe",
        "Anchored": "get_anchored",
        "CanCollide": "get_cancollide",
        "CanTouch": "get_cantouch"
    },
    "MeshPart": {
        "Position": "get_position",
        "Orientation": "get_rotation",
        "Size": "get_size",
        "CFrame": "get_cframe",
        "Anchored": "get_anchored",
        "CanCollide": "get_cancollide",
        "CanTouch": "get_cantouch"
    },
    "IntValue": {
        "Value": "get_value"
    },
    "NumberValue": {
        "Value": "get_value"
    },
    "BoolValue": {
        "Value": "get_value"
    },
    "StringValue": {
        "Value": "get_value"
    },
    "ObjectValue": {
        "Value": "get_value"
    },
    "LocalScript": {
        "Content": "get_content"
    },
    "ModuleScript": {
        "Content": "get_content"
    },
    "Sound": {
        "SoundId": "get_soundid"
    }
}

BASE_ACTIONS = {
    "BasePart": displayPosition,
    "Part": displayPosition,
    "MeshPart": displayPosition
}