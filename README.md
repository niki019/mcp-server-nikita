# Groww Play Store Review Pulse Orchestrator

This repository contains the complete implementation of the **Weekly Product Review Pulse Orchestrator** for Groww reviews. It automates the retrieval, clustering, summarization, and reporting of user reviews from the Google Play Store.

## 🚀 Architecture Overview

The system is designed as a pipeline that runs periodically (e.g., weekly) to:
1. **Ingest**: Fetch and normalize reviews for the target app (Groww) from the Play Store.
2. **Cluster**: Group reviews using a combination of DBSCAN and K-Means clustering to discover emerging themes.
3. **Summarize**: Generate localized themes, descriptions, and user sentiments using Groq LLM.
4. **Validate**: Perform verbatim quote validation to ensure all cited user feedback is authentic.
5. **Log**: Store run telemetry and idempotency checks in a local SQLite ledger (`run_audit.db`).
6. **Deliver**: 
   - Write structured reports directly to Google Docs via the custom standalone **Google Docs MCP Server**.
   - Send review summaries and highlights via the custom standalone **Gmail MCP Server**.

---

## 📂 Project Structure

- `pulse/` - Core orchestrator pipeline package.
  - `agent/` - E2E pipeline runner and orchestration agent.
  - `ingestion/` - Play Store scrapers and review normalizers.
  - `pipeline/` - Text clustering, summarization, and quote validation.
  - `ledger/` - SQLite database for execution logs and delivery audit trails.
- `mcp-servers/` - Stdio-based Model Context Protocol (MCP) servers.
  - `google-docs-mcp/` - Standalone MCP server for managing Google Docs.
  - `gmail-mcp/` - Standalone MCP server for managing Gmail drafts/sends.
- `app.py` - Streamlit dashboard application for review visualization.
- `main.py` - Core entry point CLI for authentication and running the pipeline.
- `config/` - Pipeline configuration and product-specific YAML definitions.
- `Procfile` / `nixpacks.toml` - Configurations for Railway deployment.

---

## 🛠️ Setup & Local Execution

### 1. Prerequisites
- Python 3.10+
- SQLite3

### 2. Installation
Clone the repository and install the dependencies:
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Authentication Setup
Initialize Google OAuth consent and generate credentials:
```bash
python main.py auth
```
This will open your browser, prompt for Google login, and save `token.json` into the `mcp_server/` directory.

### 4. Running the Pipeline
Run the review analyzer CLI for a specific week:
```bash
python main.py run --week 2026-W24
```

### 5. Running the Streamlit Dashboard
Launch the dashboard locally to view review pulse statistics:
```bash
streamlit run app.py
```

---

## ☁️ Deployment Configuration

The repository includes pre-built configurations for deploying:
- **Streamlit Cloud**: Deploy using `app.py` and configure environment secrets (`GOOGLE_CREDENTIALS_JSON`, `GOOGLE_TOKEN_JSON`, `GROQ_API_KEY`).
- **Railway**: Uses `Procfile` and `nixpacks.toml` to automatically run and scale the services.
