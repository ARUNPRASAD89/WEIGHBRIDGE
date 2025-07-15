from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QApplication, QDialog
)
from material_master import MaterialMaster
from supplier_master import SupplierMaster
from shift_master import ShiftMaster
from vehicle_master import VehicleMaster
from comm_port_settings import CommPortSettings
from report_designer import ReportDesigner
from delete_entities import DeleteEntities
from duplicate_ticket import DuplicateTicket

class ConfigurationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.setFixedSize(250, 400)
        layout = QVBoxLayout(self)

        self.material_btn = QPushButton("Material Master")
        self.supplier_btn = QPushButton("Supplier Master")
        self.shift_btn = QPushButton("Shift Master")
        self.vehicle_btn = QPushButton("Vehicle Master")
        self.commport_btn = QPushButton("Comm Port Setting")
        self.reportdesigner_btn = QPushButton("Report Designer")
        self.deleteentities_btn = QPushButton("Delete Entities")
        self.duplicateticket_btn = QPushButton("Duplicate Ticket")
        self.exit_btn = QPushButton("Exit")

        layout.addWidget(self.material_btn)
        layout.addWidget(self.supplier_btn)
        layout.addWidget(self.shift_btn)
        layout.addWidget(self.vehicle_btn)
        layout.addWidget(self.commport_btn)
        layout.addWidget(self.reportdesigner_btn)
        layout.addWidget(self.deleteentities_btn)
        layout.addWidget(self.duplicateticket_btn)
        layout.addStretch()
        layout.addWidget(self.exit_btn)  # Add Exit button at the bottom

        self.material_btn.clicked.connect(self.open_material_master)
        self.supplier_btn.clicked.connect(self.open_supplier_master)
        self.shift_btn.clicked.connect(self.open_shift_master)
        self.vehicle_btn.clicked.connect(self.open_vehicle_master)
        self.commport_btn.clicked.connect(self.open_comm_port_settings)
        self.reportdesigner_btn.clicked.connect(self.open_report_designer)
        self.deleteentities_btn.clicked.connect(self.open_delete_entities)
        self.duplicateticket_btn.clicked.connect(self.open_duplicate_ticket)
        self.exit_btn.clicked.connect(self.exit_to_main_menu)

    def open_material_master(self):
        self.hide()
        self.mm = MaterialMaster(parent=self)
        self.mm.show()

    def open_supplier_master(self):
        self.hide()
        self.sm = SupplierMaster(parent=self)
        self.sm.show()

    def open_shift_master(self):
        self.hide()
        self.shm = ShiftMaster(parent=self)
        self.shm.show()

    def open_vehicle_master(self):
        self.hide()
        self.vm = VehicleMaster(parent=self)
        self.vm.show()

    def open_comm_port_settings(self):
        self.hide()
        self.cp = CommPortSettings(parent=self)
        self.cp.show()

    def open_report_designer(self):
        self.hide()
        self.rd = ReportDesigner(parent=self)
        self.rd.show()

    def open_delete_entities(self):
        self.hide()
        self.de = DeleteEntities(parent=self)
        self.de.show()

    def open_duplicate_ticket(self):
        self.hide()
        self.dt = DuplicateTicket(parent=self)
        self.dt.show()

    def exit_to_main_menu(self):
        self.close()
        parent = self.parent()
        if parent:
            parent.show()

# Optional: for standalone testing
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = ConfigurationWindow()
    win.show()
    sys.exit(app.exec_())
