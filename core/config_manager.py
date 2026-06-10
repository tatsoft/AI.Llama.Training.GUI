import json
import os
from pathlib import Path


class ConfigManager:
    def __init__(self, path: str = "config.json"):
        self.path = Path(path)
        self.data = {
            "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "base_model_dir": "tinyllama-base",
            "merged_model_dir": "tinyllama-merged",
            "pdf_path": "TheStandard.pdf",
            "txt_path": "TheStandard.txt",
            "jsonl_path": "data.jsonl",
            "hf_use_local": True,
            "llama_cpp_binary": "llama.cpp/build/bin/llama-cli",
            "llama_cpp_model": "llama.cpp/mistral/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
            "epochs": 10,
            "batch_size": 1,
            "max_length": 256,
            "rag_db_conn": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=BIGB;DATABASE=LlamaDB;Trusted_Connection=yes;",
            "agentic_db_conn": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=BIGB;DATABASE=SchoolDb;Trusted_Connection=yes;",
            "agentic_model_path": "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        }
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
