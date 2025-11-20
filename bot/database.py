import sqlite3
from typing import List, Dict, Union
from datetime import datetime, timedelta

class FDataBase:
    def __init__(self, db: sqlite3.Connection):
        self.__db = db
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
                role TEXT DEFAULT 'Admin',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO admins (telegram_id, username, role) 
            VALUES (5159491775, 'owner', 'GreatAdmin');
            """
            self.__cur.executescript(sql_script)
            self.__db.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")

    def _dict_factory(self, rows) -> List[Dict]:
        if not rows:
            return []
        
        try:
            if hasattr(rows[0], 'keys'):
                return [dict(row) for row in rows]
            else:
                columns = [col[0] for col in self.__cur.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception:
            return []

    @staticmethod
    def _get_position_rank(position: str) -> int:
        if not position:
            return 1
        
        position = position.lower().strip()
        
        if 'директор' in position or 'гендиректор' in position or 'ceo' in position:
            return 5
        elif 'руководитель' in position or 'head' in position or 'начальник' in position:
            return 4
        elif 'senior' in position or 'тимлид' in position or 'lead' in position or 'главный' in position:
            return 3
        elif 'middle' in position or 'разработчик' in position or 'менеджер' in position:
            return 2
        elif 'junior' in position or 'джун' in position or 'стажер' in position:
            return 1
        
        return 2

    def get_user_by_id(self, user_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)) 
            res = self.__cur.fetchone()
            if res:
                return dict(res)
            return None
        except sqlite3.Error as e:
            print(f"Get user by id error: {e}")
            return None

    def _get_user_rank(self, telegram_id: int) -> int:
        user = self.get_user(telegram_id)
        if user and user.get('position'):
            return self._get_position_rank(user['position'])
        return self._get_position_rank(None)

    def add_user(self, telegram_id: int, username: str, full_name: str = None) -> bool:
        try:
            self.__cur.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, full_name, status) VALUES (?, ?, ?, 'pending')", 
                (telegram_id, username, full_name)
            )
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Add user error: {e}")
            return False

    def update_user_profile(self, telegram_id: int, email: str = None, phone: str = None, department: str = None, position: str = None, full_name: str = None) -> bool:
        try:
            updates = []
            params = []
            
            if email:
                updates.append("email = ?")
                params.append(email)
            if phone:
                updates.append("phone = ?")
                params.append(phone)
            if department:
                updates.append("department = ?")
                params.append(department)
            if position:
                updates.append("position = ?")
                params.append(position)
            if full_name:
                updates.append("full_name = ?")
                params.append(full_name)
                
            if updates:
                params.append(telegram_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = ?"
                self.__cur.execute(query, params)
                self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Update user profile error: {e}")
            return False

    def get_user(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                return dict(res)
            return None
        except sqlite3.Error as e:
            print(f"Get user error: {e}")
            return None

    def update_user_activity(self, telegram_id: int) -> bool:
        try:
            self.__cur.execute("UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Update user activity error: {e}")
            return False
            
    def get_user_manager(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE role = 'GreatAdmin' LIMIT 1")
            res = self.__cur.fetchone()
            if res:
                return dict(res)
            return None
        except sqlite3.Error as e:
            print(f"Get user manager error: {e}")
            return None

    def add_user_event(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("SELECT status FROM user_events WHERE user_id = ? AND event_id = ?", (user_id, event_id))
            if self.__cur.fetchone():
                return False

            self.__cur.execute("INSERT INTO user_events (user_id, event_id, status) VALUES (?, ?, 'pending')", 
                               (user_id, event_id))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Add user event error: {e}")
            return False
            
    def approve_registration(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("UPDATE user_events SET status = 'approved', registration_date = CURRENT_TIMESTAMP WHERE user_id = ? AND event_id = ? AND status = 'pending'", (user_id, event_id))
            self.__db.commit()
            return self.__cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Approve registration error: {e}")
            return False

    def reject_registration(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM user_events WHERE user_id = ? AND event_id = ? AND status = 'pending'", (user_id, event_id))
            self.__db.commit()
            return self.__cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Reject registration error: {e}")
            return False

    def get_pending_registrations(self) -> List[Dict]:
        try:
            query = """
                SELECT ue.user_id, ue.event_id, e.title AS event_title, e.location, 
                       u.full_name AS user_name, u.position AS user_position, 
                       e.date_str, e.url
                FROM user_events ue
                JOIN events e ON ue.event_id = e.id
                JOIN users u ON ue.user_id = u.id
                WHERE ue.status = 'pending'
                ORDER BY ue.registration_date ASC
            """
            self.__cur.execute(query)
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get pending registrations error: {e}")
            return []
            
    def remove_user_event(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM user_events WHERE user_id = ? AND event_id = ?", (user_id, event_id))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Remove user event error: {e}")
            return False

    def get_user_events(self, user_id: int) -> List[Dict]:
        try:
            self.__cur.execute("""
                SELECT e.*, ue.registration_date, ue.status 
                FROM events e 
                JOIN user_events ue ON e.id = ue.event_id 
                WHERE ue.user_id = ? 
                ORDER BY e.event_datetime DESC
            """, (user_id,))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get user events error: {e}")
            return []

    def get_event_by_id(self, event_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            res = self.__cur.fetchone()
            if res:
                return dict(res)
            return None
        except sqlite3.Error as e:
            print(f"Get event by id error: {e}")
            return None

    def get_events_paginated(self, telegram_id: int, page: int = 0, limit: int = 5) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            offset = page * limit
            
            query = """
                SELECT * FROM events 
                WHERE status = 'approved' 
                AND required_rank <= ? 
                AND (event_datetime >= datetime('now') OR event_datetime IS NULL)
                ORDER BY priority DESC, score DESC, event_datetime ASC 
                LIMIT ? OFFSET ?
            """
            self.__cur.execute(query, (user_rank, limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get paginated events error: {e}")
            return []

    def get_high_priority_events(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            query = """
                SELECT * FROM events 
                WHERE priority = 'high' 
                AND status = 'approved' 
                AND required_rank <= ? 
                AND (event_datetime >= datetime('now') OR event_datetime IS NULL)
                ORDER BY score DESC, event_datetime ASC
                LIMIT ?
            """
            self.__cur.execute(query, (user_rank, limit))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get high priority events error: {e}")
            return []
            
    def search_events_by_keywords(self, telegram_id: int, keywords: List[str], limit: int = 20) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            
            query = """
                SELECT * FROM events 
                WHERE status = 'approved'
                AND required_rank <= ?
                AND (event_datetime >= datetime('now') OR event_datetime IS NULL)
                AND (
                    1 = 0
            """
            params = [user_rank]
            
            for keyword in keywords:
                query += " OR title LIKE ? OR description LIKE ?"
                param = f"%{keyword}%"
                params.extend([param, param])
            
            query += ") ORDER BY score DESC LIMIT ?"
            params.append(limit)
            
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Search events by keywords error: {e}")
            return []

    def get_upcoming_events(self, telegram_id: int, days: int = 31) -> List[Dict]:
        try:
            user_rank = self._get_user_rank(telegram_id)
            end_date = datetime.now() + timedelta(days=days)
            
            query = """
                SELECT * FROM events 
                WHERE status = 'approved' 
                AND required_rank <= ?
                AND (event_datetime BETWEEN datetime('now') AND datetime(?))
                ORDER BY event_datetime ASC
                LIMIT 50
            """
            self.__cur.execute(query, (user_rank, end_date.strftime('%Y-%m-%d %H:%M:%S')))
            return self._dict_factory(self.__cur.fetchall())
            
        except sqlite3.Error as e:
            print(f"Get upcoming events error: {e}")
            return []

    def get_total_approved_events(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'approved' AND (event_datetime >= datetime('now') OR event_datetime IS NULL)")
            return self.__cur.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Get total approved events error: {e}")
            return 0
            
    def get_user_stats(self, user_id: int) -> Dict:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM user_events WHERE user_id = ? AND status = 'approved'", (user_id,))
            total_events = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT COUNT(*) FROM user_events ue 
                JOIN events e ON ue.event_id = e.id 
                WHERE ue.user_id = ? AND e.priority = 'high' AND ue.status = 'approved'
            """, (user_id,))
            high_priority = self.__cur.fetchone()[0]
            
            return {
                "total_events": total_events,
                "high_priority": high_priority
            }
        except sqlite3.Error as e:
            print(f"Get user stats error: {e}")
            return {}

    def get_admin(self, telegram_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM admins WHERE telegram_id = ?", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                return dict(res)
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
        except sqlite3.Error as e:
            print(f"Delete event error: {e}")
            
    def add_new_event(self, title, description, location, date_str, url, analysis, score, priority, required_rank, event_datetime, status):
        try:
            self.__cur.execute("""
                INSERT INTO events (title, description, location, date_str, url, analysis, score, priority, required_rank, event_datetime, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, location, date_str, url, analysis, score, priority, required_rank, event_datetime, status))
            self.__db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Add new event error: {e}")
            return False
    
    def get_stats(self) -> Dict:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM users")
            total_users = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
            active_users = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            pending_users = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events")
            total_events = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'approved'")
            approved_events = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'pending' OR status = 'new'")
            pending_events = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE priority = 'high'")
            high_priority = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM user_events")
            total_registrations = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM user_events WHERE status = 'pending'")
            pending_registrations = self.__cur.fetchone()[0]
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "pending_users": pending_users,
                "total_events": total_events,
                "approved_events": approved_events,
                "pending_events": pending_events,
                "high_priority": high_priority,
                "total_registrations": total_registrations,
                "pending_registrations": pending_registrations
            }
        except sqlite3.Error as e:
            print(f"Get stats error: {e}")
            return {}
    
    def add_admin(self, telegram_id: int, username: str, role: str) -> bool:
        try:
            self.__cur.execute(
                "INSERT OR REPLACE INTO admins (telegram_id, username, role, is_active) VALUES (?, ?, ?, 1)", 
                (telegram_id, username, role)
            )
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

    def update_admin_role(self, telegram_id: int, new_role: str) -> bool:
        try:
            self.__cur.execute("UPDATE admins SET role = ? WHERE telegram_id = ?", (new_role, telegram_id))
            self.__db.commit()
            return self.__cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Update admin role error: {e}")
            return False

    def get_pending_users(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY registered_at ASC")
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get pending users error: {e}")
            return []

    def approve_user(self, user_id: int) -> bool:
        try:
            self.__cur.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
            self.__db.commit()
            return self.__cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Approve user error: {e}")
            return False

    def reject_user(self, user_id: int) -> bool:
        try:
            self.__cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.__db.commit()
            return self.__cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Reject user error: {e}")
            return False

    def get_pending_events(self) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM events WHERE status = 'new' OR status = 'pending' ORDER BY created_at ASC")
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get pending events error: {e}")
            return []

    def force_approve_user(self, telegram_id: int) -> bool:
        try:
            self.__cur.execute("UPDATE users SET status = 'approved' WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
            return self.__cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Force approve user error: {e}")
            return False

    def get_event_registrations(self, event_id: int) -> List[Dict]:
        try:
            query = """
                SELECT u.full_name, u.position, ue.status, ue.registration_date
                FROM user_events ue
                JOIN users u ON ue.user_id = u.id
                WHERE ue.event_id = ?
                ORDER BY ue.registration_date DESC
            """
            self.__cur.execute(query, (event_id,))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get event registrations error: {e}")
            return []

    def update_event(self, event_id: int, title: str = None, description: str = None, location: str = None, date_str: str = None, url: str = None) -> bool:
        try:
            updates = []
            params = []
            
            if title:
                updates.append("title = ?")
                params.append(title)
            if description:
                updates.append("description = ?")
                params.append(description)
            if location:
                updates.append("location = ?")
                params.append(location)
            if date_str:
                updates.append("date_str = ?")
                params.append(date_str)
            if url:
                updates.append("url = ?")
                params.append(url)
                
            if updates:
                params.append(event_id)
                query = f"UPDATE events SET {', '.join(updates)} WHERE id = ?"
                self.__cur.execute(query, params)
                self.__db.commit()
                return True
            return False
        except sqlite3.Error as e:
            print(f"Update event error: {e}")
            return False

    def get_all_events_paginated(self, page: int = 0, limit: int = 10) -> List[Dict]:
        try:
            offset = page * limit
            query = "SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?"
            self.__cur.execute(query, (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get all events paginated error: {e}")
            return []

    def get_total_events_count(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events")
            return self.__cur.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Get total events count error: {e}")
            return 0

    def get_pending_users_paginated(self, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY registered_at ASC LIMIT ? OFFSET ?", (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get pending users paginated error: {e}")
            return []

    def get_total_pending_users_count(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            return self.__cur.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Get total pending users count error: {e}")
            return 0

    def get_pending_events_paginated(self, page: int = 0, limit: int = 1) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM events WHERE status = 'new' OR status = 'pending' ORDER BY created_at ASC LIMIT ? OFFSET ?", (limit, offset))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get pending events paginated error: {e}")
            return []

    def get_total_pending_events_count(self) -> int:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM events WHERE status = 'new' OR status = 'pending'")
            return self.__cur.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Get total pending events count error: {e}")
            return 0

    def search_all_events_by_keywords(self, keywords: List[str], limit: int = 20) -> List[Dict]:
        """Поиск по всем мероприятиям (включая неподтвержденные) для админа"""
        try:
            query = """
                SELECT * FROM events 
                WHERE (
                    1 = 0
            """
            params = []
            
            for keyword in keywords:
                query += " OR title LIKE ? OR description LIKE ?"
                param = f"%{keyword}%"
                params.extend([param, param])
            
            query += ") ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            self.__cur.execute(query, params)
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Search all events by keywords error: {e}")
            return []