import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QGroupBox, QDoubleSpinBox, QFileDialog,
    QFrame, QFontDialog, QApplication, QMenu, QInputDialog, QMessageBox, QCheckBox, QDialog,
    QSizePolicy
)
from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtCore import Qt, QPoint

# Make sure db_utils and ticket_printer are in the path
try:
    from db_utils import execute_query, fetch_one
    # The render_ticket_with_data function is used for the preview functionality
    from ticket_printer import render_ticket_with_data 
except ImportError as e:
    print(f"Error importing a required module: {e}")
    print("Please ensure db_utils.py and ticket_printer.py are in the same directory or in the Python path.")
    sys.exit(1)


MM_TO_PX = 3.78  # Conversion factor for a 96 DPI screen

def mm_to_px(mm):
    """Converts millimeters to pixels."""
    return int(mm * MM_TO_PX)

def px_to_mm(px):
    """Converts pixels to millimeters."""
    return px / MM_TO_PX

def safe_point_size(qfont: QFont):
    """Returns a safe integer value for a font's point size."""
    ps = qfont.pointSize()
    return int(ps) if ps > 0 else 10

def get_ticket_columns():
    """Fetches all column names from the 'tickets' table for the field dropdown."""
    try:
        rows = execute_query("SELECT column_name FROM information_schema.columns WHERE table_name = 'tickets' ORDER BY ordinal_position")
        return [row['column_name'] for row in rows]
    except Exception as e:
        QMessageBox.critical(None, "Database Error", f"Could not fetch ticket columns: {e}")
        return []

def get_all_whatsapp_template_names():
    """Fetches all saved WhatsApp template names for the 'Open' dialog."""
    try:
        rows = execute_query("SELECT templatename FROM whatsapptemplatemaster ORDER BY templatename")
        return [row['templatename'] for row in rows]
    except Exception as e:
        QMessageBox.critical(None, "Database Error", f"Could not fetch template names: {e}")
        return []


class FieldWidget(QLabel):
    """A draggable, resizable QLabel representing a database field on the canvas."""
    def __init__(self, field_name, x_mm, y_mm, w_mm, h_mm, font: QFont, parent=None):
        super().__init__(field_name, parent)
        self.field_name = field_name
        self.saved_font = QFont(font)
        
        self.setGeometry(mm_to_px(x_mm), mm_to_px(y_mm), mm_to_px(w_mm), mm_to_px(h_mm))
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self._drag_pos = None
        
        self.update_visuals()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_visuals(self):
        """
        Applies font and style to the widget.
        ## --- BLOCKADE IMPLEMENTATION --- ##
        By setting the stylesheet directly on the widget, we create a 'blockade'
        that prevents global (application-level) stylesheets from overriding
        the specific font properties of this field.
        """
        self.setFont(self.saved_font)
        family = self.saved_font.family()
        size_pt = safe_point_size(self.saved_font)
        style = (
            "background-color: rgba(240, 248, 255, 0.8);"  # Semi-transparent AliceBlue
            "border: 1px solid #666;"
            f"font-family: '{family}';"
            f"font-size: {int(size_pt)}pt;"
            f"font-weight: {'700' if self.saved_font.bold() else '400'};"
            f"font-style: {'italic' if self.saved_font.italic() else 'normal'};"
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(style)

    def update_saved_font(self, qfont: QFont):
        """Updates the stored font and refreshes the widget's appearance."""
        self.saved_font = QFont(qfont)
        self.update_visuals()

    def mousePressEvent(self, event):
        """Initiates dragging when the left mouse button is pressed."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos() # Use position relative to widget
            self.window().set_active_field(self)
            self.raise_() # Bring to front
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        ## --- MOUSE DRAGGING IMPLEMENTATION --- ##
        Moves the widget if dragging is in progress.
        """
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            parent = self.parentWidget()
            if parent:
                # Map the new position from the widget's coordinate system to the parent's
                new_pos = self.mapToParent(event.pos() - self._drag_pos)
                
                # Clamp position to stay within the parent canvas boundaries
                new_x = max(0, min(new_pos.x(), parent.width() - self.width()))
                new_y = max(0, min(new_pos.y(), parent.height() - self.height()))
                
                self.move(new_x, new_y)
                self.window().update_spinboxes_from_widget(self)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Stops the drag operation."""
        self._drag_pos = None
        event.accept()
        super().mouseReleaseEvent(event)

    def show_context_menu(self, pos):
        """Shows a context menu to delete the field."""
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Field")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == delete_action:
            self.window().remove_field_widget(self)

    def get_mm_geometry(self):
        """Returns the widget's geometry in millimeters."""
        rect = self.geometry()
        return (px_to_mm(rect.x()), px_to_mm(rect.y()), px_to_mm(rect.width()), px_to_mm(rect.height()))


class CanvasWidget(QFrame):
    """The area where fields are placed. It can have a background image."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = []
        self.bg_image = None
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #ffffff; border: 2px solid #cccccc;")

    def add_field(self, field_widget):
        """Adds a new field to the canvas."""
        field_widget.setParent(self)
        field_widget.show()
        self.fields.append(field_widget)

    def remove_field(self, field_widget):
        """Removes a field from the canvas."""
        if field_widget in self.fields:
            self.fields.remove(field_widget)
            field_widget.deleteLater()
            self.window().on_field_removed(field_widget)

    def clear_fields(self):
        """Removes all fields from the canvas."""
        for f in list(self.fields):
            self.remove_field(f)

    def set_bg_image(self, path):
        """Sets or clears the background image."""
        self.bg_image = QPixmap(path) if path else None
        self.update()  # Trigger a repaint to show the new background

    def paintEvent(self, event):
        """Paints the background image before drawing child widgets."""
        super().paintEvent(event)
        painter = QPainter(self)
        if self.bg_image and not self.bg_image.isNull():
            scaled = self.bg_image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)


class WhatsAppTemplateDesignerWindow(QDialog):
    """The main designer window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WhatsApp Image Template Designer")
        self.setGeometry(100, 100, 1280, 800)
        self.ticket_fields = get_ticket_columns()
        self.active_field_widget = None
        self.field_font = QFont("Arial", 10)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        top_controls_panel = self._create_top_controls()
        main_layout.addLayout(top_controls_panel)

        canvas_container_layout = QHBoxLayout()
        canvas_container_layout.addStretch()
        self.canvas = CanvasWidget(self)
        canvas_container_layout.addWidget(self.canvas)
        canvas_container_layout.addStretch()
        main_layout.addLayout(canvas_container_layout, 1)

        self._connect_signals()
        self.load_active_template()
        self.field_props_group.setEnabled(False)
    
    ## --- KEYBOARD SHORTCUT IMPLEMENTATION --- ##
    def keyPressEvent(self, event):
        """Handle key presses for moving the active widget."""
        if not self.active_field_widget:
            super().keyPressEvent(event)
            return

        # Check if Control key is pressed
        if event.modifiers() == Qt.ControlModifier:
            fw = self.active_field_widget
            move_increment_px = mm_to_px(1)  # Nudge by 1mm
            
            new_x, new_y = fw.x(), fw.y()

            if event.key() == Qt.Key_Up:
                new_y = max(0, new_y - move_increment_px)
            elif event.key() == Qt.Key_Down:
                new_y = min(self.canvas.height() - fw.height(), new_y + move_increment_px)
            elif event.key() == Qt.Key_Left:
                new_x = max(0, new_x - move_increment_px)
            elif event.key() == Qt.Key_Right:
                new_x = min(self.canvas.width() - fw.width(), new_x + move_increment_px)
            else:
                super().keyPressEvent(event)
                return

            fw.move(new_x, new_y)
            self.update_spinboxes_from_widget(fw)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _create_top_controls(self):
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)

        # Left Column: Main Actions
        left_col = QVBoxLayout()
        actions = ["New", "Open", "Save", "Delete", "Preview", "Exit"]
        self.buttons = {}
        for action in actions:
            btn = QPushButton(action)
            btn.setFixedWidth(120); btn.setFixedHeight(30)
            self.buttons[action] = btn
            left_col.addWidget(btn)
        left_col.addStretch()
        top_layout.addLayout(left_col)

        # Center Column: Template & Field Creation
        center_col = QVBoxLayout()
        template_group = QGroupBox("Template")
        template_layout = QHBoxLayout(template_group)
        template_layout.addWidget(QLabel("Name:"))
        self.template_name_edit = QLineEdit()
        template_layout.addWidget(self.template_name_edit)
        self.set_active_checkbox = QCheckBox("Set as Active")
        template_layout.addWidget(self.set_active_checkbox)
        center_col.addWidget(template_group)

        canvas_group = QGroupBox("Canvas Properties")
        canvas_layout = QGridLayout(canvas_group)
        self.img_height_spin = QDoubleSpinBox(suffix=" mm", maximum=500, value=160)
        self.img_width_spin = QDoubleSpinBox(suffix=" mm", maximum=500, value=260)
        self.btn_load_bg = QPushButton("Load Background Image")
        canvas_layout.addWidget(QLabel("Width:"), 0, 0); canvas_layout.addWidget(self.img_width_spin, 0, 1)
        canvas_layout.addWidget(QLabel("Height:"), 1, 0); canvas_layout.addWidget(self.img_height_spin, 1, 1)
        canvas_layout.addWidget(self.btn_load_bg, 2, 0, 1, 2)
        center_col.addWidget(canvas_group)

        field_group = QGroupBox("Insert New Field")
        field_layout = QHBoxLayout(field_group)
        self.field_combo = QComboBox(); self.field_combo.addItems(self.ticket_fields)
        self.btn_insert_field = QPushButton("Insert")
        field_layout.addWidget(QLabel("Field:")); field_layout.addWidget(self.field_combo, 1); field_layout.addWidget(self.btn_insert_field)
        center_col.addWidget(field_group)
        center_col.addStretch()
        top_layout.addLayout(center_col, 1)

        # Right Column: Field Properties
        right_col = QVBoxLayout()
        self.status_label = QLabel("Ready"); self.status_label.setStyleSheet("font-size: 14px; color: blue; font-weight: bold;")
        right_col.addWidget(self.status_label, alignment=Qt.AlignTop)

        self.field_props_group = QGroupBox("Selected Field Properties")
        props_layout = QGridLayout(self.field_props_group)
        self.top_spin = QDoubleSpinBox(suffix=" mm", maximum=500, singleStep=0.5)
        self.left_spin = QDoubleSpinBox(suffix=" mm", maximum=500, singleStep=0.5)
        self.height_spin = QDoubleSpinBox(suffix=" mm", maximum=500, singleStep=0.5)
        self.width_spin = QDoubleSpinBox(suffix=" mm", maximum=500, singleStep=0.5)
        self.font_btn = QPushButton("Change Font")
        props_layout.addWidget(QLabel("Top:"), 0, 0); props_layout.addWidget(self.top_spin, 0, 1)
        props_layout.addWidget(QLabel("Left:"), 1, 0); props_layout.addWidget(self.left_spin, 1, 1)
        props_layout.addWidget(QLabel("Height:"), 2, 0); props_layout.addWidget(self.height_spin, 2, 1)
        props_layout.addWidget(QLabel("Width:"), 3, 0); props_layout.addWidget(self.width_spin, 3, 1)
        props_layout.addWidget(self.font_btn, 4, 0, 1, 2)
        right_col.addWidget(self.field_props_group)
        
        align_group = QGroupBox("Alignment")
        align_layout = QHBoxLayout(align_group)
        self.buttons["Align Left"] = QPushButton("Left"); align_layout.addWidget(self.buttons["Align Left"])
        self.buttons["Align Center"] = QPushButton("Center"); align_layout.addWidget(self.buttons["Align Center"])
        self.buttons["Align Right"] = QPushButton("Right"); align_layout.addWidget(self.buttons["Align Right"])
        right_col.addWidget(align_group)
        
        right_col.addStretch()
        top_layout.addLayout(right_col, 1)
        return top_layout

    def _connect_signals(self):
        self.buttons["New"].clicked.connect(self.new_template)
        self.buttons["Open"].clicked.connect(self.open_template_dialog)
        self.buttons["Save"].clicked.connect(self.save_template)
        self.buttons["Delete"].clicked.connect(self.delete_template)
        self.buttons["Exit"].clicked.connect(self.accept)
        self.buttons["Preview"].clicked.connect(self.preview_template)
        self.img_width_spin.valueChanged.connect(self.update_canvas_size)
        self.img_height_spin.valueChanged.connect(self.update_canvas_size)
        self.btn_load_bg.clicked.connect(self.load_background_image)
        self.btn_insert_field.clicked.connect(self.insert_field)
        self.font_btn.clicked.connect(self.pick_font)
        self.buttons["Align Left"].clicked.connect(self.align_left)
        self.buttons["Align Center"].clicked.connect(self.align_center)
        self.buttons["Align Right"].clicked.connect(self.align_right)
        for spin in [self.top_spin, self.left_spin, self.height_spin, self.width_spin]:
            spin.valueChanged.connect(self.update_active_field_geometry)
    
    def update_canvas_size(self):
        w_px = mm_to_px(self.img_width_spin.value())
        h_px = mm_to_px(self.img_height_spin.value())
        self.canvas.setFixedSize(w_px, h_px)

    def insert_field(self):
        field_name = self.field_combo.currentText()
        if not field_name: return

        for field_widget in self.canvas.fields:
            if field_widget.field_name == field_name:
                QMessageBox.warning(self, "Duplicate Field", f"The field '{field_name}' is already on the canvas.")
                return

        fw = FieldWidget(field_name, 10, 10, 50, 10, self.field_font, self.canvas)
        self.canvas.add_field(fw)
        self.set_active_field(fw)

    def set_active_field(self, field_widget):
        if self.active_field_widget:
            self.active_field_widget.update_visuals()
        self.active_field_widget = field_widget
        if field_widget:
            field_widget.setStyleSheet(field_widget.styleSheet() + "border: 2px solid blue;")
            self.update_spinboxes_from_widget(field_widget)
            self.field_font = QFont(field_widget.saved_font)
            self.field_props_group.setEnabled(True)
        else:
            self.field_props_group.setEnabled(False)

    def update_spinboxes_from_widget(self, fw):
        for spin in [self.top_spin, self.left_spin, self.height_spin, self.width_spin]:
            spin.blockSignals(True)
        x, y, w, h = fw.get_mm_geometry()
        self.left_spin.setValue(x); self.top_spin.setValue(y)
        self.width_spin.setValue(w); self.height_spin.setValue(h)
        for spin in [self.top_spin, self.left_spin, self.height_spin, self.width_spin]:
            spin.blockSignals(False)

    def update_active_field_geometry(self):
        if not self.active_field_widget: return
        fw = self.active_field_widget
        fw.setGeometry(
            mm_to_px(self.left_spin.value()), mm_to_px(self.top_spin.value()),
            mm_to_px(self.width_spin.value()), mm_to_px(self.height_spin.value())
        )

    def pick_font(self):
        if not self.active_field_widget: return
        font, ok = QFontDialog.getFont(self.field_font, self)
        if ok:
            self.field_font = font
            self.active_field_widget.update_saved_font(font)

    def save_template(self):
        template_name = self.template_name_edit.text().strip()
        if not template_name:
            QMessageBox.warning(self, "Input Error", "Template name cannot be empty.")
            return
        try:
            if self.set_active_checkbox.isChecked():
                execute_query("UPDATE whatsapptemplatemaster SET is_active = FALSE")

            master_sql = """
                INSERT INTO whatsapptemplatemaster (templatename, imagewidth, imageheight, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (templatename) DO UPDATE SET
                imagewidth = EXCLUDED.imagewidth, imageheight = EXCLUDED.imageheight, is_active = EXCLUDED.is_active;
            """
            execute_query(master_sql, (template_name, self.img_width_spin.value(), self.img_height_spin.value(), self.set_active_checkbox.isChecked()))
            execute_query("DELETE FROM whatsapptemplatefields WHERE templatename = %s", (template_name,))
            field_sql = """
                INSERT INTO whatsapptemplatefields (templatename, fieldname, displayname, x, y, width, height, fontname, fontsize, fontstyle)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            for f in self.canvas.fields:
                x, y, w, h = f.get_mm_geometry()
                font = f.saved_font
                style = ",".join(s for s, b in [("bold", font.bold()), ("italic", font.italic())] if b) or "normal"
                execute_query(field_sql, (template_name, f.field_name, f.text(), x, y, w, h, font.family(), font.pointSize(), style))
            self.status_label.setText(f"Template '{template_name}' saved.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not save template: {e}")

    def load_template(self, template_name):
        try:
            master = fetch_one("SELECT * FROM whatsapptemplatemaster WHERE templatename = %s", (template_name,))
            if not master: return
            
            for w in [self.img_width_spin, self.img_height_spin]: w.blockSignals(True)
            self.template_name_edit.setText(master['templatename'])
            self.img_width_spin.setValue(float(master['imagewidth']))
            self.img_height_spin.setValue(float(master['imageheight']))
            self.set_active_checkbox.setChecked(bool(master['is_active']))
            self.update_canvas_size()
            for w in [self.img_width_spin, self.img_height_spin]: w.blockSignals(False)
            
            self.canvas.clear_fields()
            fields = execute_query("SELECT * FROM whatsapptemplatefields WHERE templatename = %s", (template_name,))
            for field in fields:
                font = QFont(field.get('fontname', 'Arial'), int(field.get('fontsize', 10)))
                style = field.get('fontstyle', '')
                font.setBold('bold' in style); font.setItalic('italic' in style)
                fw = FieldWidget(field['fieldname'], float(field['x']), float(field['y']), float(field['width']), float(field['height']), font, self.canvas)
                self.canvas.add_field(fw)
            self.set_active_field(None)
            self.status_label.setText(f"Loaded template: {template_name}")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load template: {e}")

    def load_active_template(self):
        active = fetch_one("SELECT templatename FROM whatsapptemplatemaster WHERE is_active = TRUE LIMIT 1")
        if active: self.load_template(active['templatename'])
        else: self.new_template()

    def new_template(self):
        self.canvas.clear_fields()
        self.template_name_edit.clear()
        self.img_width_spin.setValue(260); self.img_height_spin.setValue(160)
        self.set_active_checkbox.setChecked(False)
        self.canvas.set_bg_image(None)
        self.set_active_field(None)
        self.update_canvas_size()
        self.status_label.setText("New template. Ready to save.")

    def delete_template(self):
        name = self.template_name_edit.text().strip()
        if not name: return
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete template '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            execute_query("DELETE FROM whatsapptemplatemaster WHERE templatename = %s", (name,))
            self.new_template()
            self.status_label.setText(f"Template '{name}' deleted.")

    def open_template_dialog(self):
        names = get_all_whatsapp_template_names()
        if not names:
            QMessageBox.information(self, "No Templates Found", "There are no saved templates to open.")
            return
        name, ok = QInputDialog.getItem(self, "Open Template", "Select a template:", names, 0, False)
        if ok and name: self.load_template(name)

    def load_background_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Background Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.canvas.set_bg_image(path)
            self.status_label.setText("Background image loaded.")

    def preview_template(self):
        sample_data = {f.field_name: f"[{f.field_name}]" for f in self.canvas.fields}
        template_fields = [{'x': f.get_mm_geometry()[0], 'y': f.get_mm_geometry()[1], 'width': f.get_mm_geometry()[2], 'height': f.get_mm_geometry()[3], 'fieldname': f.field_name, 'fontname': f.saved_font.family(), 'fontsize': f.saved_font.pointSize(), 'fontstyle': ",".join(s for s, b in [("bold", f.saved_font.bold()), ("italic", f.saved_font.italic())] if b) or "normal"} for f in self.canvas.fields]
        render_ticket_with_data(template_fields=template_fields, ticket_data=sample_data, ticket_width_mm=self.img_width_spin.value(), ticket_height_mm=self.img_height_spin.value(), parent=self, preview=True)

    def align_left(self):
        if self.active_field_widget:
            self.active_field_widget.move(0, self.active_field_widget.y())
            self.update_spinboxes_from_widget(self.active_field_widget)

    def align_center(self):
        if self.active_field_widget:
            center_x = (self.canvas.width() - self.active_field_widget.width()) // 2
            self.active_field_widget.move(center_x, self.active_field_widget.y())
            self.update_spinboxes_from_widget(self.active_field_widget)

    def align_right(self):
        if self.active_field_widget:
            right_x = self.canvas.width() - self.active_field_widget.width()
            self.active_field_widget.move(right_x, self.active_field_widget.y())
            self.update_spinboxes_from_widget(self.active_field_widget)

    def remove_field_widget(self, field_widget):
        self.canvas.remove_field(field_widget)

    def on_field_removed(self, field_widget):
        if self.active_field_widget is field_widget:
            self.set_active_field(None)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    designer = WhatsAppTemplateDesignerWindow()
    designer.show()
    sys.exit(app.exec_())
