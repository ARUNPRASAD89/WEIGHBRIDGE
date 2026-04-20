from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QScrollArea
)
from PyQt5.QtCore import Qt

class HelpWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Guide")
        self.setMinimumSize(700, 650)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("Weighbridge Application User Guide")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title)

        # Scrollable help text area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        help_content = QTextEdit()
        help_content.setReadOnly(True)
        
        user_guide_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Weighbridge Kiosk User Guide</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; background-color: #f8f9fa; }
        h2, h3, h4 { color: #2c3e50; border-bottom: 1px solid #dee2e6; padding-bottom: 5px; }
        h2 { font-size: 16pt; }
        h3 { font-size: 14pt; }
        h4 { font-size: 12pt; border-bottom: none; }
        strong { color: #0056b3; }
        .section { margin-bottom: 25px; }
        ul, ol { padding-left: 20px; }
        code { background-color: #e9ecef; padding: 2px 5px; border-radius: 4px; }
    </style>
</head>
<body>

    <div class="section">
        <h2>1. The Weighing Process</h2>
        <p>The application is designed for a seamless weighment workflow, featuring automation to increase efficiency.</p>
        <h4>Transaction Types:</h4>
        <ol>
            <li><strong>Two-Stage Weighment:</strong> For vehicles where the net weight must be calculated.
                <ul>
                    <li><strong>First Weighment (Gross/Tare):</strong> Captures the first weight. The system can use <strong>Automatic Number Plate Recognition (ANPR)</strong> via camera to identify the vehicle, or you can select it manually.</li>
                    <li><strong>Second Weighment (Tare/Gross):</strong> When the vehicle returns, select its pending ticket. The system captures the second weight and automatically calculates the <strong>Net Weight</strong>.</li>
                </ul>
            </li>
            <li><strong>Single Stage Weighment:</strong> For one-off weighments or when a vehicle's empty (tare) weight is preregistered in the <strong>Vehicle Master</strong>. The net weight is calculated in one step.</li>
        </ol>
    </div>

    <div class="section">
        <h2>2. Modules in Detail</h2>
        
        <h3>Configuration Module</h3>
        <p>This is where you set up the foundational data for the application.</p>
        <ul>
            <li><strong>Masters (Vehicle, Supplier, Material, Shift):</strong> This is the master database for your operations. It is crucial to keep this data accurate. For example, in the <strong>Vehicle Master</strong>, you can pre-define the <code>Tare Weight</code> for vehicles to enable Single Stage Weighment.</li>
            <li><strong>Hardware Settings (Camera, Comm Port):</strong> Configure the connection to your physical hardware. The <strong>Comm Port</strong> settings are for the weigh indicator (scale), and the <strong>Camera Port</strong> is for the ANPR and security snapshot cameras.</li>
        </ul>

        <h3>Administration Module</h3>
        <p>This module provides powerful tools to customize the application to your exact needs.</p>
        <ul>
            <li><strong>Template Designers (Ticket, Report, WhatsApp):</strong> These visual designers allow you to customize the output. You can add your company logo, drag-and-drop data fields (like Net Weight, Vehicle No., etc.), and arrange the layout for professional-looking printed tickets and reports.</li>
            <li><strong>Rate Management (Rate Chart & Formula Editor):</strong> The system offers two ways to manage pricing:
                <ul>
                    <li><strong>Rate Chart Manager:</strong> For simple, fixed-rate pricing based on material or other straightforward criteria.</li>
                    <li><strong>Formula Editor:</strong> For complex, dynamic pricing scenarios. You can create custom mathematical formulas using variables from the transaction (e.g., <code>[NET_WEIGHT] * [BASE_RATE] + [SURCHARGE]</code>) to automate billing calculations.</li>
                </ul>
            </li>
            <li><strong>User Management:</strong> Create user accounts and assign roles (e.g., 'Operator', 'Administrator'). This controls access to sensitive areas like Administration and Configuration.</li>
            <li><strong>Data Management (Backup/Restore, Document Importer):</strong>
                <ul>
                    <li><strong>Backup:</strong> Regularly back up your database to prevent data loss.</li>
                    <li><strong>Document Importer:</strong> Perform bulk data uploads from spreadsheets (e.g., Excel/CSV) to quickly populate your Masters lists without manual entry.</li>
                </ul>
            </li>
        </ul>
    </div>

    <div class="section">
        <h2>3. Troubleshooting</h2>
        <h3>Problem: The weight is not showing up from the scale.</h3>
        <p><strong>Solution:</strong> Navigate to <strong>Configuration -> Communication Port Settings</strong>. Verify that the correct COM port is selected and that the baud rate, parity, and other settings match the specifications of your weigh indicator. Ensure the scale is on and the cable is securely connected.</p>

        <h3>Problem: The camera feed is not visible or ANPR is failing.</h3>
        <p><strong>Solution:</strong> Go to <strong>Configuration -> Camera Port Settings</strong>. Ensure the correct camera is selected. For ANPR issues, check that the license plate is well-lit, in clear view of the camera, and not obscured by dirt.</p>
        
        <h3>Problem: A calculation on the ticket seems incorrect.</h3>
        <p><strong>Solution:</strong> Check the pricing logic in <strong>Administration -> Formula Editor</strong> or <strong>Rate Chart Manager</strong>. A formula may be constructed incorrectly or a rate may be outdated. Also, verify the raw data (Gross/Tare weights) for the transaction.</p>
    </div>
    <hr>
    <p><em>For further assistance, please contact the system administrator.</em></p>

</body>
</html>
"""
        help_content.setHtml(user_guide_html)
        
        scroll.setWidget(help_content)
        main_layout.addWidget(scroll)

        # Bottom button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.exit_btn = QPushButton("Close")
        self.exit_btn.setStyleSheet("font-size: 10pt; padding: 5px 15px;")
        btn_row.addWidget(self.exit_btn)
        main_layout.addLayout(btn_row)

        self.exit_btn.clicked.connect(self.accept)
