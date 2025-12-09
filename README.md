# Tender Agent

A production-level Python application that automatically processes tender-related emails and PDFs, extracts technical specifications, and generates structured JSON outputs.

## Features

- **Automatic Gmail Processing**: Reads Gmail inbox using Gmail API and identifies tender-related emails
- **PDF Processing**: Extracts text from PDFs using multiple methods (PyPDF2, pdfminer, pdfplumber) with OCR fallback
- **Hyperlink Detection**: Automatically detects and downloads PDFs linked within documents
- **Intelligent Extraction**: Extracts technical specifications, delivery deadlines, quantities, warranty, and other important information
- **LLM Integration**: Uses LLM to format and refine extracted information
- **Tender ID Management**: Automatically extracts or generates unique tender IDs
- **Structured Output**: Saves extracted data as clean JSON files

## Project Structure

```
tender-agent/
│
├── run_agent.py              # Main entry point
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── backend/
│   ├── __init__.py
│   ├── main.py              # Main orchestrator
│   ├── config.py            # Configuration
│   │
│   ├── utils/               # Utility modules
│   │   ├── logger.py
│   │   ├── file_ops.py
│   │   ├── text_cleaner.py
│   │   └── url_resolver.py
│   │
│   ├── gmail_engine/        # Gmail processing
│   │   ├── gmail_reader.py
│   │   ├── email_classifier.py
│   │   └── attachment_downloader.py
│   │
│   ├── pdf_engine/          # PDF processing
│   │   ├── pdf_extractor.py
│   │   ├── hyperlink_scanner.py
│   │   ├── paragraph_parser.py
│   │   ├── spec_classifier.py
│   │   ├── important_info.py
│   │   └── tender_id_detector.py
│   │
│   ├── nlp/                 # NLP and LLM
│   │   ├── llm_agent.py
│   │   ├── tech_spec_extractor.py
│   │   └── tender_classifier.py
│   │
│   └── output/              # Output directories
│       ├── extracted/       # JSON outputs
│       └── raw_text/        # Raw extracted text
│
├── pdfs/                    # PDF storage
│   ├── mail_pdfs/          # PDFs from Gmail
│   ├── portal_pdfs/        # Manually downloaded PDFs
│   └── linked_pdfs/        # PDFs from hyperlinks
│
└── models/                  # Model storage
    └── tender_counter.txt  # Tender ID counter
```

## Installation

1. **Clone or download the project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR** (optional, for OCR fallback):
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - Linux: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`

4. **Set up Gmail API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download credentials and save as `credentials.json` in project root

5. **Configure LLM API** (optional):
   - Set environment variable: `LLM_API_KEY=your_api_key`
   - Set provider: `LLM_PROVIDER=openai` or `anthropic`
   - Set model: `LLM_MODEL=gpt-4o-mini` (default)

## Configuration

Edit `backend/config.py` to customize:

- Gmail credentials file paths
- Folder paths for PDFs and outputs
- LLM provider and model
- Tender ID prefix and format
- Keywords for classification

Or set environment variables:

```bash
export GMAIL_CREDENTIALS_FILE="credentials.json"
export GMAIL_TOKEN_FILE="token.json"
export LLM_API_KEY="your_key"
export LLM_PROVIDER="openai"
export LLM_MODEL="gpt-4o-mini"
```

## Usage

### Automatic Processing

Simply run:

```bash
python run_agent.py
```

The agent will:
1. Connect to Gmail and fetch emails
2. Classify tender-related emails
3. Download PDF attachments to `pdfs/mail_pdfs/`
4. Process PDFs from `pdfs/portal_pdfs/`
5. Extract text and information from all PDFs
6. Download linked PDFs from hyperlinks
7. Extract technical specifications and important info
8. Format using LLM (if configured)
9. Save structured JSON outputs to `backend/output/extracted/`

### Manual PDF Processing

Place PDFs in `pdfs/portal_pdfs/` and run the agent. They will be processed automatically.

## Output Format

Each tender generates a JSON file in `backend/output/extracted/` with the following structure:

```json
{
  "tender_id": "TDR-2025-0012",
  "source_pdf": "path/to/source.pdf",
  "linked_pdfs": ["path/to/linked1.pdf"],
  "technical_specifications": "• 4 sqmm FR single core cable...",
  "raw_technical_specs": ["spec1", "spec2"],
  "delivery": "30 days from PO",
  "deadline": "2025-02-15",
  "warranty": "2 years",
  "quantities": ["500 meters", "100 pieces"],
  "voltage": "1100V grade",
  "standards": ["IS 5831", "IS 8130", "IEC 60502"],
  "item_descriptions": ["Item 1: Cable...", "Item 2: Wire..."],
  "raw_text_file": "path/to/raw_text.txt"
}
```

## Tender ID Format

- **Extracted**: If tender ID is found in email/PDF, it's used as-is
- **Generated**: If not found, format is `TDR-YYYY-NNNN` (e.g., `TDR-2025-0001`)
- Counter is automatically incremented and saved

## Logging

Logs are saved to `logs/tender_agent_YYYYMMDD.log` and also displayed in console.

## Troubleshooting

### Gmail Authentication Issues
- Ensure `credentials.json` is in project root
- Delete `token.json` and re-authenticate if needed
- Check Gmail API is enabled in Google Cloud Console

### PDF Extraction Fails
- Ensure PDFs are not password-protected
- Try different extraction methods (configured in `config.py`)
- Enable OCR for scanned PDFs

### LLM Not Working
- Check `LLM_API_KEY` environment variable is set
- Verify API key is valid
- Check internet connection
- Agent will work without LLM (uses rule-based extraction)

### Missing Dependencies
- Run `pip install -r requirements.txt`
- For OCR: Install Tesseract separately
- For Gmail: Ensure all Google API libraries are installed

## License

This project is provided as-is for production use.

## Support

For issues or questions, check the logs in `logs/` directory for detailed error messages.

