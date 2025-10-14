from pathlib import Path

import scrapy

class EditalSpider(scrapy.Spider):
    name = "edital"
    allowed_domains = ["oportunidades.sigepe.gov.br"]
    start_urls = ["https://oportunidades.sigepe.gov.br/oportunidades-portal/api/html/"]

    def parse(self, response):
        page = response.url.split("/")[-2]
        filename = f"quotes-{page}.html"
        Path(filename).write_bytes(response.body)
        self.log(f"Saved file {filename}")
