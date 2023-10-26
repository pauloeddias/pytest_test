import asyncio
import openai
import json
import re
import os
import base64
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import openai
import warnings
import asyncio
from PyPDF2 import PdfReader
import io
import json

from .BasePostprocessor import BasePostprocessor
import os
import base64

class CustomGlobalPostprocessor(BasePostprocessor):
    def __init__(self, multi_docbytes, output_format):
        self.multi_docbytes = multi_docbytes
        self.output_format = output_format
        self.check_for_unsupported_file()

    async def call_azure(self,doc_bytes, model_name):
        if os.getenv("ENVIRONMENT") == "dev":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        base64_bytes = doc_bytes.encode("utf8")
        message_bytes = base64.b64decode(base64_bytes)

        azure_endpoint = os.environ["AZURE_ENDPOINT"]
        azure_key = os.environ["AZURE_KEY"]
        openai.api_key = os.environ["OPENAI_API_KEY"]

        # print("Sending to Azure...")
        document_analysis_client = DocumentAnalysisClient(
            endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key)
        )
        poller = document_analysis_client.begin_analyze_document(model_name, message_bytes)
        docs = poller.result()

        ret = {}
        for name, field in docs.documents[0].fields.items():
            field_value = field.value if field.value else field.content
            ret[name] = field_value
        file_type = docs.documents[0].doc_type.split(':')[-1]
        return ret

    def check_for_unsupported_file(self):
        pass

    def fetch_general_page(self, page):
        return self.call_azure(page, 'surelogix-dr-generalpage-customglobal-v1')

    def fetch_manifest_page(self, page):
        return self.call_azure(page, 'surelogix-dr-manifestpage-customglobal-v1')

    def parse_general_page(self, page):
        output = {}
        output["scac"] = 'OKOCUGL'
        output['carrier'] = page.get('carrier')
        output['mawb'] = page.get('mawb')
        return output

    def parse_manifest_page(self, page):
        output = {}
        output['hwb'] = page.get('hwb')
        output['ship_date'] = page.get('ship_date')
        output['delivery_date_time'] = page.get('delivery_date_time')
        output['shipper'] = page.get('shipper')
        output['consignee'] = page.get('consignee')
        output['DT'] = page.get('DT')
        output['OT'] = page.get('OT')
        output['pcs'] = page.get('pcs')
        output['wt'] = page.get('wt')
        output['dims'] = page.get('dims')
        output['description'] = page.get('description')
        output['SI'] = page.get('SI')
        output['PO'] = page.get('PO')

        if (
                output['ship_date']==None or
                output['delivery_date_time']==None or
                output['shipper']==None or
                output['consignee']==None or
                output['DT']==None or
                output['OT']==None or
                output['pcs']==None or
                output['wt']==None):
            return None


        return output

    def merge_pages(self, general_page, pages):
        for page in pages:
            page.update(general_page)

        return pages

    async def parse_output_format(self,shipment):
        shipper_prompt = self.get_shipper_prompt(shipment["shipper"])

        consignee_prompt = self.get_consignee_prompt(shipment["consignee"])

        delivery_date_prompt = self.get_delivery_date_and_time_prompt(shipment["delivery_date_time"], shipment["ship_date"])
        resps =await self.call_llm_multiple_prompts_async(
            [shipper_prompt, consignee_prompt, delivery_date_prompt]
        )
        shipper = json.loads(resps[0])
        consignee = json.loads(resps[1])
        delivery_date = json.loads(resps[2])

        output = {}
        output['hwb'] = shipment.get('hwb')
        output['ship_date'] = shipment.get('ship_date')
        output['delivery_date'] = delivery_date['delivery_date']
        output['delivery_time'] = delivery_date['delivery_time']
        output['shipper'] = shipper
        output['consignee'] = consignee
        output['DT'] = shipment.get('DT')
        output['OT'] = shipment.get('OT')
        dims = shipment.get('dims')
        if dims:
            dims = dims.split('DIMS:')[1].strip()
        output['SI'] = shipment.get('SI')
        output['PO'] = shipment.get('PO')

        regex = r'(\d+) @ (\d+) x (\d+) x (\d+)'
        matches = re.findall(regex, dims)
        pcs = []
        for match in matches:
            pcs.append({
                "dimensions": f"{match[1]} x {match[2]} x {match[3]}",
                "pieces": match[0],
                "weight":None,
                "description": shipment.get('description')
            })


        output["goods"] = {
            "net_weight": float(shipment.get('wt').replace(' ','')),
            "no_of_pieces": float(shipment.get('pcs').replace(' ','')),
            "pieces": pcs,
        }

        output['MA'] = shipment.get('mawb')
        output['BM'] = shipment.get('hwb')
        output['shipment_identifier'] = shipment.get('hwb')
        output['scac'] = 'OKOCUGL'
        output['handling'] = 'PUD'
        output['carrier'] = shipment.get('carrier')

        return output


    async def run(self):
        tasks = []
        general_page = self.multi_docbytes[0]
        tasks.append(asyncio.create_task(self.fetch_general_page(general_page)))
        manifest_pages = self.multi_docbytes[1:]

        for page in manifest_pages:
            tasks.append(asyncio.create_task(self.fetch_manifest_page(page)))

        results = await asyncio.gather(*tasks)
        # results = await asyncio.gather(*results)
        pages = []
        general_page = self.parse_general_page(results[0])
        for result in results[1:]:
            page = self.parse_manifest_page(result)
            if page:
                pages.append(page)
        pages = self.merge_pages(general_page,pages)

        tasks = []
        for page in pages:
            tasks.append(asyncio.create_task(self.parse_output_format(page)))
        results = await asyncio.gather(*tasks)
        return results, 'surelogix-da-customglobal-v1'

        # tasks = []
        # for prompt in prompts:
        #     tasks.append(asyncio.create_task(call_llm_async(prompt)))
        # resp = await asyncio.gather(*tasks)
        # return resp




