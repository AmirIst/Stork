import os
import sqlite3
import asyncio
from dotenv import load_dotenv
import libsql_client

load_dotenv()

async def sync_tables():
    url = os.getenv('TURSO_DATABASE_URL').replace('libsql://', 'https://')
    token = os.getenv('TURSO_AUTH_TOKEN')
    
    print(f"Connecting to Turso: {url}...")
    client = libsql_client.create_client(url, auth_token=token)
    local_conn = sqlite3.connect('stork_bot.db')
    local_conn.row_factory = sqlite3.Row
    local_cur = local_conn.cursor()

    # 1. First get all CREATE TABLE statements from sqlite_master
    schema_rows = local_cur.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' ORDER BY type DESC"
    ).fetchall()

    print(f"Found {len(schema_rows)} schema definitions.")
    for s_type, s_name, s_sql in schema_rows:
        if not s_sql:
            continue
        try:
            await client.execute(s_sql)
            print(f"  [OK] Created {s_type} {s_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  [Skip] {s_type} {s_name} already exists")
            else:
                print(f"  [Warn] {s_type} {s_name}: {e}")

    # 2. Get tables list in dependency order
    table_order = [
        'users',
        'words',
        'word_translations',
        'user_progress',
        'ai_chat_history',
        'user_achievements',
        'promo_codes',
        'user_promo_activations',
        'referrals',
        'diagnostic_history',
        'user_learning_profile',
        'bot_admins',
        'payments_history'
    ]

    for table in table_order:
        rows = local_cur.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"Table {table}: 0 rows to insert.")
            continue
        
        # Check if already has data in Turso
        t_check = await client.execute(f"SELECT count(*) as c FROM {table}")
        if t_check.rows[0]['c'] >= len(rows):
            print(f"Table {table}: already has {t_check.rows[0]['c']} rows in Turso. Skipping.")
            continue
        elif t_check.rows[0]['c'] > 0:
            # Clear table to avoid duplicates during migration
            await client.execute(f"DELETE FROM {table}")

        col_names = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(col_names))
        cols_str = ", ".join(col_names)
        insert_sql = f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({placeholders})"

        print(f"Migrating {len(rows)} rows into {table}...")
        batch_size = 50
        batch = []
        for r in rows:
            values = [r[col] for col in col_names]
            batch.append((insert_sql, values))
            if len(batch) >= batch_size:
                statements = [libsql_client.Statement(s, v) for s, v in batch]
                await client.batch(statements)
                batch = []

        if batch:
            statements = [libsql_client.Statement(s, v) for s, v in batch]
            await client.batch(statements)

        v_res = await client.execute(f"SELECT count(*) as c FROM {table}")
        print(f"  -> Verified {table}: {v_res.rows[0]['c']} rows in Turso.")

    local_conn.close()
    await client.close()
    print("\nALL TABLES MIGRATED TO TURSO CLOUD SUCCESSFULLY!")

if __name__ == '__main__':
    asyncio.run(sync_tables())
