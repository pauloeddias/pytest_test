import os
import io
import base64
from PyPDF2 import PdfReader, PdfWriter
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import random
import string

class CustomGlobalPreprocessor:

    def __init__(self, event):
        self.doc_bytes = event.get('doc_bytes')

        base64_bytes = self.doc_bytes.encode("utf8")
        message_bytes = base64.b64decode(base64_bytes)
        self.base64_message = base64_bytes.decode("utf8")

        # self.tmp_dir = os.path.join(os.getcwd(), 'test_docs/tmp')
        self.tmp_dir = '/tmp'


    def run(self):
        buffer = base64.b64decode(self.base64_message)
        f = io.BytesIO(buffer)
        pdf = PdfReader(f)
        order_pages = []
        metadata = pdf.metadata['/CreationDate'].replace('D:', '').replace("'", '')
        metadata = ''.join(e for e in metadata if e.isalnum())
        ra = ''.join(random.choices(string.ascii_lowercase, k=10))
        metadata = metadata + ra

        #remove special characters from a string



        metadata = metadata.replace(' ', '_').replace(':', '_').replace('-', '_').replace('.', '_')

        for ind, x in enumerate(pdf.pages):
            pdf_writer = PdfWriter()

            pdf_writer.add_page(x)

            output_filename = f"{self.tmp_dir}/{metadata}_{ind}.pdf"

            with open(output_filename, "wb") as out:
                pdf_writer.write(out)
            with open(output_filename, "rb") as file:
                form = file.read()

            base64_bytes = base64.b64encode(form)
            base64_message = base64_bytes.decode("utf8")
            order_pages.append(base64_message)

            os.remove(output_filename)

        return order_pages
