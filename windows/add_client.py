from PySide6.QtWidgets import QMessageBox
import re

from windows.base import load_ui
from db import get_connection


class AddClient:
    def __init__(self, parent_window, after_save_callback=None):
        self.parent_window = parent_window
        self.after_save_callback = after_save_callback
        self.ui = load_ui("add_client.ui")
        self.ui.setWindowTitle("АИС «Круглосуточная пицца на дом» – Добавление клиента")

        self.ui.leLoyaltyPoints.setText("0")

        self.ui.btnSave.clicked.connect(self.save_client)
        self.ui.btnCancel.clicked.connect(self.cancel)

    def show(self):
        self.ui.show()

    def save_client(self):
        full_name = self.ui.leFullName.text().strip()
        phone = self.ui.lePhone.text().strip()
        email = self.ui.leEmail.text().strip()
        loyalty_points_text = self.ui.leLoyaltyPoints.text().strip()

        if not full_name:
            QMessageBox.warning(self.ui, "Ошибка", "Введите ФИО клиента")
            return

        if not phone or not self.is_valid_phone(phone):
            QMessageBox.warning(self.ui, "Ошибка", "Введите номер телефона")
            return

        if not email:
            QMessageBox.warning(self.ui, "Ошибка", "Введите электронную почту")
            return
        
        if not self.is_valid_email(email):
            QMessageBox.warning(self.ui, "Ошибка", "Электронная почта должна содержать только латинские символы, обязательно @ и точку")
            return

        try:
            loyalty_points = int(loyalty_points_text or 0)
            if loyalty_points < 0:
                QMessageBox.warning(self.ui, "Ошибка", "Баллы лояльности не могут быть отрицательными")
                return
        except ValueError:
            QMessageBox.warning(self.ui, "Ошибка", "Баллы лояльности должны быть числом")
            return

        conn = None

        try:
            conn = get_connection()

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO clients(full_name, phone, email, loyalty_points)
                    VALUES (%s, %s, %s, %s)
                    RETURNING client_id;
                """, (full_name, phone, email, loyalty_points))

                new_client_id = cur.fetchone()[0]

            conn.commit()

            QMessageBox.information(self.ui, "Успех", "Клиент добавлен")

            self.ui.close()

            if self.after_save_callback:
                self.after_save_callback(new_client_id)
            else:
                self.parent_window.show()

        except Exception as e:
            if conn:
                conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

        finally:
            if conn:
                conn.close()

    def is_valid_phone(self, phone):
        return re.fullmatch(r"\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}", phone) is not None

    def is_valid_email(self, email):
        return re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email) is not None

    def cancel(self):
        self.ui.close()
        self.parent_window.show()