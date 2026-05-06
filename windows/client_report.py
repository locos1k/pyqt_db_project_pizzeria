import csv
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QFileDialog, QHeaderView
from PySide6.QtGui import QPdfWriter, QPainter, QFont, QPageSize, QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF

from windows.base import load_ui
from db import get_connection


class ClientReport:
    def __init__(self, parent_window, client_id, client_name):
        self.parent_window = parent_window
        self.client_id = client_id
        self.client_name = client_name

        self.ui = load_ui("client_report.ui")
        self.report_rows = []

        self.ui.lbTitle.setText("Отчёт по клиенту")
        self.ui.lbClientInfo.setText(f"Клиент: {self.client_name}")

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
            "Номер заказа",
            "Адрес",
            "Курьер",
            "Дата заказа",
            "Комментарий",
            "Статус заказа",
            "Статус оплаты"
        ])

        self.ui.twReport.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.twReport.horizontalHeader().setStretchLastSection(True)

    def load_report(self):
        try:
            conn = get_connection()

            with conn.cursor() as cur:
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
                    ORDER BY o.order_date_time;
                """, (self.client_id,))

                self.report_rows = cur.fetchall()

            conn.close()

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
            f"client_{self.client_id}_report.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_name:
            return

        if not file_name.endswith(".pdf"):
            file_name += ".pdf"

        try:
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
                    .client-info {{
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
                <h1>Отчёт по клиенту</h1>

                <div class="client-info">
                    <p><b>Клиент:</b> {self.client_name}</p>
                    <p><b>ID клиента:</b> {self.client_id}</p>
                </div>

                <table>
                    <tr>
                        <th>№ заказа</th>
                        <th>Адрес</th>
                        <th>Курьер</th>
                        <th>Дата заказа</th>
                        <th>Комментарий</th>
                        <th>Статус</th>
                        <th>Оплата</th>
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