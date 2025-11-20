from ics import Calendar, Event
from datetime import datetime, timedelta
import os
import uuid

class CalendarService:
    def generate_ics(self, event_data: dict) -> str:
        try:
            calendar = Calendar()
            event = Event()
            
            event.uid = f"sber-media-{uuid.uuid4()}@sber.ru"
            event.name = f"[SberMedia] {event_data['title']}"
            
            description = f"{event_data.get('description', '')}\n\n"
            if 'ai_analysis' in event_data:
                analysis = event_data['ai_analysis']
                if isinstance(analysis, str):
                    try:
                        analysis = eval(analysis) if 'summary' in analysis else {}
                    except:
                        analysis = {}
                description += f"AI анализ: {analysis.get('summary', '')}\n"
                description += f"Целевая аудитория: {analysis.get('target_audience', '')}\n"
                description += f"Оценка релевантности: {analysis.get('score', 0)}/100"
            
            event.description = description
            event.location = event_data.get('location', 'Санкт-Петербург')
            event.begin = datetime.now() + timedelta(days=1)
            event.end = event.begin + timedelta(hours=2)
            
            if event_data.get('url') and event_data['url'] not in ['invite', 'file_upload']:
                event.url = event_data['url']
            
            event.categories = ["IT", "SberMedia", "Мероприятие"]
            
            calendar.events.add(event)
            
            os.makedirs('temp', exist_ok=True)
            
            filename = f"temp/event_{event_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ics"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(calendar.serialize())
            
            return filename
            
        except Exception as e:
            print(f"Calendar generation error: {e}")
            backup_filename = f"temp/event_backup_{datetime.now().timestamp()}.ics"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write("BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR")
            return backup_filename

    def cleanup_file(self, filename: str):
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print(f"File cleanup error: {e}")