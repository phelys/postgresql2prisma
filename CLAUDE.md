# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask-based web application that connects to PostgreSQL databases and automatically generates Prisma schema files from existing database tables. The application provides a browser-based UI for database connection, table selection, and schema generation with options for single or multiple file output. Additionally, it features an AI-powered data dictionary that uses Grok AI (xAI) to analyze and explain database structures, relationships, and purposes.

## Key Commands

### Run the application
```bash
python main.py
```
Application runs on http://localhost:5000

### Install dependencies
```bash
pip install -r requirements.txt
```

### Configure API Key (required for Data Dictionary feature)
```bash
cp .env.example .env
# Edit .env and add your XAI_API_KEY
```

## Architecture

### Core Components

**main.py** - Single-file Flask application containing:
- Web server and UI (embedded HTML/CSS/JS in `HTML_TEMPLATE`)
- Database connection management via connection pool (`connection_pool`)
- PostgreSQL to Prisma type mapping in `map_postgres_to_prisma_type()`
- Schema generation logic in `generate_prisma_schema()`
- **NEW**: Database metadata extraction in `extract_database_metadata()` - extracts complete database structure including schemas, tables, columns, foreign keys, indexes, and constraints
- **NEW**: Grok AI integration via OpenAI SDK (`grok_client`)
- Configuration persistence using `db_config.json`
- Environment variables loaded from `.env` file

### Key Flows

**Database Connection Flow**:
1. User enters credentials in web UI
2. POST to `/connect` endpoint (lines 574-589) establishes connection
3. Connection stored in `active_connection` dict for subsequent operations
4. Config auto-saved to `db_config.json` and auto-loaded on startup

**Schema Generation Flow**:
1. `/schemas` endpoint queries `information_schema.tables` to list all schemas/tables
2. User selects tables via checkbox tree UI
3. `/generate` endpoint creates Prisma models with:
   - Type mapping from PostgreSQL to Prisma types
   - Primary key detection via `pg_index`
   - `@@map()` for table names and `@@schema()` for multi-schema support
   - Auto-increment and timestamp defaults
4. Output as single `.prisma` file or ZIP of multiple files

**Data Dictionary AI Flow** (NEW):
1. User switches to "Dicionário de Dados (IA)" tab
2. User selects schemas to analyze
3. `/api/data-dictionary/metadata` endpoint extracts complete metadata:
   - All tables and columns with types
   - Primary and foreign keys
   - Indexes and constraints
   - Relationships between tables
4. User sends questions via chat interface
5. `/api/data-dictionary/chat` endpoint:
   - Receives user message and conversation history
   - Calls `extract_database_metadata()` for selected schemas
   - Formats metadata as structured context for Grok AI
   - Sends prompt to Grok Beta via xAI API (OpenAI-compatible format)
   - Returns AI-generated explanation/analysis
6. UI displays response with markdown formatting
7. Conversation history maintained for context in subsequent messages

### Type Mapping

PostgreSQL types are mapped to Prisma types (lines 485-511):
- Numeric types → `Int`, `BigInt`, `Float`, `Decimal`
- Text types → `String`
- Temporal types → `DateTime`
- JSON/JSONB → `Json`
- UUID → `String`
- Bytea → `Bytes`

### Multi-Schema Support

The application handles PostgreSQL multi-schema databases by:
- Including `@@schema("schema_name")` directive in each model
- Naming output files as `{schema}_{table}.prisma` in multi-file mode
- Excluding system schemas (`pg_catalog`, `information_schema`)

## API Endpoints

### Existing Endpoints
- `GET /` - Main web interface
- `POST /connect` - Establish database connection
- `GET /schemas` - List all schemas and tables
- `POST /table-details` - Get detailed info about a specific table
- `POST /generate` - Generate Prisma schemas

### NEW: Data Dictionary Endpoints
- `POST /api/data-dictionary/metadata` - Get complete metadata for selected schemas
- `POST /api/data-dictionary/chat` - Chat with Grok AI about database structure

## Grok AI Integration (xAI)

### Configuration
- API Key loaded from `XAI_API_KEY` environment variable (`.env` file)
- Client initialized at startup: `grok_client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")`
- If API key not found, feature is disabled (logs warning)
- Uses OpenAI-compatible API format

### Model Used
- **Model**: `grok-3`
- **Max Tokens**: 4096
- **Temperature**: 0.7
- **System Prompt**: Includes complete database structure as context
- **Language**: Portuguese Brazilian for responses

### Context Provided to AI
The `chat_data_dictionary()` endpoint builds a comprehensive context including:
- Database name
- For each schema and table:
  - All columns with types, nullability, defaults
  - Primary keys
  - Foreign keys with references
  - Indexes (unique/non-unique)
  - Constraints (UNIQUE, CHECK)
- Instructions to analyze structure, explain purposes, identify relationships, suggest use cases

### Conversation Management
- History maintained client-side in JavaScript (`conversationHistory` array)
- Sent with each request to maintain context
- Formatted as `{role: 'user'|'assistant', content: 'message'}`

## Important Implementation Details

- **Connection State**: Connection pool (`connection_pool`) managed globally - reconnecting replaces pool
- **Model Naming**: Table names converted to PascalCase (e.g., `user_accounts` → `UserAccounts`)
- **Primary Keys**: Auto-detected and marked with `@id` attribute
- **Nullable Fields**: Marked with `?` suffix unless part of primary key
- **Default Values**: Auto-detected for autoincrement (`nextval`) and timestamps (`now()`)
- **Metadata Extraction**: `extract_database_metadata()` performs comprehensive queries to `information_schema` and `pg_catalog` for complete structure analysis
- **Tab Interface**: JavaScript-based tab switching between "Schema Generator" and "Data Dictionary"