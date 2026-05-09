from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QAbstractItemView

from windows.base import load_ui
from db import get_connection


class ClientsWindow:
    def __init__(self, admin_menu):
        self.admin_menu = admin_menu
        self.ui = load_ui("clients.ui")

        self.conn = None
        self.clients_data = []
        self.current_client_index = 0

        self.ui.leClientId.hide()

        self.ui.btnBack.clicked.connect(self.back)
        self.ui.btnPrev.clicked.connect(self.prev_client)
        self.ui.btnNext.clicked.connect(self.next_client)

        self.ui.btnEditClient.clicked.connect(self.edit_client)
        self.ui.btnDeleteClient.clicked.connect(self.delete_client)
        self.ui.btnAddClient.clicked.connect(self.add_client)
        self.ui.btnOpenReport.clicked.connect(self.open_report)

        self.setup_tables()
        self.load_clients()

    def show(self):
        self.ui.show()

    def back(self):
        self.ui.close()
        self.admin_menu.show()

    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = get_connection()

    def setup_tables(self):
        self.ui.twAddresses.setColumnCount(6)
        self.ui.twAddresses.setHorizontalHeaderLabels([
            "Город", "Улица", "Дом", "Квартира", "Этаж", "Комментарий"
        ])
        self.ui.twAddresses.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.ui.twAddresses.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.twAddresses.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twAddresses.setSelectionMode(QAbstractItemView.SingleSelection)

        self.ui.twOrders.setColumnCount(7)
        self.ui.twOrders.setHorizontalHeaderLabels([
            "Order ID", "Адрес", "Курьер", "Дата заказа", "Комментарий", "Статус заказа", "Статус оплаты"
        ])
        self.ui.twOrders.setColumnHidden(0, True)
        self.ui.twOrders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.ui.twOrders.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.twOrders.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twOrders.setSelectionMode(QAbstractItemView.SingleSelection)

    def load_clients(self):
        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT client_id, full_name, phone, email, loyalty_points
                    FROM clients
                    ORDER BY client_id;
                """)
                self.clients_data = cur.fetchall()

            if self.clients_data:
                self.current_client_index = 0
                self.show_current_client()
            else:
                QMessageBox.information(self.ui, "Информация", "Клиенты не найдены")

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def show_current_client(self):
        client = self.clients_data[self.current_client_index]

        client_id, full_name, phone, email, loyalty_points = client

        self.ui.leClientId.setText(str(client_id))
        self.ui.leFullName.setText(full_name or "")
        self.ui.lePhone.setText(phone or "")
        self.ui.leEmail.setText(email or "")
        self.ui.leLoyaltyPoints.setText(str(loyalty_points or 0))

        self.load_addresses(client_id)
        self.load_orders(client_id)

    def prev_client(self):
        if self.current_client_index > 0:
            self.current_client_index -= 1
            self.show_current_client()

    def next_client(self):
        if self.current_client_index < len(self.clients_data) - 1:
            self.current_client_index += 1
            self.show_current_client()

    def load_addresses(self, client_id):
        self.ui.twAddresses.clearContents()
        self.ui.twAddresses.setRowCount(0)

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT city, street, house, apartment, floor, comment
                FROM addresses
                WHERE client_id = %s
                ORDER BY address_id;
            """, (client_id,))
            rows = cur.fetchall()

        self.ui.twAddresses.setRowCount(len(rows))

        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                text = "-" if value is None or str(value).strip() == "" else str(value)
                self.ui.twAddresses.setItem(i, j, QTableWidgetItem(text))

    def load_orders(self, client_id):
        self.ui.twOrders.clearContents()
        self.ui.twOrders.setRowCount(0)

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    o.order_id,
                    a.city || ', ' || a.street || ', д. ' || a.house ||
                        COALESCE(', кв. ' || a.apartment, '') AS full_address,
                    c.full_name AS courier_name,
                    TO_CHAR(o.order_date_time, 'DD.MM.YYYY HH24:MI') AS order_dt,
                    o.comment,
                    o.status,
                    p.status AS payment_status
                FROM orders o
                LEFT JOIN addresses a ON a.address_id = o.address_id
                LEFT JOIN couriers c ON c.courier_id = o.courier_id
                LEFT JOIN payments p ON p.payment_id = o.payment_id
                WHERE o.client_id = %s
                ORDER BY o.order_id;
            """, (client_id,))
            rows = cur.fetchall()

        self.ui.twOrders.setRowCount(len(rows))

        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                text = "-" if value is None or str(value).strip() == "" else str(value)
                self.ui.twOrders.setItem(i, j, QTableWidgetItem(text))

    def edit_client(self):
        if not self.ui.leClientId.text():
            QMessageBox.warning(self.ui, "Ошибка", "Клиент не выбран")
            return

        try:
            self.connect_db()

            client_id = int(self.ui.leClientId.text())
            full_name = self.ui.leFullName.text().strip()
            phone = self.ui.lePhone.text().strip()
            email = self.ui.leEmail.text().strip()
            loyalty_points = int(self.ui.leLoyaltyPoints.text() or 0)

            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE clients
                    SET full_name = %s,
                        phone = %s,
                        email = %s,
                        loyalty_points = %s
                    WHERE client_id = %s;
                """, (full_name, phone, email, loyalty_points, client_id))

            self.conn.commit()

            QMessageBox.information(self.ui, "Успех", "Данные клиента сохранены")

            self.load_clients()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def delete_client(self):
        if not self.ui.leClientId.text():
            QMessageBox.warning(self.ui, "Ошибка", "Клиент не выбран")
            return

        answer = QMessageBox.question(
            self.ui,
            "Удаление",
            "Удалить выбранного клиента?",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        try:
            self.connect_db()

            client_id = int(self.ui.leClientId.text())

            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM clients
                    WHERE client_id = %s;
                """, (client_id,))

            self.conn.commit()

            QMessageBox.information(self.ui, "Успех", "Клиент удалён")

            self.load_clients()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e)) 

    def open_report(self):
        if not self.ui.leClientId.text():
            QMessageBox.warning(self.ui, "Ошибка", "Клиент не выбран")
            return

        from windows.client_report import ClientReport

        client_id = int(self.ui.leClientId.text())
        client_name = self.ui.leFullName.text()

        self.client_report_window = ClientReport(self, client_id, client_name)
        self.client_report_window.show()
        self.ui.close()

    def add_client(self):
        from windows.add_client import AddClient

        self.add_client_window = AddClient(
            parent_window=self,
            after_save_callback=self.after_client_added
        )
        self.add_client_window.show()
        self.ui.close()


    def after_client_added(self, new_client_id):
        self.ui.show()
        self.load_clients()

        for i, client in enumerate(self.clients_data):
            if client[0] == new_client_id:
                self.current_client_index = i
                self.show_current_client()
                break