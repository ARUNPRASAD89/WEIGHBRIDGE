from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QGroupBox, QDoubleSpinBox, QFileDialog,
    QFrame, QFontDialog, QApplication, QMenu, QInputDialog, QMessageBox, QCheckBox, QDialog
)
from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtCore import Qt, QRect, QPoint

from db_utils import execute_query, fetch_one
from ticket_printer import render_ticket_with_data

MM_TO_PX = 3.78  # for 96 DPI

def mm_to_px(mm):
    return int(mm * MM_TO_PX)

def px_to_mm(px):
    return px / MM_TO_PX

def safe_point_size(qfont: QFont):
    """Return a sane integer point size for a QFont, with fallbacks."""
    ps = qfont.pointSize()
    if ps and ps > 0:
        return int(ps)
    try:
        pfs = qfont.pointSizeF()
        if pfs and pfs > 0.0:
            return int(round(pfs))
    except Exception:
        pass
    # fallback to application default point size
    app = QApplication.instance()
    if app:
        return int(app.font().pointSize())
    return 10

def get_ticket_columns():
    rows = execute_query("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'tickets'
        ORDER BY ordinal_position
    """)
    return [row['column_name'] for row in rows]

def get_all_template_names():
    rows = execute_query("SELECT templatename FROM templatemaster ORDER BY templatename")
    return [row['templatename'] for row in rows]


class FieldWidget(QLabel):
    """
    A label representing a field on the canvas. Stores its own QFont (saved_font)
    and applies an explicit widget stylesheet containing the font-family and font-size.
    A widget-level stylesheet will not be overridden by parent/app styles for font properties.
    """
    def __init__(self, field_name, x_mm, y_mm, w_mm, h_mm, font: QFont, parent=None):
        super().__init__(field_name, parent)
        self.field_name = field_name

        # store the intended font and apply it
        self.saved_font = QFont(font)
        self.setFont(self.saved_font)

        # geometry in px
        self.setGeometry(mm_to_px(x_mm), mm_to_px(y_mm), mm_to_px(w_mm), mm_to_px(h_mm))
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # frame & visual defaults
        self.setFrameShape(QFrame.Panel)
        self.setFrameShadow(QFrame.Raised)
        self.setScaledContents(True)
        self.setMouseTracking(True)
        self._drag_pos = None

        # Ensure the widget has its own stylesheet so parent/app styles don't override fonts.
        # We'll include background & border plus explicit font-family and font-size.
        self._apply_font_stylesheet()

        # context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def _apply_font_stylesheet(self):
        family = self.saved_font.family()
        size_pt = safe_point_size(self.saved_font)
        bold = 'bold' if self.saved_font.bold() else 'normal'
        italic = 'italic' if self.saved_font.italic() else 'normal'
        # keep color and border consistent, but explicitly set font properties at widget level
        style = (
            "background-color: #f9f9f9;"
            "border: 1px solid #222;"
            f" font-family: '{family}';"
            f" font-size: {int(size_pt)}pt;"
            f" font-weight: { '700' if bold == 'bold' else '400' };"
            f" font-style: {italic};"
        )
        # Make sure the widget uses styled background so stylesheet backgrounds are painted
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Apply stylesheet (overrides parent/app QLabel rules for font-family/size)
        self.setStyleSheet(style)

    def update_saved_font(self, qfont: QFont):
        """Update saved font and re-apply stylesheet and widget font."""
        self.saved_font = QFont(qfont)
        self.setFont(self.saved_font)
        self._apply_font_stylesheet()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            parent = self.parentWidget()
            if parent:
                # Calculate new position relative to the parent widget (the canvas)
                new_pos = event.globalPos() - self._drag_pos - parent.mapToGlobal(QPoint(0, 0))
                
                # Clamp the position to stay within the canvas boundaries
                new_x = max(0, min(new_pos.x(), parent.width() - self.width()))
                new_y = max(0, min(new_pos.y(), parent.height() - self.height()))
                
                self.move(new_x, new_y)

                # Ask main window to update spinboxes if applicable
                main_w = self.window()
                try:
                    if isinstance(main_w, TicketEntryDesignerWindow) and main_w.active_field_widget is self:
                        main_w.update_spinboxes_from_widget(self)
                except Exception:
                    pass

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
    """
    Canvas widget that holds FieldWidget children. We assign a canvas-level stylesheet
    that does not include QLabel font rules; field widgets have per-widget styles.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = []
        self.bg_image = None
        # ensure canvas background is styled on its own (prevents inheritance issues)
        self.setAttribute(Qt.WA_StyledBackground, True)
        # minimal canvas stylesheet — no font declarations here
        self.setStyleSheet("background-color: white; border: 1px solid #bbb;")

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
        for f in list(self.fields):
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


class TicketEntryDesignerWindow(QDialog):
    """
    Designer window that uses CanvasWidget and FieldWidget which resist global stylesheet
    font overrides by using per-widget styles and storing a saved_font used when saving.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket Print Designer")
        self.setMinimumSize(1200, 900)
        self.ticket_fields = get_ticket_columns()
        self.active_field_widget = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # --- Top Controls Layout ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        # --- Left Buttons Column ---
        self.left_btn_layout = QVBoxLayout()
        self.left_btn_layout.setSpacing(10)
        btn_names = ["New", "Open", "Delete", "Save", "Print Preview", "Help", "Exit"]
        self.btn_dict = {}
        for text in btn_names:
            btn = QPushButton(text)
            btn.setFixedWidth(110)
            btn.setMinimumHeight(32)
            self.left_btn_layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self.btn_dict[text] = btn
        self.left_btn_layout.addStretch(1)
        top_layout.addLayout(self.left_btn_layout)

        # Button actions
        self.btn_dict["New"].clicked.connect(self.new_template)
        self.btn_dict["Save"].clicked.connect(self.save_template)
        self.btn_dict["Delete"].clicked.connect(self.delete_template)
        self.btn_dict["Open"].clicked.connect(self.open_template_dialog)
        self.btn_dict["Exit"].clicked.connect(self.return_to_administration)
        self.btn_dict["Print Preview"].clicked.connect(self.preview_print)

        # --- Field Spec Group ---
        field_spec = QGroupBox("Field Spec")
        field_spec_layout = QGridLayout(field_spec)
        field_spec_layout.setHorizontalSpacing(10)
        field_spec_layout.setVerticalSpacing(6)

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
        # default logical font used when inserting new fields (kept separate from styles)
        self.field_font = QFont("Tahoma", 14)

        field_spec_layout.addWidget(QLabel("Height:"), 0, 0)
        field_spec_layout.addWidget(self.height_spin, 0, 1)
        field_spec_layout.addWidget(QLabel("Width:"), 0, 2)
        field_spec_layout.addWidget(self.width_spin, 0, 3)
        field_spec_layout.addWidget(QLabel("Top:"), 1, 0)
        field_spec_layout.addWidget(self.top_spin, 1, 1)
        field_spec_layout.addWidget(QLabel("Left:"), 1, 2)
        field_spec_layout.addWidget(self.left_spin, 1, 3)
        field_spec_layout.addWidget(self.font_btn, 2, 0, 1, 4, alignment=Qt.AlignCenter)
        top_layout.addWidget(field_spec, alignment=Qt.AlignTop)

        # --- Template Name and Status ---
        center_top_layout = QVBoxLayout()
        template_line = QHBoxLayout()
        template_line.addStretch(1)
        template_line.addWidget(QLabel("Template Name:"))
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setFixedWidth(200)
        template_line.addWidget(self.template_name_edit)
        self.set_default_checkbox = QCheckBox("Set as Default")
        template_line.addWidget(self.set_default_checkbox)
        template_line.addStretch(1)
        center_top_layout.addLayout(template_line)
        self.status_label = QLabel("STATUS")
        self.status_label.setStyleSheet("color: red;")
        center_top_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)
        top_layout.addLayout(center_top_layout)

        # --- Controls Group ---
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(8)
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
        top_layout.addWidget(controls_group, alignment=Qt.AlignTop)

        # --- Ticket Spec Group ---
        ticket_spec_group = QGroupBox("Ticket Spec")
        ticket_spec_layout = QGridLayout(ticket_spec_group)
        ticket_spec_layout.setHorizontalSpacing(10)
        ticket_spec_layout.setVerticalSpacing(6)
        self.ticket_height_spin = QDoubleSpinBox()
        self.ticket_height_spin.setMaximum(300.0)
        self.ticket_height_spin.setValue(100.0)
        self.ticket_height_spin.setSuffix(" mm")
        self.ticket_width_spin = QDoubleSpinBox()
        self.ticket_width_spin.setMaximum(300.0)
        self.ticket_width_spin.setValue(150.0)
        self.ticket_width_spin.setSuffix(" mm")
        ticket_spec_layout.addWidget(QLabel("Height:"), 0, 0)
        ticket_spec_layout.addWidget(self.ticket_height_spin, 0, 1)
        ticket_spec_layout.addWidget(QLabel("Width:"), 1, 0)
        ticket_spec_layout.addWidget(self.ticket_width_spin, 1, 1)
        top_layout.addWidget(ticket_spec_group, alignment=Qt.AlignTop)

        # --- Alignment Buttons ---
        align_layout = QVBoxLayout()
        align_layout.addWidget(QLabel("Alignment"))
        row = QHBoxLayout()
        self.left_align_btn = QPushButton("L")
        self.center_align_btn = QPushButton("C")
        self.right_align_btn = QPushButton("R")
        for b in [self.left_align_btn, self.center_align_btn, self.right_align_btn]:
            b.setFixedWidth(32)
        row.addWidget(self.left_align_btn)
        row.addWidget(self.center_align_btn)
        row.addWidget(self.right_align_btn)
        align_layout.addLayout(row)
        align_layout.addStretch(1)
        top_layout.addLayout(align_layout)

        self.left_align_btn.clicked.connect(self.align_left)
        self.center_align_btn.clicked.connect(self.align_center)
        self.right_align_btn.clicked.connect(self.align_right)

        main_layout.addLayout(top_layout)

        # --- Font Controls ---
        font_box = QGroupBox("Font")
        font_layout = QVBoxLayout(font_box)
        font_layout.addWidget(QLabel("Tahoma"), alignment=Qt.AlignLeft)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        # Change Font button (opens QFontDialog)
        self.change_font_btn = QPushButton("Change Font")
        self.change_font_btn.clicked.connect(self.pick_font)
        btn_row.addWidget(self.change_font_btn)

        # Bold and Italic toggle buttons
        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedWidth(36)
        self.bold_btn.clicked.connect(self.toggle_bold)
        btn_row.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedWidth(36)
        self.italic_btn.clicked.connect(self.toggle_italic)
        btn_row.addWidget(self.italic_btn)

        # Apply font family/style to all fields
        self.apply_font_all_btn = QPushButton("Apply Font to All")
        self.apply_font_all_btn.clicked.connect(self.apply_font_to_all_fields)
        btn_row.addWidget(self.apply_font_all_btn)

        # Default reset button
        self.default_font_btn = QPushButton("Default")
        self.default_font_btn.clicked.connect(self.reset_default_font)
        btn_row.addWidget(self.default_font_btn)

        font_layout.addLayout(btn_row)
        main_layout.addWidget(font_box, alignment=Qt.AlignLeft)

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

        # Load the default template on startup
        self.load_default_template()

    def return_to_administration(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()
        else:
            app = QApplication.instance()
            if app:
                app.quit()

    def closeEvent(self, event):
        parent = self.parent()
        if parent is None:
            app = QApplication.instance()
            if app:
                app.quit()
        event.accept()

    def get_template_name(self):
        return self.template_name_edit.text().strip()

    def insert_field(self):
        field_name = self.field_combo.currentText()
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
        self.update_spinboxes_from_widget(field_widget)
        # reflect widget font in controls
        if field_widget:
            sf = getattr(field_widget, "saved_font", field_widget.font())
            self.field_font = QFont(sf)
            self.bold_btn.setChecked(self.field_font.bold())
            self.italic_btn.setChecked(self.field_font.italic())

    def update_spinboxes_from_widget(self, field_widget):
        """Updates the spinboxes based on a field widget's geometry."""
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
            # keep saved_font in sync when modifying via UI
            fw.setFont(self.field_font)
            fw.update_saved_font(self.field_font)
        else:
            self.active_field_widget = None

    def pick_font(self):
        font, ok = QFontDialog.getFont(self.field_font, self)
        if ok:
            self.field_font = font
            # update bold/italic toggle buttons
            self.bold_btn.setChecked(self.field_font.bold())
            self.italic_btn.setChecked(self.field_font.italic())
            # update active field (and its saved font)
            self.update_active_field()
            if self.active_field_widget:
                self.active_field_widget.update_saved_font(font)

    def toggle_bold(self, checked):
        self.field_font.setBold(bool(checked))
        # update active widget immediately
        if self.active_field_widget:
            current = QFont(self.active_field_widget.saved_font)
            current.setBold(bool(checked))
            # keep other attributes (size, family)
            self.active_field_widget.update_saved_font(current)
        # keep change visible for newly inserted fields as well

    def toggle_italic(self, checked):
        self.field_font.setItalic(bool(checked))
        if self.active_field_widget:
            current = QFont(self.active_field_widget.saved_font)
            current.setItalic(bool(checked))
            self.active_field_widget.update_saved_font(current)

    def apply_font_to_all_fields(self):
        """
        Apply current field_font's family and style to all fields.
        Preserve each field's point size to avoid changing layout unexpectedly.
        """
        for f in self.canvas.fields:
            old = getattr(f, "saved_font", f.font())
            # preserve point size; apply family and styles from self.field_font
            new_font = QFont(self.field_font.family(), safe_point_size(old))
            new_font.setBold(self.field_font.bold())
            new_font.setItalic(self.field_font.italic())
            new_font.setUnderline(self.field_font.underline())
            f.update_saved_font(new_font)
        self.status_label.setText("Applied font family/style to all fields.")

    def reset_default_font(self):
        self.field_font = QFont("Tahoma", 14)
        self.bold_btn.setChecked(self.field_font.bold())
        self.italic_btn.setChecked(self.field_font.italic())
        # update active if any
        if self.active_field_widget:
            self.active_field_widget.update_saved_font(self.field_font)

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
        execute_query("DELETE FROM templatefields WHERE templatename=%s", (template_name,))
        execute_query("DELETE FROM templatemaster WHERE templatename=%s", (template_name,))
        self.canvas.clear_fields()
        self.status_label.setText(f"Template '{template_name}' deleted.")
        self.template_name_edit.clear()
        self.set_default_checkbox.setChecked(False)
        self.active_field_widget = None

    def load_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose background image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.canvas.set_bg_image(path)

    def _fontstyle_from_qfont(self, qf: QFont):
        """Return a comma separated fontstyle string for storage (e.g. 'bold,italic')."""
        parts = []
        if qf.bold():
            parts.append("bold")
        if qf.italic():
            parts.append("italic")
        if qf.underline():
            parts.append("underline")
        return ",".join(parts) if parts else "normal"

    def _apply_fontstyle_to_qfont(self, qf: QFont, fontstyle_str: str):
        """Apply font style flags stored as string to a QFont instance."""
        if not fontstyle_str:
            return qf
        s = fontstyle_str.lower()
        qf.setBold("bold" in s)
        qf.setItalic("italic" in s)
        qf.setUnderline("underline" in s)
        return qf

    def save_template(self):
        template_name = self.get_template_name()
        if not template_name:
            self.status_label.setText("Please enter a template name.")
            return

        is_default = self.set_default_checkbox.isChecked()

        if is_default:
            execute_query("UPDATE templatemaster SET defaulttemplate=FALSE")

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
            is_default
        ))

        # Delete previous field rows for this template
        execute_query("DELETE FROM templatefields WHERE templatename=%s", (template_name,))

        # Insert current canvas fields using saved_font (robustly get point size)
        for f in self.canvas.fields:
            fs = getattr(f, "saved_font", None)
            if fs is None:
                fs = f.font()

            fontsize = safe_point_size(fs)
            x_mm, y_mm, w_mm, h_mm = f.get_mm_geometry()
            fontstyle = self._fontstyle_from_qfont(fs)

            # Note: schema must include fontstyle column (ALTER TABLE needed if missing)
            field_sql = """
                INSERT INTO templatefields
                (templatename, fieldname, displayname, x, y, width, height, fontname, fontsize, fontstyle)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_query(field_sql, (
                template_name, f.field_name, f.text(),
                x_mm, y_mm, w_mm, h_mm,
                fs.family(), int(fontsize), fontstyle
            ))
        self.status_label.setText("Template Saved")

    def load_default_template(self):
        default = fetch_one("SELECT templatename FROM templatemaster WHERE defaulttemplate=TRUE")
        if default:
            self.template_name_edit.setText(default['templatename'])
            self.load_template()
            self.set_default_checkbox.setChecked(True)
        else:
            self.set_default_checkbox.setChecked(False)

    def load_template(self):
        template_name = self.get_template_name()
        template = fetch_one("SELECT * FROM templatemaster WHERE templatename=%s", (template_name,))
        if template:
            self.ticket_height_spin.setValue(float(template['ticketheight']))
            self.ticket_width_spin.setValue(float(template['ticketwidth']))
            self.update_canvas_size()
            self.set_default_checkbox.setChecked(bool(template['defaulttemplate']))
            fields = execute_query("SELECT * FROM templatefields WHERE templatename=%s", (template_name,))
            self.canvas.clear_fields()
            for field in fields:
                # Some rows may not have fontstyle (older schema) — handle defensively
                fontname = field.get('fontname') or "Tahoma"
                fontsize = int(field.get('fontsize') or 12)
                fontstyle = field.get('fontstyle') or field.get('fontstyle', "normal")
                qf = QFont(fontname, fontsize)
                qf = self._apply_fontstyle_to_qfont(qf, fontstyle)

                fw = FieldWidget(
                    field['fieldname'],
                    float(field['x']),
                    float(field['y']),
                    float(field['width']),
                    float(field['height']),
                    qf,
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

    # Alignment functions
    def align_left(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            rect = self.active_field_widget.geometry()
            self.active_field_widget.setGeometry(0, rect.y(), rect.width(), rect.height())
            self.left_spin.setValue(px_to_mm(0))

    def align_center(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            field = self.active_field_widget
            canvas_width = self.canvas.width()
            field_width = field.width()
            center_x = (canvas_width - field_width) // 2
            field.setGeometry(center_x, field.y(), field.width(), field.height())
            self.left_spin.setValue(px_to_mm(center_x))

    def align_right(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            field = self.active_field_widget
            canvas_width = self.canvas.width()
            field_width = field.width()
            right_x = canvas_width - field_width
            field.setGeometry(right_x, field.y(), field.width(), field.height())
            self.left_spin.setValue(px_to_mm(right_x))

    # Keyboard shortcuts for moving field by 10mm
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress and QApplication.keyboardModifiers() == Qt.ControlModifier:
            if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
                fw = self.active_field_widget
                rect = fw.geometry()
                move_amt_px = mm_to_px(10)
                if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
                    new_y = rect.y() + move_amt_px
                    fw.setGeometry(rect.x(), new_y, rect.width(), rect.height())
                    self.top_spin.setValue(px_to_mm(new_y))
                    return True
                elif event.key() in (Qt.Key_Minus, Qt.Key_Underscore):
                    new_y = max(0, rect.y() - move_amt_px)
                    fw.setGeometry(rect.x(), new_y, rect.width(), rect.height())
                    self.top_spin.setValue(px_to_mm(new_y))
                    return True
                elif event.key() == Qt.Key_Left:
                    new_x = max(0, rect.x() - move_amt_px)
                    fw.setGeometry(new_x, rect.y(), rect.width(), rect.height())
                    self.left_spin.setValue(px_to_mm(new_x))
                    return True
                elif event.key() == Qt.Key_Right:
                    new_x = rect.x() + move_amt_px
                    fw.setGeometry(new_x, rect.y(), rect.width(), rect.height())
                    self.left_spin.setValue(px_to_mm(new_x))
                    return True
        return super().eventFilter(obj, event)

    def preview_print(self):
        sample_data = {f.field_name: f.field_name for f in self.canvas.fields}
        template_fields = []
        for f in self.canvas.fields:
            x, y, w, h = f.get_mm_geometry()
            # Use saved_font for preview metadata where possible
            fs = getattr(f, "saved_font", f.font())
            template_fields.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'fieldname': f.field_name,
                'fontname': fs.family(),
                'fontsize': safe_point_size(fs),
                'fontstyle': self._fontstyle_from_qfont(fs)
            })
        ticket_width_mm = self.ticket_width_spin.value()
        ticket_height_mm = self.ticket_height_spin.value()
        render_ticket_with_data(
            template_fields=template_fields,
            ticket_data=sample_data,
            ticket_width_mm=ticket_width_mm,
            ticket_height_mm=ticket_height_mm,
            parent=self,
            preview=True
        )

    def new_template(self):
        self.canvas.clear_fields()
        self.template_name_edit.clear()
        self.ticket_height_spin.setValue(100.0)
        self.ticket_width_spin.setValue(150.0)
        self.status_label.setText("Ready for new template.")
        self.active_field_widget = None
        self.set_default_checkbox.setChecked(False)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = TicketEntryDesignerWindow()
    win.show()
    sys.exit(app.exec_())
