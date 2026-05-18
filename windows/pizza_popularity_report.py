from PySide6.QtWidgets import (
    QMessageBox,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QVBoxLayout,
)

from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)

from PySide6.QtGui import QTextDocument, QPageLayout, QPainter, QFont
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF, Qt, QMargins

from windows.base import load_ui
from db import get_connection


class PizzaPopularityReport:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.ui = load_ui("pizza_popularity_report.ui")

        self.report_rows = []
        self.chart_view = None

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
        self.ui.twReport.setColumnCount(3)
        self.ui.twReport.setHorizontalHeaderLabels([
            "Пицца",
            "Количество",
            "Общая сумма",
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
                        p.name,
                        COALESCE(SUM(op.quantity), 0) AS total_quantity,
                        COALESCE(SUM(op.quantity * p.price), 0) AS total_amount
                    FROM pizza p
                    LEFT JOIN orderpizza op ON op.pizza_id = p.pizza_id
                    GROUP BY p.pizza_id, p.name
                    ORDER BY total_quantity DESC, p.name;
                """)

                self.report_rows = cur.fetchall()

            conn.close()

            self.fill_table()
            self.build_chart()

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def fill_table(self):
        self.ui.twReport.clearContents()
        self.ui.twReport.setRowCount(len(self.report_rows))

        for i, row in enumerate(self.report_rows):
            pizza_name = str(row[0])
            quantity = str(row[1])
            total_amount = f"{float(row[2]):.2f}"

            self.ui.twReport.setItem(i, 0, QTableWidgetItem(pizza_name))
            self.ui.twReport.setItem(i, 1, QTableWidgetItem(quantity))
            self.ui.twReport.setItem(i, 2, QTableWidgetItem(total_amount))

        self.ui.twReport.resizeColumnsToContents()

    def build_chart(self):
        if self.chart_view is not None:
            layout = self.ui.chartWidget.layout()
            if layout is not None:
                layout.removeWidget(self.chart_view)

            self.chart_view.deleteLater()
            self.chart_view = None

        bar_set = QBarSet("Количество заказанных пицц")
        bar_set.setColor("#ff9800")

        categories = []
        max_quantity = 0

        for row in self.report_rows[:10]:
            pizza_name = str(row[0])
            quantity = int(row[1] or 0)

            categories.append(pizza_name)
            bar_set.append(quantity)

            if quantity > max_quantity:
                max_quantity = quantity

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Диаграмма популярности пицц")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        chart.setTheme(QChart.ChartThemeDark)
        chart.setBackgroundBrush(Qt.transparent)
        chart.setPlotAreaBackgroundVisible(False)
        chart.setMargins(QMargins(10, 10, 10, 60))

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)

        font = QFont()
        font.setPointSize(10)
        axis_x.setLabelsFont(font)
        axis_x.setLabelsAngle(-35)

        axis_y = QValueAxis()
        axis_y.setRange(0, max_quantity + 1)
        axis_y.setLabelFormat("%d")

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)

        self.chart_view = QChartView(chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        self.chart_view.setMinimumHeight(360)

        layout = self.ui.chartWidget.layout()
        if layout is None:
            layout = QVBoxLayout(self.ui.chartWidget)
            self.ui.chartWidget.setLayout(layout)

        layout.addWidget(self.chart_view)

    def save_pdf(self):
        if not self.report_rows:
            QMessageBox.warning(self.ui, "Ошибка", "Нет данных для сохранения")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self.ui,
            "Сохранить отчёт в PDF",
            "pizza_popularity_report.pdf",
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
                    }
                    th {
                        background-color: #eeeeee;
                        font-weight: bold;
                        text-align: center;
                    }
                </style>
            </head>
            <body>
                <h1>Аналитика популярности пицц</h1>

                <table>
                    <tr>
                        <th>Пицца</th>
                        <th>Количество заказанных штук</th>
                        <th>Общая сумма</th>
                    </tr>
            """

            for row in self.report_rows:
                pizza_name = "-" if row[0] is None else str(row[0])
                quantity = "-" if row[1] is None else str(row[1])
                total_amount = f"{float(row[2] or 0):.2f}"

                html += f"""
                    <tr>
                        <td>{pizza_name}</td>
                        <td>{quantity}</td>
                        <td>{total_amount}</td>
                    </tr>
                """

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