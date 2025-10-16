# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.mail import MailSender
import pymongo
import os


class MongoPipeline:
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
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[self.collection_name].insert_one(ItemAdapter(item).asdict())
        return item

class NotificationPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mailer=MailSender.from_crawler(crawler)
        )

    def __init__(self, mailer):
        self.mailer = mailer

    def process_item(self, item, spider):
        # Send a notification for the scraped item
        self.mailer.send(
            to=[os.getenv('SCRAPY_SEND_TO')],
            subject="Gov Oportunidades: Edital encontrado",
            body=(
            f"Encontramos uma nova oportunidade que corresponde às palavras-chave {os.getenv('SCRAPY_KEY_WORDS')}.\n\n"
            "Detalhes:\n"
            f"Link: {ItemAdapter(item).get('url')}\n\n"
            )
        )
        return item
    