# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class EditalItem(scrapy.Item):
    # Link extraído da página
    url = scrapy.Field()

class EditalExtractor(scrapy.Item):
    url = scrapy.Field()
    text = scrapy.Field()
