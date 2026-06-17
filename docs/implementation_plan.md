# 📋 Weekly Product Review Pulse — Phase-Wise Implementation Plan

This document outlines the step-by-step plan for building, testing, and deploying the **Weekly Product Review Pulse** system for Groww Play Store reviews.

---

## Phase 1: Environment Setup & Google Auth Foundation
*Objective: Set up the workspace, configure dependencies, and establish secure connection tokens with Google API.*

### Tasks
1.  **Project Initialization**:
    *   Create the workspace folder structure (`src/`, `mcp_server/`, `doc/`).
    *   Create a virtual environment (`.venv`) and install core dependencies.
2.  **Define Dependencies (`requirements.txt`)**:
    *   `google-api-python-client` & `google-auth-httplib2` & `google-auth-oauthlib` (Google Workspace connection).
    *   `mcp[cli]` (FastMCP SDK).
    *   `google-play-scraper` (Play Store reviews retrieval).
    *   `scikit-learn` & `numpy` (Clustering & vector calculations).
    *   `python-dotenv` (Load credentials and key variables).
    *   `google-generativeai` or `openai` (For embeddings & LLM).
3.  **Google Client Helper (`mcp_server/google_client.py`)**:
    *   Create a helper class to load `credentials.json`, run the local authentication server, and save credentials to `token.json`.
    *   Implement methods to test Google Doc access and Gmail sending.
4.  **CLI Auth Helper (`main.py auth`)**:
    *   Expose a CLI command to trigger the initial browser authentication flow so the user can easily log in once to generate `token.json`.

---

## Phase 2: Custom Workspace MCP Server Development
*Objective: Build the Google Workspace MCP server using FastMCP and expose Docs and Gmail tools.*

### Tasks
1.  **Develop FastMCP Server (`mcp_server/server.py`)**:
    *   Initialize a `FastMCP("Workspace-Server")` server.
    *   Implement the `append_to_doc` tool:
        *   Accepts `doc_id`, `section_title`, and `markdown_content`.
        *   Appends a new heading and converts the markdown content to Google Docs batch update requests.
        *   Returns the specific HTTP URL pointing directly to the new heading anchor.
    *   Implement the `send_gmail_teaser` tool:
        *   Accepts `recipient`, `subject`, and `html_body`.
        *   Compiles a MIME HTML message and sends it via the Gmail API.
2.  **Isolate & Test Server**:
    *   Run the server in development mode using `mcp dev mcp_server/server.py`.
    *   Verify both tools function as expected in the MCP Inspector interface.

---

## Phase 3: Data Ingestion & PII Cleaning
*Objective: Retrieve Play Store reviews and scrub sensitive information.*

### Tasks
1.  **Scraper Logic (`src/ingest.py`)**:
    *   Use `google-play-scraper` to pull reviews for `com.nextbillion.groww`.
    *   Filter reviews by timestamp to retrieve only reviews belonging to the target ISO week.
2.  **PII Filter Integration**:
    *   Write text cleaners to strip phone numbers, email addresses, and potential names.
3.  **Local Caching layer**:
    *   Save fetched reviews to a local `.cache/reviews_[ISO_WEEK].json` file during local testing to prevent redundant calls.

---

## Phase 4: Clustering & Analysis
*Objective: Embed reviews and cluster them into distinct feedback themes.*

### Tasks
1.  **Embeddings Generator (`src/analyze.py`)**:
    *   Connect to the chosen Embedding API (Gemini or OpenAI).
    *   Generate vectors for all reviews from the target week.
2.  **Clustering Engine**:
    *   Implement DBSCAN to group reviews into semantic clusters. DBSCAN is ideal because it automatically identifies outlier reviews as "noise".
    *   If DBSCAN struggles with sparse clusters, add K-Means as an optional fallback.

---

## Phase 5: LLM Summarization & Quote Validation
*Objective: Convert clusters into structured insights and ensure verbatim quote accuracy.*

### Tasks
1.  **LLM Prompt Builder (`src/summarize.py`)**:
    *   Configure the LLM client to use Groq's `llama-3.3-70b-versatile` model.
    *   Create templates containing review clusters, instructing the LLM to output:
        *   Theme Name
        *   Theme Description
        *   Verbatim representative quote
        *   Actionable ideas
2.  **Quote Verification System**:
    *   For each quote returned by the LLM, search the raw reviews dataset for an exact match.
    *   If no exact match exists, find the closest semantic match or remove the quote to ensure zero LLM hallucinations.
3.  **Safety & Rate Limits**:
    *   Enforce safety guidelines by treating review content strictly as data, not system instructions.
    *   Implement client-side rate limit management to stay within Groq's tiers:
        *   **Model:** `llama-3.3-70b-versatile`
        *   **Requests per Minute (RPM):** 30
        *   **Requests per Day (RPD):** 1,000
        *   **Tokens per Minute (TPM):** 12,000
        *   **Tokens per Day (TPD):** 100,000
        *   *Implementation:* Incorporate a request-spacing delay (e.g. 2 seconds between sequential cluster queries) and automatic retry-after-backoff handling when receiving `429` (rate limit) responses.

---

## Phase 6: Orchestration, Idempotency & CLI
*Objective: Connect all modules together, ensure one-run-per-week constraints, and expose the main command line interface.*

### Tasks
1.  **SQLite Audit Database (`src/orchestrator.py`)**:
    *   Write database handlers to check for prior successful runs of the target ISO week.
2.  **Doc Content Checking**:
    *   Before appending, read the document's headings. If a header for the target week already exists (e.g. `## Week 25 - 2026`), skip execution to avoid duplicating sections.
3.  **Pipeline Orchestrator**:
    *   Run the modules sequentially: Ingest -> Clean -> Cluster -> LLM -> MCP Appends -> MCP Emails -> Log Audit.
4.  **CLI Interface (`main.py`)**:
    *   Implement arguments:
        *   `auth`: Run Google credentials verification flow.
        *   `run --week [YYYY-Www]`: Process reviews for a specific week.
        *   `run-current`: Automatically runs for the preceding completed week.
        *   `--mock`: Run the entire pipeline using built-in mock reviews to avoid API quotas.

---

## Phase 7: Verification & Launch
*Objective: Perform end-to-end testing and document deployment.*

### Tasks
1.  **End-to-End Dry Run**:
    *   Run the pipeline using `--mock` to check the database logs, Doc appends, and Gmail teasers.
2.  **Live Run**:
    *   Add your `credentials.json` and run the pipeline on live Play Store reviews for a recent week.
    *   Verify the Google Doc contains clean, dated sections and the Gmail inbox receives a deep-linked teaser message.
