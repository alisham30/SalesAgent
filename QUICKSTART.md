# Quick Start Guide

## 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## 2. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download and save as `credentials.json` in project root

## 3. Optional: LLM Setup

Set environment variables:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your_api_key"
$env:LLM_PROVIDER="openai"
$env:LLM_MODEL="gpt-4o-mini"

# Linux/Mac
export OPENAI_API_KEY="your_api_key"
export LLM_PROVIDER="openai"  # or "anthropic"
export LLM_MODEL="gpt-4o-mini"
```

Or create `.env` file in the project root:
```env
# Required: Your LLM API key (supports both OPENAI_API_KEY and LLM_API_KEY)
OPENAI_API_KEY=your_api_key_here
# OR
# LLM_API_KEY=your_api_key_here

# Provider: "openai" or "anthropic"
LLM_PROVIDER=openai

# Model name (examples below)
LLM_MODEL=gpt-4o-mini

# Optional: Custom API endpoint (for OpenAI-compatible APIs)
# LLM_BASE_URL=https://api.openai.com/v1
```

**Note:** The code supports both `OPENAI_API_KEY` (standard OpenAI variable) and `LLM_API_KEY` (custom variable).

**LLM Provider Options:**

**OpenAI:**
- `gpt-4o-mini` (recommended, cost-effective)
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

**Anthropic:**
- `claude-3-5-sonnet-20241022`
- `claude-3-opus-20240229`
- `claude-3-haiku-20240307`

**Note:** The agent works without LLM configuration - it will use rule-based extraction instead.

## 4. Run the Agent

```bash
python run_agent.py
```

## 5. Place Manual PDFs

Place PDFs you want to process in:
```
pdfs/portal_pdfs/
```

## 6. Check Outputs

Extracted JSON files will be in:
```
backend/output/extracted/
```

Raw text files will be in:
```
backend/output/raw_text/
```

## Troubleshooting

- **Gmail authentication**: First run will open browser for OAuth. Token saved in `token.json`
- **No LLM**: Agent works without LLM, uses rule-based extraction
- **PDF extraction fails**: Check if PDF is password-protected or corrupted
- **OCR not working**: Install Tesseract OCR separately

