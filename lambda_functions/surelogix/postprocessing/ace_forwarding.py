import asyncio
import openai
import json

from .BasePostprocessor import BasePostprocessor
from ._common import UnintendedFileException


class ACEForwardBOLPostprocessor(BasePostprocessor):
    def __init__(self, ret, output_format):
        self.ret = ret
        self.output_format = output_format
        self.check_for_unsupported_file()

    def check_for_unsupported_file(self):
        if (
            self.ret.get("shipper") == None
            or self.ret.get("consignee") == None
            or self.ret.get("ship_date") == None
            or self.ret.get("BOL") == None
            or self.ret.get("PO") == None
        ):
            raise UnintendedFileException("Unintended file")


    def parse_output_format(self, shipper, consignee,delivery_date):
        for i in self.output_format:
            self.output_format[i] = None

        self.output_format['shipper'] = shipper
        self.output_format['consignee'] = consignee
        self.output_format['goods'] = {
            "net_weight": self.ret.get('weight'),
            "no_of_pieces": self.ret.get('pcs'),
            'pieces': self.ret.get('goods_table')
        }
        self.output_format['shipment_identifier'] = self.ret.get('BOL')
        self.output_format['MA'] = None
        self.output_format['scac'] = "ACE Forwarding"
        self.output_format['shipment_date'] = self.ret.get('ship_date')
        self.output_format['payment_method'] = 'PP'
        self.output_format['PO'] = self.ret.get('PO')
        self.output_format['SI'] = self.ret.get('SI')
        self.output_format['handling'] = 'Delivery'
        self.output_format['delivery_date'] = delivery_date
        self.output_format['BM'] = self.ret.get('BOL')
        self.output_format['PRG'] = None
        self.output_format['REF'] = None
        self.output_format['CR'] = None
        self.output_format['BOL'] = self.ret.get('BOL')




    async def run(self):
        shipper_prompt = self.get_shipper_prompt(self.ret.get('shipper'))

        consignee_prompt = self.get_consignee_prompt()

        resps = await self.call_llm_multiple_prompts_async(
            [shipper_prompt, consignee_prompt]
        )

        self.get_goods_table()

        shipper = json.loads(resps[0])
        consignee = json.loads(resps[1])
        delivery_date = consignee.get('delivery_date')
        consignee.pop('delivery_date', None)

        self.parse_output_format(shipper, consignee, delivery_date)

        return self.output_format

    def get_shipper_prompt(self, shipper):
        prompt = f"""The following is the information of the shipper of a shipment. It contains the name of the shipper, its address and contact information.

        {shipper}

        """
        prompt += r"""
        From that, extract the following JSON:

        {
            "name": "string",
            "address": {
                "street": "string. Only the street address. May or may not contain a PO Number. May contain a second line. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
                "city": "string",
                "state": "string. The code of the state",
                "country_code": "string. Default is 'US'"
            },
            "contact": {
                "name": "string. An email under E.",
                "tel": "string",
                "fax": "string. Under F."
            }
        }

        Do not invent information. If the information is not there, leave it as null, unless a default is specified.
        """

        return prompt


    def get_consignee_prompt(self):

        consignee = self.ret.get('consignee')

        prompt = f"""The following is the information of the consignee of a shipment. It contains the name of the consignee, its address and contact information.

        {consignee}

        """
        prompt += r"""
        From that, extract the following JSON:

        {
            "name": "string",
            "delivery_date": "string. Format: MM/DD/YYYY",
            "address": {
                "street": "string. Only the street address. May or may not contain a PO Number. May contain a second line. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
                "city": "string",
                "state": "string. The code of the state",
                "postal_code": "string",
                "country_code": "string. Default is 'US'"
            },
            "contact": {
                "name": "string",
                "tel": "string",
                "fax": "string. Might not exist"
            }
        }

        Do not invent information. If the information is not there, leave it as null, unless a default is specified.
        """
        return prompt


    def get_goods_table(self):
        goods = []
        dims = self.ret.get('dimensions', '').replace('×', 'X').replace(' ', '').replace('"', '')
        dims = ' X '.join(dims.split('X'))
        pieces = self.ret.get('pcs').replace('.', '')
        goods.append({'description': self.ret.get('description'),
                      'dimensions': dims,
                      "pieces": int(pieces),
                      'weight': self.ret.get('weight'),
                      'package_type': self.ret.get('type')
                      })
        self.ret['goods_table'] = goods
