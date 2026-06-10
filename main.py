import sys
import os
from PySide6.QtWidgets import QApplication, QWizard
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from pages.page0_download import DownloadModelPage
from pages.page1_pdf import PdfToTextPage
from pages.page2_jsonl import GenerateJsonlPage
from pages.page3_finetune import FineTunePage
from pages.page4_merge import MergePage
from pages.page5_test import TestInferencePage
from pages.page6_rag import RagPage
from pages.page7_agentic import AgenticSqlPage
from core.config_manager import ConfigManager


class LlamaTrainingWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🦙 Llama Fine-Tuning Wizard")
        self.setMinimumSize(900, 680)
        self.setWizardStyle(QWizard.ModernStyle)

        self.config = ConfigManager()

        self.addPage(DownloadModelPage(self.config))
        self.addPage(PdfToTextPage(self.config))
        self.addPage(GenerateJsonlPage(self.config))
        self.addPage(FineTunePage(self.config))
        self.addPage(MergePage(self.config))
        self.addPage(TestInferencePage(self.config))
        self.addPage(RagPage(self.config))
        self.addPage(AgenticSqlPage(self.config))

        self.setButtonText(QWizard.NextButton, "Next ▶")
        self.setButtonText(QWizard.BackButton, "◀ Back")
        self.setButtonText(QWizard.FinishButton, "Finish ✅")
        self.setButtonText(QWizard.CancelButton, "Cancel")

    def accept(self):
        self.config.save()
        super().accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    wizard = LlamaTrainingWizard()
    wizard.show()
    sys.exit(app.exec())
