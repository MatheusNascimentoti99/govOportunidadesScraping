import re
import scrapy
import pdfplumber
import io
from govoportunidades.items import EditalExtractor

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
                            links.add(response.urljoin(match.group(1)))
        
        yield from response.follow_all(links, self.parse_edital)

    def parse_edital(self, response):
        # retrieve all links in the first occurrence div.br-list
        edital_link = response.css("div.br-list a::attr(href)").get()

        if edital_link:
            yield response.follow(edital_link, callback=self.parse_pdf, cb_kwargs=dict(main_url=response.url))

    def parse_pdf(self, response, main_url):
        # Check and get the PDF response
        content_type = response.headers.get('Content-Type', b'').decode().lower()
        if 'pdf' not in content_type:
            self.logger.warning(f"Not a PDF! Got {content_type} from {response.url}")
            self.logger.debug(response.text[:500])  # show the start of the response
            return

        # Download and extract text from the PDF
        with pdfplumber.open(io.BytesIO(response.body)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

            if not text.strip():
                self.logger.warning(f"No text extracted from PDF at {response.url}")
                return
            # Yield the extracted text as an item
            yield EditalExtractor(url=main_url, text=text)
