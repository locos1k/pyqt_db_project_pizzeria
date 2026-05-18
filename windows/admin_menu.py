from windows.base import load_ui


class AdminMenuWindow:
    def __init__(self, login_window):
        self.login_window = login_window
        self.ui = load_ui("admin_menu.ui")

        self.ui.btnLogout.clicked.connect(self.logout)
        self.ui.btnClients.clicked.connect(self.open_clients)
        self.ui.btnOrders.clicked.connect(self.open_orders)
        self.ui.btnCouriers.clicked.connect(self.open_couriers)
        self.ui.btnCourierReport.clicked.connect(self.open_couriers_load_report)

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

    def open_orders(self):
        from windows.orders import Orders

        self.orders_window = Orders(self)
        self.orders_window.show()
        self.ui.close()

    def open_couriers(self):
        from windows.couriers import Couriers

        self.couriers_window = Couriers(self)
        self.couriers_window.show()
        self.ui.close()

    def open_couriers_load_report(self):
        from windows.couriers_load_report import CouriersLoadReport

        self.couriers_load_report_window = CouriersLoadReport(self)
        self.couriers_load_report_window.show()
        self.ui.close()