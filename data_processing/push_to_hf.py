from datasets import load_dataset
from huggingface_hub import login, HfApi
import sys
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")  # Also checking wtf/.env just in case

print("Log in to Hugging Face...")
if "HF_TOKEN" in os.environ:
    hf_key = os.environ["HF_TOKEN"]
    login(token=hf_key, add_to_git_credential=True)
elif len(sys.argv) > 1:
    hf_key = sys.argv[1]
    login(token=hf_key, add_to_git_credential=True)
else:
    print("WARNING: HF_TOKEN not provided as argument or in .env!")
    sys.exit(1)

api = HfApi()

try:
    print("Creating repo if not exists...")
    api.create_repo(repo_id="hung20gg/financial-forecast", repo_type="dataset", exist_ok=True)
except Exception as e:
    print("Could not create repo/Already exists:", e)

print("Pushing raw JSONL files to HuggingFace hub `hung20gg/financial-forecast`...")

try:
    api.upload_file(
        path_or_fileobj="data/train.jsonl",
        path_in_repo="train.jsonl",
        repo_id="hung20gg/financial-forecast",
        repo_type="dataset"
    )
    print("Uploaded train.jsonl")
    
    api.upload_file(
        path_or_fileobj="data/test.jsonl",
        path_in_repo="test.jsonl",
        repo_id="hung20gg/financial-forecast",
        repo_type="dataset"
    )
    print("Uploaded test.jsonl")
except Exception as e:
    print("Failed to push dataset:", e)
    sys.exit(1)

readme_content = """---
language:
- vi
task_categories:
- question-answering
- tabular-classification
dataset_info:
  features:
  - name: data_source
    dtype: string
  - name: prompt
    list:
    - name: role
      dtype: string
    - name: content
      dtype: string
  - name: ability
    dtype: string
  - name: reward_model
    struct:
    - name: style
      dtype: string
    - name: ground_truth
      dtype: string
  - name: extra_info
    struct:
    - name: split
      dtype: string
    - name: index
      dtype: int64
    - name: answer
      dtype: string
    - name: question
      dtype: string
configs:
- config_name: default
  data_files:
  - split: train
    path: train.jsonl
  - split: test
    path: test.jsonl
---

# Financial Forecast Dataset (ktln)

This dataset contains financial indicators, macroeconomics metrics, commodities percent changes, and stock return calculations in Vietnam (Q3 2023 to Q3 2025). The queries are generated in Vietnamese. It's intended to train specific Local LLMs using HuggingFace GRPO (GSM8K format) tuning for math and reasoning.

## Dataset Structure

The structure mimics the `gsm8k` format.
- `data_source`: Indicates the source of data (`ktln`)
- `prompt`: The question prompt formatted as OpenAI conversation roles. Example: `[{"role": "user", "content": "Lợi nhuận ròng của ngành Dịch vụ Tài chính..."}]`.
- `ability`: `math`
- `reward_model`: Ground truth string rules for extraction and comparison.
- `extra_info`: Additional details tracking the `split`, `index`, `answer`, and the raw `question`.

### Fields Available:
- **Macroeconomics**: Inflation (% change) and Unemployment (% change).
- **Indices & Commodities**: Return percentages for VN30, Gold, Silver, Crude Oil WTI, Brent Crude Oil, Natural Gas, Gasolines.
- **Financial Ratios**: NIM and Bad Debt Ratios for Banks.
- **Financial Statements**: Net Income (Lợi nhuận ròng), Revenue (Doanh thu), and Loans to Customers (Dư nợ cho vay khách hàng \- Banks only). Differentiates between Companies, Banks, and average Industry figures.

### Splits
- **Train**: Q3 2023 -> Q2 2025 (~2500 samples)
- **Test**: Q3 2025 (~330 samples)
"""

with open("README_hf.md", "w") as f:
    f.write(readme_content)

print("Pushing README.md to Hugging Face...")
try:
    api.upload_file(
        path_or_fileobj="README_hf.md",
        path_in_repo="README.md",
        repo_id="hung20gg/financial-forecast",
        repo_type="dataset"
    )
    print("Pushed README successfully!")
except Exception as e:
    print("Failed to push README:", e)

