# Updated ticket_entry_designer_window.py
# Fix: Ensure FieldWidget's built-in mouse handlers are used (don't override mousePressEvent)
# so fields can be moved by mouse drag. Removed assignments that replaced the method.
# Keeps zoom, rulers, scrollable canvas, keyboard nudges, maximize, presets, etc.

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QGroupBox, QDoubleSpinBox, QFileDialog,
    QFrame, QFontDialog, QApplication, QMenu, QInputDialog, QMessageBox, QCheckBox, QDialog,
    QScrollArea, QSizePolicy, QSpinBox
)
from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtCore import Qt, QRect, QPoint

from db_utils import execute_query, fetch_one
from ticket_printer import render_ticket_with_data

MM_TO_PX = 3.78  # for 96 DPI

def mm_to_px(mm):
    return int(round(mm * MM_TO_PX))

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
    Field widget that stores geometry in millimetres and renders at visual pixels depending on zoom.
    Dragging calculations convert between visual px and mm so saved mm positions remain accurate.
    """
    def __init__(self, field_name, x_mm, y_mm, w_mm, h_mm, font: QFont, parent_canvas):
        super().__init__(field_name, parent_canvas)
        self.field_name = field_name
        self.parent_canvas = parent_canvas  # CanvasWidget instance

        # store geometry in mm (authoritative)
        self.x_mm = float(x_mm)
        self.y_mm = float(y_mm)
        self.width_mm = float(w_mm)
        self.height_mm = float(h_mm)

        # store font for saving/loading
        self.saved_font = QFont(font)
        self.setFont(self.saved_font)

        # visual attributes
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFrameShape(QFrame.Panel)
        self.setFrameShadow(QFrame.Raised)
        self.setScaledContents(True)
        self.setMouseTracking(True)

        self._dragging = False
        self._drag_offset = QPoint(0, 0)

        self._apply_font_stylesheet()

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # set initial visual geometry according to parent's zoom
        self.update_visual_geometry(getattr(self.parent_canvas, "zoom", 1.0))

    def _apply_font_stylesheet(self):
        family = self.saved_font.family()
        size_pt = safe_point_size(self.saved_font)
        bold = 'bold' if self.saved_font.bold() else 'normal'
        italic = 'italic' if self.saved_font.italic() else 'normal'
        style = (
            "background-color: #f9f9f9;"
            "border: 1px solid #222;"
            f" font-family: '{family}';"
            f" font-size: {int(size_pt)}pt;"
            f" font-weight: { '700' if bold == 'bold' else '400' };"
            f" font-style: {italic};"
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(style)

    def update_saved_font(self, qfont: QFont):
        self.saved_font = QFont(qfont)
        self.setFont(self.saved_font)
        self._apply_font_stylesheet()

    def update_visual_geometry(self, zoom: float):
        """Set widget geometry in parent (canvas) based on stored mm geometry and zoom."""
        px_x = mm_to_px(self.x_mm) * zoom
        px_y = mm_to_px(self.y_mm) * zoom
        px_w = mm_to_px(self.width_mm) * zoom
        px_h = mm_to_px(self.height_mm) * zoom
        px_w = max(4, int(round(px_w)))
        px_h = max(4, int(round(px_h)))
        self.setGeometry(int(round(px_x)), int(round(px_y)), px_w, px_h)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            # keep offset within the widget so it doesn't jump
            self._drag_offset = event.pos()
            self.raise_()
            # set active in the main window (TicketEntryDesignerWindow expects signature set_active_field(event, widget))
            try:
                main_w = self.window()
                if hasattr(main_w, "set_active_field"):
                    main_w.set_active_field(event, self)
            except Exception:
                pass
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            parent = self.parentWidget()
            if parent:
                # compute new top-left in parent's coordinates (visual px)
                global_pos = event.globalPos()
                parent_global = parent.mapToGlobal(QPoint(0, 0))
                new_top_left_px = global_pos - parent_global - self._drag_offset

                # clamp to canvas
                max_x = parent.width() - self.width()
                max_y = parent.height() - self.height()
                new_x_px = max(0, min(new_top_left_px.x(), max_x))
                new_y_px = max(0, min(new_top_left_px.y(), max_y))

                # convert visual px back to mm with zoom consideration
                zoom = getattr(parent, "zoom", 1.0)
                base_px_x = int(round(new_x_px / zoom))
                base_px_y = int(round(new_y_px / zoom))
                new_x_mm = px_to_mm(base_px_x)
                new_y_mm = px_to_mm(base_px_y)

                # apply new stored mm positions and update visuals
                self.x_mm = new_x_mm
                self.y_mm = new_y_mm
                self.update_visual_geometry(zoom)

                # notify window to update spinboxes
                try:
                    main_w = self.window()
                    if hasattr(main_w, "update_spinboxes_from_widget") and main_w.active_field_widget is self:
                        main_w.update_spinboxes_from_widget(self)
                except Exception:
                    pass

            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
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
        """Return authoritative mm geometry."""
        return (self.x_mm, self.y_mm, self.width_mm, self.height_mm)


class CanvasWidget(QFrame):
    """
    Canvas that hosts FieldWidget children. Keeps zoom factor and updates children
    when zoom or canvas size changes.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = []
        self.bg_image = None
        self.zoom = 1.0
        self.base_width_px = 0
        self.base_height_px = 0
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: white; border: 1px solid #bbb;")

    def add_field(self, field_widget):
        field_widget.setParent(self)
        field_widget.show()
        self.fields.append(field_widget)
        field_widget.update_visual_geometry(self.zoom)

    def remove_field(self, field_widget):
        if field_widget in self.fields:
            self.fields.remove(field_widget)
            field_widget.deleteLater()
            top = self.window()
            if hasattr(top, 'active_field_widget') and top.active_field_widget is field_widget:
                top.active_field_widget = None

    def clear_fields(self):
        for f in list(self.fields):
            f.close()
        self.fields.clear()

    def set_bg_image(self, path):
        self.bg_image = QPixmap(path)
        self.update()

    def set_zoom(self, zoom: float):
        if zoom <= 0:
            return
        self.zoom = zoom
        if self.base_width_px and self.base_height_px:
            self.setFixedSize(int(round(self.base_width_px * zoom)), int(round(self.base_height_px * zoom)))
        for f in self.fields:
            f.update_visual_geometry(self.zoom)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self.bg_image:
            scaled = self.bg_image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)


class TicketEntryDesignerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket Print Designer")
        self.setMinimumSize(1200, 900)
        self.ticket_fields = get_ticket_columns()
        self.active_field_widget = None
        self._is_maximized = False
        self.zoom = 1.0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Top controls
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # Left buttons
        self.left_btn_layout = QVBoxLayout()
        self.left_btn_layout.setSpacing(8)
        btn_names = ["New", "Open", "Delete", "Save", "Print Preview", "Maximize", "Help", "Exit"]
        self.btn_dict = {}
        for text in btn_names:
            btn = QPushButton(text)
            btn.setFixedWidth(110)
            btn.setMinimumHeight(28)
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
        self.btn_dict["Maximize"].clicked.connect(self.toggle_maximize)

        # Field spec group
        field_spec = QGroupBox("Field Spec")
        field_spec_layout = QGridLayout(field_spec)
        field_spec_layout.setHorizontalSpacing(10)
        field_spec_layout.setVerticalSpacing(6)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setMaximum(1000.0)
        self.height_spin.setValue(10.0)
        self.height_spin.setSuffix(" mm")
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setMaximum(1000.0)
        self.width_spin.setValue(50.0)
        self.width_spin.setSuffix(" mm")
        self.top_spin = QDoubleSpinBox()
        self.top_spin.setMaximum(1000.0)
        self.top_spin.setValue(10.0)
        self.top_spin.setSuffix(" mm")
        self.left_spin = QDoubleSpinBox()
        self.left_spin.setMaximum(1000.0)
        self.left_spin.setValue(10.0)
        self.left_spin.setSuffix(" mm")
        self.font_btn = QPushButton("Font")
        self.font_btn.clicked.connect(self.pick_font)
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

        # Template name & status
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

        # Controls group
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

        # Ticket spec
        ticket_spec_group = QGroupBox("Ticket Spec")
        ticket_spec_layout = QGridLayout(ticket_spec_group)
        ticket_spec_layout.setHorizontalSpacing(10)
        ticket_spec_layout.setVerticalSpacing(6)
        self.ticket_height_spin = QDoubleSpinBox()
        self.ticket_height_spin.setMaximum(1000.0)
        self.ticket_height_spin.setValue(100.0)
        self.ticket_height_spin.setSuffix(" mm")
        self.ticket_width_spin = QDoubleSpinBox()
        self.ticket_width_spin.setMaximum(1000.0)
        self.ticket_width_spin.setValue(150.0)
        self.ticket_width_spin.setSuffix(" mm")

        # Copies spinbox (new)
        self.copies_spin = QSpinBox()
        self.copies_spin.setMinimum(1)
        self.copies_spin.setMaximum(99)
        self.copies_spin.setValue(1)
        self.copies_spin.setToolTip("Number of copies to print for this template")

        ticket_spec_layout.addWidget(QLabel("Page Size:"), 0, 0)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["Custom", "A4 (210 x 297 mm)", "A5 (148 x 210 mm)", "Letter (216 x 279 mm)", "Receipt (80 x 200 mm)"])
        self.page_size_combo.setCurrentIndex(0)
        ticket_spec_layout.addWidget(self.page_size_combo, 0, 1, 1, 2)
        self.page_size_combo.currentIndexChanged.connect(self.apply_page_preset)

        ticket_spec_layout.addWidget(QLabel("Height:"), 1, 0)
        ticket_spec_layout.addWidget(self.ticket_height_spin, 1, 1)
        ticket_spec_layout.addWidget(QLabel("Width:"), 2, 0)
        ticket_spec_layout.addWidget(self.ticket_width_spin, 2, 1)

        # place Copies control
        ticket_spec_layout.addWidget(QLabel("Copies:"), 1, 2)
        ticket_spec_layout.addWidget(self.copies_spin, 1, 3)

        top_layout.addWidget(ticket_spec_group, alignment=Qt.AlignTop)

        # Zoom controls
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QHBoxLayout(zoom_group)
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(28, 28)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(28, 28)
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_100_btn = QPushButton("100%")
        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addWidget(self.zoom_fit_btn)
        zoom_layout.addWidget(self.zoom_100_btn)
        zoom_layout.addWidget(self.zoom_label)
        self.zoom_out_btn.clicked.connect(lambda: self.change_zoom(0.8))
        self.zoom_in_btn.clicked.connect(lambda: self.change_zoom(1.25))
        self.zoom_fit_btn.clicked.connect(self.zoom_fit_to_view)
        self.zoom_100_btn.clicked.connect(lambda: self.set_zoom(1.0))
        top_layout.addWidget(zoom_group, alignment=Qt.AlignTop)

        # Alignment
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

        # Font controls
        font_box = QGroupBox("Font")
        font_layout = QVBoxLayout(font_box)
        font_layout.addWidget(QLabel("Tahoma"), alignment=Qt.AlignLeft)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.change_font_btn = QPushButton("Change Font")
        self.change_font_btn.clicked.connect(self.pick_font)
        btn_row.addWidget(self.change_font_btn)

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

        self.apply_font_all_btn = QPushButton("Apply Font to All")
        self.apply_font_all_btn.clicked.connect(self.apply_font_to_all_fields)
        btn_row.addWidget(self.apply_font_all_btn)

        self.default_font_btn = QPushButton("Default")
        self.default_font_btn.clicked.connect(self.reset_default_font)
        btn_row.addWidget(self.default_font_btn)

        font_layout.addLayout(btn_row)
        main_layout.addWidget(font_box, alignment=Qt.AlignLeft)

        # Rulers (top and left) containers
        self.top_ruler_container = QWidget()
        self.top_ruler_layout = QHBoxLayout(self.top_ruler_container)
        self.top_ruler_layout.setContentsMargins(0, 0, 0, 0)
        self.top_ruler_layout.setSpacing(0)
        self.top_ruler_inner = QWidget()
        self.top_ruler_inner_layout = QHBoxLayout(self.top_ruler_inner)
        self.top_ruler_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.top_ruler_inner_layout.setSpacing(0)
        self.top_ruler_layout.addWidget(self.top_ruler_inner)
        main_layout.addWidget(self.top_ruler_container)

        self.left_ruler_container = QWidget()
        self.left_ruler_layout = QVBoxLayout(self.left_ruler_container)
        self.left_ruler_layout.setContentsMargins(0, 0, 0, 0)
        self.left_ruler_layout.setSpacing(0)
        self.left_ruler_inner = QWidget()
        self.left_ruler_inner_layout = QVBoxLayout(self.left_ruler_inner)
        self.left_ruler_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.left_ruler_inner_layout.setSpacing(0)

        # Design area / canvas inside scroll area
        design_area_layout = QHBoxLayout()
        design_area_layout.setSpacing(0)
        design_area_layout.addWidget(self.left_ruler_container)

        self.canvas = CanvasWidget(None)
        self.canvas.base_width_px = mm_to_px(self.ticket_width_spin.value())
        self.canvas.base_height_px = mm_to_px(self.ticket_height_spin.value())
        self.canvas.setFixedSize(self.canvas.base_width_px, self.canvas.base_height_px)
        self.canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.canvas.zoom = self.zoom

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setMinimumSize(600, 400)
        design_area_layout.addWidget(self.scroll_area)
        main_layout.addLayout(design_area_layout)

        # build rulers and link scrollbars
        self._build_rulers()
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._on_hscroll)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_vscroll)

        # steppers/connects
        self.height_spin.valueChanged.connect(self.update_active_field)
        self.width_spin.valueChanged.connect(self.update_active_field)
        self.top_spin.valueChanged.connect(self.update_active_field)
        self.left_spin.valueChanged.connect(self.update_active_field)
        self.ticket_height_spin.valueChanged.connect(self.update_canvas_size)
        self.ticket_width_spin.valueChanged.connect(self.update_canvas_size)

        # keyboard event filter
        self.installEventFilter(self)

        # load default
        self.load_default_template()

    # Ruler helpers
    def _build_rulers(self):
        for i in reversed(range(self.top_ruler_inner_layout.count())):
            w = self.top_ruler_inner_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        for i in reversed(range(self.left_ruler_inner_layout.count())):
            w = self.left_ruler_inner_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        num_ticks = 60
        for i in range(num_ticks):
            lab = QLabel(str(i * 10))
            lab.setAlignment(Qt.AlignCenter)
            lab.setFixedWidth(int(round(mm_to_px(10) * self.zoom)))
            self.top_ruler_inner_layout.addWidget(lab)
        for i in range(num_ticks):
            lab = QLabel(str(i * 10))
            lab.setAlignment(Qt.AlignVCenter)
            lab.setFixedHeight(int(round(mm_to_px(10) * self.zoom)))
            self.left_ruler_inner_layout.addWidget(lab)

        self.top_ruler_inner.setFixedHeight(int(round(mm_to_px(10) * self.zoom)))
        self.left_ruler_inner.setFixedWidth(int(round(mm_to_px(10) * self.zoom)))

        for i in reversed(range(self.top_ruler_layout.count())):
            item = self.top_ruler_layout.takeAt(i)
            if item:
                w = item.widget()
                if w:
                    w.setParent(None)
        self.top_ruler_layout.addWidget(self.top_ruler_inner)

        for i in reversed(range(self.left_ruler_layout.count())):
            item = self.left_ruler_layout.takeAt(i)
            if item:
                w = item.widget()
                if w:
                    w.setParent(None)
        self.left_ruler_layout.addWidget(self.left_ruler_inner)

    def _on_hscroll(self, value):
        self.top_ruler_inner.move(-int(round(value)), 0)

    def _on_vscroll(self, value):
        self.left_ruler_inner.move(0, -int(round(value)))

    # Zoom functions
    def set_zoom(self, factor: float):
        if factor <= 0.05:
            return
        self.zoom = factor
        self.canvas.set_zoom(self.zoom)
        self.zoom_label.setText(f"{int(round(self.zoom * 100))}%")
        self._build_rulers()
        self.scroll_area.viewport().update()
        self._on_hscroll(self.scroll_area.horizontalScrollBar().value())
        self._on_vscroll(self.scroll_area.verticalScrollBar().value())

    def change_zoom(self, multiplier: float):
        self.set_zoom(self.zoom * multiplier)

    def set_canvas_base_size_from_spins(self):
        w_mm = self.ticket_width_spin.value()
        h_mm = self.ticket_height_spin.value()
        self.canvas.base_width_px = mm_to_px(w_mm)
        self.canvas.base_height_px = mm_to_px(h_mm)

    def update_canvas_size(self):
        self.set_canvas_base_size_from_spins()
        self.canvas.setFixedSize(int(round(self.canvas.base_width_px * self.zoom)),
                                 int(round(self.canvas.base_height_px * self.zoom)))
        self.canvas.zoom = self.zoom
        for f in self.canvas.fields:
            f.update_visual_geometry(self.zoom)
        self._build_rulers()
        self._on_hscroll(self.scroll_area.horizontalScrollBar().value())
        self._on_vscroll(self.scroll_area.verticalScrollBar().value())
        self.status_label.setText(f"Canvas set to {self.ticket_width_spin.value()} x {self.ticket_height_spin.value()} mm (zoom {int(round(self.zoom*100))}%)")

    def zoom_fit_to_view(self):
        viewport_size = self.scroll_area.viewport().size()
        if not hasattr(self.canvas, 'base_width_px') or not hasattr(self.canvas, 'base_height_px'):
            return
        if self.canvas.base_width_px == 0 or self.canvas.base_height_px == 0:
            return
        sx = viewport_size.width() / float(self.canvas.base_width_px)
        sy = viewport_size.height() / float(self.canvas.base_height_px)
        fit_zoom = min(sx, sy) * 0.95
        fit_zoom = max(0.05, min(5.0, fit_zoom))
        self.set_zoom(fit_zoom)

    # Window controls
    def toggle_maximize(self):
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            self.showMaximized()
            self._is_maximized = True
            self.btn_dict["Maximize"].setText("Restore")
        else:
            self.showNormal()
            try:
                self.setGeometry(self._normal_geometry)
            except Exception:
                pass
            self._is_maximized = False
            self.btn_dict["Maximize"].setText("Maximize")

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

    # Field insertion & selection (DO NOT override FieldWidget.mousePressEvent here)
    def insert_field(self):
        field_name = self.field_combo.currentText()
        x = self.left_spin.value()
        y = self.top_spin.value()
        w = self.width_spin.value()
        h = self.height_spin.value()
        fw = FieldWidget(field_name, x, y, w, h, self.field_font, self.canvas)
        # rely on FieldWidget.mousePressEvent to call set_active_field on click
        # do not override mousePressEvent (that breaks dragging)
        self.canvas.add_field(fw)
        self.set_active_field(None, fw)

    def set_active_field(self, event, field_widget):
        self.active_field_widget = field_widget
        if field_widget:
            self.update_spinboxes_from_widget(field_widget)
            sf = getattr(field_widget, "saved_font", field_widget.font())
            self.field_font = QFont(sf)
            self.bold_btn.setChecked(self.field_font.bold())
            self.italic_btn.setChecked(self.field_font.italic())

    def update_spinboxes_from_widget(self, field_widget):
        if not field_widget:
            return
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
            fw.x_mm = self.left_spin.value()
            fw.y_mm = self.top_spin.value()
            fw.width_mm = self.width_spin.value()
            fw.height_mm = self.height_spin.value()
            fw.update_visual_geometry(self.zoom)
        else:
            self.active_field_widget = None

    # Fonts
    def pick_font(self):
        font, ok = QFontDialog.getFont(self.field_font, self)
        if ok:
            self.field_font = font
            self.bold_btn.setChecked(self.field_font.bold())
            self.italic_btn.setChecked(self.field_font.italic())
            self.update_active_field()
            if self.active_field_widget:
                self.active_field_widget.update_saved_font(font)

    def toggle_bold(self, checked):
        self.field_font.setBold(bool(checked))
        if self.active_field_widget:
            current = QFont(self.active_field_widget.saved_font)
            current.setBold(bool(checked))
            self.active_field_widget.update_saved_font(current)

    def toggle_italic(self, checked):
        self.field_font.setItalic(bool(checked))
        if self.active_field_widget:
            current = QFont(self.active_field_widget.saved_font)
            current.setItalic(bool(checked))
            self.active_field_widget.update_saved_font(current)

    def apply_font_to_all_fields(self):
        for f in self.canvas.fields:
            old = getattr(f, "saved_font", f.font())
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
        if self.active_field_widget:
            self.active_field_widget.update_saved_font(self.field_font)

    # Canvas size / templates
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
        parts = []
        if qf.bold():
            parts.append("bold")
        if qf.italic():
            parts.append("italic")
        if qf.underline():
            parts.append("underline")
        return ",".join(parts) if parts else "normal"

    def _apply_fontstyle_to_qfont(self, qf: QFont, fontstyle_str: str):
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

        # include copies column (uses DEFAULT 1 where callers don't provide it)
        template_sql = """
            INSERT INTO templatemaster
            (templatename, ticketheight, ticketwidth, defaulttemplate, copies)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (templatename) DO UPDATE
            SET ticketheight=EXCLUDED.ticketheight,
                ticketwidth=EXCLUDED.ticketwidth,
                defaulttemplate=EXCLUDED.defaulttemplate,
                copies=EXCLUDED.copies
        """
        execute_query(template_sql, (
            template_name,
            self.ticket_height_spin.value(),
            self.ticket_width_spin.value(),
            is_default,
            int(self.copies_spin.value())
        ))

        execute_query("DELETE FROM templatefields WHERE templatename=%s", (template_name,))

        for f in self.canvas.fields:
            fs = getattr(f, "saved_font", None)
            if fs is None:
                fs = f.font()
            fontsize = safe_point_size(fs)
            x_mm, y_mm, w_mm, h_mm = f.get_mm_geometry()
            fontstyle = self._fontstyle_from_qfont(fs)
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
            # defensively handle missing copies column by falling back to 1
            try:
                copies_val = int(template.get('copies', 1) if template.get('copies', None) is not None else 1)
            except Exception:
                copies_val = 1

            self.ticket_height_spin.setValue(float(template['ticketheight']))
            self.ticket_width_spin.setValue(float(template['ticketwidth']))
            self.copies_spin.setValue(copies_val)
            self.update_canvas_size()
            self.set_default_checkbox.setChecked(bool(template.get('defaulttemplate')))
            fields = execute_query("SELECT * FROM templatefields WHERE templatename=%s", (template_name,))
            self.canvas.clear_fields()
            for field in fields:
                fontname = field.get('fontname') or "Tahoma"
                fontsize = int(field.get('fontsize') or 12)
                fontstyle = field.get('fontstyle') or "normal"
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
                # rely on FieldWidget's own mousePressEvent (do not override)
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

    # Alignment
    def align_left(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            fw = self.active_field_widget
            fw.x_mm = 0.0
            fw.update_visual_geometry(self.zoom)
            self.left_spin.setValue(0.0)

    def align_center(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            fw = self.active_field_widget
            canvas_mm_w = px_to_mm(self.canvas.base_width_px)
            center_x_mm = (canvas_mm_w - fw.width_mm) / 2.0
            fw.x_mm = max(0.0, center_x_mm)
            fw.update_visual_geometry(self.zoom)
            self.left_spin.setValue(fw.x_mm)

    def align_right(self):
        if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
            fw = self.active_field_widget
            canvas_mm_w = px_to_mm(self.canvas.base_width_px)
            fw.x_mm = max(0.0, canvas_mm_w - fw.width_mm)
            fw.update_visual_geometry(self.zoom)
            self.left_spin.setValue(fw.x_mm)

    # Keyboard movement & event filter
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ShiftModifier:
                step_mm = 10.0
            elif modifiers & Qt.ControlModifier:
                step_mm = 0.1
            else:
                step_mm = 1.0

            if self.active_field_widget and self.active_field_widget.parent() is self.canvas:
                fw = self.active_field_widget
                moved = False
                if event.key() == Qt.Key_Left:
                    fw.x_mm = max(0.0, fw.x_mm - step_mm)
                    moved = True
                elif event.key() == Qt.Key_Right:
                    canvas_mm_w = px_to_mm(self.canvas.base_width_px)
                    fw.x_mm = min(canvas_mm_w - fw.width_mm, fw.x_mm + step_mm)
                    moved = True
                elif event.key() == Qt.Key_Up:
                    fw.y_mm = max(0.0, fw.y_mm - step_mm)
                    moved = True
                elif event.key() == Qt.Key_Down:
                    canvas_mm_h = px_to_mm(self.canvas.base_height_px)
                    fw.y_mm = min(canvas_mm_h - fw.height_mm, fw.y_mm + step_mm)
                    moved = True

                if moved:
                    fw.update_visual_geometry(self.zoom)
                    self.update_spinboxes_from_widget(fw)
                    return True

        return super().eventFilter(obj, event)

    def preview_print(self):
        sample_data = {f.field_name: f.field_name for f in self.canvas.fields}
        template_fields = []
        for f in self.canvas.fields:
            x, y, w, h = f.get_mm_geometry()
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
        self.copies_spin.setValue(1)
        self.status_label.setText("Ready for new template.")
        self.active_field_widget = None
        self.set_default_checkbox.setChecked(False)

    def apply_page_preset(self, index):
        if index == 0:
            return
        if index == 1:  # A4
            w, h = 210.0, 297.0
        elif index == 2:  # A5
            w, h = 148.0, 210.0
        elif index == 3:  # Letter
            w, h = 216.0, 279.0
        elif index == 4:  # Receipt
            w, h = 80.0, 200.0
        else:
            return
        self.ticket_width_spin.setValue(w)
        self.ticket_height_spin.setValue(h)
        self.update_canvas_size()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = TicketEntryDesignerWindow()
    win.show()
    sys.exit(app.exec_())
