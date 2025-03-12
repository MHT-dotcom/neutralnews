import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('search_db.sqlite')
c = conn.cursor()
c.execute("DELETE FROM search_history WHERE timestamp < ?", 
          ((datetime.now() - timedelta(days=90)).isoformat(),))
conn.commit()
conn.close()