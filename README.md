# 🦙 AI Llama Training GUI

A full **PySide6 GUI Wizard** wrapping the [AI.Llama.Traing.Offline](https://github.com/tatsoft/AI.Llama.Traing.Offline) pipeline.

Provides a step-by-step wizard UI for:
- Downloading the base TinyLlama model
- Converting PDF → TXT
- Generating JSONL training data (via llama.cpp offline)
- LoRA fine-tuning with live log streaming
- Merging LoRA adapter into base model
- Inference / sanity check
- RAG with FAISS
- Agentic SQL (natural language → MSSQL)

## Install

```bash
pip install -r requirements.txt
```

> On **Linux + NVIDIA GPU**: uncomment `bitsandbytes` in `requirements.txt`  
> On **Windows / AMD / CPU-only**: leave it commented

## Run

```bash
python main.py
```

## Structure

```
AI.Llama.Training.GUI/
├── main.py                  ← Entry point, launches QWizard
├── requirements.txt
├── config.json              ← Auto-generated, saves wizard state
├── core/
│   ├── config_manager.py    ← Persistent config load/save
│   └── workers.py           ← QThread workers for all heavy tasks
└── pages/
    ├── page0_download.py    ← Step 0: Download base model
    ├── page1_pdf.py         ← Step 1.0: PDF → TXT
    ├── page2_jsonl.py       ← Step 1.1: TXT → JSONL
    ├── page3_finetune.py    ← Step 2: LoRA fine-tuning
    ├── page4_merge.py       ← Step 3: Merge LoRA
    ├── page5_test.py        ← Step 4: Inference test
    ├── page6_rag.py         ← Step 5: RAG with FAISS
    └── page7_agentic.py     ← Step 6: Agentic SQL
```
