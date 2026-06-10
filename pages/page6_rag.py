from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTextEdit, QLabel
from PySide6.QtCore import Qt, QThread

from core.workers import RagWorker


class RagPage(QWizardPage):
    def __init__(self, config):
        super().__init__()
        self.setTitle("Step 5: RAG with FAISS + MSSQL")
        self.config = config

        layout = QVBoxLayout()
        form = QFormLayout()

        self.conn_edit = QLineEdit(self.config.get("rag_db_conn"))
        self.model_edit = QLineEdit(self.config.get("merged_model_dir"))
        self.question_edit = QLineEdit("What are company hours?")

        form.addRow("MSSQL connection string:", self.conn_edit)
        form.addRow("GGUF model path:", self.model_edit)
        form.addRow("Question:", self.question_edit)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.run_btn = QPushButton("Run RAG query")
        self.run_btn.clicked.connect(self.start_job)

        layout.addLayout(form)
        layout.addWidget(QLabel("Answer:"))
        layout.addWidget(self.log_view)
        layout.addWidget(self.run_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def start_job(self):
        conn_str = self.conn_edit.text().strip()
        model_path = self.model_edit.text().strip()
        question = self.question_edit.text().strip()
        if not conn_str or not model_path or not question:
            return

        self.config.set("rag_db_conn", conn_str)

        self.run_btn.setEnabled(False)
        self.log_view.clear()

        self.thread = QThread()
        self.worker = RagWorker(conn_str, model_path, question)
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
