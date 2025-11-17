import asyncio
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    win = MainWindow()
    win.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
