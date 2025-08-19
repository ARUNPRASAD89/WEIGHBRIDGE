import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QDialog, QMessageBox,
    QListWidgetItem, QGroupBox, QGridLayout, QComboBox, QFontDialog, QSpinBox,
    QDoubleSpinBox, QFrame, QSplitter, QSizePolicy, QScrollArea, QApplication,
    QFontComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from db_utils import execute_query, fetch_all, fetch_one


def get_ticket_fields():
    try:
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tickets'
            ORDER BY ordinal_position;
        """
        rows = fetch_all(query)
        if not rows:
            QMessageBox.warning(None, "Warning", "Could not find any columns for the 'tickets' table.")
            return []
        return [row['column_name'] for row in rows]
    except Exception as e:
        QMessageBox.critical(None, "Database Error",
                             f"Could not load fields from the 'tickets' table.\nError: {e}")
        return []


class ReportDesigner(QDialog):
    CONTROL_HEIGHT = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Report Designer")
        self.resize(1400, 900)

        self.header_fonts = [QFont("Arial", 10) for _ in range(3)]
        self.footer_fonts = [QFont("Arial", 10) for _ in range(2)]
        self.header_edits = []
        self.footer_edits = []

        root_splitter = QSplitter(Qt.Horizontal, self)

        # Left panel
        self.template_group = self._create_template_selection_group()
        root_splitter.addWidget(self.template_group)

        # Center (scrollable)
        center_container = QWidget()
        center_vbox = QVBoxLayout(center_container)
        center_vbox.setContentsMargins(4, 4, 4, 4)
        center_vbox.setSpacing(12)

        self.page_layout_group = self._create_page_layout_group()
        center_vbox.addWidget(self.page_layout_group)

        self.header_group = self._create_header_footer_group("Page Header", 3, self.header_edits, self.header_fonts, True)
        center_vbox.addWidget(self.header_group)

        self.field_group = self._create_field_editor_group()
        center_vbox.addWidget(self.field_group, 1)

        self.footer_group = self._create_header_footer_group("Page Footer", 2, self.footer_edits, self.footer_fonts, False)
        center_vbox.addWidget(self.footer_group)

        center_vbox.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(center_container)
        scroll.setWidgetResizable(True)
        root_splitter.addWidget(scroll)

        # Right actions
        self.action_panel = self._create_action_panel()
        root_splitter.addWidget(self.action_panel)

        root_splitter.setStretchFactor(0, 0)
        root_splitter.setStretchFactor(1, 1)
        root_splitter.setStretchFactor(2, 0)

        dialog_layout = QHBoxLayout(self)
        dialog_layout.addWidget(root_splitter)

        self._apply_unified_styling()
        self.setup_connections()
        self.load_template_names()
        self.set_a4_defaults()

    def closeEvent(self, event):
        parent = self.parent()
        if parent is not None:
            parent.show()
            parent.raise_()
            parent.activateWindow()
        super().closeEvent(event)

    # ---------- UI Creation ----------

    def _apply_unified_styling(self):
        style = f"""
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton {{
            min-height: {self.CONTROL_HEIGHT}px;
        }}
        QListWidget {{
            font-size: 12px;
        }}
        QGroupBox {{
            font-weight: bold;
        }}
        """
        self.setStyleSheet(style)

    def _create_template_selection_group(self):
        group = QGroupBox("Select Template")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.template_list = QListWidget()
        self.template_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout.addWidget(self.template_list)
        return group

    def _create_page_layout_group(self):
        group = QGroupBox("Template & Page Layout (mm / font)")
        grid = QGridLayout(group)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        lbl_name = QLabel("Template Name:")
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("Enter or select a template name")
        self.set_default_btn = QPushButton("Set as Default")
        self.set_default_btn.setCheckable(True)

        grid.addWidget(lbl_name, 0, 0)
        grid.addWidget(self.template_name_edit, 0, 1, 1, 3)
        grid.addWidget(self.set_default_btn, 0, 4)

        self.pagewidth_edit = QDoubleSpinBox(); self.pagewidth_edit.setRange(40, 1000)
        self.pageheight_edit = QDoubleSpinBox(); self.pageheight_edit.setRange(40, 1000)
        self.topmargin_edit = QDoubleSpinBox(); self.topmargin_edit.setRange(0, 200); self.topmargin_edit.setValue(10)
        self.leftmargin_edit = QDoubleSpinBox(); self.leftmargin_edit.setRange(0, 200); self.leftmargin_edit.setValue(10)
        self.lineheight_edit = QDoubleSpinBox(); self.lineheight_edit.setRange(1, 50); self.lineheight_edit.setValue(7.0)

        # Font families & sizes
        self.header_font_family_combo = QFontComboBox()
        self.header_font_family_combo.setCurrentFont(QFont("Arial"))
        self.header_font_size_edit = QSpinBox(); self.header_font_size_edit.setRange(5, 72); self.header_font_size_edit.setValue(10)

        self.detail_font_family_combo = QFontComboBox()
        self.detail_font_family_combo.setCurrentFont(QFont("Arial"))
        self.detail_font_size_edit = QSpinBox(); self.detail_font_size_edit.setRange(5, 72); self.detail_font_size_edit.setValue(8)

        self.set_a4_btn = QPushButton("Set A4")

        # Row 1
        grid.addWidget(QLabel("Page Width:"), 1, 0)
        grid.addWidget(self.pagewidth_edit, 1, 1)
        grid.addWidget(QLabel("Page Height:"), 1, 2)
        grid.addWidget(self.pageheight_edit, 1, 3)
        grid.addWidget(self.set_a4_btn, 1, 4)

        # Row 2
        grid.addWidget(QLabel("Top Margin:"), 2, 0)
        grid.addWidget(self.topmargin_edit, 2, 1)
        grid.addWidget(QLabel("Left Margin:"), 2, 2)
        grid.addWidget(self.leftmargin_edit, 2, 3)
        grid.addWidget(QLabel("Line Height:"), 2, 4)
        grid.addWidget(self.lineheight_edit, 2, 5)

        # Row 3 (Header font)
        grid.addWidget(QLabel("Header Font:"), 3, 0)
        grid.addWidget(self.header_font_family_combo, 3, 1)
        grid.addWidget(QLabel("Size:"), 3, 2)
        grid.addWidget(self.header_font_size_edit, 3, 3)

        # Row 4 (Detail font)
        grid.addWidget(QLabel("Detail Font:"), 4, 0)
        grid.addWidget(self.detail_font_family_combo, 4, 1)
        grid.addWidget(QLabel("Size:"), 4, 2)
        grid.addWidget(self.detail_font_size_edit, 4, 3)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        return group

    def _create_header_footer_group(self, title, count, edit_list_ref, font_list_ref, is_header):
        group = QGroupBox(title)
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(6)
        for i in range(count):
            line_box = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText(f"Line {i+1}")
            font_btn = QPushButton("F")
            font_btn.setToolTip("Select Font")
            font_btn.setFixedWidth(34)
            font_btn.clicked.connect(
                lambda _, e=edit, f=font_list_ref[i], idx=i, h=is_header: self.open_font_dialog(e, f, idx, h)
            )
            line_box.addWidget(edit, 1)
            line_box.addWidget(font_btn, 0)
            vbox.addLayout(line_box)
            edit_list_ref.append(edit)
        return group

    def _create_field_editor_group(self):
        group = QGroupBox("Field Layout")
        outer_vbox = QVBoxLayout(group)
        outer_vbox.setContentsMargins(8, 8, 8, 8)
        outer_vbox.setSpacing(10)

        selection_frame = QFrame()
        sel_layout = QHBoxLayout(selection_frame)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(8)

        self.fields_list = QListWidget()
        self.fields_list.addItems(get_ticket_fields())
        self.fields_list.setMinimumWidth(220)
        sel_layout.addWidget(self.fields_list, 2)

        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(6)
        self.add_one_btn = QPushButton(">")
        self.remove_one_btn = QPushButton("<")
        self.move_up_btn = QPushButton("▲")
        self.move_down_btn = QPushButton("▼")
        for b in (self.add_one_btn, self.remove_one_btn, self.move_up_btn, self.move_down_btn):
            b.setFixedWidth(46)
            buttons_col.addWidget(b)
        buttons_col.addStretch(1)
        sel_layout.addLayout(buttons_col, 0)

        self.field_table = QTableWidget(0, 2)
        self.field_table.setHorizontalHeaderLabels(["Field Name", "Caption"])
        self.field_table.horizontalHeader().setStretchLastSection(True)
        self.field_table.verticalHeader().setVisible(False)
        self.field_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.field_table.setSelectionMode(QTableWidget.SingleSelection)
        self.field_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sel_layout.addWidget(self.field_table, 4)
        outer_vbox.addWidget(selection_frame, 3)

        # Field properties
        props_group = QGroupBox("Selected Field Properties")
        grid = QGridLayout(props_group)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.field_caption_edit = QLineEdit()
        self.x_pos_edit = QDoubleSpinBox(); self.x_pos_edit.setRange(-1000, 5000)
        self.y_pos_edit = QDoubleSpinBox(); self.y_pos_edit.setRange(-1000, 5000)
        self.width_edit = QDoubleSpinBox(); self.width_edit.setRange(0, 5000); self.width_edit.setValue(40)
        self.font_name_edit = QLineEdit("Arial")
        self.font_size_edit = QSpinBox(); self.font_size_edit.setRange(1, 200); self.font_size_edit.setValue(10)
        self.alignment_combo = QComboBox(); self.alignment_combo.addItems(["LEFT", "RIGHT", "CENTER"])

        self.save_field_props_btn = QPushButton("Update Field")
        self.apply_font_size_all_btn = QPushButton("Set Size To All Fields")
        self.apply_font_family_all_btn = QPushButton("Set Family To All Fields")

        grid.addWidget(QLabel("Caption:"), 0, 0)
        grid.addWidget(self.field_caption_edit, 0, 1, 1, 3)

        grid.addWidget(QLabel("X (mm):"), 1, 0)
        grid.addWidget(self.x_pos_edit, 1, 1)
        grid.addWidget(QLabel("Y (mm):"), 1, 2)
        grid.addWidget(self.y_pos_edit, 1, 3)

        grid.addWidget(QLabel("Width (mm):"), 2, 0)
        grid.addWidget(self.width_edit, 2, 1)
        grid.addWidget(QLabel("Alignment:"), 2, 2)
        grid.addWidget(self.alignment_combo, 2, 3)

        grid.addWidget(QLabel("Font Name:"), 3, 0)
        grid.addWidget(self.font_name_edit, 3, 1)
        grid.addWidget(QLabel("Font Size:"), 3, 2)
        grid.addWidget(self.font_size_edit, 3, 3)

        grid.addWidget(self.save_field_props_btn, 4, 0, 1, 2)
        grid.addWidget(self.apply_font_size_all_btn, 4, 2, 1, 2)
        grid.addWidget(self.apply_font_family_all_btn, 5, 2, 1, 2)

        outer_vbox.addWidget(props_group, 2)
        return group

    def _create_action_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 20, 8, 20)
        vbox.setSpacing(20)

        self.add_btn = QPushButton("Add")
        self.save_btn = QPushButton("Save")
        self.delete_btn = QPushButton("Delete")
        self.exit_btn = QPushButton("Exit")

        for b in (self.add_btn, self.save_btn, self.delete_btn, self.exit_btn):
            b.setMinimumWidth(110)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            vbox.addWidget(b)

        vbox.addStretch(1)
        return panel

    # ---------- Connections ----------

    def setup_connections(self):
        self.exit_btn.clicked.connect(self.close)
        self.fields_list.itemDoubleClicked.connect(lambda item: self._add_field(item.text()))
        self.add_one_btn.clicked.connect(lambda: self._add_field(self.fields_list.currentItem().text())
                                         if self.fields_list.currentItem() else None)
        self.remove_one_btn.clicked.connect(self.remove_selected_field)
        self.move_up_btn.clicked.connect(lambda: self._move_field(-1))
        self.move_down_btn.clicked.connect(lambda: self._move_field(1))

        self.save_btn.clicked.connect(self.save_report_template)
        self.add_btn.clicked.connect(self.add_new_template)
        self.delete_btn.clicked.connect(self.delete_report_template)

        self.template_list.itemClicked.connect(
            lambda item: self.load_template(item.text().replace(" (Default)", "")))
        self.set_default_btn.clicked.connect(self.set_template_as_default)
        self.set_a4_btn.clicked.connect(self.set_a4_defaults)

        self.field_table.itemClicked.connect(self.on_field_selected)
        self.save_field_props_btn.clicked.connect(self.save_field_properties_to_table)
        self.apply_font_size_all_btn.clicked.connect(self.apply_font_size_to_all_fields)
        self.apply_font_family_all_btn.clicked.connect(self.apply_font_family_to_all_fields)

    # ---------- Logic ----------

    def set_a4_defaults(self):
        self.pagewidth_edit.setValue(210)
        self.pageheight_edit.setValue(297)

    def remove_selected_field(self):
        row = self.field_table.currentRow()
        if row >= 0:
            self.field_table.removeRow(row)

    def _move_field(self, direction: int):
        row = self.field_table.currentRow()
        if row < 0:
            return
        target = row + direction
        if not (0 <= target < self.field_table.rowCount()):
            return
        for col in range(self.field_table.columnCount()):
            current_item = self.field_table.takeItem(row, col)
            target_item = self.field_table.takeItem(target, col)
            self.field_table.setItem(row, col, target_item)
            self.field_table.setItem(target, col, current_item)
        self.field_table.selectRow(target)

    def _add_field(self, field_name):
        if not field_name:
            return
        for r in range(self.field_table.rowCount()):
            it = self.field_table.item(r, 0)
            if it and it.text() == field_name:
                return
        row_pos = self.field_table.rowCount()
        self.field_table.insertRow(row_pos)
        self.field_table.setItem(row_pos, 0, QTableWidgetItem(field_name))
        caption_item = QTableWidgetItem(field_name)

        last_x, last_y, last_width = 0, 0, 0
        if row_pos > 0:
            last_item = self.field_table.item(row_pos - 1, 1)
            if last_item and last_item.data(Qt.UserRole):
                lp = last_item.data(Qt.UserRole)
                last_x = lp.get('x', 0)
                last_y = lp.get('y', 0)
                last_width = lp.get('width', 40)

        new_x = last_x + last_width + 5
        props = {"x": new_x, "y": last_y, "width": 40,
                 "fontname": self.detail_font_family_combo.currentFont().family(),
                 "fontsize": self.detail_font_size_edit.value(),
                 "alignment": "LEFT"}
        caption_item.setData(Qt.UserRole, props)
        self.field_table.setItem(row_pos, 1, caption_item)
        self.field_table.selectRow(row_pos)
        self.on_field_selected(caption_item)

    def on_field_selected(self, item):
        if not item:
            return
        row = item.row()
        caption_item = self.field_table.item(row, 1)
        if not caption_item:
            self.clear_field_properties()
            return
        props = caption_item.data(Qt.UserRole)
        if props:
            self.field_caption_edit.setText(caption_item.text())
            self.x_pos_edit.setValue(props.get('x', 0))
            self.y_pos_edit.setValue(props.get('y', 0))
            self.width_edit.setValue(props.get('width', 40))
            self.font_name_edit.setText(props.get('fontname', 'Arial'))
            self.font_size_edit.setValue(props.get('fontsize', 10))
            self.alignment_combo.setCurrentText(props.get('alignment', 'LEFT'))

    def save_field_properties_to_table(self):
        row = self.field_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Field Selected", "Select a field row first.")
            return
        caption_item = self.field_table.item(row, 1)
        caption_item.setText(self.field_caption_edit.text())
        props = {
            "x": self.x_pos_edit.value(),
            "y": self.y_pos_edit.value(),
            "width": self.width_edit.value(),
            "fontname": self.font_name_edit.text(),
            "fontsize": self.font_size_edit.value(),
            "alignment": self.alignment_combo.currentText()
        }
        caption_item.setData(Qt.UserRole, props)
        QMessageBox.information(self, "Updated", "Field updated in table. Click 'Save' to persist template.")

    def apply_font_size_to_all_fields(self):
        new_size = self.font_size_edit.value()
        changed = 0
        for r in range(self.field_table.rowCount()):
            item = self.field_table.item(r, 1)
            if not item:
                continue
            props = item.data(Qt.UserRole) or {}
            props['fontsize'] = new_size
            item.setData(Qt.UserRole, props)
            changed += 1
        QMessageBox.information(self, "Font Size Applied",
                                f"Font size {new_size} applied to {changed} field(s). Remember to Save.")

    def apply_font_family_to_all_fields(self):
        fam = self.detail_font_family_combo.currentFont().family()
        changed = 0
        for r in range(self.field_table.rowCount()):
            item = self.field_table.item(r, 1)
            if not item: continue
            props = item.data(Qt.UserRole) or {}
            props['fontname'] = fam
            item.setData(Qt.UserRole, props)
            changed += 1
        QMessageBox.information(self, "Font Family Applied",
                                f"Font family '{fam}' applied to {changed} field(s). Remember to Save.")

    def save_report_template(self):
        name = self.template_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Template Name is required.")
            return
        try:
            is_default = self.set_default_btn.isChecked()
            if is_default:
                execute_query('UPDATE ReportTemplate SET "Default" = FALSE')

            execute_query("""
                INSERT INTO ReportTemplate (reporttemplatename, "Default",
                                            pagewidth, pageheight, topmargin, leftmargin,
                                            headerfontsize, detailfontsize, lineheight,
                                            headerfontname, detailfontname)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (reporttemplatename) DO UPDATE SET
                    "Default"       = EXCLUDED."Default",
                    pagewidth       = EXCLUDED.pagewidth,
                    pageheight      = EXCLUDED.pageheight,
                    topmargin       = EXCLUDED.topmargin,
                    leftmargin      = EXCLUDED.leftmargin,
                    headerfontsize  = EXCLUDED.headerfontsize,
                    detailfontsize  = EXCLUDED.detailfontsize,
                    lineheight      = EXCLUDED.lineheight,
                    headerfontname  = EXCLUDED.headerfontname,
                    detailfontname  = EXCLUDED.detailfontname;
            """, (
                name, is_default,
                self.pagewidth_edit.value(), self.pageheight_edit.value(),
                self.topmargin_edit.value(), self.leftmargin_edit.value(),
                self.header_font_size_edit.value(), self.detail_font_size_edit.value(),
                self.lineheight_edit.value(),
                self.header_font_family_combo.currentFont().family(),
                self.detail_font_family_combo.currentFont().family()
            ))

            execute_query("DELETE FROM ReportDetail WHERE reporttemplatename=%s", (name,))
            execute_query("DELETE FROM ReportDesigner WHERE reporttemplatename=%s", (name,))

            for r in range(self.field_table.rowCount()):
                field_name = self.field_table.item(r, 0).text()
                caption_item = self.field_table.item(r, 1)
                caption, props = caption_item.text(), caption_item.data(Qt.UserRole)
                execute_query("""
                    INSERT INTO ReportDetail (reporttemplatename, fieldname, fieldcaption,
                                              x, y, width, fontname, fontsize, alignment)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (name, field_name, caption,
                      props.get('x', 0), props.get('y', 0), props.get('width', 40),
                      props.get('fontname', 'Arial'), props.get('fontsize', 10),
                      props.get('alignment', 'LEFT')))

            for i, edit in enumerate(self.header_edits):
                if edit.text().strip():
                    font = self.header_fonts[i]
                    execute_query("""
                        INSERT INTO ReportDesigner (reporttemplatename, section, sectioncaption,
                                                    fontname, size, bold, italic, underline)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (name, f"Header{i+1}", edit.text().strip(),
                          font.family(), font.pointSize(), font.bold(),
                          font.italic(), font.underline()))

            for i, edit in enumerate(self.footer_edits):
                if edit.text().strip():
                    font = self.footer_fonts[i]
                    execute_query("""
                        INSERT INTO ReportDesigner (reporttemplatename, section, sectioncaption,
                                                    fontname, size, bold, italic, underline)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (name, f"Footer{i+1}", edit.text().strip(),
                          font.family(), font.pointSize(), font.bold(),
                          font.italic(), font.underline()))

            QMessageBox.information(self, "Saved", f"Template '{name}' saved successfully.")
            self.load_template_names()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not save template:\n{e}")

    def load_template(self, name):
        self.clear_all_fields()
        self.template_name_edit.setText(name)
        try:
            template_data = fetch_one("SELECT * FROM ReportTemplate WHERE reporttemplatename=%s", (name,))
            if template_data:
                self.set_default_btn.setChecked(template_data.get('Default', False))
                self.pagewidth_edit.setValue(template_data.get('pagewidth', 210))
                self.pageheight_edit.setValue(template_data.get('pageheight', 297))
                self.topmargin_edit.setValue(template_data.get('topmargin', 10))
                self.leftmargin_edit.setValue(template_data.get('leftmargin', 10))
                self.header_font_size_edit.setValue(template_data.get('headerfontsize', 10))
                self.detail_font_size_edit.setValue(template_data.get('detailfontsize', 8))
                self.lineheight_edit.setValue(float(template_data.get('lineheight', 7.0) or 7.0))

                header_family = template_data.get('headerfontname', 'Arial') or 'Arial'
                detail_family = template_data.get('detailfontname', 'Arial') or 'Arial'
                self.header_font_family_combo.setCurrentFont(QFont(header_family))
                self.detail_font_family_combo.setCurrentFont(QFont(detail_family))

            detail_rows = fetch_all("SELECT * FROM ReportDetail WHERE reporttemplatename=%s ORDER BY id", (name,))
            self.field_table.setRowCount(len(detail_rows))
            for i, row_data in enumerate(detail_rows):
                self.field_table.setItem(i, 0, QTableWidgetItem(row_data["fieldname"]))
                caption_item = QTableWidgetItem(row_data["fieldcaption"])
                caption_item.setData(Qt.UserRole, dict(row_data))
                self.field_table.setItem(i, 1, caption_item)

            designer_rows = fetch_all("SELECT * FROM ReportDesigner WHERE reporttemplatename=%s", (name,))
            for s in designer_rows:
                font = QFont(s.get('fontname', 'Arial'), s.get('size', 10))
                font.setBold(s.get('bold', False))
                font.setItalic(s.get('italic', False))
                font.setUnderline(s.get('underline', False))

                target_edits = self.header_edits if s["section"].startswith("Header") else self.footer_edits
                target_fonts = self.header_fonts if s["section"].startswith("Header") else self.footer_fonts
                idx = int(s["section"][-1]) - 1
                if 0 <= idx < len(target_edits):
                    target_edits[idx].setText(s["sectioncaption"])
                    target_edits[idx].setFont(font)
                    target_fonts[idx] = font

            if self.field_table.rowCount() > 0:
                self.field_table.selectRow(0)
                self.on_field_selected(self.field_table.item(0, 0))

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load template '{name}':\n{e}")

    def add_new_template(self):
        self.clear_all_fields()
        self.template_list.clearSelection()
        self.template_name_edit.setFocus()

    def clear_all_fields(self):
        self.template_name_edit.clear()
        self.set_a4_defaults()
        self.topmargin_edit.setValue(10)
        self.leftmargin_edit.setValue(10)
        self.header_font_family_combo.setCurrentFont(QFont("Arial"))
        self.detail_font_family_combo.setCurrentFont(QFont("Arial"))
        self.header_font_size_edit.setValue(10)
        self.detail_font_size_edit.setValue(8)
        self.lineheight_edit.setValue(7.0)
        for i, edit in enumerate(self.header_edits):
            edit.clear()
            self.header_fonts[i] = QFont("Arial", 10)
            edit.setFont(self.header_fonts[i])
        for i, edit in enumerate(self.footer_edits):
            edit.clear()
            self.footer_fonts[i] = QFont("Arial", 10)
            edit.setFont(self.footer_fonts[i])
        self.field_table.setRowCount(0)
        self.clear_field_properties()

    def clear_field_properties(self):
        self.field_caption_edit.clear()
        self.x_pos_edit.setValue(0)
        self.y_pos_edit.setValue(0)
        self.width_edit.setValue(40)
        self.font_name_edit.setText("Arial")
        self.font_size_edit.setValue(10)
        self.alignment_combo.setCurrentIndex(0)

    def delete_report_template(self):
        selected = self.template_list.currentItem()
        if not selected:
            return
        name = selected.text().replace(" (Default)", "")
        if QMessageBox.question(self, "Confirm Delete",
                                f"Delete template '{name}'?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                execute_query("DELETE FROM ReportTemplate WHERE reporttemplatename=%s", (name,))
                execute_query("DELETE FROM ReportDetail WHERE reporttemplatename=%s", (name,))
                execute_query("DELETE FROM ReportDesigner WHERE reporttemplatename=%s", (name,))
                self.load_template_names()
                self.clear_all_fields()
            except Exception as e:
                QMessageBox.critical(self, "DB Error", f"Could not delete template:\n{e}")

    def set_template_as_default(self):
        selected = self.template_list.currentItem()
        if not selected:
            self.set_default_btn.setChecked(False)
            return
        name_to_set = selected.text().replace(" (Default)", "")
        is_checked = self.set_default_btn.isChecked()
        try:
            if is_checked:
                execute_query('UPDATE ReportTemplate SET "Default" = FALSE')
                execute_query('UPDATE ReportTemplate SET "Default" = TRUE WHERE reporttemplatename = %s',
                              (name_to_set,))
            else:
                execute_query('UPDATE ReportTemplate SET "Default" = FALSE WHERE reporttemplatename = %s',
                              (name_to_set,))
            self.load_template_names()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not set default status:\n{e}")

    def open_font_dialog(self, line_edit, font_obj, index, is_header):
        ok, font = QFontDialog.getFont(font_obj, self)
        if ok:
            target_list = self.header_fonts if is_header else self.footer_fonts
            target_list[index] = font
            line_edit.setFont(font)

    def load_template_names(self):
        current_selection_text = (self.template_list.currentItem().text().replace(" (Default)", "")
                                  if self.template_list.currentItem() else None)
        self.template_list.clear()
        try:
            rows = fetch_all('SELECT reporttemplatename, "Default" FROM ReportTemplate ORDER BY reporttemplatename')
            for r in rows:
                name = r["reporttemplatename"]
                is_default = r["Default"]
                item = QListWidgetItem(name)
                if is_default:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                    item.setText(f"{name} (Default)")
                self.template_list.addItem(item)
                if name == current_selection_text:
                    self.template_list.setCurrentItem(item)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Could not load templates:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = ReportDesigner()
    dlg.show()
    sys.exit(app.exec_())
