from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QThread

from core.workers import MergeWorker


class MergePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 3: Merge LoRA into Base Model")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.base_dir_edit = QLineEdit(self.config.get("base_model_dir"))
        self.lora_dir_edit = QLineEdit("tinyllama-finetuned")
        self.out_dir_edit = QLineEdit(self.config.get("merged_model_dir"))

        form.addRow("Base model dir:", self.base_dir_edit)
        form.addRow("LoRA dir:", self.lora_dir_edit)
        form.addRow("Output merged dir:", self.out_dir_edit)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Merge")
        self.run_btn.clicked.connect(self.start_job)

        layout.addLayout(form)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_view)
        layout.addWidget(self.run_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def start_job(self):
        base_dir = self.base_dir_edit.text().strip()
        lora_dir = self.lora_dir_edit.text().strip()
        out_dir = self.out_dir_edit.text().strip() or "tinyllama-merged"
        if not base_dir or not lora_dir:
            return

        self.config.set("base_model_dir", base_dir)
        self.config.set("merged_model_dir", out_dir)

        self.run_btn.setEnabled(False)
        self.log_view.clear()

        self.thread = QThread()
        self.worker = MergeWorker(base_dir, lora_dir, out_dir)
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
        return bool(self.out_dir_edit.text().strip())
