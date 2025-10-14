import re
import scrapy
from urllib.parse import urlparse

from govoportunidades.items import EditalItem

class EditalSpider(scrapy.Spider):
    name = "edital"
    allowed_domains = ["oportunidades.sigepe.gov.br"]
    start_urls = ["https://oportunidades.sigepe.gov.br/oportunidades-portal/api/html/"]


    def parse(self, response):
        # Extrai todos os onclicks de tags <a>
        actions = response.css('a.text-blue-warm-vivid-80::attr(onclick)').getall()

        # Normaliza para URLs absolutas e filtra valores vazios/anchors/javascript
        links = set()
        for action in actions:
                if action and "window.open" in action:
                    # Extract the ID from "window.open(this.href+ID,'popup','width=800,height=600');return false;"
                    for match in [re.search(r"this\.href\+(\w+)", action)]:
                        if match:
                            yield EditalItem(url=response.urljoin(match.group(1)))
