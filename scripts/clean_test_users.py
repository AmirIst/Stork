import os
import sqlite3
import asyncio
from dotenv import load_dotenv
import libsql_client

load_dotenv()

REAL_USER_IDS = [6725392176, 190417869, 6214246763, 624123747]

async def cleanup_database():
    url = os.getenv('TURSO_DATABASE_URL').replace('libsql://', 'https://')
    token = os.getenv('TURSO_AUTH_TOKEN')
    
    print(f"Connecting to Turso: {url}...")
    client = libsql_client.create_client(url, auth_token=token)

    # Clean Turso
    tables_with_user_id = [
        'user_progress',
        'user_achievements',
        'ai_chat_history',
        'diagnostic_history',
        'user_learning_profile',
        'user_promo_activations'
    ]

    real_ids_str = ", ".join(str(i) for i in REAL_USER_IDS)
    
    for tbl in tables_with_user_id:
        sql = f"DELETE FROM {tbl} WHERE user_id NOT IN ({real_ids_str})"
        await client.execute(sql)
        print(f"Cleaned {tbl} in Turso")

    await client.execute(f"DELETE FROM referrals WHERE inviter_id NOT IN ({real_ids_str}) OR referred_id NOT IN ({real_ids_str})")
    print("Cleaned referrals in Turso")

    await client.execute(f"DELETE FROM users WHERE user_id NOT IN ({real_ids_str})")
    print("Cleaned users in Turso")

    # Verify counts in Turso
    res_users = await client.execute("SELECT count(*) as c FROM users")
    print(f"Turso remaining users count: {res_users.rows[0]['c']}")

    res_all = await client.execute("SELECT user_id, username, first_name, score FROM users")
    for r in res_all.rows:
        print(f"  Turso user: {r['user_id']} | @{r['username']} | {r['first_name']} | score={r['score']}")

    await client.close()

    # Also clean local stork_bot.db
    local_conn = sqlite3.connect('stork_bot.db')
    local_cur = local_conn.cursor()
    for tbl in tables_with_user_id:
        local_cur.execute(f"DELETE FROM {tbl} WHERE user_id NOT IN ({real_ids_str})")
    local_cur.execute(f"DELETE FROM referrals WHERE inviter_id NOT IN ({real_ids_str}) OR referred_id NOT IN ({real_ids_str})")
    local_cur.execute(f"DELETE FROM users WHERE user_id NOT IN ({real_ids_str})")
    local_conn.commit()
    local_conn.close()
    print("Cleaned local stork_bot.db")

if __name__ == '__main__':
    asyncio.run(cleanup_database())
