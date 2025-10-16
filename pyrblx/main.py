import os
import sys

from PyQt5.QtWidgets import QApplication

from app import Application

packages = [
    "pymem==1.13.0",
    "psutil==5.9.6",
    "keyboard==0.13.5",
    "mouse==0.7.1",
    "PyQt5==5.15.10",
    "pyautogui==0.9.54",
    "xxhash==3.6.0",
    "zstandard==0.25.0",
    "sip==6.13.1"
]

if __name__ == '__main__':
    os.system(f"pip install {' '.join(pckg for pckg in packages)}")

    runner = QApplication(sys.argv)

    app = Application()
    app.run()

    runner.exec_()