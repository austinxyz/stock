---
name: MySQL Executor
description: Execute MySQL commands with automatic credential loading from backend/.env. Supports SQL files, inline queries, and interactive shell. Use this skill when the user asks to query the database, execute SQL, or check database schema.
---

# MySQL Executor Skill

Execute MySQL commands for the Stock Investment project database with automatic credential loading.

## Usage

The skill accepts three modes of operation:

1. **Execute SQL file**:
   - User provides a file path
   - Example: "run the migration file database/migrations/V1_create_stock_tables.sql"

2. **Execute inline query**:
   - User provides a SQL query string
   - Example: "show me all stock holdings"
   - Example: "query the database: SELECT * FROM portfolios LIMIT 10"

3. **Interactive shell**:
   - User asks to open MySQL shell
   - Example: "open mysql shell"
   - Example: "connect to the database"

## Implementation Steps

When this skill is invoked:

1. **Locate MySQL Client**:
   ```bash
   MYSQL_CLIENT=$(brew --prefix mysql-client)/bin/mysql
   ```

2. **Load Credentials**:
   ```bash
   source backend/.env
   # Loads: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
   ```

3. **Execute Command**:
   ```bash
   # For SQL file
   $MYSQL_CLIENT -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD $DB_NAME < file.sql

   # For inline query
   $MYSQL_CLIENT -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "QUERY"

   # For interactive shell
   $MYSQL_CLIENT -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD $DB_NAME
   ```

## Common SQL Queries

### Schema Inspection
```sql
-- List all tables
SHOW TABLES;

-- Describe table structure
DESCRIBE portfolios;
DESCRIBE holdings;
DESCRIBE stocks;

-- Show table creation
SHOW CREATE TABLE portfolios;
```

### Data Queries
```sql
-- View all portfolios
SELECT * FROM portfolios WHERE is_active = 1;

-- View current holdings with stock info
SELECT h.*, s.symbol, s.name
FROM holdings h
JOIN stocks s ON h.stock_id = s.id
WHERE h.quantity > 0
ORDER BY h.updated_at DESC;

-- Check stock basic info
SELECT * FROM stocks WHERE market IN ('US', 'HK') LIMIT 10;

-- View strategy backtest results
SELECT * FROM backtest_results WHERE strategy_id = 1 ORDER BY created_at DESC;
```

## Error Handling

- **Missing .env file**: Show error and instruct to create backend/.env
- **MySQL client not found**: Suggest `brew install mysql-client`
- **Connection failed**: Display parsed connection details for debugging
- **SQL error**: Show full error message and query context

## Prerequisites

- MySQL client installed: `brew install mysql-client`
- Database credentials in `backend/.env`
- Must run from project root directory

## Database Information

- **Database Name**: stock_investment
- **Tables**: portfolios, holdings, stocks, strategies, backtest_results, etc.
- **Shared Server**: Same MySQL server as other projects but different schema
