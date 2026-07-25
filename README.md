# Prompt Lab · Workbench CLI

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![OpenAI SDK](https://img.shields.io/badge/OpenAI_SDK-AsyncOpenAI-412991?style=flat-square&logo=openai&logoColor=white)](https://github.com/openai/openai-python)
[![ProxyAPI](https://img.shields.io/badge/ProxyAPI-OpenAI--compatible-0EA5E9?style=flat-square)](https://proxyapi.ru/)
[![Prompts](https://img.shields.io/badge/Prompts-JSON_templates-7C3AED?style=flat-square)](#prompt-templates)
[![CLI](https://img.shields.io/badge/Mode-interactive_CLI-F59E0B?style=flat-square)](#quick-start)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](#license)

**JSON prompt templates → interactive CLI → ProxyAPI → structured answer + usage stats.**  
A small prompt-engineering workbench: pick a template, run a question (or built-in `test_input`), tune model params, get a clean response.

> Clone → set `PROXY_API_KEY` → `python prompt_chat.py` → choose a prompt → done.

---

## About

This repository is a **prompt lab**, not a heavy product. The goal is to keep prompts as versioned JSON files and run them through a repeatable CLI loop.

What you get:

1. **Three ready-made prompts** in `prompts/` (`summary`, `code_structure`, `task_planning`)
2. An **interactive CLI** that builds a system message from JSON fields (`role`, `context`, `structure`, `format`)
3. Generation via **ProxyAPI** (OpenAI-compatible Chat Completions)
4. Optional **test runner** + **DOCX report** for homework / demos

### Features

| Feature | Description |
|--------|-------------|
| **Prompt menu** | Numbered list of templates from `prompts/*.json` |
| **Test input shortcut** | Offer built-in `test_input` with `y/n` |
| **Model settings** | Ask for `temperature`, `max_tokens`, `model` before each request |
| **Usage stats** | Print model id + total / prompt / completion tokens |
| **Non-interactive mode** | `-p` / `-q` flags for scripts and pipes |
| **Batch testing** | `run_prompt_tests.py` runs all `test_input`s and stores JSON metrics |
| **DOCX report** | `build_report_docx.py` builds a workbook-style report |

---

## Tech stack

- **Python 3.11+**
- **openai** (`AsyncOpenAI`)
- **python-dotenv**
- **python-docx** (report generation)
- **ProxyAPI** endpoint: `https://api.proxyapi.ru/openai/v1`

---

## Project layout

```text
prompt-lab-workbench/
├── prompt_chat.py          # Interactive / CLI entrypoint
├── run_prompt_tests.py     # Batch run of all prompt test_inputs
├── build_report_docx.py    # Rebuild DOCX report from saved metrics
├── prompts/
│   ├── summary.json
│   ├── code_structure.json
│   └── task_planning.json
├── reports/
│   ├── test_results.json
│   └── otchet_testirovanie_promptov.docx
├── .env.example
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Quick start

### Requirements

- Python **3.11+**
- ProxyAPI key from [proxyapi.ru](https://proxyapi.ru/)

### Setup

```bash
git clone https://github.com/nifontovoleg/prompt-lab-workbench.git
cd prompt-lab-workbench

python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

Fill `.env`:

```env
PROXY_API_KEY=your-proxyapi-key-here
PROXY_API_BASE_URL=https://api.proxyapi.ru/openai/v1
PROXY_API_MODEL=gpt-4o-mini
```

### Run interactive CLI

```bash
python prompt_chat.py
```

Flow:

```text
📋 Available prompts
1️⃣ Choose prompt (1-N) or type "выход"
✅ Selected prompt: ...
💡 Optional test_input → 🧐 use it? (y/n)
⚙️ Model settings (temperature / max_tokens / model)
⏳ Send request
📤 Answer + request info (tokens)
```

### Non-interactive mode

```bash
python prompt_chat.py -p summary -q "Paste a long article here..."
python prompt_chat.py --list
```

### Batch tests + report

```bash
python run_prompt_tests.py      # calls API for every prompts/*.json test_input
python build_report_docx.py     # rebuild DOCX from reports/test_results.json
```

Report path: `reports/otchet_testirovanie_promptov.docx`  
(Upload to Google Drive → Open with Google Docs.)

---

## Prompt templates

| ID | Name | Version | Purpose |
|----|------|---------|---------|
| `summary` | Text summary | 1.1 | Structured short summary of long text |
| `code_structure` | Code structure generation | 1.7 | Project architecture / folders / API / DB / tests |
| `task_planning` | Task planning | 1.4 | Goal → phases → tasks → deps → risks → checkpoints |

Each JSON file follows the same shape:

```text
prompt_id, name, category, version, description
role, context
structure.components[]
format.requirements[]
examples, usage_instructions
test_input, expected_test_output_description
```

The CLI turns these fields into a single **system** message and sends the user question as the **user** message.

---

## How it works

```text
prompts/*.json
      │
      ▼
build_system_message()
      │
      ├── role
      ├── context
      ├── structure / components
      └── format / requirements
      │
      ▼
AsyncOpenAI(base_url=ProxyAPI)
      │
      ▼
chat.completions.create(...)
      │
      ├── assistant content
      └── usage (prompt / completion / total tokens)
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_API_KEY` | — | Required. ProxyAPI key (`OPENAI_API_KEY` also accepted) |
| `PROXY_API_BASE_URL` | `https://api.proxyapi.ru/openai/v1` | OpenAI-compatible base URL |
| `PROXY_API_MODEL` | `gpt-4o-mini` | Default model |

Interactive defaults when Enter is pressed:

| Setting | Default |
|---------|---------|
| `temperature` | `0.7` |
| `max_tokens` | `2000` |
| `model` | value from env / `gpt-4o-mini` |

---

## Example session

```text
📋 Доступные промпты:
  1. Генерация структуры кода (code_structure)
  2. Резюме текста (summary)
  3. Планирование задач (task_planning)

1️⃣ Выберите промпт (1-3) или 'выход' для завершения: 2
✅ Выбран промпт: Резюме текста
💡 Доступен тестовый вопрос:
...
🧐 Использовать тестовый вопрос? (y/n, по умолчанию n): y
⚙️ Настройки модели:
🌡️ Введите temperature (0.0-1.0, по умолчанию 0.7):
🔢 Введите max_tokens (по умолчанию 2000):
🤖 Введите модель (по умолчанию gpt-4o-mini):

⏳ Отправляем запрос к OpenAI...

📤 Ответ:
# ... structured summary ...

Информация о запросе:
- Модель: gpt-4o-mini-2024-07-18
- Использовано токенов: 912
- Промпт токены: 637
- Ответ токены: 275
```

---

## Add your own prompt

1. Create `prompts/my_prompt.json` with at least `prompt_id`, `name`, `role`, and preferably `structure` / `format` / `test_input`
2. Restart `python prompt_chat.py`
3. The new file appears in the menu automatically

Tip: keep `test_input` + `expected_test_output_description` so `run_prompt_tests.py` can score coverage later.

---

## Roadmap

### 1. Better prompt tooling

- JSON Schema validation for `prompts/*.json`
- Prompt version diff (`v1` vs `v2`) with a comparison table
- Export system message preview without calling the API

### 2. Better CLI UX

- Streaming answers
- Save last answer to `runs/<prompt_id>-<timestamp>.md`
- Colorized output / Windows UTF-8 helper

### 3. Evaluation

- Stronger auto-checks against `expected_test_output_description`
- Token / latency scoreboard across models
- Optional second-pass “judge” prompt

### 4. Integrations

- Telegram wrapper around the same prompt loader
- FastAPI endpoint: `POST /generate {prompt_id, question}`
- Multi-provider switch (ProxyAPI / OpenAI / OpenRouter)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `PROXY_API_KEY` missing | Copy `.env.example` → `.env` and set the key |
| Mojibake in Windows console | Use Windows Terminal / set `PYTHONIOENCODING=utf-8` |
| Empty answer / truncated structure | Raise `max_tokens` (especially for `code_structure`) |
| Prompt not listed | Ensure file is `prompts/<id>.json` and valid JSON |
| API errors | Check balance / model name on ProxyAPI |

---

## Why this project

| Goal | Outcome |
|------|---------|
| Prompt engineering practice | Role / context / structure / format kept as data |
| Repeatable runs | Interactive CLI + batch tester |
| Measurable demos | Token usage + DOCX report |
| Easy extension | Drop a new JSON file into `prompts/` |

---

## License

MIT — free for learning and personal experiments.

---

<p align="center">
  Built with ☕ for prompt labs and tiny CLI tools<br>
  <a href="https://github.com/nifontovoleg">@nifontovoleg</a> · <a href="https://www.nifontovv.ru/">nifontovv.ru</a>
</p>
