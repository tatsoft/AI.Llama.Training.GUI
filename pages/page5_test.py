from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QLabel
from PySide6.QtCore import Qt, QThread

from core.workers import TestInferenceWorker


class TestInferencePage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 4: Test Inference")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.model_dir_edit = QLineEdit(self.config.get("merged_model_dir"))
        self.prompt_edit = QLineEdit("### Instruction:\nWho is Hassan Habib?\n\n### Input:\n\n### Response:\n")

        form.addRow("Merged model dir:", self.model_dir_edit)
        form.addRow("Prompt:", self.prompt_edit)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Run test")
        self.run_btn.clicked.connect(self.start_job)

        layout.addLayout(form)
        layout.addWidget(QLabel("Output:"))
        layout.addWidget(self.log_view)
        layout.addWidget(self.run_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def start_job(self):
        model_dir = self.model_dir_edit.text().strip()
        prompt = self.prompt_edit.text().strip()
        if not model_dir or not prompt:
            return

        self.config.set("merged_model_dir", model_dir)

        self.run_btn.setEnabled(False)
        self.log_view.clear()

        self.thread = QThread()
        self.worker = TestInferenceWorker(model_dir, prompt)
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
        return True
