from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QLabel, QHBoxLayout, QProgressBar
from PySide6.QtCore import Qt, QThread

from core.workers import PdfToTextWorker


class PdfToTextPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 1.0: PDF → Text")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.pdf_edit = QLineEdit(self.config.get("pdf_path"))
        pdf_btn = QPushButton("Browse…")
        pdf_btn.clicked.connect(self.browse_pdf)
        pdf_row = QHBoxLayout()
        pdf_row.addWidget(self.pdf_edit)
        pdf_row.addWidget(pdf_btn)

        self.txt_edit = QLineEdit(self.config.get("txt_path"))
        txt_btn = QPushButton("Browse…")
        txt_btn.clicked.connect(self.browse_txt)
        txt_row = QHBoxLayout()
        txt_row.addWidget(self.txt_edit)
        txt_row.addWidget(txt_btn)

        form.addRow("Input PDF:", pdf_row)
        form.addRow("Output TXT:", txt_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate until we know page count

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Convert")
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

    def browse_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", filter="PDF Files (*.pdf)")
        if path:
            self.pdf_edit.setText(path)

    def browse_txt(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select TXT", filter="Text Files (*.txt)")
        if path:
            self.txt_edit.setText(path)

    def start_job(self):
        pdf_path = self.pdf_edit.text().strip()
        txt_path = self.txt_edit.text().strip()
        if not pdf_path or not txt_path:
            return

        self.config.set("pdf_path", pdf_path)
        self.config.set("txt_path", txt_path)

        self.run_btn.setEnabled(False)
        self.log_view.clear()
        self.progress_bar.setRange(0, 0)

        self.thread = QThread()
        self.worker = PdfToTextWorker(pdf_path, txt_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def append_log(self, text: str):
        self.log_view.append(text)

    def on_finished(self, ok: bool, msg: str):
        self.run_btn.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.append_log(msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def validatePage(self) -> bool:
        return bool(self.txt_edit.text().strip())
