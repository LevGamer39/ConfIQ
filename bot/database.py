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
            with open('sq_db.sql', 'r', encoding='utf-8') as f:
                sql_script = f.read()
            self.__cur.executescript(sql_script)
            self.__db.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")

    def add_user(self, telegram_id: int, username: str, full_name: str = None) -> bool:
        try:
            self.__cur.execute("INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)", 
                               (telegram_id, username, full_name))
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
                columns = [col[0] for col in self.__cur.description]
                return dict(zip(columns, res))
            return None
        except sqlite3.Error as e:
            print(f"Get user error: {e}")
            return None

    def log_user_activity(self, user_id: int, action: str, details: str = None):
        try:
            self.__cur.execute("INSERT INTO user_activity (user_id, action, details) VALUES (?, ?, ?)", 
                              (user_id, action, details))
            self.__db.commit()
        except sqlite3.Error as e:
            print(f"Log user activity error: {e}")

    def add_user_event(self, user_id: int, event_id: int) -> bool:
        try:
            self.__cur.execute("INSERT OR IGNORE INTO user_events (user_id, event_id) VALUES (?, ?)", 
                               (user_id, event_id))
            self.__db.commit()
            
            user = self.get_user_by_id(user_id)
            if user:
                self.log_user_activity(user_id, "event_registration", f"Registered for event {event_id}")
            
            return True
        except sqlite3.Error as e:
            print(f"Add user event error: {e}")
            return False

    def get_user_by_id(self, user_id: int) -> Union[Dict, None]:
        try:
            self.__cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            res = self.__cur.fetchone()
            if res:
                columns = [col[0] for col in self.__cur.description]
                return dict(zip(columns, res))
            return None
        except sqlite3.Error as e:
            print(f"Get user by id error: {e}")
            return None

    def get_user_events(self, user_id: int) -> List[Dict]:
        try:
            self.__cur.execute("""
                SELECT e.*, ue.registration_date, ue.status 
                FROM events e
                JOIN user_events ue ON e.id = ue.event_id
                WHERE ue.user_id = ? AND e.status = 'approved'
                ORDER BY ue.registration_date DESC
            """, (user_id,))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get user events error: {e}")
            return []

    def get_user_stats(self, user_id: int) -> Dict:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM user_events WHERE user_id = ?", (user_id,))
            total_events = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT COUNT(*) FROM user_events ue
                JOIN events e ON ue.event_id = e.id
                WHERE ue.user_id = ? AND e.priority = 'high'
            """, (user_id,))
            high_priority = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT COUNT(DISTINCT DATE(registration_date)) 
                FROM user_events 
                WHERE user_id = ? AND registration_date >= date('now', '-30 days')
            """, (user_id,))
            active_days = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT COUNT(*) FROM user_activity 
                WHERE user_id = ? AND performed_at >= date('now', '-7 days')
            """, (user_id,))
            weekly_activity = self.__cur.fetchone()[0]
            
            return {
                'total_events': total_events,
                'high_priority': high_priority,
                'active_days_30': active_days,
                'weekly_activity': weekly_activity
            }
        except sqlite3.Error as e:
            print(f"Get user stats error: {e}")
            return {'total_events': 0, 'high_priority': 0, 'active_days_30': 0, 'weekly_activity': 0}

    def get_all_users_stats(self) -> Dict:
        try:
            self.__cur.execute("SELECT COUNT(*) FROM users")
            total_users = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(*) FROM user_events")
            total_registrations = self.__cur.fetchone()[0]
            
            self.__cur.execute("SELECT COUNT(DISTINCT user_id) FROM user_events")
            active_users = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_active >= date('now', '-7 days')
            """)
            weekly_active_users = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT COUNT(*) FROM user_events 
                WHERE registration_date >= date('now', '-7 days')
            """)
            weekly_registrations = self.__cur.fetchone()[0]
            
            self.__cur.execute("""
                SELECT department, COUNT(*) as count 
                FROM users 
                WHERE department IS NOT NULL 
                GROUP BY department
            """)
            departments = dict(self.__cur.fetchall())
            
            return {
                'total_users': total_users,
                'total_registrations': total_registrations,
                'active_users': active_users,
                'weekly_active_users': weekly_active_users,
                'weekly_registrations': weekly_registrations,
                'departments': departments
            }
        except sqlite3.Error as e:
            print(f"Get all users stats error: {e}")
            return {'total_users': 0, 'total_registrations': 0, 'active_users': 0, 'weekly_active_users': 0, 'weekly_registrations': 0, 'departments': {}}

    def update_user_activity(self, telegram_id: int):
        try:
            self.__cur.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))
            self.__db.commit()
        except sqlite3.Error as e:
            print(f"Update user activity error: {e}")

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

            self.__cur.execute("SELECT COUNT(*) FROM events WHERE priority = 'high' AND status = 'approved'")
            stats['high_priority'] = self.__cur.fetchone()[0]
            
            user_stats = self.get_all_users_stats()
            stats.update(user_stats)
            
        except sqlite3.Error as e:
            print(f"Get stats error: {e}")
        return stats

    def add_event(self, title, description, date_str, location, url, ai_analysis, score, is_it_related, source, status='pending', priority='medium', participants=0, registration_info='', payment_info='', conditions=''):
        try:
            if url not in ["invite", "file_upload"] and url.startswith("http"):
                self.__cur.execute("SELECT id FROM events WHERE url = ?", (url,))
                if self.__cur.fetchone():
                    return False

            self.__cur.execute('''
                INSERT INTO events (title, description, date_str, location, url, ai_analysis, score, is_it_related, source, status, priority, participants, registration_info, payment_info, conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, date_str, location, url, ai_analysis, score, is_it_related, source, status, priority, participants, registration_info, payment_info, conditions))
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
            self.__cur.execute("SELECT * FROM events WHERE status = 'approved' ORDER BY priority DESC, score DESC, created_at DESC LIMIT ?", (limit,))
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
                ORDER BY priority DESC, score DESC 
                LIMIT ?
            '''
            
            self.__cur.execute(sql, query_params)
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Search events by keywords error: {e}")
            return []

    def search_events_by_criteria(self, criteria: dict, limit: int = 20) -> List[Dict]:
        try:
            query_parts = []
            query_params = []
            
            theme_mapping = {
                'ai': ['искусственный интеллект', 'AI', 'нейросеть', 'машинное обучение', 'ML'],
                'data_science': ['data science', 'анализ данных', 'машинное обучение', 'ML', 'аналитика'],
                'development': ['разработка', 'программирование', 'код', 'IT', 'технологии', 'dev'],
                'management': ['менеджмент', 'управление', 'проекты', 'agile', 'scrum', 'руководство'],
                'security': ['кибербезопасность', 'безопасность', 'security', 'защита'],
                'cloud': ['облачные технологии', 'cloud', 'облако', 'микросервисы']
            }
            
            location_mapping = {
                'spb': ['СПб', 'Санкт-Петербург', 'Петербург', 'spb'],
                'msk': ['Москва', 'МСК', 'msk'],
                'online': ['онлайн', 'online', 'вебинар', 'zoom', 'teams']
            }
            
            if 'theme' in criteria and criteria['theme']:
                theme_conditions = []
                for theme in criteria['theme']:
                    if theme in theme_mapping:
                        for keyword in theme_mapping[theme]:
                            theme_conditions.append("(title LIKE ? OR description LIKE ? OR ai_analysis LIKE ?)")
                            query_params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
                if theme_conditions:
                    query_parts.append(f"({' OR '.join(theme_conditions)})")
            
            if 'location' in criteria and criteria['location']:
                location_conditions = []
                for location in criteria['location']:
                    if location in location_mapping:
                        for keyword in location_mapping[location]:
                            location_conditions.append("(location LIKE ? OR description LIKE ? OR ai_analysis LIKE ?)")
                            query_params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
                if location_conditions:
                    query_parts.append(f"({' OR '.join(location_conditions)})")
            
            if 'date' in criteria and criteria['date']:
                date_conditions = []
                current_date = datetime.now()
                
                for date_period in criteria['date']:
                    if date_period == 'week':
                        target_date = current_date + timedelta(days=7)
                        date_conditions.append("(date_str LIKE ? OR date_str LIKE ?)")
                        query_params.extend([f'%{current_date.strftime("%d.%m")}%', f'%{target_date.strftime("%d.%m")}%'])
                    elif date_period == 'month':
                        date_conditions.append("(date_str LIKE ? OR date_str LIKE ? OR date_str LIKE ?)")
                        query_params.extend([f'%март%', f'%апрель%', f'%май%'])
                    elif date_period == 'quarter':
                        date_conditions.append("(date_str LIKE ? OR date_str LIKE ? OR date_str LIKE ? OR date_str LIKE ?)")
                        query_params.extend([f'%2025%', f'%июнь%', f'%июль%', f'%август%'])
                
                if date_conditions:
                    query_parts.append(f"({' OR '.join(date_conditions)})")
            
            if 'audience' in criteria and criteria['audience']:
                audience_mapping = {
                    'developers': ['разработчик', 'программист', 'developer', 'engineer'],
                    'managers': ['руководитель', 'менеджер', 'manager', 'lead'],
                    'analysts': ['аналитик', 'analyst', 'data scientist'],
                    'researchers': ['исследователь', 'research', 'scientist']
                }
                
                audience_conditions = []
                for audience in criteria['audience']:
                    if audience in audience_mapping:
                        for keyword in audience_mapping[audience]:
                            audience_conditions.append("(description LIKE ? OR ai_analysis LIKE ?)")
                            query_params.extend([f'%{keyword}%', f'%{keyword}%'])
                if audience_conditions:
                    query_parts.append(f"({' OR '.join(audience_conditions)})")
            
            if not query_parts:
                return self.get_approved_events(limit)
            
            where_clause = " AND ".join(query_parts)
            query_params.append(limit)
            
            sql = f'''
                SELECT * FROM events 
                WHERE {where_clause} 
                AND status = 'approved' 
                ORDER BY priority DESC, score DESC 
                LIMIT ?
            '''
            
            self.__cur.execute(sql, query_params)
            return self._dict_factory(self.__cur.fetchall())
            
        except sqlite3.Error as e:
            print(f"Search events by criteria error: {e}")
            return []

    def get_events_paginated(self, page: int = 0, limit: int = 5) -> List[Dict]:
        try:
            offset = page * limit
            self.__cur.execute("SELECT * FROM events WHERE status = 'approved' ORDER BY priority DESC, score DESC, created_at DESC LIMIT ? OFFSET ?", (limit, offset))
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

    def get_high_priority_events(self, limit: int = 10) -> List[Dict]:
        try:
            self.__cur.execute("SELECT * FROM events WHERE priority = 'high' AND status = 'approved' ORDER BY score DESC LIMIT ?", (limit,))
            return self._dict_factory(self.__cur.fetchall())
        except sqlite3.Error as e:
            print(f"Get high priority events error: {e}")
            return []

    def _dict_factory(self, rows):
        if not rows or rows[0] is None:
            return []
        columns = [col[0] for col in self.__cur.description]
        return [dict(zip(columns, row)) for row in rows]