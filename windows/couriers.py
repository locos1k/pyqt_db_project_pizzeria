from PySide6.QtWidgets import QMessageBox

from windows.base import load_ui
from db import get_connection


class Couriers:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.ui = load_ui("couriers.ui")

        self.conn = None
        self.couriers_data = []
        self.current_courier_index = 0

        self.ui.leCourierId.hide()

        self.ui.cbStatus.clear()
        self.ui.cbStatus.addItems(["active", "on_delivery", "inactive"])

        self.ui.btnBack.clicked.connect(self.back)
        self.ui.btnPrev.clicked.connect(self.prev_courier)
        self.ui.btnNext.clicked.connect(self.next_courier)

        self.ui.btnAddCourier.clicked.connect(self.add_courier)
        self.ui.btnEditCourier.clicked.connect(self.edit_courier)
        self.ui.btnDeleteCourier.clicked.connect(self.delete_courier)

        self.ui.btnCourierOrders.clicked.connect(self.open_courier_orders)
        self.ui.btnOpenReport.clicked.connect(self.open_report)

        self.load_couriers()

    def show(self):
        self.ui.show()

    def back(self):
        self.ui.close()
        self.parent_window.show()

    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = get_connection()

    def load_couriers(self):
        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT courier_id, full_name, phone, rating, status
                    FROM couriers
                    ORDER BY courier_id;
                """)
                self.couriers_data = cur.fetchall()

            if not self.couriers_data:
                QMessageBox.information(self.ui, "Информация", "Курьеры не найдены")
                self.clear_fields()
                return

            if self.current_courier_index >= len(self.couriers_data):
                self.current_courier_index = len(self.couriers_data) - 1

            self.show_current_courier()

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def show_current_courier(self):
        if not self.couriers_data:
            return

        courier = self.couriers_data[self.current_courier_index]

        courier_id, full_name, phone, rating, status = courier

        self.ui.leCourierId.setText(str(courier_id))
        self.ui.leFullName.setText(full_name or "")
        self.ui.lePhone.setText(phone or "")
        self.ui.leRating.setText(str(rating or 0))

        index = self.ui.cbStatus.findText(status)
        if index >= 0:
            self.ui.cbStatus.setCurrentIndex(index)

    def prev_courier(self):
        if not self.couriers_data:
            return

        if self.current_courier_index > 0:
            self.current_courier_index -= 1
            self.show_current_courier()

    def next_courier(self):
        if not self.couriers_data:
            return

        if self.current_courier_index < len(self.couriers_data) - 1:
            self.current_courier_index += 1
            self.show_current_courier()

    def clear_fields(self):
        self.ui.leCourierId.clear()
        self.ui.leFullName.clear()
        self.ui.lePhone.clear()
        self.ui.leRating.clear()
        self.ui.cbStatus.setCurrentIndex(0)

    def add_courier(self):
        self.ui.leCourierId.clear()
        self.ui.leFullName.clear()
        self.ui.lePhone.clear()
        self.ui.leRating.setText("0")
        self.ui.cbStatus.setCurrentIndex(0)

        QMessageBox.information(
            self.ui,
            "Добавление",
            "Введите данные нового курьера и нажмите «Сохранить»"
        )

    def edit_courier(self):
        full_name = self.ui.leFullName.text().strip()
        phone = self.ui.lePhone.text().strip()
        rating_text = self.ui.leRating.text().strip()
        status = self.ui.cbStatus.currentText()

        if not full_name:
            QMessageBox.warning(self.ui, "Ошибка", "Введите ФИО курьера")
            return

        if not phone:
            QMessageBox.warning(self.ui, "Ошибка", "Введите телефон курьера")
            return

        try:
            rating = float(rating_text or 0)
        except ValueError:
            QMessageBox.warning(self.ui, "Ошибка", "Рейтинг должен быть числом")
            return

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                if self.ui.leCourierId.text():
                    courier_id = int(self.ui.leCourierId.text())

                    cur.execute("""
                        UPDATE couriers
                        SET full_name = %s,
                            phone = %s,
                            rating = %s,
                            status = %s
                        WHERE courier_id = %s;
                    """, (full_name, phone, rating, status, courier_id))

                    message = "Данные курьера сохранены"

                else:
                    cur.execute("""
                        INSERT INTO couriers(full_name, phone, rating, status)
                        VALUES (%s, %s, %s, %s)
                        RETURNING courier_id;
                    """, (full_name, phone, rating, status))

                    new_courier_id = cur.fetchone()[0]
                    message = "Курьер добавлен"

            self.conn.commit()

            QMessageBox.information(self.ui, "Успех", message)

            self.load_couriers()

            if not self.ui.leCourierId.text():
                return

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def delete_courier(self):
        if not self.ui.leCourierId.text():
            QMessageBox.warning(self.ui, "Ошибка", "Курьер не выбран")
            return

        answer = QMessageBox.question(
            self.ui,
            "Удаление",
            "Удалить выбранного курьера?",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        try:
            self.connect_db()

            courier_id = int(self.ui.leCourierId.text())

            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM couriers
                    WHERE courier_id = %s;
                """, (courier_id,))

            self.conn.commit()

            QMessageBox.information(self.ui, "Успех", "Курьер удалён")

            self.load_couriers()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def open_courier_orders(self):
        if not self.ui.leCourierId.text():
            QMessageBox.warning(self.ui, "Ошибка", "Курьер не выбран")
            return

        courier_id = int(self.ui.leCourierId.text())

        from windows.orders import Orders

        self.orders_window = Orders(
            parent_window=self,
            courier_id=courier_id,
            mode="admin"
        )
        self.orders_window.show()
        self.ui.close()

    def open_report(self):
        if not self.ui.leCourierId.text():
            QMessageBox.warning(self.ui, "Ошибка", "Курьер не выбран")
            return

        from windows.courier_report import CourierReport

        courier_id = int(self.ui.leCourierId.text())

        self.courier_report_window = CourierReport(self, courier_id)
        self.courier_report_window.show()
        self.ui.close()