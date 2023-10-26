# Postprocessing for Stevens DA, DR scac:TBD data extraction

import re
from datetime import datetime
from ._common import UnintendedFileException

from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import openai
import asyncio
import json

from .BasePostprocessor import BasePostprocessor
import os
import base64


def convert_dict_values_to_none(data: dict) -> dict:
    """fpo
    Recursively converts dictionary values to None.

    Args:
        data (dict): The dictionary to process.

    Returns:
        dict: The modified dictionary with values set to None.
    """
    if isinstance(data, dict):
        data_copy = data.copy()
        for key, value in data_copy.items():
            data_copy[key] = convert_dict_values_to_none(value)

    elif isinstance(data, list):
        data_copy = data.copy()
        tmp_list = []
        for item in data_copy:
            tmp_list.append(convert_dict_values_to_none(item))
        data_copy = tmp_list
    else:
        data_copy = None
    return data_copy


class StevensDaDrExecutor(BasePostprocessor):
    def __init__(self, input_data, output_format):
        self.model_name = 'surelogix-da-dr-stevens-v6'
        self.is_multiple = type(input_data) is list
        self.input_data = input_data
        self.base_output = convert_dict_values_to_none(output_format)

    async def call_azure(self, doc_bytes):
        base64_bytes = doc_bytes.encode("utf8")
        message_bytes = base64.b64decode(base64_bytes)

        azure_endpoint = os.environ["AZURE_ENDPOINT"]
        azure_key = os.environ["AZURE_KEY"]
        openai.api_key = os.environ["OPENAI_API_KEY"]

        document_analysis_client = DocumentAnalysisClient(
            endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key)
        )
        async with document_analysis_client:
            poller = await document_analysis_client.begin_analyze_document(self.model_name, message_bytes)
            docs = await poller.result()

        ret = {}
        for name, field in docs.documents[0].fields.items():
            field_value = field.value if field.value else field.content
            ret[name] = field_value
        self.check_for_unsupported_file(ret)
        return ret

    def process_document(self, event):
        return self.call_azure(event)

    def get_ship_cons_prompt(self, text):
        # print('parse_ship_cons_data')
        # print(text)

        prompt = f"""The following is the information of the shipper or consignee of a shipment. It contains the name of the shipper, its address and contact information.

                {text}

                """
        prompt += r"""
                From that, extract the following JSON:

                {
                    "name": "string. Placed before address data. Can contains 'code / company name'
                    Possible examples:: 'GALILEE LEARNING CENTER #2', 'SUR240Z / SURE LOGIX', 'PRO178 / PROJECT VISUAL INTERNATIONAL INC', 'CMCTS'",
                    "address": {
                        "street": "string. Examples: '123 Main St', '1625 GARY ST', '6310 CLIFT STREET'",
                        "city": "string",
                        "state": "string. The code of the state",
                        "postal_code": "string. Find postal code by city and street. Examples: '70506'. Only digits should be returned",
                        "country_code": "string. Default is 'US'"
                    },
                    "contact": {
                        "name": "string. Examples: 'HALEY FEINGOLD', 'SHIPPING', 'SHEPARD/TFORCE', 'TRE MOSELEY', 'DEB'. Default ''",
                        "tel": "string. Phone number. Might not exist. Default ''",
                        "fax": "string. Might not exist. Default ''"
                    },
                    "notes": "string. Might not exist. Default ''"
                }

                """
        # Do not invent information. If the information is not there, leave it as null, unless a default is specified. Do not use examples as default values.

        return prompt

    def convert_time(self, string):
        res = {
            "time": None,
            "meridien": None,
            "timezone": None
        }
        if string:
            match = re.search(r'\d{1,2}:\d{2}$', string)
            if match:
                string = match.group(0)

            time_obj = datetime.strptime(string, '%H:%M')
            res = {
                "time": time_obj.strftime('%H:%M'),
                "meridien": time_obj.strftime('%p'),
                "timezone": None
            }

        return res

    def check_for_unsupported_file(self, ret):
        if (
                ret.get("consignee") is None
                or ret.get("shipper") is None
                or ret.get("waybill") is None
                or ret.get("ot") is None
                or ret.get("dt") is None
        ):
            print('consignee', ret.get("consignee"))
            print('shipper', ret.get("shipper"))
            print('waybill', ret.get("waybill"))
            print('ot', ret.get("ot"))
            print('dt', ret.get("dt"))

            raise UnintendedFileException

    async def parse_output(self, ret):
        output_format = {**self.base_output}
        waybill = ret.get("waybill", "")
        if waybill:
            waybill = waybill.replace('*', '')
        output_format.update({
            'scac': 'CROWN',  # tmp, will be updated when will be provided
            'shipment_identifier': waybill,
            'payment_method': 'PP',
            'handling': 'PUD',
            'BM': waybill,
            'MA': ret.get("mawb", ""),
            'SI': ret.get("si", ""),
            'OT': ret.get('ot'),
            'DT': ret.get('dt'),

            'shipment_date': ret.get("ship_date", ""),
            'shipment_time': self.convert_time(ret.get('ship_time')),

            'ready_date': ret.get('ready_date'),
            'ready_time': self.convert_time(ret.get('ready_time')),

            'delivery_date': ret.get('delivery_date'),
            'delivery_time': self.convert_time(ret.get('delivery_time')),

            "goods": {
                "pieces": [{
                    "description": ret.get('goods_description', ''),
                    "dimensions": None,
                    "weight": ret.get('total_weight', ''),
                    "package_type": ret.get('pack_type', ''),
                    'pieces': None
                }],
                "net_weight": ret.get('total_weight'),
            },
        })

        no_of_pieces = ret.get('total_pcs')
        if no_of_pieces:
            no_of_pieces = ''.join(i for i in no_of_pieces if i.isdigit())
        output_format['goods'].update({
            'no_of_pieces': no_of_pieces
        })

        shipper_prompt = self.get_ship_cons_prompt(ret.get('shipper'))
        consignee_prompt = self.get_ship_cons_prompt(ret.get('consignee'))
        oai_res = await self.call_llm_multiple_prompts_async([shipper_prompt, consignee_prompt])
        shipper_parsed = json.loads(oai_res[0])
        consignee_parsed = json.loads(oai_res[1])
        output_format.update({
            'shipper': shipper_parsed,
            'consignee': consignee_parsed
        })

        if output_format['shipment_date']:
            output_format['shipment_date'] = output_format['shipment_date'].replace('-', '/')

        if output_format['delivery_date']:
            output_format['delivery_date'] = output_format['delivery_date'].replace('-', '/')

        if output_format['ready_date']:
            output_format['ready_date'] = output_format['ready_date'].replace('-', '/')

        return output_format

    async def run(self):
        if self.is_multiple:
            tasks = []
            for doc_bytes in self.input_data:
                tasks.append(asyncio.create_task(self.process_document(doc_bytes)))
            processed_results = await asyncio.gather(*tasks)
            parse_tasks = []
            for p_res in processed_results:
                parse_tasks.append(asyncio.create_task(self.parse_output(p_res)))
            results = await asyncio.gather(*parse_tasks)
            return results, self.model_name
        else:
            self.check_for_unsupported_file(self.input_data)
            result = await self.parse_output(self.input_data)
            return result

