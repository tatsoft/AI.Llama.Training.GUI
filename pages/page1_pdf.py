# pages/page1_pdf.py

from PySide6.QtWidgets import (
    QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QTextEdit, QFileDialog, QLabel,
    QHBoxLayout, QProgressBar
)
from PySide6.QtCore import Qt, QThread

from core.workers import PdfToTextWorker


class PdfToTextPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 1: Data Input (PDF or TXT)")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        # Single input file: can be .pdf or .txt
        self.input_edit = QLineEdit(self.config.get("pdf_path"))
        input_btn = QPushButton("Browse…")
        input_btn.clicked.connect(self.browse_input)
        input_row = QHBoxLayout()
        input_row.addWidget(self.input_edit)
        input_row.addWidget(input_btn)

        # Normalized TXT path (where the JSONL step will read from)
        self.txt_edit = QLineEdit(self.config.get("txt_path"))
        txt_btn = QPushButton("Browse…")
        txt_btn.clicked.connect(self.browse_txt)
        txt_row = QHBoxLayout()
        txt_row.addWidget(self.txt_edit)
        txt_row.addWidget(txt_btn)

        form.addRow("Input file (.pdf or .txt):", input_row)
        form.addRow("Normalized TXT output:", txt_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate while extracting

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Prepare TXT")
        self.run_btn.clicked.connect(self.start_job)

        layout.addLayout(form)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_view)
        layout.addWidget(self.run_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select input file",
            filter="Documents (*.pdf *.txt);;All Files (*.*)",
        )
        if path:
            self.input_edit.setText(path)
            # If it's a .txt, default normalized TXT to same path
            if path.lower().endswith(".txt") and not self.txt_edit.text().strip():
                self.txt_edit.setText(path)

    def browse_txt(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select TXT output",
            filter="Text Files (*.txt)",
        )
        if path:
            self.txt_edit.setText(path)

    def start_job(self):
        input_path = self.input_edit.text().strip()
        txt_path = self.txt_edit.text().strip()

        if not input_path:
            return

        # If input is already TXT, just normalize paths and skip extraction
        if input_path.lower().endswith(".txt"):
            # If no explicit txt_path, use the input as normalized TXT
            if not txt_path:
                txt_path = input_path
                self.txt_edit.setText(txt_path)

            self.config.set("pdf_path", input_path)  # keeps last chosen path
            self.config.set("txt_path", txt_path)
            self.log_view.append("Input is TXT; no PDF extraction needed.")
            # No worker / thread needed; we just normalize and return
            return

        # Input is PDF → run PdfToTextWorker
        if not txt_path:
            # Default TXT name next to PDF
            if input_path.lower().endswith(".pdf"):
                txt_path = input_path[:-4] + ".txt"
                self.txt_edit.setText(txt_path)

        self.config.set("pdf_path", input_path)
        self.config.set("txt_path", txt_path)

        self.run_btn.setEnabled(False)
        self.log_view.clear()
        self.progress_bar.setRange(0, 0)  # busy

        self.thread = QThread()
        self.worker = PdfToTextWorker(input_path, txt_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def append_log(self, text: str):
        self.log_view.append(text)

    def on_finished(self, ok: bool, msg: str):
        self.run_btn.setEnabled(True)
        # mark progress as done
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.append_log(msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def validatePage(self) -> bool:
        # Wizard can go next if we have a TXT path (normalized input for JSONL step)
        return bool(self.txt_edit.text().strip())