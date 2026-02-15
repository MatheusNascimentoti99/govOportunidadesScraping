# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.mail import MailSender
try:
    import pymongo  # type: ignore
except Exception:  # pragma: no cover - pymongo é opcional
    pymongo = None
import json
import sqlite3
from datetime import datetime, timezone

import requests
from scrapy.exceptions import DropItem


class MongoDBPipeline:
    collection_name = "scrapy_items"

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_db=crawler.settings.get("MONGO_DATABASE", "items"),
        )

    def open_spider(self, spider):
        if pymongo is None:
            spider.logger.error("MongoDBPipeline: pymongo não está instalado. Desabilite este pipeline ou instale pymongo.")
            # Evita quebrar o crawl: inicializa db/client como None
            self.client = None
            self.db = None
            return
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        if getattr(self, 'client', None):
            self.client.close()

    def process_item(self, item, spider):
        if getattr(self, 'db', None):
            self.db[self.collection_name].insert_one(ItemAdapter(item).asdict())
        return item

class SQLitePipeline:
    table_name = "matching_editais"

    def __init__(self, db_path: str, keywords: list[str]):
        self.db_path = db_path
        # Normaliza palavras-chave (minúsculas, sem espaços) e remove vazias
        self.keywords = [kw.strip().lower() for kw in keywords if kw and kw.strip()]
        self.conn: sqlite3.Connection | None = None

    @classmethod
    def from_crawler(cls, crawler):
        db_path = crawler.settings.get("EDITAIS_DB_PATH", "editais.db")
        keywords = crawler.settings.getlist("KEY_WORDS") or crawler.settings.get("KEY_WORDS", [])
        # Em alguns setups KEY_WORDS pode vir como string separada por vírgula
        if isinstance(keywords, str):
            keywords = [s.strip() for s in keywords.split(",")]
        return cls(db_path=db_path, keywords=keywords)

    def open_spider(self, spider):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                text TEXT,
                matched_keywords TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    def close_spider(self, spider):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def _match_keywords(self, text: str) -> list[str]:
        if not self.keywords:
            return []
        text_l = (text or "").lower()
        return [kw for kw in self.keywords if kw and kw in text_l]

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        text = adapter.get("text")
        url = adapter.get("url")
        if not text or not url:
            return item

        matched = self._match_keywords(text)
        # Anexa a informação ao item para consumo por outros pipelines, se desejado
        if matched:
            adapter["matched_keywords"] = matched
            if self.conn:
                try:
                    self.conn.execute(
                        f"INSERT OR IGNORE INTO {self.table_name} (url, text, matched_keywords, created_at) VALUES (?, ?, ?, ?)",
                        (
                            url,
                            text,
                            ", ".join(matched),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    self.conn.commit()
                except sqlite3.Error as e:
                    spider.logger.error(f"SQLitePipeline: erro ao inserir {url}: {e}")
        return item


class NotificationPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        mailer = MailSender.from_crawler(crawler)
        mail_to = crawler.settings.getlist("MAIL_TO") or crawler.settings.get("MAIL_TO", [])
        if isinstance(mail_to, str):
            mail_to = [s.strip() for s in mail_to.split(",") if s.strip()]
        key_words = crawler.settings.getlist("KEY_WORDS") or crawler.settings.get("KEY_WORDS", [])
        if isinstance(key_words, str):
            key_words = [s.strip() for s in key_words.split(",") if s.strip()]
        return cls(mailer=mailer, mail_to=mail_to, key_words=key_words)

    def __init__(self, mailer, mail_to: list[str], key_words: list[str]):
        self.mailer = mailer
        self.mail_to = mail_to
        self.key_words = key_words

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        text = (adapter.get("text") or "")
        # Calcula as palavras do .env (KEY_WORDS) que realmente aparecem no texto
        text_l = text.lower()
        matched = [kw for kw in self.key_words if kw and kw.lower() in text_l]
        if not matched:
            return item
        if not self.mail_to:
            spider.logger.warning("NotificationPipeline: MAIL_TO vazio; pulando envio de email.")
            return item

        # Anexa ao item para consumo adiante (e possível export)
        adapter["matched_keywords"] = matched

        url = adapter.get("url") or ""
        text = adapter.get("text") or ""
        summary = adapter.get("summary") or ""
        subject = "Gov Oportunidades: Edital encontrado"

        if summary:
            body = (
                "Encontramos uma nova oportunidade que corresponde às palavras-chave: "
                + ", ".join(matched)
                + "\n\n"
                + summary
                + "\n\n"
                + f"Link: {url}\n"
            )
        else:
            body = (
                "Encontramos uma nova oportunidade que corresponde às palavras-chave: "
                + ", ".join(matched)
                + "\n\nDetalhes:\n"
                + f"Link: {url}\n\n"
                + "Texto inicial:\n"
                + text[:500]
                + "\n"
            )
        try:
            self.mailer.send(to=self.mail_to, subject=subject, body=body)
        except Exception as e:
            spider.logger.error(f"NotificationPipeline: falha ao enviar email: {e}")
        return item


class NotificationDedupPipeline:
    """
    Descarta itens já notificados (URL já presente em matching_editais no SQLite).
    Coloque este pipeline antes do SQLitePipeline e NotificationPipeline.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    @classmethod
    def from_crawler(cls, crawler):
        db_path = crawler.settings.get("EDITAIS_DB_PATH", "editais.db")
        return cls(db_path=db_path)

    def open_spider(self, spider):
        self.conn = sqlite3.connect(self.db_path)
        # Garante a tabela, caso a ordem de pipelines varie
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS matching_editais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                text TEXT,
                matched_keywords TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    def close_spider(self, spider):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url")
        if not url or not self.conn:
            return item
        try:
            cur = self.conn.execute("SELECT 1 FROM matching_editais WHERE url = ? LIMIT 1", (url,))
            if cur.fetchone() is not None:
                raise DropItem(f"Item já notificado anteriormente: {url}")
        except sqlite3.Error as e:
            spider.logger.error(f"NotificationDedupPipeline: falha ao consultar DB: {e}")
        return item


class OpenRouterResumePipeline:
    """Chama a API do OpenRouter para resumir o texto do edital em português.

    Insere o resumo no campo ``summary`` do item para que o
    ``NotificationPipeline`` possa incluí-lo no corpo do e-mail.
    Funciona apenas para itens que já possuem ``matched_keywords``.
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str, max_text_length: int):
        self.api_key = api_key
        self.model = model
        self.max_text_length = max_text_length

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            api_key=crawler.settings.get("OPENROUTER_API_KEY", ""),
            model=crawler.settings.get("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free"),
            max_text_length=crawler.settings.getint("OPENROUTER_MAX_TEXT_LENGTH", 4000),
        )

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Só resume itens que tiverem keywords correspondentes
        if not adapter.get("matched_keywords"):
            return item

        if not self.api_key:
            spider.logger.warning(
                "OpenRouterResumePipeline: OPENROUTER_API_KEY não configurada; "
                "pulando resumo."
            )
            return item

        text = (adapter.get("text") or "")[:self.max_text_length]
        if not text.strip():
            return item

        try:
            summary = self._summarize(text)
            adapter["summary"] = summary
            spider.logger.info(
                f"OpenRouterResumePipeline: resumo gerado ({len(summary)} chars) "
                f"para {adapter.get('url')}"
            )
        except Exception as e:
            spider.logger.error(
                f"OpenRouterResumePipeline: falha ao resumir edital: {e}"
            )

        return item

    def _summarize(self, text: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente especializado resumo de textos de oportunidades de vagas"
                        "do governo brasileiro. Resuma o texto do edital de forma "
                        "clara e objetiva em português, destacando: objeto da "
                        "oportunidade, local, data de abertura, data de fechamento, "
                        "das propostas, e requisitos principais. Máximo 300 palavras."
                        "O texto deve ser formatado para e-mail."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Resuma o seguinte edital:\n\n{text}",
                },
            ],
        }
        response = requests.post(
            self.OPENROUTER_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
