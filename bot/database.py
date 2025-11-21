import sqlite3
from typing import List, Dict, Union
from datetime import datetime, timedelta

class FDataBase:
    def __init__(self, db: sqlite3.Connection):
        self.__db = db
        self.__db.row_factory = sqlite3.Row
        self.__cur = self.__db.cursor()
        self._init_tables()

    def _init_tables(self):
        try:
            sql_script = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                department TEXT,
                position TEXT,
                status TEXT DEFAULT 'pending',
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                date_str TEXT,
                url TEXT,
                analysis TEXT,
                score INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                required_rank INTEGER DEFAULT 1,
                event_datetime DATETIME,
                status TEXT DEFAULT 'new',
                source TEXT DEFAULT 'parser', 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (event_id) REFERENCES events (id),
                UNIQUE(user_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                role TEXT DEFAULT 'Manager',
                is_active BOOLEAN DEFAULT 1,
                notification_day TEXT,
                notification_time TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                url TEXT UNIQUE NOT NULL,
                base_url TEXT,
                is_active BOOLEAN DEFAULT 1
            );
            """
            self.__cur.executescript(sql_script)
            
            # Миграции
            try:
                self.__cur.execute("ALTER TABLE admins ADD COLUMN notification_day TEXT")
                self.__cur.execute("ALTER TABLE admins ADD COLUMN notification_time TEXT")
            except: pass
            
            # Базовые источники (если таблица пуста)
            self.__cur.execute("SELECT COUNT(*) FROM sources")
            if self.__cur.fetchone()[0] == 0:
                base_sources = [
                    ("IT Event Hub", "https://it-event-hub.ru/", "https://it-event-hub.ru/"),
                    ("Tproger", "https://tproger.ru/events/", "https://tproger.ru"),
                    ("Habr Career", "https://career.habr.com/events", "https://career.habr.com")
                ]
                self.__cur.executemany("INSERT INTO sources (name, url, base_url) VALUES (?, ?, ?)", base_sources)

            self.__db.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")

    def _dict_factory(self, rows) -> List[Dict]:
        if not rows: return []
        try:
            if hasattr(rows[0], 'keys'): return [dict(row) for row in rows]
            else:
                columns = [col[0] for col in self.__cur.description]
                return [dict(zip(columns, row)) for row in rows]
        except: return []

    def _get_position_rank(self, position: str) -> int:
        if not position: return 1
        pos = position.lower().strip()
        if any(x in pos for x in ['директор', 'гендиректор', 'ceo']): return 5
        if any(x in pos for x in ['руководитель', 'head', 'начальник']): return 4
        if any(x in pos for x in ['senior', 'тимлид', 'lead', 'главный']): return 3
        if any(x in pos for x in ['middle', 'разработчик', 'менеджер']): return 2
        return 1

    def _get_user_rank(self, telegram_id: int) -> int:
        user = self.get_user(telegram_id)
        return self._get_position_rank(user['position']) if user else 1

    # --- SOURCES METHODS ---
    def get_active_sources(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM sources WHERE is_active = 1")
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def add_source(self, name: str, url: str, base_url: str) -> bool:
        try:
            self.__cur.execute("INSERT INTO sources (name, url, base_url) VALUES (?, ?, ?)", (name, url, base_url))
            self.__db.commit()
            return True
        except: return False

    def delete_source(self, source_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            self.__db.commit()
            return True
        except: return False

    # --- USER METHODS ---
    def get_user(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            res = self.__cur.fetchone()
            return dict(res) if res else None
        except: return None
        
    def get_user_by_id(self, user_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            res = self.__cur.fetchone()
            return dict(res) if res else None
        except: return None

    def add_user(self, telegram_id: int, username: str, full_name: str = None) -> bool:
        try:
            self.__cur.execute("INSERT OR IGNORE INTO users (telegram_id, username, full_name, status) VALUES (?, ?, ?, 'pending')", (telegram_id, username, full_name))
            self.__db.commit()
            return True
        except: return False

    def update_user_profile(self, telegram_id: int, **kwargs) -> bool:
        if not kwargs: return False
        columns = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(telegram_id)
        try:
            self.__cur.execute(f"UPDATE users SET {columns} WHERE telegram_id = ?", values)
            self.__db.commit()
            return True
        except: return False
        
    def update_user_activity(self, telegram_id: int):
        try:
            self.__cur.execute("UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
        except: pass

    def get_user_manager(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE role IN ('Manager', 'TechSupport') AND is_active = 1 LIMIT 1")
            res = self.__cur.fetchone()
            return dict(res) if res else None
        except: return None

    # --- EVENT METHODS ---
    def add_new_event(self, title, description, location, date_str, url, analysis, score, priority, required_rank, event_datetime, status, source='parser'):
        try:
            self.__cur.execute("""
                INSERT INTO events (title, description, location, date_str, url, analysis, score, priority, required_rank, event_datetime, status, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, location, date_str, url, analysis, score, priority, required_rank, event_datetime, status, source))
            self.__db.commit()
            return True
        except Exception as e:
            print(f"Error adding event: {e}")
            return False

    def get_event_by_id(self, event_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            res = self.__cur.fetchone()
            return dict(res) if res else None
        except: return None

    def check_event_exists_by_url(self, url: str) -> bool:
        if not url: return False
        try:
            self.__cur.execute("SELECT id FROM events WHERE url = ?", (url,))
            return bool(self.__cur.fetchone())
        except: return False

    def get_events_paginated(self, telegram_id: int, page: int = 0, limit: int = 1, source: str = None) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            offset = page * limit
            query = "SELECT * FROM events WHERE status = 'approved' AND required_rank <= ? AND (event_datetime IS NOT NULL)"
            params = [user_rank]
            if source == 'partner': query += " AND source = 'partner'"
            else: query += " AND source != 'partner'"
            query += " ORDER BY priority DESC, score DESC, event_datetime ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except Exception as e:
            print(f"Error in get_events_paginated: {e}")
            return []

    def get_high_priority_events_paginated(self, telegram_id: int, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            offset = page * limit
            self.__cur.execute(
                "SELECT * FROM events WHERE priority = 'high' AND status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL ORDER BY score DESC LIMIT ? OFFSET ?",
                (user_rank, limit, offset)
            )
            return self._dict_factory(self.__cur.fetchall())
        except Exception as e:
            print(f"Error in get_high_priority_events_paginated: {e}")
            return []

    def get_total_priority_events(self, telegram_id: int) -> int:
        try:
            user_rank = self._get_user_rank(telegram_id)
            self.__cur.execute(
                "SELECT COUNT(*) FROM events WHERE priority = 'high' AND status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL",
                (user_rank,)
            )
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except:
            return 0

    def get_partner_events_paginated(self, telegram_id: int, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            offset = page * limit
            self.__cur.execute(
                "SELECT * FROM events WHERE source = 'partner' AND status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL ORDER BY event_datetime ASC LIMIT ? OFFSET ?",
                (user_rank, limit, offset)
            )
            return self._dict_factory(self.__cur.fetchall())
        except Exception as e:
            print(f"Error in get_partner_events_paginated: {e}")
            return []

    def get_total_partner_events(self, telegram_id: int) -> int:
        try:
            user_rank = self._get_user_rank(telegram_id)
            self.__cur.execute(
                "SELECT COUNT(*) FROM events WHERE source = 'partner' AND status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL",
                (user_rank,)
            )
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except:
            return 0

    def get_user_events_paginated(self, telegram_id: int, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            user = self.get_user(telegram_id)
            if not user:
                return []
            offset = page * limit
            self.__cur.execute(
                "SELECT e.*, ue.status, ue.registration_date FROM events e JOIN user_events ue ON e.id = ue.event_id WHERE ue.user_id = ? ORDER BY e.event_datetime DESC LIMIT ? OFFSET ?",
                (user['id'], limit, offset)
            )
            return self._dict_factory(self.__cur.fetchall())
        except Exception as e:
            print(f"Error in get_user_events_paginated: {e}")
            return []

    def get_total_user_events(self, telegram_id: int) -> int:
        try:
            user = self.get_user(telegram_id)
            if not user:
                return 0
            self.__cur.execute(
                "SELECT COUNT(*) FROM user_events WHERE user_id = ?",
                (user['id'],)
            )
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except:
            return 0

    def get_partner_events(self, telegram_id: int) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            query = "SELECT * FROM events WHERE status = 'approved' AND source = 'partner' AND required_rank <= ? AND (event_datetime IS NOT NULL) ORDER BY event_datetime ASC"
            self.__cur.execute(query, (user_rank,))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_all_events_for_export(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM events ORDER BY created_at DESC")
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    # --- ADMIN METHODS ---
    def get_admin(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE telegram_id = ?", (telegram_id,))
            res = self.__cur.fetchone()
            return dict(res) if res else None
        except: return None
        
    def get_admins_by_notification(self, day_of_week: str, time_str: str) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE (notification_day = ? OR notification_day = 'every_day') AND notification_time = ? AND is_active = 1", (day_of_week, time_str))
            return self._dict_factory(self.__cur.fetchall())
        except: return []
        
    def get_admins_by_time(self, time_str: str) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE notification_time = ? AND is_active = 1", (time_str,))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def update_admin_notification(self, telegram_id: int, day: str, time: str):
        try:
            self.__cur.execute("UPDATE admins SET notification_day = ?, notification_time = ? WHERE telegram_id = ?", (day, time, telegram_id))
            self.__db.commit()
        except: pass

    def get_pending_events_paginated(self, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM events WHERE status IN ('new', 'pending') ORDER BY created_at ASC LIMIT ? OFFSET ?", (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_total_pending_events_count(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status IN ('new', 'pending')")
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except: return 0

    def update_status(self, event_id: int, status: str):
        try:
            self.__cur.execute("UPDATE events SET status = ? WHERE id = ?", (status, event_id))
            self.__db.commit()
        except: pass

    def delete_event(self, event_id: int):
        try:
            self.__cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.__db.commit()
        except: pass

    def update_event(self, event_id: int, **kwargs) -> bool:
        if not kwargs: return False
        columns = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(event_id)
        try:
            self.__cur.execute(f"UPDATE events SET {columns} WHERE id = ?", values)
            self.__db.commit()
            return True
        except: return False
        
    def get_all_events_paginated(self, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_total_events_count(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events")
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except: return 0
        
    def search_all_events_by_keywords(self, keywords: List[str], limit: int = 20) -> List[Dict]:
        try:
            query = "SELECT * FROM events WHERE (1=0"
            params = []
            for k in keywords:
                query += " OR title LIKE ? OR description LIKE ?"
                params.extend([f"%{k}%", f"%{k}%"])
            query += ") ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except: return []
    
    # --- REGISTRATIONS & BULK ---
    def add_user_event(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("INSERT INTO user_events (user_id, event_id, status) VALUES (?, ?, 'pending')", (user_id, event_id))
            self.__db.commit()
            return True
        except: return False

    def remove_user_event(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM user_events WHERE user_id = ? AND event_id = ?", (user_id, event_id))
            self.__db.commit()
            return True
        except: return False

    def get_user_events(self, user_id: int) -> List[Dict]:
        try:
            self.__cur.execute("SELECT e.*, ue.status, ue.registration_date FROM events e JOIN user_events ue ON e.id = ue.event_id WHERE ue.user_id = ? ORDER BY e.event_datetime DESC", (user_id,))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_pending_registrations(self) -> List[Dict]:
        try:
            query = "SELECT ue.user_id, ue.event_id, e.title AS event_title, u.full_name AS user_name, u.position AS user_position, e.date_str, e.url, u.telegram_id FROM user_events ue JOIN events e ON ue.event_id = e.id JOIN users u ON ue.user_id = u.id WHERE ue.status = 'pending'"
            self.__cur.execute(query)
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_events_with_pending_registrations(self, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            offset = page * limit
            query = "SELECT e.id, e.title, e.date_str, COUNT(ue.user_id) as pending_count FROM events e JOIN user_events ue ON e.id = ue.event_id WHERE ue.status = 'pending' GROUP BY e.id ORDER BY e.event_datetime ASC LIMIT ? OFFSET ?"
            self.__cur.execute(query, (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except: return []
        
    def get_total_events_with_pending_regs(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(DISTINCT event_id) FROM user_events WHERE status = 'pending'")
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except: return 0

    def approve_all_event_registrations(self, event_id: int) -> List[Dict]:
        try:
            query = "SELECT u.telegram_id, e.title, e.date_str FROM user_events ue JOIN users u ON ue.user_id = u.id JOIN events e ON ue.event_id = e.id WHERE ue.event_id = ? AND ue.status = 'pending'"
            self.__cur.execute(query, (event_id,))
            users = self._dict_factory(self.__cur.fetchall())
            self.__cur.execute("UPDATE user_events SET status = 'approved' WHERE event_id = ? AND status = 'pending'", (event_id,))
            self.__db.commit()
            return users
        except: return []

    def reject_all_event_registrations(self, event_id: int) -> List[Dict]:
        try:
            query = "SELECT u.telegram_id, e.title, e.date_str FROM user_events ue JOIN users u ON ue.user_id = u.id JOIN events e ON ue.event_id = e.id WHERE ue.event_id = ? AND ue.status = 'pending'"
            self.__cur.execute(query, (event_id,))
            users = self._dict_factory(self.__cur.fetchall())
            self.__cur.execute("DELETE FROM user_events WHERE event_id = ? AND status = 'pending'", (event_id,))
            self.__db.commit()
            return users
        except: return []

    def approve_registration(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("UPDATE user_events SET status = 'approved' WHERE user_id = ? AND event_id = ?", (user_id, event_id))
            self.__db.commit()
            return True
        except: return False

    def reject_registration(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM user_events WHERE user_id = ? AND event_id = ?", (user_id, event_id))
            self.__db.commit()
            return True
        except: return False

    def get_event_registrations(self, event_id: int) -> List[Dict]:
        try:
            self.__cur.execute("SELECT u.full_name, u.position, ue.status, ue.registration_date FROM user_events ue JOIN users u ON ue.user_id = u.id WHERE ue.event_id = ?", (event_id,))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    # --- USER APPROVAL ---
    def get_pending_users(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE status = 'pending'")
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_pending_users_paginated(self, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY registered_at ASC LIMIT ? OFFSET ?", (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_total_pending_users_count(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except: return 0

    def approve_user(self, user_id: int) -> bool:
        try:
            self.__cur.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
            self.__db.commit()
            return True
        except: return False

    def reject_user(self, user_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.__db.commit()
            return True
        except: return False

    def force_approve_user(self, telegram_id: int):
        try:
            self.__cur.execute("UPDATE users SET status = 'approved' WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
        except: pass

    # --- ADMIN MGMT ---
    def add_admin(self, telegram_id: int, username: str, role: str):
        try:
            self.__cur.execute("INSERT OR REPLACE INTO admins (telegram_id, username, role, is_active) VALUES (?, ?, ?, 1)", (telegram_id, username, role))
            self.__db.commit()
        except: pass
    
    def remove_admin(self, telegram_id: int):
        try:
            self.__cur.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
        except: pass

    def get_all_admins(self):
        try:
            self.__cur.execute("SELECT * FROM admins")
            return self._dict_factory(self.__cur.fetchall())
        except: return []
        
    def update_admin_role(self, telegram_id: int, new_role: str):
        try:
            self.__cur.execute("UPDATE admins SET role = ? WHERE telegram_id = ?", (new_role, telegram_id))
            self.__db.commit()
        except: pass

    # --- STATS ---
    def get_stats(self) -> Dict:
        try:
            stats = {}
            for table in ['users', 'events']:
                self.__cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"total_{table}"] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
            stats["active_users"] = self.__cur.fetchone()[0]
            self.__cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            stats["pending_users"] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'approved'")
            stats["approved_events"] = self.__cur.fetchone()[0]
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'pending' OR status = 'new'")
            stats["pending_events"] = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM user_events")
            stats["total_registrations"] = self.__cur.fetchone()[0]
            self.__cur.execute("SELECT COUNT(*) FROM user_events WHERE status = 'pending'")
            stats["pending_registrations"] = self.__cur.fetchone()[0]
            return stats
        except: return {}
    
    def get_upcoming_events(self, telegram_id: int, days: int = 31) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            end_date = datetime.now() + timedelta(days=days)
            self.__cur.execute("SELECT * FROM events WHERE status = 'approved' AND required_rank <= ? AND (event_datetime <= datetime(?)) ORDER BY event_datetime ASC", (user_rank, end_date.strftime('%Y-%m-%d %H:%M:%S')))
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_high_priority_events(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            self.__cur.execute("SELECT * FROM events WHERE priority = 'high' AND status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL ORDER BY score DESC LIMIT ?", (user_rank, limit))
            return self._dict_factory(self.__cur.fetchall())
        except: return []
        
    def search_events_by_keywords(self, telegram_id: int, keywords: List[str], limit: int = 20) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            query = "SELECT * FROM events WHERE status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL AND (1=0"
            params = [user_rank]
            for k in keywords:
                query += " OR title LIKE ? OR description LIKE ?"
                params.extend([f"%{k}%", f"%{k}%"])
            query += ") ORDER BY score DESC LIMIT ?"
            params.append(limit)
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except: return []
        
    def get_user_stats(self, user_id: int) -> Dict:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM user_events WHERE user_id = ? AND status = 'approved'", (user_id,))
            res = self.__cur.fetchone()
            total = res[0] if res else 0
            return {"total_events": total, "high_priority": 0}
        except: return {}
        
    def get_all_approved_users(self):
        try:
            self.__cur.execute("SELECT * FROM users WHERE status = 'approved' ORDER BY full_name")
            return self._dict_factory(self.__cur.fetchall())
        except: return []

    def get_total_approved_events(self, source_filter='all') -> int:
        try:
            query = "SELECT COUNT(*) FROM events WHERE status = 'approved' AND (event_datetime >= datetime('now') OR event_datetime IS NULL)"
            if source_filter == 'main': query += " AND source != 'partner'"
            elif source_filter == 'partner': query += " AND source = 'partner'"
            self.__cur.execute(query)
            res = self.__cur.fetchone()
            return res[0] if res else 0
        except: return 0
    def search_events_with_filters(self, telegram_id: int, keywords: list, date_filter: str = None, priority_filter: str = None) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            query = "SELECT * FROM events WHERE status = 'approved' AND required_rank <= ? AND event_datetime IS NOT NULL"
            params = [user_rank]
            
            # Фильтр по ключевым словам
            if keywords:
                query += " AND (1=0"
                for kw in keywords:
                    query += " OR title LIKE ? OR description LIKE ?"
                    params.extend([f"%{kw}%", f"%{kw}%"])
                query += ")"
            
            # Фильтр по дате
            if date_filter == "week":
                query += " AND event_datetime BETWEEN datetime('now') AND datetime('now', '+7 days')"
            
            # Фильтр по приоритету
            if priority_filter == "high":
                query += " AND priority = 'high'"
            
            query += " ORDER BY priority DESC, score DESC, event_datetime ASC LIMIT 50"
            
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except Exception as e:
            print(f"Error in search_events_with_filters: {e}")
            return []

    def search_admin_events_with_filters(self, keywords: list, status_filter: str = None, source_filter: str = None, limit: int = 20) -> List[Dict]:
        try:
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            
            # Фильтр по ключевым словам
            if keywords:
                query += " AND (1=0"
                for kw in keywords:
                    query += " OR title LIKE ? OR description LIKE ?"
                    params.extend([f"%{kw}%", f"%{kw}%"])
                query += ")"
            
            # Фильтр по статусу
            if status_filter:
                if status_filter == "approved":
                    query += " AND status = 'approved'"
                elif status_filter in ["pending", "new"]:
                    query += " AND (status = 'pending' OR status = 'new')"
            
            # Фильтр по источнику
            if source_filter:
                query += " AND source = ?"
                params.append(source_filter)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except Exception as e:
            print(f"Error in search_admin_events_with_filters: {e}")
            return []