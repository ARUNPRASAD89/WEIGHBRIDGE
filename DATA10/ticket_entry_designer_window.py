from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QGroupBox, QDoubleSpinBox, QFileDialog,
    QFrame, QFontDialog, QApplication, QMenu, QInputDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtCore import Qt, QRect, QPoint
from db_utils import execute_query, fetch_one

MM_TO_PX = 3.78  # for 96 DPI

def mm_to_px(mm):
    return int(mm * MM_TO_PX)

def px_to_mm(px):
    return px / MM_TO_PX

def get_ticket_columns():
    rows = execute_query("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'tickets'
        ORDER BY ordinal_position
    """)
    return [row[0] for row in rows]

def get_all_template_names():
    rows = execute_query("SELECT templatename FROM templatemaster ORDER BY templatename")
    return [row[0] for row in rows]

class FieldWidget(QLabel):
    def __init__(self, field_name, x_mm, y_mm, w_mm, h_mm, font: QFont, parent=None):
        super().__init__(field_name, parent)
        self.field_name = field_name
        self.setFont(font)
        self.setStyleSheet("background-color: #f9f9f9; border: 1px solid #222;")
        self.setGeometry(mm_to_px(x_mm), mm_to_px(y_mm), mm_to_px(w_mm), mm_to_px(h_mm))
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFrameShape(QFrame.Panel)
        self.setFrameShadow(QFrame.Raised)
        self.setScaledContents(True)
        self.setMouseTracking(True)
        self._drag_pos = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            parent = self.parentWidget()
            if parent:
                new_pos = event.globalPos() - self._drag_pos - parent.mapToGlobal(QPoint(0, 0))
                self.move(new_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
        super().mouseReleaseEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Field")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == delete_action:
            parent = self.parentWidget()
            if hasattr(parent, "remove_field"):
                parent.remove_field(self)

    def get_mm_geometry(self):
        rect = self.geometry()
        return (
            px_to_mm(rect.x()),
            px_to_mm(rect.y()),
            px_to_mm(rect.width()),
            px_to_mm(rect.height())
        )

class CanvasWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = []
        self.bg_image = None

    def add_field(self, field_widget):
        field_widget.setParent(self)
        field_widget.show()
        self.fields.append(field_widget)

    def remove_field(self, field_widget):
        if field_widget in self.fields:
            self.fields.remove(field_widget)
            field_widget.deleteLater()
            parent = self.parentWidget()
            if hasattr(parent, 'active_field_widget') and parent.active_field_widget is field_widget:
                parent.active_field_widget = None

    def clear_fields(self):
        for f in self.fields:
            f.close()
        self.fields.clear()

    def set_bg_image(self, path):
        self.bg_image = QPixmap(path)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self.bg_image:
            # Fill canvas, preserve aspect ratio, center the image
            scaled = self.bg_image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

class TicketEntryDesignerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ticket Print Designer")
        self.setMinimumSize(1200, 900)
        self.ticket_fields = get_ticket_columns()
        self.active_field_widget = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)

        # --- Top Controls Layout ---
        top_layout = QHBoxLayout()
        # Left-side buttons
        left_btn_layout = QVBoxLayout()
        for text in ["Open", "Delete", "Save", "Help", "Exit"]:
            btn = QPushButton(text)
            btn.setFixedWidth(70)
            left_btn_layout.addWidget(btn)
            if text == "Save":
                btn.clicked.connect(self.save_template)
            if text == "Delete":
                btn.clicked.connect(self.delete_template)
            if text == "Open":
                btn.clicked.connect(self.open_template_dialog)
            if text == "Exit":
                btn.clicked.connect(self.close)
        left_btn_layout.addStretch(1)
        top_layout.addLayout(left_btn_layout)

        # Field Spec with spinners (mm)
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setMaximum(300.0)
        self.height_spin.setValue(10.0)
        self.height_spin.setSuffix(" mm")
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setMaximum(300.0)
        self.width_spin.setValue(50.0)
        self.width_spin.setSuffix(" mm")
        self.top_spin = QDoubleSpinBox()
        self.top_spin.setMaximum(300.0)
        self.top_spin.setValue(10.0)
        self.top_spin.setSuffix(" mm")
        self.left_spin = QDoubleSpinBox()
        self.left_spin.setMaximum(300.0)
        self.left_spin.setValue(10.0)
        self.left_spin.setSuffix(" mm")
        self.font_btn = QPushButton("Font")
        self.font_btn.clicked.connect(self.pick_font)
        self.field_font = QFont("Tahoma", 10)

        field_spec = QGroupBox("Field Spec")
        field_spec_layout = QGridLayout(field_spec)
        field_spec_layout.addWidget(QLabel("Height"), 0, 0)
        field_spec_layout.addWidget(self.height_spin, 0, 1)
        field_spec_layout.addWidget(QLabel("Width"), 0, 2)
        field_spec_layout.addWidget(self.width_spin, 0, 3)
        field_spec_layout.addWidget(QLabel("Top"), 1, 0)
        field_spec_layout.addWidget(self.top_spin, 1, 1)
        field_spec_layout.addWidget(QLabel("Left"), 1, 2)
        field_spec_layout.addWidget(self.left_spin, 1, 3)
        field_spec_layout.addWidget(self.font_btn, 2, 0, 1, 4)
        top_layout.addWidget(field_spec)

        # Template Name and Status
        center_top_layout = QVBoxLayout()
        template_line = QHBoxLayout()
        template_line.addWidget(QLabel(), 1)
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setText("TEST2")
        self.template_name_edit.setFixedWidth(200)
        template_line.addWidget(QLabel("Template Name : "))
        template_line.addWidget(self.template_name_edit)
        center_top_layout.addLayout(template_line)
        self.status_label = QLabel("STATUS")
        self.status_label.setStyleSheet("color: red;")
        center_top_layout.addWidget(self.status_label)
        top_layout.addLayout(center_top_layout)

        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout(controls_group)
        controls_layout.addWidget(QLabel("Field"), 0, 0)
        self.field_combo = QComboBox()
        self.field_combo.addItems(self.ticket_fields)
        controls_layout.addWidget(self.field_combo, 0, 1)
        field_insert_btn = QPushButton("...")
        controls_layout.addWidget(field_insert_btn, 0, 2)
        field_insert_btn.clicked.connect(self.insert_field)
        controls_layout.addWidget(QLabel("Formula"), 1, 0)
        controls_layout.addWidget(QLineEdit(), 1, 1, 1, 2)
        controls_layout.addWidget(QPushButton("Modify DB"), 2, 0)
        controls_layout.addWidget(QPushButton("Label"), 2, 1)
        img_btn = QPushButton("Load Preprinted Image")
        controls_layout.addWidget(img_btn, 3, 0, 1, 3)
        img_btn.clicked.connect(self.load_bg_image)
        top_layout.addWidget(controls_group)

        # Ticket Spec group (in mm)
        self.ticket_height_spin = QDoubleSpinBox()
        self.ticket_height_spin.setMaximum(300.0)
        self.ticket_height_spin.setValue(100.0)
        self.ticket_height_spin.setSuffix(" mm")
        self.ticket_width_spin = QDoubleSpinBox()
        self.ticket_width_spin.setMaximum(300.0)
        self.ticket_width_spin.setValue(150.0)
        self.ticket_width_spin.setSuffix(" mm")
        ticket_spec_group = QGroupBox("Ticket Spec")
        ticket_spec_layout = QGridLayout(ticket_spec_group)
        ticket_spec_layout.addWidget(QLabel("Height"), 0, 0)
        ticket_spec_layout.addWidget(self.ticket_height_spin, 0, 1)
        ticket_spec_layout.addWidget(QLabel("Width"), 1, 0)
        ticket_spec_layout.addWidget(self.ticket_width_spin, 1, 1)
        top_layout.addWidget(ticket_spec_group)

        # Alignment buttons
        align_layout = QVBoxLayout()
        align_layout.addWidget(QLabel("Alignment"))
        row = QHBoxLayout()
        self.left_align_btn = QPushButton("L")
        self.center_align_btn = QPushButton("C")
        self.right_align_btn = QPushButton("R")
        row.addWidget(self.left_align_btn)
        row.addWidget(self.center_align_btn)
        row.addWidget(self.right_align_btn)
        align_layout.addLayout(row)
        top_layout.addLayout(align_layout)

        self.left_align_btn.clicked.connect(self.align_left)
        self.center_align_btn.clicked.connect(self.align_center)
        self.right_align_btn.clicked.connect(self.align_right)

        main_layout.addLayout(top_layout)

        # --- Font Controls ---
        font_box = QGroupBox("Font")
        font_layout = QVBoxLayout(font_box)
        font_layout.addWidget(QLabel("Tahoma"))
        btn_row = QHBoxLayout()
        btn_row.addWidget(QPushButton("Change Font"))
        btn_row.addWidget(QPushButton("Underline"))
        btn_row.addWidget(QPushButton("Default"))
        font_layout.addLayout(btn_row)
        main_layout.addWidget(font_box)

        # --- Rulers (top and left) in mm ---
        ruler_top = QHBoxLayout()
        for i in range(1, 31):
            lab = QLabel(str(i*10))
            lab.setAlignment(Qt.AlignCenter)
            lab.setFixedWidth(mm_to_px(10))
            ruler_top.addWidget(lab)
        main_layout.addLayout(ruler_top)

        ruler_left = QVBoxLayout()
        for i in range(1, 31):
            lab = QLabel(str(i*10))
            lab.setAlignment(Qt.AlignVCenter)
            lab.setFixedHeight(mm_to_px(10))
            ruler_left.addWidget(lab)

        # --- Design Area / Canvas ---
        design_area_layout = QHBoxLayout()
        design_area_layout.addLayout(ruler_left)
        self.canvas = CanvasWidget(self)
        self.update_canvas_size()
        design_area_layout.addWidget(self.canvas)
        main_layout.addLayout(design_area_layout)

        # Connect steppers to update active field
        self.height_spin.valueChanged.connect(self.update_active_field)
        self.width_spin.valueChanged.connect(self.update_active_field)
        self.top_spin.valueChanged.connect(self.update_active_field)
        self.left_spin.valueChanged.connect(self.update_active_field)
        self.ticket_height_spin.valueChanged.connect(self.update_canvas_size)
        self.ticket_width_spin.valueChanged.connect(self.update_canvas_size)

        # Enable keyboard shortcuts for field movement
        self.installEventFilter(self)

    def get_template_name(self):
        return self.template_name_edit.text().strip()

    def insert_field(self):
        field_name = self.field_combo.currentText()
        # ALLOW multiple fields with same name by removing duplicate check!
        x = self.left_spin.value()
        y = self.top_spin.value()
        w = self.width_spin.value()
        h = self.height_spin.value()
        fw = FieldWidget(field_name, x, y, w, h, self.field_font, self.canvas)
        fw.mousePressEvent = lambda event, fw=fw: self.set_active_field(event, fw)
        fw.customContextMenuRequested.connect(lambda pos, fw=fw: fw.show_context_menu(pos))
        fw.show()
        self.canvas.add_field(fw)
        self.set_active_field(None, fw)

    def set_active_field(self, event, field_widget):
        self.active_field_widget = field_widget
        self.height_spin.blockSignals(True)
        self.width_spin.blockSignals(True)
        self.top_spin.blockSignals(True)
        self.left_spin.blockSignals(True)
        x_mm, y_mm, w_mm, h_mm = field_widget.get_mm_geometry()
        self.height_spin.setValue(h_mm)
        self.width_spin.setValue(w_mm)
        self.top_spin.setValue(y_mm)
        self.left_spin.setValue(x_mm)
        self.height_spin.blockSignals(False)
        self.width_spin.blockSignals(False)
        self.top_spin.blockSignals(False)
        self.left_spin.blockSignals(False)

    def update_active_field(self):
        fw = self.active_field_widget
        if fw and fw.parent() is self.canvas:
            fw.setGeometry(
                mm_to_px(self.left_spin.value()),
                mm_to_px(self.top_spin.value()),
                mm_to_px(self.width_spin.value()),
                mm_to_px(self.height_spin.value())
            )
            fw.setFont(self.field_font)
        else:
            self.active_field_widget = None

    def pick_font(self):
        font, ok = QFontDialog.getFont(self.field_font, self)
        if ok:
            self.field_font = font
            self.update_active_field()

    def update_canvas_size(self):
        self.canvas.setFixedSize(
            mm_to_px(self.ticket_width_spin.value()),
            mm_to_px(self.ticket_height_spin.value())
        )

    def delete_active_field(self):
        if self.active_field_widget:
            self.canvas.remove_field(self.active_field_widget)
            self.active_field_widget = None

    def delete_template(self):
        template_name = self.get_template_name()
        if not template_name:
            self.status_label.setText("Please enter a template name to delete.")
            return
        reply = QMessageBox.question(self, "Delete Template",
                f"Are you sure you want to delete template '{template_name}'?",
                QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        # Delete from fields first due to foreign key constraint
        execute_query("DELETE FROM templatefields WHERE templatename=%s", (template_name,))
        # Then delete from master table
        execute_query("DELETE FROM templatemaster WHERE templatename=%s", (template_name,))
        self.canvas.clear_fields()
        self.status_label.setText(f"Template '{template_name}' deleted.")

    def load_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose background image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.canvas.set_bg_image(path)

    def save_template(self):
        template_name = self.get_template_name()
        if not template_name:
            self.status_label.setText("Please enter a template name.")
            return
        template_sql = """
            INSERT INTO templatemaster
            (templatename, ticketheight, ticketwidth, defaulttemplate)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (templatename) DO UPDATE
            SET ticketheight=EXCLUDED.ticketheight, ticketwidth=EXCLUDED.ticketwidth, defaulttemplate=EXCLUDED.defaulttemplate
        """
        execute_query(template_sql, (
            template_name,
            self.ticket_height_spin.value(),
            self.ticket_width_spin.value(),
            False
        ))

        execute_query("DELETE FROM templatefields WHERE templatename=%s", (template_name,))
        for f in self.canvas.fields:
            fs = f.font()
            x_mm, y_mm, w_mm, h_mm = f.get_mm_geometry()
            field_sql = """
                INSERT INTO templatefields
                (templatename, fieldname, displayname, x, y, width, height, fontname, fontsize)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_query(field_sql, (
                template_name, f.field_name, f.text(),
                x_mm, y_mm, w_mm, h_mm,
                fs.family(), fs.pointSize()
            ))
        self.status_label.setText("Template Saved")

    def load_template(self):
        template_name = self.get_template_name()
        template = fetch_one("SELECT * FROM templatemaster WHERE templatename=%s", (template_name,))
        if template:
            self.ticket_height_spin.setValue(float(template[1]))
            self.ticket_width_spin.setValue(float(template[2]))
            self.update_canvas_size()
            fields = execute_query("SELECT * FROM templatefields WHERE templatename=%s", (template_name,))
            self.canvas.clear_fields()
            for field in fields:
                fw = FieldWidget(
                    field[1],                     # fieldname
                    float(field[3]),              # x
                    float(field[4]),              # y
                    float(field[5]),              # width
                    float(field[6]),              # height
                    QFont(field[7], field[8]),    # fontname, fontsize
                    self.canvas
                )
                fw.mousePressEvent = lambda event, fw=fw: self.set_active_field(event, fw)
                fw.customContextMenuRequested.connect(lambda pos, fw=fw: fw.show_context_menu(pos))
                fw.show()
                self.canvas.add_field(fw)
            self.status_label.setText(f"Template '{template_name}' loaded.")
        else:
            self.status_label.setText("Template not found.")

    def open_template_dialog(self):
        # Show a dialog with all saved template names, let user pick one
        names = get_all_template_names()
        if not names:
            self.status_label.setText("No saved templates found.")
            return
        current_name = self.get_template_name()
        if current_name not in names:
            current_index = 0
        else:
            current_index = names.index(current_name)
        name, ok = QInputDialog.getItem(self, "Open Template", "Select a template to load:", names, current_index, False)
        if ok and name:
            self.template_name_edit.setText(name)
            self.load_template()

    # Alignment button operations
    def align_left(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            rect = self.active_field_widget.geometry()
            self.active_field_widget.setGeometry(
                0, rect.y(), rect.width(), rect.height()
            )
            self.left_spin.setValue(px_to_mm(0))

    def align_center(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            field = self.active_field_widget
            canvas_width = self.canvas.width()
            field_width = field.width()
            center_x = (canvas_width - field_width) // 2
            field.setGeometry(
                center_x, field.y(), field.width(), field.height()
            )
            self.left_spin.setValue(px_to_mm(center_x))

    def align_right(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            field = self.active_field_widget
            canvas_width = self.canvas.width()
            field_width = field.width()
            right_x = canvas_width - field_width
            field.setGeometry(
                right_x, field.y(), field.width(), field.height()
            )
            self.left_spin.setValue(px_to_mm(right_x))

    # Keyboard shortcuts for moving field by 10mm
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress and QApplication.keyboardModifiers() == Qt.ControlModifier:
            if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
                fw = self.active_field_widget
                rect = fw.geometry()
                move_amt_px = mm_to_px(10)
                # + or - on numpad and main keyboard
                if event.key() in (Qt.Key_Plus, Qt.Key_Equal):  # Qt.Key_Equal is Shift + '='
                    # Move down 10mm (increase top/y)
                    new_y = rect.y() + move_amt_px
                    fw.setGeometry(rect.x(), new_y, rect.width(), rect.height())
                    self.top_spin.setValue(px_to_mm(new_y))
                    return True
                elif event.key() in (Qt.Key_Minus, Qt.Key_Underscore):
                    # Move up 10mm (decrease top/y)
                    new_y = max(0, rect.y() - move_amt_px)
                    fw.setGeometry(rect.x(), new_y, rect.width(), rect.height())
                    self.top_spin.setValue(px_to_mm(new_y))
                    return True
                elif event.key() == Qt.Key_Left:
                    # Move left 10mm (decrease left/x)
                    new_x = max(0, rect.x() - move_amt_px)
                    fw.setGeometry(new_x, rect.y(), rect.width(), rect.height())
                    self.left_spin.setValue(px_to_mm(new_x))
                    return True
                elif event.key() == Qt.Key_Right:
                    # Move right 10mm (increase left/x)
                    new_x = rect.x() + move_amt_px
                    fw.setGeometry(new_x, rect.y(), rect.width(), rect.height())
                    self.left_spin.setValue(px_to_mm(new_x))
                    return True
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = TicketEntryDesignerWindow()
    win.show()
    sys.exit(app.exec_())
