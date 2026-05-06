from pathlib import Path

from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile


BASE_DIR = Path(__file__).resolve().parent.parent


def load_ui(ui_name: str):
    ui_path = BASE_DIR / "ui" / ui_name

    loader = QUiLoader()
    ui_file = QFile(str(ui_path))

    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Не удалось открыть UI-файл: {ui_path}")

    window = loader.load(ui_file)
    ui_file.close()

    if window is None:
        raise RuntimeError(f"Не удалось загрузить UI-файл: {ui_path}")

    return window