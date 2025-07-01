from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QApplication
)
from material_master import MaterialMaster
from supplier_master import SupplierMaster
from shift_master import ShiftMaster
from vehicle_master import VehicleMaster
from comm_port_settings import CommPortSettings
from report_designer import ReportDesigner
from delete_entities import DeleteEntities
from duplicate_ticket import DuplicateTicket

class ConfigurationWindow(QWidget):
    def __init__(self):
        super().__init__()
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

        layout.addWidget(self.material_btn)
        layout.addWidget(self.supplier_btn)
        layout.addWidget(self.shift_btn)
        layout.addWidget(self.vehicle_btn)
        layout.addWidget(self.commport_btn)
        layout.addWidget(self.reportdesigner_btn)
        layout.addWidget(self.deleteentities_btn)
        layout.addWidget(self.duplicateticket_btn)
        layout.addStretch()

        self.material_btn.clicked.connect(self.open_material_master)
        self.supplier_btn.clicked.connect(self.open_supplier_master)
        self.shift_btn.clicked.connect(self.open_shift_master)
        self.vehicle_btn.clicked.connect(self.open_vehicle_master)
        self.commport_btn.clicked.connect(self.open_comm_port_settings)
        self.reportdesigner_btn.clicked.connect(self.open_report_designer)
        self.deleteentities_btn.clicked.connect(self.open_delete_entities)
        self.duplicateticket_btn.clicked.connect(self.open_duplicate_ticket)

    def open_material_master(self):
        self.mm = MaterialMaster()
        self.mm.show()

    def open_supplier_master(self):
        self.sm = SupplierMaster()
        self.sm.show()

    def open_shift_master(self):
        self.shm = ShiftMaster()
        self.shm.show()

    def open_vehicle_master(self):
        self.vm = VehicleMaster()
        self.vm.show()

    def open_comm_port_settings(self):
        self.cp = CommPortSettings()
        self.cp.show()

    def open_report_designer(self):
        self.rd = ReportDesigner()
        self.rd.show()

    def open_delete_entities(self):
        self.de = DeleteEntities()
        self.de.show()

    def open_duplicate_ticket(self):
        self.dt = DuplicateTicket()
        self.dt.show()

# Optional: for standalone testing
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = ConfigurationWindow()
    win.show()
    sys.exit(app.exec_())