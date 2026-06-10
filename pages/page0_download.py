from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QThread

from core.workers import DownloadModelWorker


class DownloadModelPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 0: Download Base Model")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.model_id_edit = QLineEdit(self.config.get("model_id"))
        self.base_dir_edit = QLineEdit(self.config.get("base_model_dir"))
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self.browse_dir)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self.base_dir_edit)
        dir_row.addWidget(browse_btn)

        form.addRow("HuggingFace model ID:", self.model_id_edit)
        form.addRow("Base model directory:", dir_row)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.start_download)

        layout.addLayout(form)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_view)
        layout.addWidget(self.download_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select base model directory")
        if path:
            self.base_dir_edit.setText(path)

    def start_download(self):
        model_id = self.model_id_edit.text().strip()
        base_dir = self.base_dir_edit.text().strip()
        if not model_id or not base_dir:
            return

        self.config.set("model_id", model_id)
        self.config.set("base_model_dir", base_dir)

        self.download_btn.setEnabled(False)
        self.log_view.clear()

        self.thread = QThread()
        self.worker = DownloadModelWorker(model_id, base_dir)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def append_log(self, text: str):
        self.log_view.append(text)

    def on_finished(self, ok: bool, msg: str):
        self.download_btn.setEnabled(True)
        self.append_log(msg)
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def validatePage(self) -> bool:
        # allow next if base dir exists
        base_dir = self.base_dir_edit.text().strip()
        return bool(base_dir)
