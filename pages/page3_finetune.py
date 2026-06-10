from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QLabel, QSpinBox, QProgressBar
from PySide6.QtCore import Qt, QThread

from core.workers import FineTuneWorker


class FineTunePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 2: LoRA Fine-Tuning")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.jsonl_edit = QLineEdit(self.config.get("jsonl_path"))
        self.base_dir_edit = QLineEdit(self.config.get("base_model_dir"))
        self.out_dir_edit = QLineEdit("tinyllama-finetuned")

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 100)
        self.epochs_spin.setValue(int(self.config.get("epochs", 10)))

        self.maxlen_spin = QSpinBox()
        self.maxlen_spin.setRange(64, 4096)
        self.maxlen_spin.setValue(int(self.config.get("max_length", 256)))

        form.addRow("Training JSONL:", self.jsonl_edit)
        form.addRow("Base model dir (optional):", self.base_dir_edit)
        form.addRow("Output dir:", self.out_dir_edit)
        form.addRow("Epochs:", self.epochs_spin)
        form.addRow("Max length:", self.maxlen_spin)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.epochs_spin.value())

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Start fine-tuning")
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
        self.current_epoch = 0

    def start_job(self):
        jsonl_path = self.jsonl_edit.text().strip()
        out_dir = self.out_dir_edit.text().strip() or "tinyllama-finetuned"
        base_dir = self.base_dir_edit.text().strip() or self.config.get("base_model_dir")
        epochs = self.epochs_spin.value()
        maxlen = self.maxlen_spin.value()

        if not jsonl_path:
            return

        self.config.set("jsonl_path", jsonl_path)
        if base_dir:
            self.config.set("base_model_dir", base_dir)
        self.config.set("epochs", epochs)
        self.config.set("max_length", maxlen)

        self.run_btn.setEnabled(False)
        self.log_view.clear()
        self.progress_bar.setRange(0, epochs)
        self.progress_bar.setValue(0)
        self.current_epoch = 0

        self.thread = QThread()
        self.worker = FineTuneWorker(jsonl_path, out_dir, base_dir, epochs, maxlen)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def on_progress(self, text: str):
        self.log_view.append(text)
        # crude epoch detection: look for "epoch" keyword
        if "epoch" in text.lower():
            self.current_epoch += 1
            self.progress_bar.setValue(self.current_epoch)

    def on_finished(self, ok: bool, msg: str):
        self.run_btn.setEnabled(True)
        if ok:
            self.progress_bar.setValue(self.progress_bar.maximum())
        self.log_view.append(msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def validatePage(self) -> bool:
        return True
