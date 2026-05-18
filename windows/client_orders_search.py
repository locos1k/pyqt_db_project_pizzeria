import html

from PySide6.QtWidgets import (
    QMessageBox,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QInputDialog,
)

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter

from windows.base import load_ui
from db import get_connection


class ClientOrdersSearch:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.ui = load_ui("client_orders_search.ui")

        self.conn = None
        self.report_rows = []
        self.current_client_info = None

        self.ui.btnBack_3.clicked.connect(self.back)
        self.ui.btnSearch.clicked.connect(self.search_client)
        self.ui.btnClear.clicked.connect(self.clear_search)
        self.ui.btnSavePdf_3.clicked.connect(self.save_pdf)

        self.ui.leClientSearch.returnPressed.connect(self.search_client)

        self.setup_table()
        self.clear_client_info()

    def show(self):
        self.ui.show()

    def back(self):
        self.ui.close()
        self.parent_window.show()

    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = get_connection()

    def setup_table(self):
        self.ui.twOrders.setColumnCount(4)
        self.ui.twOrders.setHorizontalHeaderLabels([
            "Дата заказа",
            "Статус заказа",
            "Статус оплаты",
            "Сумма",
        ])

        self.ui.twOrders.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.twOrders.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twOrders.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.twOrders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.twOrders.horizontalHeader().setStretchLastSection(True)

    def clear_client_info(self):
        self.current_client_info = None

        self.ui.lbClientName.setText("ФИО: -")
        self.ui.lbClientPhone.setText("Телефон: -")
        self.ui.lbClientEmail.setText("Email: -")
        self.ui.lbClientPoints.setText("Баллы лояльности: -")
        self.ui.lbOrdersCount.setText("Количество заказов: -")
        self.ui.lbOrdersTotal.setText("Общая сумма: -")

    def search_client(self):
        client_search = self.ui.leClientSearch.text().strip()

        if not client_search:
            QMessageBox.warning(self.ui, "Ошибка", "Введите ФИО клиента или часть ФИО")
            return

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT client_id, full_name, phone, email, loyalty_points
                    FROM clients
                    WHERE LOWER(full_name) LIKE LOWER(%s)
                    ORDER BY full_name;
                """, (f"%{client_search}%",))

                clients = cur.fetchall()

            if not clients:
                self.clear_search()
                QMessageBox.information(self.ui, "Информация", "Клиент не найден")
                return

            selected_client = None

            if len(clients) == 1:
                selected_client = clients[0]
            else:
                items = [
                    f"{client[1]} | {client[2] or 'телефон не указан'} | {client[3] or 'email не указан'}"
                    for client in clients
                ]

                selected_text, ok = QInputDialog.getItem(
                    self.ui,
                    "Выбор клиента",
                    "Найдено несколько клиентов. Выберите нужного:",
                    items,
                    0,
                    False
                )

                if not ok:
                    return

                selected_index = items.index(selected_text)
                selected_client = clients[selected_index]

            self.load_client_report(selected_client)

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def load_client_report(self, client):
        client_id, full_name, phone, email, loyalty_points = client

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        TO_CHAR(o.order_date_time, 'DD.MM.YYYY HH24:MI') AS order_dt,
                        o.status AS order_status,
                        p.status AS payment_status,
                        p.amount
                    FROM orders o
                    LEFT JOIN payments p ON p.payment_id = o.payment_id
                    WHERE o.client_id = %s
                    ORDER BY o.order_date_time DESC, o.order_id DESC;
                """, (client_id,))

                self.report_rows = cur.fetchall()

            orders_count = len(self.report_rows)
            orders_total = sum(float(row[3] or 0) for row in self.report_rows)

            self.current_client_info = {
                "client_id": client_id,
                "full_name": full_name,
                "phone": phone,
                "email": email,
                "loyalty_points": loyalty_points,
                "orders_count": orders_count,
                "orders_total": orders_total,
            }

            self.ui.lbClientName.setText(f"ФИО: {full_name}")
            self.ui.lbClientPhone.setText(f"Телефон: {phone or '-'}")
            self.ui.lbClientEmail.setText(f"Email: {email or '-'}")
            self.ui.lbClientPoints.setText(f"Баллы лояльности: {loyalty_points or 0}")
            self.ui.lbOrdersCount.setText(f"Количество заказов: {orders_count}")
            self.ui.lbOrdersTotal.setText(f"Общая сумма: {orders_total:.2f} руб.")

            self.ui.twOrders.clearContents()
            self.ui.twOrders.setRowCount(len(self.report_rows))

            for i, row in enumerate(self.report_rows):
                for j, value in enumerate(row):
                    text = "-" if value is None or str(value).strip() == "" else str(value)
                    self.ui.twOrders.setItem(i, j, QTableWidgetItem(text))

            self.ui.twOrders.resizeColumnsToContents()

            if not self.report_rows:
                QMessageBox.information(self.ui, "Информация", "У выбранного клиента нет заказов")

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def clear_search(self):
        self.ui.leClientSearch.clear()

        self.ui.twOrders.clearContents()
        self.ui.twOrders.setRowCount(0)

        self.report_rows = []
        self.clear_client_info()

    def save_pdf(self):
        if self.current_client_info is None:
            QMessageBox.warning(self.ui, "Ошибка", "Сначала выберите клиента")
            return

        if not self.report_rows:
            QMessageBox.warning(self.ui, "Ошибка", "Нет заказов для сохранения")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self.ui,
            "Сохранить отчёт в PDF",
            "client_report.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_name:
            return

        if not file_name.endswith(".pdf"):
            file_name += ".pdf"

        try:
            client = self.current_client_info

            full_name = html.escape(str(client["full_name"] or "-"))
            phone = html.escape(str(client["phone"] or "-"))
            email = html.escape(str(client["email"] or "-"))
            loyalty_points = html.escape(str(client["loyalty_points"] or 0))
            orders_count = html.escape(str(client["orders_count"]))
            orders_total = f'{client["orders_total"]:.2f} руб.'

            html_text = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        font-size: 10pt;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 16pt;
                        margin-bottom: 15px;
                    }}
                    .info {{
                        margin-bottom: 15px;
                        font-size: 10pt;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    th, td {{
                        border: 1px solid #000;
                        padding: 5px;
                        vertical-align: top;
                    }}
                    th {{
                        background-color: #eeeeee;
                        font-weight: bold;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <h1>Отчёт по клиенту</h1>

                <div class="info">
                    <p><b>ФИО:</b> {full_name}</p>
                    <p><b>Телефон:</b> {phone}</p>
                    <p><b>Email:</b> {email}</p>
                    <p><b>Баллы лояльности:</b> {loyalty_points}</p>
                    <p><b>Количество заказов:</b> {orders_count}</p>
                    <p><b>Общая сумма заказов:</b> {orders_total}</p>
                </div>

                <table>
                    <tr>
                        <th>Дата заказа</th>
                        <th>Статус заказа</th>
                        <th>Статус оплаты</th>
                        <th>Сумма</th>
                    </tr>
            """

            for row in self.report_rows:
                formatted_row = [
                    "-" if value is None or str(value).strip() == "" else str(value)
                    for value in row
                ]

                html_text += "<tr>"
                for value in formatted_row:
                    html_text += f"<td>{html.escape(str(value))}</td>"
                html_text += "</tr>"

            html_text += """
                </table>
            </body>
            </html>
            """

            document = QTextDocument()
            document.setHtml(html_text)

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_name)
            printer.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Millimeter)

            document.print_(printer)

            QMessageBox.information(self.ui, "Успех", "Отчёт сохранён в PDF")

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка", str(e))