from PySide6.QtWidgets import QMessageBox

from windows.base import load_ui
from db import get_connection


class AddAddress:
    def __init__(self, parent_window, client_id, after_save_callback=None):
        self.parent_window = parent_window
        self.client_id = client_id
        self.after_save_callback = after_save_callback

        self.ui = load_ui("add_address.ui")

        self.ui.leCity.setText("Москва")

        self.ui.btnSave.clicked.connect(self.save_address)
        self.ui.btnCancel.clicked.connect(self.cancel)

    def show(self):
        self.ui.show()

    def save_address(self):
        city = self.ui.leCity.text().strip()
        street = self.ui.leStreet.text().strip()
        house = self.ui.leHouse.text().strip()
        apartment = self.ui.leApartment.text().strip()
        floor_text = self.ui.leFloor.text().strip()
        comment = self.ui.teComment.toPlainText().strip()

        if not city:
            QMessageBox.warning(self.ui, "Ошибка", "Введите город")
            return

        if not street:
            QMessageBox.warning(self.ui, "Ошибка", "Введите улицу")
            return

        if not house:
            QMessageBox.warning(self.ui, "Ошибка", "Введите дом")
            return

        try:
            floor = int(floor_text) if floor_text else None
        except ValueError:
            QMessageBox.warning(self.ui, "Ошибка", "Этаж должен быть числом")
            return

        apartment = apartment if apartment else None
        comment = comment if comment else None

        conn = None

        try:
            conn = get_connection()

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO addresses(client_id, city, street, house, apartment, floor, comment)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING address_id;
                """, (
                    self.client_id,
                    city,
                    street,
                    house,
                    apartment,
                    floor,
                    comment
                ))

                new_address_id = cur.fetchone()[0]

            conn.commit()

            QMessageBox.information(self.ui, "Успех", "Адрес добавлен")

            self.ui.close()

            if self.after_save_callback:
                self.after_save_callback(new_address_id)
            else:
                self.parent_window.show()

        except Exception as e:
            if conn:
                conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

        finally:
            if conn:
                conn.close()

    def cancel(self):
        self.ui.close()
        self.parent_window.show()