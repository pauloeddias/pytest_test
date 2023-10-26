# Postprocessing for LARSON scac:OKOLAR data extraction

from ._common import UnintendedFileException

from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import openai
import asyncio
import json

from .BasePostprocessor import BasePostprocessor
import os
import base64
from datetime import datetime


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


class LarsonExecutor(BasePostprocessor):
    def __init__(self, multi_docbytes, output_format):
        self.model_name = 'surelogix-mrgpod-larson-v1'
        self.multi_docbytes = multi_docbytes
        self.base_output = convert_dict_values_to_none(output_format)

    def check_for_unsupported_file(self, ret):
        if (
            ret.get("consignee_data") is None
            or ret.get("shipment_identifier") is None
            # or ret.get("shipment_date") is None
        ):
            raise UnintendedFileException

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

    def get_parse_dict_by_rules_prompt(self, input_data, output_rules):
        prompt = f"""
            Parse the following:
            
            {input_data}
            
            From that, extract the following JSON:
            
            {output_rules}
            
            Do not invent information. If the information is not there, leave it as '', unless a default is specified. Do not use examples as default values.
        """

        # ret = await self.call_llm_multiple_prompts_async([prompt])
        # resp = json.loads(ret)
        return prompt

    def get_ship_cons_prompt(self, text):
        prompt = f"""The following is the information of the shipper or consignee of a shipment. It contains the name of the shipper, its address and contact information.

                {text}

                """
        prompt += r"""
                From that, extract the following JSON:

                {
                    "name": "string. Contains at start of the string before address dataExamples: '22775 LOWES OF SLIDELL 1684'",
                    "address": {
                        "street": "string. Only the steet address. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
                        "city": "string",
                        "state": "string. The code of the state",
                        "postal_code": "string",
                        "country_code": "string. Default is 'US'"
                    },
                    "contact": {
                        "name": "string. Examples: 'FOR AAMD 2023', 'HALEY FEINGOLD', 'SHIPPING', 'SHEPARD/TFORCE', 'TRE MOSELEY', 'DEB'. Default '' ",
                        "tel": "string. Might not exist. Examples: '860-257-3300'. Convert to format '000-000-0000'. Default ''",
                        "fax": "string. Might not exist. Default ''"
                    },
                    "notes": "string. Might not exist. Default ''"
                }

                Do not invent information. If the information is not there, leave it as null, unless a default is specified. Do not use examples as default values.
                """

        # ret = await self.call_llm_multiple_prompts_async([prompt])
        # resp = json.loads(ret)
        return prompt

    async def parse_output(self, ret):
        output_format = {**self.base_output}
        # Output with default values
        output_format.update({
            'scac': 'OKOLAR',
            'shipment_identifier': ret.get("shipment_identifier"),
            'payment_method': 'PP',
            'handling': 'PUD',
            'MA': ret.get("MA"),
            'BM': ret.get("shipment_identifier"),

            'shipment_date': ret.get("shipment_date"),
            'delivery_time': {
                'time': "16:00",
                'timezone': None,
                'meridien': 'PM'
            },

            'shipper': {
                "name": ret.get("shipper_name"),
                "address": {
                    "street": None,
                    "city": None,
                    "state": None,
                    "postal_code": None,
                    "country_code": None,
                },
                "contact": {
                    "name": None,
                    "tel": None,
                    "fax": None,
                },
                "notes": None
            },
            "goods": {
                "net_weight": ret.get('piece_weight'),
                "no_of_pieces": ret.get('piece_count'),
                "pieces": [
                    {
                        "description": None,
                        "dimensions": None,
                        "weight": None,
                        'pieces': None
                    }
                ]
            },
        })

        # Need to clean output data with openai
        input_data = {
            "input_shipment_date": output_format.get('shipment_date', "")
        }

        output_rules = """
                {
                    "shipment_date": "string. Extract from 'input_shipment_date'. If not date found return '' else convert to format 'MM/DD/YYYY'.",
                }
                """

        consignee_prompt = self.get_ship_cons_prompt(ret.get('consignee_data'))
        by_rules_prompt = self.get_parse_dict_by_rules_prompt(input_data, output_rules)

        oai_res = await self.call_llm_multiple_prompts_async([consignee_prompt, by_rules_prompt])

        consignee_parsed = json.loads(oai_res[0])
        output_format.update({
            'consignee': consignee_parsed
        })

        cleaned_data = json.loads(oai_res[1])

        shipment_cleaned_date = cleaned_data.get('shipment_date')
        now_date = datetime.now().strftime('%m/%d/%Y')
        shipment_date = shipment_cleaned_date if shipment_cleaned_date else now_date
        output_format.update({
            'shipment_date': shipment_date,
            'delivery_date': shipment_date
        })

        return output_format

    async def run(self):
        tasks = []
        for doc_bytes in self.multi_docbytes:
            tasks.append(asyncio.create_task(self.process_document(doc_bytes)))
        processed_results = await asyncio.gather(*tasks)

        parse_tasks = []
        for p_res in processed_results:
            parse_tasks.append(asyncio.create_task(self.parse_output(p_res)))
        results = await asyncio.gather(*parse_tasks)

        return results, self.model_name

