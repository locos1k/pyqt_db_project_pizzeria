from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt

from windows.base import load_ui
from db import get_connection


class CreateOrder:
    def __init__(self, operator_menu):
        self.operator_menu = operator_menu
        self.ui = load_ui("create_order.ui")

        self.conn = None
        self.order_items = []
        self.is_refreshing_table = False

        self.ui.btnBack.clicked.connect(self.back)
        self.ui.btnAddPizza.clicked.connect(self.add_pizza_to_order)
        self.ui.btnRemovePizza.clicked.connect(self.remove_pizza_from_order)
        self.ui.btnClearOrder.clicked.connect(self.clear_order)
        self.ui.btnSaveOrder.clicked.connect(self.save_order)
        self.ui.btnNewClient.clicked.connect(self.open_add_client)
        self.ui.btnNewAddress.clicked.connect(self.open_add_address)

        self.ui.cbClient.currentIndexChanged.connect(self.load_addresses_for_client)
        self.ui.twOrderItems.itemChanged.connect(self.on_order_item_changed)

        self.setup_table()
        self.setup_static_values()
        self.load_initial_data()

    def show(self):
        self.ui.show()

    def back(self):
        self.ui.close()
        self.operator_menu.show()

    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = get_connection()

    def setup_table(self):
        self.ui.twOrderItems.setColumnCount(5)
        self.ui.twOrderItems.setHorizontalHeaderLabels([
            "Pizza ID", "Пицца", "Количество", "Цена", "Сумма"
        ])

        self.ui.twOrderItems.setColumnHidden(0, True)
        self.ui.twOrderItems.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ui.twOrderItems.horizontalHeader().setStretchLastSection(True)

        self.ui.twOrderItems.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self.ui.twOrderItems.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.twOrderItems.setSelectionMode(QAbstractItemView.SingleSelection)

    def setup_static_values(self):
        self.ui.cbPaymentMethod.clear()
        self.ui.cbPaymentMethod.addItems([
            "cash",
            "card",
            "online"
        ])

        self.ui.sbQuantity.setMinimum(1)
        self.ui.sbQuantity.setMaximum(100)
        self.ui.sbQuantity.setValue(1)

    def load_initial_data(self):
        try:
            self.connect_db()
            self.load_clients()
            self.load_couriers()
            self.load_pizza()

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def load_clients(self):
        self.ui.cbClient.clear()

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT client_id, full_name
                FROM clients
                ORDER BY full_name;
            """)
            rows = cur.fetchall()

        for client_id, full_name in rows:
            self.ui.cbClient.addItem(full_name, client_id)

        self.load_addresses_for_client()

    def load_addresses_for_client(self):
        self.ui.cbAddress.clear()

        client_id = self.ui.cbClient.currentData()
        if client_id is None:
            return

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        address_id,
                        city || ', ' || street || ', д. ' || house ||
                            COALESCE(', кв. ' || apartment, '') AS full_address
                    FROM addresses
                    WHERE client_id = %s
                    ORDER BY address_id;
                """, (client_id,))
                rows = cur.fetchall()

            for address_id, full_address in rows:
                self.ui.cbAddress.addItem(full_address, address_id)

        except Exception as e:
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))

    def load_couriers(self):
        self.ui.cbCourier.clear()

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT courier_id, full_name
                FROM couriers
                WHERE status = 'active'
                ORDER BY full_name;
                
            """)
            rows = cur.fetchall()

        for courier_id, full_name in rows:
            self.ui.cbCourier.addItem(full_name, courier_id)

    def load_pizza(self):
        self.ui.cbPizza.clear()

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT pizza_id, name, price
                FROM pizza
                WHERE is_active = true
                ORDER BY name;
            """)
            rows = cur.fetchall()

        for pizza_id, name, price in rows:
            self.ui.cbPizza.addItem(f"{name} — {price} руб.", {
                "pizza_id": pizza_id,
                "name": name,
                "price": float(price)
            })

    def add_pizza_to_order(self):
        pizza_data = self.ui.cbPizza.currentData()

        if pizza_data is None:
            QMessageBox.warning(self.ui, "Ошибка", "Выберите пиццу")
            return

        quantity = self.ui.sbQuantity.value()
        pizza_id = pizza_data["pizza_id"]
        name = pizza_data["name"]
        price = pizza_data["price"]

        for item in self.order_items:
            if item["pizza_id"] == pizza_id:
                item["quantity"] += quantity
                item["total"] = item["price"] * item["quantity"]
                self.refresh_order_items_table()
                return

        self.order_items.append({
            "pizza_id": pizza_id,
            "name": name,
            "quantity": quantity,
            "price": price,
            "total": price * quantity
        })

        self.refresh_order_items_table()

    def refresh_order_items_table(self):
        self.is_refreshing_table = True

        self.ui.twOrderItems.clearContents()
        self.ui.twOrderItems.setRowCount(len(self.order_items))

        for i, item in enumerate(self.order_items):
            pizza_id_item = QTableWidgetItem(str(item["pizza_id"]))
            name_item = QTableWidgetItem(item["name"])
            quantity_item = QTableWidgetItem(str(item["quantity"]))
            price_item = QTableWidgetItem(f"{item['price']:.2f}")
            total_item = QTableWidgetItem(f"{item['total']:.2f}")

            pizza_id_item.setFlags(pizza_id_item.flags() & ~Qt.ItemIsEditable)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)

            self.ui.twOrderItems.setItem(i, 0, pizza_id_item)
            self.ui.twOrderItems.setItem(i, 1, name_item)
            self.ui.twOrderItems.setItem(i, 2, quantity_item)
            self.ui.twOrderItems.setItem(i, 3, price_item)
            self.ui.twOrderItems.setItem(i, 4, total_item)

        self.ui.twOrderItems.resizeColumnsToContents()
        self.ui.twOrderItems.setColumnHidden(0, True)

        order_total = sum(item["total"] for item in self.order_items)
        self.ui.lbTotal.setText(f"Итого: {order_total:.2f} руб.")

        self.is_refreshing_table = False

    def on_order_item_changed(self, item):
        if self.is_refreshing_table:
            return

        row = item.row()
        column = item.column()

        if column != 2:
            self.refresh_order_items_table()
            return

        try:
            new_quantity = int(item.text())

            if new_quantity <= 0:
                QMessageBox.warning(self.ui, "Ошибка", "Количество должно быть больше 0")
                self.refresh_order_items_table()
                return

            self.order_items[row]["quantity"] = new_quantity
            self.order_items[row]["total"] = self.order_items[row]["price"] * new_quantity

            self.refresh_order_items_table()

        except ValueError:
            QMessageBox.warning(self.ui, "Ошибка", "Количество должно быть целым числом")
            self.refresh_order_items_table()

    def remove_pizza_from_order(self):
        row = self.ui.twOrderItems.currentRow()

        if row < 0:
            QMessageBox.warning(self.ui, "Ошибка", "Выберите позицию для удаления")
            return

        self.order_items.pop(row)
        self.refresh_order_items_table()

    def clear_order(self):
        self.order_items.clear()
        self.ui.teComment.clear()
        self.ui.sbQuantity.setValue(1)
        self.refresh_order_items_table()

    def open_add_client(self):
        from windows.add_client import AddClient

        self.add_client_window = AddClient(
            parent_window=self,
            after_save_callback=self.after_client_added
        )
        self.add_client_window.show()
        self.ui.close()

    def after_client_added(self, new_client_id):
        self.ui.show()
        self.load_clients()

        index = self.ui.cbClient.findData(new_client_id)
        if index >= 0:
            self.ui.cbClient.setCurrentIndex(index)

        self.load_addresses_for_client()

    def open_add_address(self):
        client_id = self.ui.cbClient.currentData()

        if client_id is None:
            QMessageBox.warning(self.ui, "Ошибка", "Сначала выберите клиента")
            return

        from windows.add_address import AddAddress

        self.add_address_window = AddAddress(
            parent_window=self,
            client_id=client_id,
            after_save_callback=self.after_address_added
        )
        self.add_address_window.show()
        self.ui.close()

    def after_address_added(self, new_address_id):
        self.ui.show()
        self.load_addresses_for_client()

        index = self.ui.cbAddress.findData(new_address_id)
        if index >= 0:
            self.ui.cbAddress.setCurrentIndex(index)

    def save_order(self):
        client_id = self.ui.cbClient.currentData()
        address_id = self.ui.cbAddress.currentData()
        courier_id = self.ui.cbCourier.currentData()
        order_status = "created"
        payment_method = self.ui.cbPaymentMethod.currentText()
        comment = self.ui.teComment.toPlainText().strip()

        if client_id is None:
            QMessageBox.warning(self.ui, "Ошибка", "Выберите клиента")
            return

        if address_id is None:
            QMessageBox.warning(self.ui, "Ошибка", "Выберите адрес доставки")
            return

        if courier_id is None:
            QMessageBox.warning(self.ui, "Ошибка", "Выберите курьера")
            return

        if not self.order_items:
            QMessageBox.warning(self.ui, "Ошибка", "Добавьте хотя бы одну пиццу в заказ")
            return

        order_total = sum(item["total"] for item in self.order_items)

        try:
            self.connect_db()

            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO payments(status, amount, method)
                    VALUES (%s, %s, %s)
                    RETURNING payment_id;
                """, (
                    "created",
                    order_total,
                    payment_method
                ))

                payment_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO orders(
                        client_id,
                        address_id,
                        courier_id,
                        order_date_time,
                        delivered_date_time,
                        comment,
                        status,
                        payment_id,
                        order_date
                    )
                    VALUES (
                        %s, %s, %s,
                        CURRENT_TIMESTAMP,
                        NULL,
                        %s,
                        %s,
                        %s,
                        CURRENT_DATE
                    )
                    RETURNING order_id;
                """, (
                    client_id,
                    address_id,
                    courier_id,
                    comment if comment else None,
                    order_status,
                    payment_id
                ))

                order_id = cur.fetchone()[0]

                for item in self.order_items:
                    cur.execute("""
                        INSERT INTO orderpizza(order_id, pizza_id, quantity)
                        VALUES (%s, %s, %s);
                    """, (
                        order_id,
                        item["pizza_id"],
                        item["quantity"]
                    ))

            self.conn.commit()

            QMessageBox.information(
                self.ui,
                "Успех",
                f"Заказ №{order_id} успешно создан"
            )

            self.clear_order()
            self.load_couriers()

        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self.ui, "Ошибка БД", str(e))