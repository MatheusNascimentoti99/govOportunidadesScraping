import re
import io
import scrapy
import pdfplumber
from govoportunidades.items import EditalExtractor

class EditalSpider(scrapy.Spider):
    name = "edital"
    allowed_domains = ["oportunidades.sigepe.gov.br"]
    start_urls = ["https://oportunidades.sigepe.gov.br/oportunidades-portal/api/html/"]

    def parse(self, response):
        
        # Extrai todos os onclicks de tags <a> que estão dentro de um ancestral com um span "Encerra em:"
        actions = set()
        for a in response.xpath('//a'):
            # pega os três primeiros ancestrais
            ancestors = a.xpath('ancestor::*[position() <= 3]')
            
            # verifica se algum ancestral tem um span com o texto
            if ancestors.xpath('.//span[contains(., "Encerra em:")]'):
                for match in [re.search(r"this\.href\+(\w+)", a.xpath('@onclick').get())]:
                        if match:
                            actions.add(response.urljoin(match.group(1)))

        yield from response.follow_all(actions, self.parse_edital)

    def parse_edital(self, response):
        # retrieve all links in the first occurrence div.br-list
        edital_link = response.css("div.br-list a::attr(href)").get()

        if not edital_link:
            return

        pdf_url = response.urljoin(edital_link)

        yield response.follow(pdf_url, callback=self.parse_pdf, cb_kwargs=dict(main_url=response.url))

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

        if self.settings.get("KEY_WORDS") and not any(keyword.lower() in text.lower() for keyword in self.settings.get("KEY_WORDS")):
            return
        # Yield o conteúdo extraído
        yield EditalExtractor(url=main_url, text=text)
