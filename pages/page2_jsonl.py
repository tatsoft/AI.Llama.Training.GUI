from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QThread

from core.workers import JsonlWorker


class GenerateJsonlPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 1.1: TXT → JSONL (offline)")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.txt_edit = QLineEdit(self.config.get("txt_path"))
        txt_btn = QPushButton("Browse…")
        txt_btn.clicked.connect(self.browse_txt)
        txt_row = QHBoxLayout()
        txt_row.addWidget(self.txt_edit)
        txt_row.addWidget(txt_btn)

        self.jsonl_edit = QLineEdit(self.config.get("jsonl_path"))
        jsonl_btn = QPushButton("Browse…")
        jsonl_btn.clicked.connect(self.browse_jsonl)
        jsonl_row = QHBoxLayout()
        jsonl_row.addWidget(self.jsonl_edit)
        jsonl_row.addWidget(jsonl_btn)

        self.cli_edit = QLineEdit(self.config.get("llama_cpp_binary"))
        self.model_edit = QLineEdit(self.config.get("llama_cpp_model"))

        form.addRow("Input TXT:", txt_row)
        form.addRow("Output JSONL:", jsonl_row)
        form.addRow("llama.cpp binary:", self.cli_edit)
        form.addRow("llama.cpp model:", self.model_edit)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Generate")
        self.run_btn.clicked.connect(self.start_job)

        layout.addLayout(form)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_view)
        layout.addWidget(self.run_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def browse_txt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select TXT", filter="Text Files (*.txt)")
        if path:
            self.txt_edit.setText(path)

    def browse_jsonl(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select JSONL", filter="JSONL Files (*.jsonl)")
        if path:
            self.jsonl_edit.setText(path)

    def start_job(self):
        txt_path = self.txt_edit.text().strip()
        jsonl_path = self.jsonl_edit.text().strip()
        cli = self.cli_edit.text().strip()
        model = self.model_edit.text().strip()
        if not txt_path or not jsonl_path or not cli or not model:
            return

        self.config.set("txt_path", txt_path)
        self.config.set("jsonl_path", jsonl_path)
        self.config.set("llama_cpp_binary", cli)
        self.config.set("llama_cpp_model", model)

        self.run_btn.setEnabled(False)
        self.log_view.clear()

        self.thread = QThread()
        self.worker = JsonlWorker(txt_path, jsonl_path, cli, model)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def append_log(self, text: str):
        self.log_view.append(text)

    def on_finished(self, ok: bool, msg: str):
        self.run_btn.setEnabled(True)
        self.append_log(msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def validatePage(self) -> bool:
        return bool(self.jsonl_edit.text().strip())
