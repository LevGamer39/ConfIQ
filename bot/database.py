import sqlite3
from typing import List, Dict, Union
from datetime import datetime

class FDataBase:
    def __init__(self, db: sqlite3.Connection):
        self.__db = db
        self.__cur = self.__db.cursor()
        self._init_tables()

    def _init_tables(self):
        try:
            with open('sq_db.sql', 'r', encoding='utf-8') as f:
                sql_script = f.read()
            self.__cur.executescript(sql_script)
            self.__db.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")

    def add_admin(self, telegram_id: int, username: str, role: str = "Admin") -> bool:
        try:
            self.__cur.execute("INSERT INTO admins (telegram_id, username, role) VALUES (?, ?, ?)", 
                               (telegram_id, username, role))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Add admin error: {e}")
            return False

    def remove_admin(self, telegram_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Remove admin error: {e}")
            return False

    def get_admin(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE telegram_id = ?", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                columns = [col[0] for col in self.__cur.description]
                return dict(zip(columns, res))
            return None
        except sqlite3.Error as e:
            print(f"Get admin error: {e}")
            return None

    def get_all_admins(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM admins ORDER BY role, created_at")
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get all admins error: {e}")
            return []

    def get_stats(self) -> Dict:
        stats = {}
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events")
            stats['total_events'] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'pending'")
            stats['pending'] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'approved'")
            stats['approved'] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE source = 'partner'")
            stats['partners'] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM admins")
            stats['total_admins'] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE date_str LIKE '%2025%' AND status = 'approved'")
            stats['upcoming_2025'] = self.__cur.fetchone()[0]

            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'rejected'")
            stats['rejected'] = self.__cur.fetchone()[0]

            self.__cur.execute("SELECT AVG(score) FROM events WHERE status = 'approved'")
            stats['avg_score'] = round(self.__cur.fetchone()[0] or 0, 1)

            self.__cur.execute("SELECT COUNT(*) FROM events WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')")
            stats['this_month'] = self.__cur.fetchone()[0]
            
        except sqlite3.Error as e:
            print(f"Get stats error: {e}")
        return stats

    def add_event(self, title, description, date_str, location, url, ai_analysis, score, is_it_related, source, status='pending'):
        try:
            if url != "invite" and url != "file_upload":
                self.__cur.execute("SELECT id FROM events WHERE url = ?", (url,))
                if self.__cur.fetchone():
                    return False

            self.__cur.execute('''
                INSERT INTO events (title, description, date_str, location, url, ai_analysis, score, is_it_related, source, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, date_str, location, url, ai_analysis, score, is_it_related, source, status))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Add event error: {e}")
            return False

    def get_pending_events(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM events WHERE status = 'pending' AND is_it_related = 1 ORDER BY score DESC, created_at DESC")
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get pending events error: {e}")
            return []

    def get_approved_events(self, limit: int = 100) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM events WHERE status = 'approved' ORDER BY score DESC, created_at DESC LIMIT ?", (limit,))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get approved events error: {e}")
            return []

    def get_event_by_id(self, event_id: int) -> Dict:
        try:
            self.__cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            res = self.__cur.fetchone()
            return self._dict_factory([res])[0] if res else None
        except sqlite3.Error as e:
            print(f"Get event by id error: {e}")
            return None

    def update_status(self, event_id: int, status: str):
        try:
            self.__cur.execute("UPDATE events SET status = ? WHERE id = ?", (status, event_id))
            self.__db.commit()
        except sqlite3.Error as e:
            print(f"Update status error: {e}")

    def delete_event(self, event_id: int):
        try:
            self.__cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Delete event error: {e}")
            return False

    def search_events(self, query: str, limit: int = 10) -> List[Dict]:
        try:
            self.__cur.execute('''
                SELECT * FROM events 
                WHERE (title LIKE ? OR description LIKE ? OR ai_analysis LIKE ?) 
                AND status = 'approved' 
                ORDER BY score DESC 
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Search events error: {e}")
            return []

    def search_events_by_keywords(self, keywords: list, limit: int = 10) -> List[Dict]:
        try:
            placeholders = ' OR '.join(['title LIKE ? OR description LIKE ? OR ai_analysis LIKE ?'] * len(keywords))
            query_params = []
            for keyword in keywords:
                query_params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
            
            query_params.append(limit)
            
            sql = f'''
                SELECT * FROM events 
                WHERE ({placeholders}) 
                AND status = 'approved' 
                ORDER BY score DESC 
                LIMIT ?
            '''
            
            self.__cur.execute(sql, query_params)
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Search events by keywords error: {e}")
            return []

    def get_events_paginated(self, page: int = 0, limit: int = 5) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM events WHERE status = 'approved' ORDER BY score DESC, created_at DESC LIMIT ? OFFSET ?", (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get paginated events error: {e}")
            return []

    def get_total_approved_events(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'approved'")
            return self.__cur.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Get total approved events error: {e}")
            return 0

    def _dict_factory(self, rows):
        if not rows or rows[0] is None:
            return []
        columns = [col[0] for col in self.__cur.description]
        return [dict(zip(columns, row)) for row in rows]