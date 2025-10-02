# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask-based web application that connects to PostgreSQL databases and automatically generates Prisma schema files from existing database tables. The application provides a browser-based UI for database connection, table selection, and schema generation with options for single or multiple file output.

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

## Architecture

### Core Components

**main.py** - Single-file Flask application containing:
- Web server and UI (embedded HTML/CSS/JS in `HTML_TEMPLATE`)
- Database connection management via `active_connection` global state
- PostgreSQL to Prisma type mapping in `map_postgres_to_prisma_type()` (lines 483-512)
- Schema generation logic in `generate_prisma_schema()` (lines 514-568)
- Configuration persistence using `db_config.json`

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

## Important Implementation Details

- **Connection State**: Single active connection stored in module-level `active_connection` dict - reconnecting replaces the previous connection
- **Model Naming**: Table names converted to PascalCase (e.g., `user_accounts` → `UserAccounts`)
- **Primary Keys**: Auto-detected and marked with `@id` attribute
- **Nullable Fields**: Marked with `?` suffix unless part of primary key
- **Default Values**: Auto-detected for autoincrement (`nextval`) and timestamps (`now()`)