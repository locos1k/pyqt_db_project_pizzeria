from windows.base import load_ui


class AdminMenuWindow:
    def __init__(self, login_window):
        self.login_window = login_window
        self.ui = load_ui("admin_menu.ui")

        self.ui.btnLogout.clicked.connect(self.logout)
        self.ui.btnClients.clicked.connect(self.open_clients)

    def show(self):
        self.ui.show()

    def logout(self):
        self.ui.close()
        self.login_window.show()

    def open_clients(self):
        from windows.clients import ClientsWindow

        self.clients_window = ClientsWindow(self)
        self.clients_window.show()
        self.ui.close()