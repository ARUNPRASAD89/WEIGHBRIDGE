from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QTextBrowser, QTabWidget, QPushButton, QSplitter, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class HelpWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HTML Help")
        self.setFixedSize(540, 440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        # Simulated menu bar (static, non-functional)
        menubar = QHBoxLayout()
        font = QFont("Arial", 9, QFont.Bold)
        menubar.addWidget(QPushButton("File"))
        menubar.addWidget(QPushButton("Edit"))
        menubar.addWidget(QPushButton("View"))
        menubar.addWidget(QPushButton("Go"))
        menubar.addWidget(QPushButton("Help"))
        menubar.addStretch(1)
        main_layout.addLayout(menubar)

        # Toolbar (static, non-functional)
        toolbar = QHBoxLayout()
        for label in ["Hide", "Back", "Forward", "Print", "Options"]:
            btn = QPushButton(label)
            btn.setFont(QFont("Arial", 8))
            btn.setFixedSize(54, 22)
            toolbar.addWidget(btn)
        toolbar.addStretch(1)
        main_layout.addLayout(toolbar)

        # Tabs: Contents, Index, Search, Favorites (simulate tabs)
        tab_widget = QTabWidget()
        tab_widget.setFont(QFont("Arial", 9))
        tab_widget.setFixedHeight(32)
        tab_widget.setTabPosition(QTabWidget.North)
        # Add empty tabs for look only
        for tab in ["Contents", "Index", "Search", "Favorites"]:
            tab_widget.addTab(QWidget(), tab)
        main_layout.addWidget(tab_widget)

        # Splitter for navigation and content
        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizes([180, 360])

        # Help Topics Tree
        help_tree = QTreeWidget()
        help_tree.setHeaderHidden(True)
        help_tree.setFont(QFont("Arial", 9))
        root = QTreeWidgetItem(help_tree, ["Login to Weighsoft"])
        QTreeWidgetItem(root, ["Weighsoft Enterprise"])
        QTreeWidgetItem(root, ["Transactions"])
        QTreeWidgetItem(root, ["Reports"])
        QTreeWidgetItem(root, ["Administration"])
        QTreeWidgetItem(root, ["Configuration"])
        QTreeWidgetItem(root, ["About Essae Digtronics"])
        help_tree.expandAll()
        splitter.addWidget(help_tree)

        # Help Content Area
        help_content = QTextBrowser()
        help_content.setFont(QFont("Arial", 10))
        help_content.setPlainText(
            "When you launch the\nWeighSoft Enterprise"
        )
        splitter.addWidget(help_content)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)