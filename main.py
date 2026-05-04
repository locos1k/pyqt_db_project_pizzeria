import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile


def load_ui(path: str):
    loader = QUiLoader()
    ui_file = QFile(path)

    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Cannot open UI file: {path}")

    window = loader.load(ui_file)
    ui_file.close()

    if window is None:
        raise RuntimeError(f"Cannot load UI file: {path}")

    return window


app = QApplication(sys.argv)

window = load_ui("ui/login.ui")
window.show()

sys.exit(app.exec())