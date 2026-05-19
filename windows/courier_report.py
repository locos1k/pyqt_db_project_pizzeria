from PySide6.QtWidgets import (
    QMessageBox,
    QTableWidgetItem,
    QFileDialog,
    QHeaderView,
    QAbstractItemView,
)

from PySide6.QtGui import QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF

from windows.base import load_ui
from db import get_connection


class CourierReport:
    def __init__(self, parent_window, courier_id):
        self.parent_window = parent_window
        self.courier_id = courier_id
        self.ui = load_ui("courier_report.ui")
        self.ui.setWindowTitle("АИС «Круглосуточная пицца на дом» – Отчет по курьеру")

        self.courier_info = None
        self.report_rows = []

        self.ui.btnBack.clicked.connect(self.back)
        self.ui.btnSavePdf.clicked.connect(self.save_pdf)

        self.setup_table()
        self.load_report()

    def show(self):
        self.ui.show()

    def back(self):
        self.ui.close()
        self.parent_window.show()

    def setup_table(self):
        self.ui.twReport.setColumnCount(7)
        self.ui.twReport.setHorizontalHeaderLabels([
            "№ заказа",
            "Клиент",
            "Адрес",
            "Дата заказа",
            "Статус заказа",
            "Статус оплаты",
            "Сумма",
        ])

        self.ui.twReport.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.twReport.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twReport.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.twReport.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.twReport.horizontalHeader().setStretchLastSection(True)

    def load_report(self):
        try:
            conn = get_connection()

            with conn.cursor() as cur:
                cur.execute("""
                    SELECT full_name, phone, rating, status
                    FROM couriers
                    WHERE courier_id = %s;
                """, (self.courier_id,))

                self.courier_info = cur.fetchone()

                if self.courier_info is None:
                    QMessageBox.warning(self.ui, "Ошибка", "Курьер не найден")
                    conn.close()
                    return

                cur.execute("""
                    SELECT
                        o.order_id,
                        cl.full_name AS client_name,
                        a.city || ', ' || a.street || ', д. ' || a.house ||
                            COALESCE(', кв. ' || a.apartment, '') AS full_address,
                        TO_CHAR(o.order_date_time, 'DD.MM.YYYY HH24:MI') AS order_dt,
                        o.status AS order_status,
                        p.status AS payment_status,
                        p.amount
                    FROM orders o
                    JOIN clients cl ON cl.client_id = o.client_id
                    LEFT JOIN addresses a ON a.address_id = o.address_id
                    LEFT JOIN payments p ON p.payment_id = o.payment_id
                    WHERE o.courier_id = %s
                    ORDER BY o.order_date_time DESC, o.order_id DESC;
                """, (self.courier_id,))

                self.report_rows = cur.fetchall()

            conn.close()

            full_name, phone, rating, status = self.courier_info
            orders_count = len(self.report_rows)

            self.ui.lbCourierInfo.setText(
                f"Курьер: {full_name} | Телефон: {phone} | Рейтинг: {rating} | Статус: {status}"
            )

            self.ui.lbOrdersCount.setText(
                f"Количество заказов: {orders_count}"
            )

            self.ui.twReport.clearContents()
            self.ui.twReport.setRowCount(len(self.report_rows))

            for i, row in enumerate(self.report_rows):
                for j, value in enumerate(row):
                    text = "-" if value is None or str(value).strip() == "" else str(value)
                    self.ui.twReport.setItem(i, j, QTableWidgetItem(text))

            self.ui.twReport.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def save_pdf(self):
        if not self.report_rows:
            QMessageBox.warning(self.ui, "Ошибка", "Нет данных для сохранения")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self.ui,
            "Сохранить отчёт в PDF",
            f"courier_{self.courier_id}_report.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_name:
            return

        if not file_name.endswith(".pdf"):
            file_name += ".pdf"

        try:
            full_name, phone, rating, status = self.courier_info
            orders_count = len(self.report_rows)

            html = f"""
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
                        font-size: 18pt;
                        margin-bottom: 20px;
                    }}
                    .courier-info {{
                        margin-bottom: 20px;
                        font-size: 11pt;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    th, td {{
                        border: 1px solid #000;
                        padding: 5px;
                        vertical-align: top;
                        word-wrap: break-word;
                    }}
                    th {{
                        background-color: #eeeeee;
                        font-weight: bold;
                        text-align: center;
                    }}
                    td {{
                        font-size: 9pt;
                    }}
                </style>
            </head>
            <body>
                <h1>Отчёт по курьеру</h1>

                <div class="courier-info">
                    <p><b>ФИО:</b> {full_name}</p>
                    <p><b>Телефон:</b> {phone}</p>
                    <p><b>Рейтинг:</b> {rating}</p>
                    <p><b>Статус:</b> {status}</p>
                    <p><b>Количество заказов:</b> {orders_count}</p>
                </div>

                <table>
                    <tr>
                        <th>№ заказа</th>
                        <th>Клиент</th>
                        <th>Адрес</th>
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

                html += "<tr>"
                for value in formatted_row:
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
            printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)

            document.print_(printer)

            QMessageBox.information(self.ui, "Успех", "Отчёт сохранён в PDF")

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка", str(e))