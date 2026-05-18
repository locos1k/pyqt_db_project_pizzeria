from PySide6.QtWidgets import (
    QMessageBox,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QComboBox,
    QFileDialog
)

from PySide6.QtCore import QDate, Qt, QMarginsF
from PySide6.QtGui import QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter

from windows.base import load_ui
from db import get_connection


class Orders:
    ORDER_STATUSES = ["created", "in_preparation", "delivered", "cancelled"]
    PAYMENT_STATUSES = ["paid", "not_paid", "cancelled"]

    def __init__(self, parent_window, courier_id=None, mode="operator"):
        self.parent_window = parent_window
        self.ui = load_ui("orders.ui")

        self.conn = None
        self.courier_id = courier_id
        self.mode = mode

        self.is_loading_table = False
        self.orders_rows = []
        self.active_couriers = []

        self.ui.btnBack.clicked.connect(self.back)
        self.ui.btnClearFilter.clicked.connect(self.clear_filters)
        self.ui.btnSavePdf.clicked.connect(self.save_pdf_report)

        self.ui.leSearchClient.textChanged.connect(self.load_orders)
        self.ui.leSearchCourier.textChanged.connect(self.load_orders)

        self.ui.rbAll.toggled.connect(self.load_orders)
        self.ui.rbCreated.toggled.connect(self.load_orders)
        self.ui.rbPreparing.toggled.connect(self.load_orders)
        self.ui.rbDelivered.toggled.connect(self.load_orders)
        self.ui.rbCancelled.toggled.connect(self.load_orders)

        self.ui.chUseDateFilter.toggled.connect(self.load_orders)
        self.ui.deDateFrom.dateChanged.connect(self.load_orders)
        self.ui.deDateTo.dateChanged.connect(self.load_orders)

        self.ui.twOrders.cellClicked.connect(self.load_order_items)

        self.setup_dates()
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

        if self.ui.rbCancelled.isChecked():
            return "cancelled"

        return None

    def load_orders(self):
        try:
            self.connect_db()
            self.load_active_couriers()

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

            if self.ui.chUseDateFilter.isChecked():
                date_from = self.ui.deDateFrom.date().toString("yyyy-MM-dd")
                date_to = self.ui.deDateTo.date().toString("yyyy-MM-dd")

                sql += " AND o.order_date_time::date BETWEEN %s AND %s"
                params.append(date_from)
                params.append(date_to)
            
            if self.courier_id is not None:
                sql += " AND cr.courier_id = %s"
                params.append(self.courier_id)

            sql += " ORDER BY o.order_date_time DESC, o.order_id DESC"

            with self.conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

            self.is_loading_table = True

            self.ui.twOrders.clearContents()
            self.ui.twOrders.setRowCount(len(rows))
            self.orders_rows = rows

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    text = "-" if value is None or str(value).strip() == "" else str(value)

                    if j in [2, 9, 10]:
                        item = QTableWidgetItem("")
                    else:
                        item = QTableWidgetItem(text)

                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.ui.twOrders.setItem(i, j, item)

            self.add_status_comboboxes()
            self.add_courier_comboboxes()
    
            self.is_loading_table = False

            self.ui.twOrders.resizeColumnsToContents()
            self.ui.twOrders.resizeRowsToContents()
            self.ui.twOrders.setColumnHidden(0, True)

            self.ui.twOrderItems.clearContents()
            self.ui.twOrderItems.setRowCount(0)

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def add_status_comboboxes(self):
        for row in range(self.ui.twOrders.rowCount()):
            order_id_item = self.ui.twOrders.item(row, 0)
            if order_id_item is None:
                continue

            current_order_status = self.orders_rows[row][9]
            current_payment_status = self.orders_rows[row][10]

            current_order_status = str(current_order_status) if current_order_status else "created"
            current_payment_status = str(current_payment_status) if current_payment_status else "not_paid"

            cb_order_status = QComboBox()
            cb_order_status.addItems(self.ORDER_STATUSES)

            index = cb_order_status.findText(current_order_status)
            if index >= 0:
                cb_order_status.setCurrentIndex(index)

            cb_order_status.currentTextChanged.connect(
                lambda value, r=row: self.update_order_status(r, value)
            )

            cb_payment_status = QComboBox()
            cb_payment_status.addItems(self.PAYMENT_STATUSES)

            index = cb_payment_status.findText(current_payment_status)
            if index >= 0:
                cb_payment_status.setCurrentIndex(index)

            cb_payment_status.currentTextChanged.connect(
                lambda value, r=row: self.update_payment_status(r, value)
            )

            self.ui.twOrders.setCellWidget(row, 9, cb_order_status)
            self.ui.twOrders.setCellWidget(row, 10, cb_payment_status)

    def update_order_status(self, row, new_status):
        if self.is_loading_table:
            return

        if new_status not in self.ORDER_STATUSES:
            QMessageBox.warning(self.ui, "Ошибка", "Недопустимый статус заказа")
            self.load_orders()
            return

        order_id = int(self.ui.twOrders.item(row, 0).text())

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders
                    SET status = %s
                    WHERE order_id = %s;
                """, (new_status, order_id))

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))


    def update_payment_status(self, row, new_status):
        if self.is_loading_table:
            return

        if new_status not in self.PAYMENT_STATUSES:
            QMessageBox.warning(self.ui, "Ошибка", "Недопустимый статус оплаты")
            self.load_orders()
            return

        order_id = int(self.ui.twOrders.item(row, 0).text())

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE payments
                    SET status = %s
                    WHERE payment_id = (
                        SELECT payment_id
                        FROM orders
                        WHERE order_id = %s
                    );
                """, (new_status, order_id))

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
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

    def load_active_couriers(self):
        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT courier_id, full_name
                    FROM couriers
                    WHERE status = 'active'
                    ORDER BY full_name;
                """)
                self.active_couriers = cur.fetchall()

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def add_courier_comboboxes(self):
        for row in range(self.ui.twOrders.rowCount()):
            order_id_item = self.ui.twOrders.item(row, 0)

            if order_id_item is None:
                continue

            current_courier_name = self.orders_rows[row][2]

            cb_courier = QComboBox()

            if current_courier_name:
                cb_courier.addItem(str(current_courier_name), None)

            for courier_id, full_name in self.active_couriers:
                if str(full_name) != str(current_courier_name):
                    cb_courier.addItem(full_name, courier_id)

            cb_courier.currentIndexChanged.connect(
                lambda index, r=row: self.update_order_courier(r)
            )

            self.ui.twOrders.setCellWidget(row, 2, cb_courier)

    def update_order_courier(self, row):
        if self.is_loading_table:
            return

        cb_courier = self.ui.twOrders.cellWidget(row, 2)

        if cb_courier is None:
            return

        courier_id = cb_courier.currentData()

        if courier_id is None:
            return

        order_id = int(self.ui.twOrders.item(row, 0).text())

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders
                    SET courier_id = %s
                    WHERE order_id = %s;
                """, (courier_id, order_id))

            self.conn.commit()

            self.load_orders()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def setup_dates(self):
        today = QDate.currentDate()

        self.ui.deDateFrom.setCalendarPopup(True)
        self.ui.deDateTo.setCalendarPopup(True)

        self.ui.deDateFrom.setDate(today.addMonths(-1))
        self.ui.deDateTo.setDate(today)

        self.ui.chUseDateFilter.setChecked(False)

    def save_pdf_report(self):
        if self.ui.twOrders.rowCount() == 0:
            QMessageBox.warning(self.ui, "Ошибка", "Нет данных для сохранения")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self.ui,
            "Сохранить отчёт в PDF",
            "orders_report.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_name:
            return

        if not file_name.endswith(".pdf"):
            file_name += ".pdf"

        try:
            headers = [
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
            ]

            html = """
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        font-size: 8pt;
                    }
                    h1 {
                        text-align: center;
                        font-size: 16pt;
                        margin-bottom: 15px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    th, td {
                        border: 1px solid #000;
                        padding: 4px;
                        vertical-align: top;
                        word-wrap: break-word;
                    }
                    th {
                        background-color: #eeeeee;
                        font-weight: bold;
                        text-align: center;
                    }
                </style>
            </head>
            <body>
                <h1>Отчёт по заказам</h1>
                <table>
                    <tr>
            """

            for header in headers:
                html += f"<th>{header}</th>"

            html += "</tr>"

            for row in range(self.ui.twOrders.rowCount()):
                html += "<tr>"

                for col in range(1, self.ui.twOrders.columnCount()):
                    widget = self.ui.twOrders.cellWidget(row, col)

                    if isinstance(widget, QComboBox):
                        value = widget.currentText()
                    else:
                        item = self.ui.twOrders.item(row, col)
                        value = item.text() if item else "-"

                    html += f"<td>{value}</td>"

                html += "</tr>"

            html += """
                </table>
            </body>
            </html>
            """

            document = QTextDocument()
            document.setHtml(html)

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_name)
            printer.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Millimeter)

            document.print_(printer)

            QMessageBox.information(self.ui, "Успех", "Отчёт сохранён в PDF")

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка", str(e))

    def clear_filters(self):
        self.ui.leSearchClient.clear()
        self.ui.leSearchCourier.clear()
        self.ui.rbAll.setChecked(True)
        self.ui.chUseDateFilter.setChecked(False)
        self.load_orders()