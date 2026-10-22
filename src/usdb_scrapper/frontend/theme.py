"""Purple desktop palette with contrasting controls and status accents."""

PURPLE_THEME = """
QWidget { background: #181126; color: #eee8fa; font-size: 14px; }
QMainWindow, QDialog { background: #181126; }
QLabel { background: transparent; }
QTabWidget::pane { border: 1px solid #44305e; border-radius: 10px; }
QTabBar::tab { background: #241a35; color: #bdafcf; padding: 13px 28px; margin-right: 4px; }
QTabBar::tab:selected { background: #6d3fc0; color: white; }
QTabBar::tab:hover { background: #493061; }
QLineEdit, QComboBox, QSpinBox {
    background: #261b38; border: 1px solid #59416f; border-radius: 6px;
    padding: 9px; selection-background-color: #8959d7; color: #f7f2ff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #ba93ff; }
QPushButton {
    background: #493064; color: #f7f2ff; border: 1px solid #76549a;
    border-radius: 6px; padding: 10px 18px; font-weight: 600;
}
QPushButton:hover { background: #66418b; border-color: #ba93ff; }
QPushButton:pressed { background: #382348; }
QPushButton:disabled { background: #2b2237; color: #877994; border-color: #44364f; }
QPushButton#primary { background: #8351d4; border-color: #a579ef; color: white; }
QPushButton#primary:hover { background: #9868e4; }
QPushButton#start { background: #286b65; border-color: #54c9ba; color: #f0fffc; }
QPushButton#start:hover { background: #34877e; }
QTableWidget {
    background: #1e162c; alternate-background-color: #291d3b;
    border: 1px solid #44305e; border-radius: 8px; gridline-color: #382848;
    selection-background-color: #593883; selection-color: white;
}
QTableWidget::item { padding: 8px; border-bottom: 1px solid #382848; }
QHeaderView::section { background: #332146; color: #d9c2fc; border: none; padding: 12px;
    font-weight: 600; }
QScrollBar:vertical { background: #241a35; width: 12px; }
QScrollBar::handle:vertical { background: #76549a; min-height: 24px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QStatusBar { background: #281b39; color: #cbb9e3; padding: 6px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #a579ef; background: #261b38;
    border-radius: 4px; }
QCheckBox::indicator:checked { background: #a579ef; border: 3px solid #d8c2ff; }
QToolTip { background: #44305e; color: white; border: 1px solid #ba93ff; }
"""
