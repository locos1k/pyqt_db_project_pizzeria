from PySide6.QtWidgets import QMessageBox
from windows.base import load_ui


class LoginWindow:
    def __init__(self):
        self.ui = load_ui("login.ui")

        self.ui.btnLogin.clicked.connect(self.login)
        self.ui.btnAbout.clicked.connect(self.show_about)
        self.ui.btnExit.clicked.connect(self.ui.close)

    def show(self):
        self.ui.show()

    def login(self):
        user = self.ui.cbUser.currentText()
        password = self.ui.lePassword.text()

        if user == "Администратор" and password == "admin":
            from windows.admin_menu import AdminMenuWindow

            self.admin_window = AdminMenuWindow(self)
            self.admin_window.show()
            self.ui.close()

        elif user == "Оператор" and password == "operator":
            from windows.operator_menu import OperatorMenuWindow

            self.operator_window = OperatorMenuWindow(self)
            self.operator_window.show()
            self.ui.close()

        else:
            QMessageBox.warning(self.ui, "Ошибка", "Неверный пользователь или пароль")

    def show_about(self):
        QMessageBox.information(
            self.ui,
            "О программе",
            "АИС «Круглосуточная пицца на дом»\nМакет приложения на PySide6"
        )