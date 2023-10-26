import os
import io
import base64
from PyPDF2 import PdfReader, PdfWriter
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential


IS_LOCAL = eval(os.getenv('IS_LOCAL', 'False'))


class SplitLarsonBase64:

    def __init__(self, event):
        self.doc_bytes = event.get('doc_bytes')

        base64_bytes = self.doc_bytes.encode("utf8")
        message_bytes = base64.b64decode(base64_bytes)
        self.base64_message = base64_bytes.decode("utf8")

        # For development need to place split files to test directory
        if IS_LOCAL:
            self.tmp_dir = os.path.join(os.getcwd(), 'test_docs/tmp')
        else:
            self.tmp_dir = '/tmp'

        # Extract data with Asure
        model_name = "prebuilt-document"
        document_analysis_client = DocumentAnalysisClient(
            endpoint=os.environ["AZURE_ENDPOINT"],
            credential=AzureKeyCredential(os.environ["AZURE_KEY"]),
        )
        poller = document_analysis_client.begin_analyze_document(model_name, message_bytes)
        self.docs = poller.result()

    def run(self):
        buffer = base64.b64decode(self.base64_message)
        f = io.BytesIO(buffer)
        pdf = PdfReader(f)
        b64 = []
        order_pages = {}
        for i in self.docs.key_value_pairs:
            if 'BOL/RMA' in i.key.content:
                order_id = i.value.content if i.value else None
                if order_id:
                    if order_id not in order_pages.keys():
                        order_pages.update({order_id: []})
                    order_pages[order_id].extend([region.page_number for region in i.key.bounding_regions])

        for k, v in order_pages.items():
            pdf_writer = PdfWriter()

            for page_num in v:
                pdf_writer.add_page(pdf.pages[page_num-1])

            output_filename = f"{self.tmp_dir}/order_{k}.pdf"

            with open(output_filename, "wb") as out:
                pdf_writer.write(out)
            with open(output_filename, "rb") as file:
                form = file.read()

            base64_bytes = base64.b64encode(form)
            base64_message = base64_bytes.decode("utf8")
            b64.append(base64_message)

            if not IS_LOCAL:
                # delete the file output_filename
                os.remove(output_filename)

        return b64
