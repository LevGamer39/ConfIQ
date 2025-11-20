from datetime import datetime, timedelta
import re
from typing import List, Dict

class IcsGenerator:
    @staticmethod
    def _parse_russian_date(date_str):
        months = {
            'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
            'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
        }
        
        try:
            current_year = datetime.now().year
            date_str = date_str.lower()
            
            day_match = re.search(r'\d{1,2}', date_str)
            if not day_match:
                return datetime.now() + timedelta(days=1)
                
            day = int(day_match.group(0))
            
            month = datetime.now().month
            for m_name, m_num in months.items():
                if m_name in date_str:
                    month = m_num
                    break
            
            event_date = datetime(current_year, month, day, 10, 0)
            
            if event_date < datetime.now():
                event_date = event_date.replace(year=current_year + 1)
                
            return event_date
        except:
            return datetime.now() + timedelta(days=1)

    @staticmethod
    def _create_vevent(event: Dict, now_str: str) -> str:
        date_for_parsing = event.get('event_datetime') or event.get('date_str', 'не указана')
        
        try:
            dt_start = datetime.strptime(date_for_parsing, '%Y-%m-%d %H:%M:%S')
        except:
            dt_start = IcsGenerator._parse_russian_date(event.get('date_str', ''))

        dt_end = dt_start + timedelta(hours=2)
        
        dt_format = "%Y%m%dT%H%M%S"
        start_str = dt_start.strftime(dt_format)
        end_str = dt_end.strftime(dt_format)
        
        clean_desc = event.get('description', 'Подробности по ссылке.').replace('\n', '\\n')
        
        vevent = (
            "BEGIN:VEVENT\n"
            f"DTSTAMP:{now_str}\n"
            f"UID:{event['id']}-{abs(hash(event['title']+event['location']))}\n"
            f"DTSTART:{start_str}\n"
            f"DTEND:{end_str}\n"
            f"SUMMARY:{event['title']}\n"
            f"DESCRIPTION:{clean_desc}\n"
            f"LOCATION:{event['location']}\n"
            "END:VEVENT\n"
        )
        return vevent
        
    @staticmethod
    def generate_ics(title, description, location, date_str):
        event = {
            'id': abs(hash(title)),
            'title': title,
            'description': description,
            'location': location,
            'date_str': date_str,
        }
        
        now_str = datetime.now().strftime("%Y%m%dT%H%M%S")
        vevent = IcsGenerator._create_vevent(event, now_str)
        
        ics_content = (
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//Sber AI Media Agent//RU\n"
            "CALSCALE:GREGORIAN\n"
            f"{vevent}"
            "END:VCALENDAR\n"
        )
        return ics_content

    @staticmethod
    def generate_bulk_ics(events: List[Dict]) -> str:
        now_str = datetime.now().strftime("%Y%m%dT%H%M%S")
        vevents = [IcsGenerator._create_vevent(event, now_str) for event in events]
        
        ics_content = (
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//Sber AI Media Agent//RU\n"
            "CALSCALE:GREGORIAN\n"
            f"{''.join(vevents)}"
            "END:VCALENDAR\n"
        )
        return ics_content