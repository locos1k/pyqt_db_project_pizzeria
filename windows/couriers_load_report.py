from PySide6.QtWidgets import (
    QMessageBox,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
)

from PySide6.QtGui import QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF

from windows.base import load_ui
from db import get_connection


class CouriersLoadReport:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.ui = load_ui("couriers_load_report.ui")

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
            "Курьер",
            "Телефон",
            "Статус",
            "Кол-во заказов",
            "Доставлено",
            "Общая сумма",
            "Средний этаж",
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
                    SELECT
                        c.full_name AS courier_name,
                        c.phone,
                        c.status,
                        COUNT(o.order_id) AS orders_count,
                        COUNT(o.order_id) FILTER (WHERE o.status = 'delivered') AS delivered_count,
                        COALESCE(SUM(p.amount), 0) AS total_amount,
                        ROUND(AVG(a.floor), 2) AS avg_floor
                    FROM couriers c
                    LEFT JOIN orders o ON o.courier_id = c.courier_id
                    LEFT JOIN payments p ON p.payment_id = o.payment_id
                    LEFT JOIN addresses a ON a.address_id = o.address_id
                    GROUP BY c.courier_id, c.full_name, c.phone, c.status
                    ORDER BY orders_count DESC, delivered_count DESC, c.full_name;
                """)

                self.report_rows = cur.fetchall()

            conn.close()

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
            "couriers_load_report.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_name:
            return

        if not file_name.endswith(".pdf"):
            file_name += ".pdf"

        try:
            html = """
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        font-size: 10pt;
                    }
                    h1 {
                        text-align: center;
                        font-size: 18pt;
                        margin-bottom: 20px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    th, td {
                        border: 1px solid #000;
                        padding: 5px;
                        vertical-align: top;
                        word-wrap: break-word;
                    }
                    th {
                        background-color: #eeeeee;
                        font-weight: bold;
                        text-align: center;
                    }
                    td {
                        font-size: 9pt;
                    }
                </style>
            </head>
            <body>
                <h1>Отчёт по нагрузке на курьеров</h1>

                <table>
                    <tr>
                        <th>Курьер</th>
                        <th>Телефон</th>
                        <th>Статус</th>
                        <th>Кол-во заказов</th>
                        <th>Доставлено</th>
                        <th>Общая сумма</th>
                        <th>Средний этаж</th>
                    </tr>
            """

            for row in self.report_rows:
                html += "<tr>"

                for value in row:
                    text = "-" if value is None or str(value).strip() == "" else str(value)
                    html += f"<td>{text}</td>"

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