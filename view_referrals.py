import sqlite3
from pathlib import Path

# مسیر پایگاه داده
db_path = Path(__file__).parent / "db" / "database.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.execute("SELECT * FROM referrals")
rows = cur.fetchall()
conn.close()

# چاپ نتایج
print("UID       | ownInviteCode | inviteSid   | invitationCode | registerTime      | direct | deposit | balance | trade | level")
for r in rows:
    print(r)
