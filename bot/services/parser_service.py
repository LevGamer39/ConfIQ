import requests
import re
from bs4 import BeautifulSoup
import time
import logging

logger = logging.getLogger(__name__)

class ParserService:
    def __init__(self):
        self.sources = [
            {
                "name": "IT Event Hub",
                "url": "https://it-event-hub.ru/",
                "heuristic": True 
            },
            {
                "name": "SPb Prompt",
                "url": "https://spbprompt.ru/",
                "heuristic": True
            },
            {
                "name": "All Events",
                "url": "https://all-events.ru/events/calendar/city-is-sankt-peterburg/theme-is-informatsionnye_tekhnologii/",
                "heuristic": True
            }
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache'
        }

    def _get_soup(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                if response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding
                return BeautifulSoup(response.text, 'html.parser')
            else:
                logger.error(f"Статус {response.status_code} для {url}")
        except Exception as e:
            logger.error(f"Ошибка доступа к {url}: {e}")
        return None

    def _clean_text(self, text):
        if not text:
            return ""
        return " ".join(text.split())

    def _contains_date(self, text):
        patterns = [
            r'\d{1,2}\.\d{2}', 
            r'\d{1,2}\s+(янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
            r'сегодня|завтра'
        ]
        text_lower = text.lower()
        for pat in patterns:
            if re.search(pat, text_lower):
                return True
        return False

    def _is_valid_block(self, title, text, link):
        if not title or len(title) < 5: return False
        if not link or link == '#' or 'javascript' in link: return False
        if len(text) > 1000: return False
        
        bad_words = ['политика', 'cookie', 'войти', 'регистрация', 'все права', 'календарь', 'архив']
        if any(w in title.lower() for w in bad_words):
            return False
            
        return True

    def _heuristic_parse(self, soup, base_url):
        events = []
        seen_links = set()

        potential_blocks = soup.find_all(['div', 'article', 'li', 'a'])
        
        for block in potential_blocks:
            if block.find_parent(['nav', 'footer', 'header']):
                continue
                
            title_elem = block.find(['h2', 'h3', 'h4', 'h5', 'div', 'a'], class_=re.compile(r'title|name|header', re.I))
            
            link_elem = block.find('a', href=True)
            if not link_elem: 
                if block.name == 'a' and block.has_attr('href'):
                    link_elem = block
                else:
                    continue

            if title_elem:
                title = self._clean_text(title_elem.get_text())
            else:
                title = self._clean_text(link_elem.get_text())

            link = link_elem['href']
            if link.startswith('/'):
                from urllib.parse import urljoin
                link = urljoin(base_url, link)
            elif not link.startswith('http'):
                continue

            full_text = self._clean_text(block.get_text())

            if link not in seen_links and self._is_valid_block(title, full_text, link):
                has_date = self._contains_date(full_text)
                is_event_context = any(w in full_text.lower() for w in ['место', 'спикер', 'регистрац', 'участие', 'бесплатно', 'руб'])
                
                if has_date or is_event_context:
                    date_match = re.search(r'(\d{1,2}\s+[а-яА-Я]{3,})|(\d{2}\.\d{2})', full_text)
                    date_str = date_match.group(0) if date_match else "См. на сайте"
                    
                    events.append({
                        "text": f"{title}. Дата: {date_str}. Источник: {base_url}",
                        "url": link,
                        "source": "parser"
                    })
                    seen_links.add(link)

        return events[:15]

    def get_events(self):
        all_events = []
        print("🔄 Запуск умного эвристического парсера...")
        
        for source in self.sources:
            try:
                soup = self._get_soup(source['url'])
                if soup:
                    events = self._heuristic_parse(soup, source['url'])
                    
                    if events:
                        print(f"✅ {source['name']}: найдено {len(events)}")
                        all_events.extend(events)
                    else:
                        print(f"⚠️ {source['name']}: пусто (возможно, сложная структура)")
                else:
                    print(f"❌ {source['name']}: нет ответа")
            
            except Exception as e:
                print(f"❌ Ошибка обработки {source['name']}: {e}")
            
            time.sleep(1) 
            
        print(f"📊 Всего собрано потенциальных событий: {len(all_events)}")
        return all_events