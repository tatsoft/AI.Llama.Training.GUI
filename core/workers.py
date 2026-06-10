from PySide6.QtCore import QObject, Signal, QThread
import subprocess
import os
import sys
import traceback


class BaseWorker(QObject):
    progress = Signal(str)
    finished = Signal(bool, str)

    def log(self, msg: str):
        self.progress.emit(msg)

    def done(self, ok: bool, msg: str = ""):
        self.finished.emit(ok, msg)


class DownloadModelWorker(BaseWorker):
    def __init__(self, model_id: str, output_dir: str):
        super().__init__()
        self.model_id = model_id
        self.output_dir = output_dir

    def run(self):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.log(f"Downloading {self.model_id}...")
            model = AutoModelForCausalLM.from_pretrained(self.model_id)
            tokenizer = AutoTokenizer.from_pretrained(self.model_id)

            os.makedirs(self.output_dir, exist_ok=True)
            model.save_pretrained(self.output_dir)
            tokenizer.save_pretrained(self.output_dir)
            self.log(f"Saved to {self.output_dir}")
            self.done(True, "Download complete")
        except Exception as e:
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class PdfToTextWorker(BaseWorker):
    def __init__(self, pdf_path: str, txt_path: str):
        super().__init__()
        self.pdf_path = pdf_path
        self.txt_path = txt_path

    def run(self):
        try:
            import fitz
            import re
            import os

            if not os.path.exists(self.pdf_path):
                self.done(False, f"PDF not found: {self.pdf_path}")
                return

            doc = fitz.open(self.pdf_path)
            self.log(f"Reading '{self.pdf_path}' with {len(doc)} pages...")

            full_text = ""
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                full_text += text + "\n\n"
                self.log(f"Page {page_num} extracted")

            text = full_text
            text = re.sub(r'-\n', '', text)
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
            text = re.sub(r'\n{2,}', '\n\n', text)

            with open(self.txt_path, "w", encoding="utf-8") as out:
                out.write(text.strip())

            self.done(True, f"Saved to {self.txt_path}")
        except Exception as e:
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class JsonlWorker(BaseWorker):
    def __init__(self, txt_file: str, jsonl_file: str, llama_cli: str, llama_model: str):
        super().__init__()
        self.txt_file = txt_file
        self.jsonl_file = jsonl_file
        self.llama_cli = llama_cli
        self.llama_model = llama_model

    def run(self):
        try:
            import os
            import json
            import re
            import nltk
            from nltk.tokenize import sent_tokenize
            import subprocess

            nltk.download('punkt', quiet=True)

            if not os.path.exists(self.txt_file):
                self.done(False, f"TXT not found: {self.txt_file}")
                return

            with open(self.txt_file, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            def clean_text(text):
                text = re.sub(r'-\n', '', text)
                text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
                text = re.sub(r'\n{2,}', '\n\n', text)
                return text.strip()

            def split_into_paragraphs(text, min_words=30, max_words=100):
                paragraphs = []
                for block in text.split('\n\n'):
                    block = block.strip()
                    if not block:
                        continue
                    sentences = sent_tokenize(block)
                    chunk = ""
                    word_count = 0
                    for sentence in sentences:
                        words = sentence.split()
                        word_count += len(words)
                        chunk += " " + sentence
                        if min_words <= word_count <= max_words:
                            paragraphs.append(chunk.strip())
                            chunk = ""
                            word_count = 0
                    if chunk:
                        paragraphs.append(chunk.strip())
                return paragraphs

            def call_llama_cli(prompt: str) -> str:
                cmd = [self.llama_cli, "--model", self.llama_model, "--prompt", prompt, "--n-predict", "256"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                out_lines = []
                for line in proc.stdout:
                    out_lines.append(line)
                proc.wait()
                return ''.join(out_lines).strip()

            paragraphs = split_into_paragraphs(clean_text(raw_text))
            self.log(f"Found {len(paragraphs)} paragraphs")

            written_count = 0
            with open(self.jsonl_file, 'w', encoding='utf-8') as out:
                for i, paragraph in enumerate(paragraphs):
                    prompt = (
                        "You are helping train an AI chatbot based on a book called *The Standard* by Hassan Habib.\n\n"
                        "Given the paragraph below, write up to 3 different natural-language questions that could be answered by it.\n"
                        "Write each question on a new line. Do not include explanations or extra commentary.\n\n"
                        f"Paragraph:\n{paragraph}\n"
                    )
                    raw_text = call_llama_cli(prompt)
                    questions = []
                    for q in raw_text.split("\n"):
                        q = q.strip()
                        if q.endswith("?") and len(q.split()) >= 3 and not q.lower().startswith(("of", "and", "the")):
                            q = re.sub(r'^\d+(\.\d+)*[\).]?\s*', '', q)
                            questions.append(q)
                    questions = list(set(questions))
                    if not questions:
                        continue
                    for question in questions:
                        entry = {
                            "instruction": question,
                            "input": "",
                            "output": paragraph.strip(),
                        }
                        out.write(json.dumps(entry, ensure_ascii=False) + '\n')
                        written_count += 1
                    self.log(f"Paragraph {i+1}: {len(questions)} questions")

            self.done(True, f"Wrote {written_count} Q&A pairs to {self.jsonl_file}")
        except Exception as e:
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class FineTuneWorker(BaseWorker):
    def __init__(self, jsonl_file: str, output_dir: str, model_dir: str, epochs: int, max_length: int):
        super().__init__()
        self.jsonl_file = jsonl_file
        self.output_dir = output_dir
        self.model_dir = model_dir
        self.epochs = epochs
        self.max_length = max_length

    def run(self):
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
            from datasets import load_dataset
            from peft import LoraConfig, get_peft_model, TaskType

            if not os.path.exists(self.jsonl_file):
                self.done(False, f"JSONL not found: {self.jsonl_file}")
                return

            if os.path.exists(self.model_dir):
                model_name = self.model_dir
            else:
                model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

            self.log(f"Loading tokenizer/model from {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)

            lora_config = LoraConfig(
                r=8,
                lora_alpha=16,
                lora_dropout=0.1,
                bias="none",
                task_type=TaskType.CAUSAL_LM,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            )
            model = get_peft_model(model, lora_config)

            dataset = load_dataset("json", data_files=self.jsonl_file)["train"]

            def format_prompt(example):
                return {
                    "text": f"### Instruction:\n{example['instruction']}\n\n### Input:\n{example['input']}\n\n### Response:\n{example['output']}"
                }

            dataset = dataset.map(format_prompt)

            def tokenize(example):
                tokens = tokenizer(example["text"], truncation=True, padding="max_length", max_length=self.max_length)
                tokens["labels"] = tokens["input_ids"].copy()
                return tokens

            tokenized_dataset = dataset.map(tokenize, remove_columns=dataset.column_names)

            training_args = TrainingArguments(
                output_dir=self.output_dir,
                per_device_train_batch_size=1,
                num_train_epochs=self.epochs,
                save_strategy="epoch",
                logging_steps=5,
                fp16=torch.cuda.is_available(),
                report_to="none",
                remove_unused_columns=False,
            )

            data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

            def callback_log(step, logs):
                self.log(f"step {step}: {logs}")

            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
            )

            trainer.train()
            trainer.model.save_pretrained(self.output_dir)
            tokenizer.save_pretrained(self.output_dir)
            self.done(True, f"Fine-tuned model saved to {self.output_dir}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class MergeWorker(BaseWorker):
    def __init__(self, base_model_dir: str, lora_dir: str, output_dir: str):
        super().__init__()
        self.base_model_dir = base_model_dir
        self.lora_dir = lora_dir
        self.output_dir = output_dir

    def run(self):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel

            base_model = AutoModelForCausalLM.from_pretrained(self.base_model_dir)
            model = PeftModel.from_pretrained(base_model, self.lora_dir)

            model = model.merge_and_unload()

            os.makedirs(self.output_dir, exist_ok=True)
            model.save_pretrained(self.output_dir)
            AutoTokenizer.from_pretrained(self.lora_dir).save_pretrained(self.output_dir)
            self.done(True, f"Merged model saved to {self.output_dir}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class TestInferenceWorker(BaseWorker):
    def __init__(self, model_dir: str, prompt: str):
        super().__init__()
        self.model_dir = model_dir
        self.prompt = prompt

    def run(self):
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM

            tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            model = AutoModelForCausalLM.from_pretrained(self.model_dir, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = model.to(device)

            inputs = tokenizer(self.prompt, return_tensors="pt").to(device)
            model.eval()
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=80)
            text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            self.log(text)
            self.done(True, "Inference complete")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class RagWorker(BaseWorker):
    def __init__(self, conn_str: str, llm_model_path: str, question: str):
        super().__init__()
        self.conn_str = conn_str
        self.llm_model_path = llm_model_path
        self.question = question

    def run(self):
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            import numpy as np
            from llama_cpp import Llama
            import pyodbc

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM knowledge")
            documents = [row[0] for row in cursor.fetchall() if row[0] is not None]
            if not documents:
                self.done(False, "No documents in knowledge table")
                return

            doc_embeddings = embedder.encode(documents, convert_to_numpy=True)
            dimension = doc_embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(doc_embeddings)
            id_to_doc = {i: doc for i, doc in enumerate(documents)}

            query_vec = embedder.encode([self.question], convert_to_numpy=True)
            distances, indices = index.search(query_vec, 3)
            retrieved_docs = [id_to_doc[idx] for idx in indices[0]]

            context = "\n\n".join(retrieved_docs)
            prompt = f"Context:\n{context}\n\nQuestion: {self.question}\nAnswer:"

            llm = Llama(model_path=self.llm_model_path, n_ctx=2048, n_threads=4)
            response = llm(prompt, max_tokens=200)
            answer = response['choices'][0]['text'].strip()
            self.log(answer)
            conn.close()
            self.done(True, "RAG query complete")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))


class AgenticWorker(BaseWorker):
    def __init__(self, conn_str: str, model_path: str, user_question: str):
        super().__init__()
        self.conn_str = conn_str
        self.model_path = model_path
        self.user_question = user_question

    def run(self):
        try:
            import pyodbc
            from llama_cpp import Llama
            import re

            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()

            def get_db_schema(cursor):
                schema = ""
                cursor.execute(
                    """
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_CATALOG = DB_NAME()
                    """
                )
                tables = [row[0] for row in cursor.fetchall()]
                for table in tables:
                    cursor.execute(
                        f"""
                        SELECT COLUMN_NAME, DATA_TYPE 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = '{table}'
                        """
                    )
                    columns = cursor.fetchall()
                    schema += f"Table: {table}\n"
                    for column_name, data_type in columns:
                        schema += f"- {column_name} ({data_type})\n"
                    schema += "\n"
                return schema.strip()

            def build_prompt(user_question, schema, error_message=None, previous_sql=None):
                if error_message:
                    return f"""
You previously generated this SQL which failed:

{previous_sql}

The error was:
{error_message}

Try again. ONLY use the tables and columns listed in this schema.

Schema:
{schema}

User question:
"{user_question}"

Respond ONLY with a valid Microsoft SQL Server SELECT query and end it with a semicolon.
"""
                else:
                    return f"""
You are a SQL expert. You will receive a database schema and a user question.

You MUST:
- Use ONLY table and column names exactly as provided in the schema
- NEVER invent or singularize table names like 'Student' if only 'Students' exists
- Output ONLY a valid Microsoft SQL Server SELECT statement ending with a semicolon

Schema:
{schema}

Question: "{user_question}"

Output:
"""

            def extract_valid_sql(text):
                match = re.search(r"(SELECT\s.+?;)", text, re.IGNORECASE | re.DOTALL)
                if not match:
                    raise ValueError("No valid SELECT statement found.")
                sql = match.group(1).strip()
                if "LIMIT" in sql.upper():
                    raise ValueError("Invalid keyword 'LIMIT' for T-SQL.")
                return sql

            llm = Llama(model_path=self.model_path)
            schema = get_db_schema(cursor)

            MAX_RETRIES = 2
            attempt = 0
            error_message = None
            sql_query = None
            data = None

            while attempt < MAX_RETRIES:
                prompt = build_prompt(self.user_question, schema, error_message, sql_query)
                response = llm(prompt=prompt, max_tokens=200)
                raw_response = response['choices'][0]['text'].strip()
                self.log(f"Attempt {attempt + 1} response:\n{raw_response}")

                try:
                    sql_query = extract_valid_sql(raw_response)
                    cursor.execute(sql_query)
                    results = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    data = [dict(zip(columns, row)) for row in results]
                    if not data:
                        raise ValueError("Query ran but returned no results.")
                    break
                except Exception as e:
                    error_message = str(e)
                    attempt += 1

            if data:
                summary_prompt = (
                    f"Here are the results of the query:\n{data}\nSummarize this nicely for the user."
                )
                summary = llm(prompt=summary_prompt, max_tokens=200)['choices'][0]['text'].strip()
                self.log(summary)
                self.done(True, "Agentic SQL complete")
            else:
                self.done(False, "Failed after retries; no data")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log(tb)
            self.done(False, str(e))
