from windows.base import load_ui


class OperatorMenuWindow:
    def __init__(self, login_window):
        self.login_window = login_window
        self.ui = load_ui("operator_menu.ui")
        self.ui.setWindowTitle("АИС «Круглосуточная пицца на дом» – Меню Оператора")

        self.ui.btnLogout.clicked.connect(self.logout)
        self.ui.btnCreateOrder.clicked.connect(self.open_create_order)
        self.ui.btnOrders.clicked.connect(self.open_orders)
        self.ui.btnClientReport.clicked.connect(self.open_client_orders_search)

    def show(self):
        self.ui.show()

    def logout(self):
        self.ui.close()
        self.login_window.show()
    
    def open_create_order(self):
        from windows.create_order import CreateOrder

        self.create_order_window = CreateOrder(self)
        self.create_order_window.show()
        self.ui.close()

    def open_orders(self):
        from windows.orders import Orders

        self.orders_window = Orders(self, mode="operator")
        self.orders_window.show()
        self.ui.close()

    def open_client_orders_search(self):
        from windows.client_orders_search import ClientOrdersSearch

        self.client_orders_search_window = ClientOrdersSearch(self)
        self.client_orders_search_window.show()
        self.ui.close()