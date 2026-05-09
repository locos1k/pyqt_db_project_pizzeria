from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QAbstractItemView
from windows.base import load_ui
from db import get_connection


class Orders:
    def __init__(self, parent_window, courier_id=None):
        self.parent_window = parent_window
        self.ui = load_ui("orders.ui")

        self.conn = None
        self.courier_id = courier_id

        self.ui.btnBack.clicked.connect(self.back)
        self.ui.btnClearFilter.clicked.connect(self.clear_filters)

        self.ui.leSearchClient.textChanged.connect(self.load_orders)
        self.ui.leSearchCourier.textChanged.connect(self.load_orders)

        self.ui.rbAll.toggled.connect(self.load_orders)
        self.ui.rbCreated.toggled.connect(self.load_orders)
        self.ui.rbPreparing.toggled.connect(self.load_orders)
        self.ui.rbDelivered.toggled.connect(self.load_orders)

        self.ui.twOrders.cellClicked.connect(self.load_order_items)

        self.setup_tables()
        self.ui.rbAll.setChecked(True)
        self.load_orders()

    def show(self):
        self.ui.show()

    def back(self):
        self.ui.close()
        self.parent_window.show()

    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = get_connection()

    def setup_tables(self):
        self.ui.twOrders.setColumnCount(12)
        self.ui.twOrders.setHorizontalHeaderLabels([
            "Order ID",
            "Клиент",
            "Курьер",
            "Город",
            "Улица",
            "Дом",
            "Квартира",
            "Этаж",
            "Дата заказа",
            "Статус заказа",
            "Статус оплаты",
            "Сумма"
        ])

        self.ui.twOrders.setColumnHidden(0, True)
        self.ui.twOrders.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.twOrders.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twOrders.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.twOrders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.twOrders.horizontalHeader().setStretchLastSection(True)

        self.ui.twOrderItems.setColumnCount(4)
        self.ui.twOrderItems.setHorizontalHeaderLabels([
            "Пицца",
            "Количество",
            "Цена",
            "Сумма"
        ])

        self.ui.twOrderItems.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.twOrderItems.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twOrderItems.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.twOrderItems.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.twOrderItems.horizontalHeader().setStretchLastSection(True)

    def get_selected_status(self):
        if self.ui.rbCreated.isChecked():
            return "created"

        if self.ui.rbPreparing.isChecked():
            return "in_preparation"

        if self.ui.rbDelivered.isChecked():
            return "delivered"

        return None

    def load_orders(self):
        try:
            self.connect_db()

            client_search = self.ui.leSearchClient.text().strip()
            courier_search = self.ui.leSearchCourier.text().strip()
            status = self.get_selected_status()

            sql = """
                SELECT
                    o.order_id,
                    cl.full_name AS client_name,
                    cr.full_name AS courier_name,
                    a.city,
                    a.street,
                    a.house,
                    a.apartment,
                    a.floor,
                    TO_CHAR(o.order_date_time, 'DD.MM.YYYY HH24:MI') AS order_dt,
                    o.status AS order_status,
                    p.status AS payment_status,
                    p.amount
                FROM orders o
                JOIN clients cl ON cl.client_id = o.client_id
                LEFT JOIN couriers cr ON cr.courier_id = o.courier_id
                LEFT JOIN addresses a ON a.address_id = o.address_id
                LEFT JOIN payments p ON p.payment_id = o.payment_id
                WHERE 1 = 1
            """

            params = []

            if client_search:
                sql += " AND LOWER(cl.full_name) LIKE LOWER(%s)"
                params.append(f"%{client_search}%")

            if courier_search:
                sql += " AND LOWER(cr.full_name) LIKE LOWER(%s)"
                params.append(f"%{courier_search}%")

            if status:
                sql += " AND o.status = %s"
                params.append(status)
            
            if self.courier_id is not None:
                sql += " AND cr.courier_id = %s"
                params.append(self.courier_id)

            sql += " ORDER BY o.order_date_time DESC, o.order_id DESC"

            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

            self.ui.twOrders.clearContents()
            self.ui.twOrders.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    text = "-" if value is None or str(value).strip() == "" else str(value)
                    self.ui.twOrders.setItem(i, j, QTableWidgetItem(text))

            self.ui.twOrders.resizeColumnsToContents()
            self.ui.twOrders.setColumnHidden(0, True)

            self.ui.twOrderItems.clearContents()
            self.ui.twOrderItems.setRowCount(0)

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def load_order_items(self, row, column):
        order_id_item = self.ui.twOrders.item(row, 0)

        if order_id_item is None:
            return

        order_id = int(order_id_item.text())

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        p.name,
                        op.quantity,
                        p.price,
                        op.quantity * p.price AS total
                    FROM orderpizza op
                    JOIN pizza p ON p.pizza_id = op.pizza_id
                    WHERE op.order_id = %s
                    ORDER BY p.name;
                """, (order_id,))

                rows = cur.fetchall()

            self.ui.twOrderItems.clearContents()
            self.ui.twOrderItems.setRowCount(len(rows))

            for i, row_data in enumerate(rows):
                for j, value in enumerate(row_data):
                    text = "-" if value is None or str(value).strip() == "" else str(value)
                    self.ui.twOrderItems.setItem(i, j, QTableWidgetItem(text))

            self.ui.twOrderItems.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def clear_filters(self):
        self.ui.leSearchClient.clear()
        self.ui.leSearchCourier.clear()
        self.ui.rbAll.setChecked(True)
        self.load_orders()