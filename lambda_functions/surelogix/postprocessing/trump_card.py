import asyncio
import openai
import json
import re
from ._common import UnintendedFileException
from .BasePostprocessor import BasePostprocessor


async def call_llm_async(prompt, temperature=0.0):
    completion = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        # model="gpt-4-0613",
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
    )
    return completion.choices[0].message["content"]


async def call_llm_multiple_prompts_async(prompts):
    tasks = []
    for prompt in prompts:
        tasks.append(asyncio.create_task(call_llm_async(prompt)))
    resp = await asyncio.gather(*tasks)
    return resp


class TrumpCardPostprocessing(BasePostprocessor):
    def __init__(self, ret, output_format):
        self.ret = ret
        self.output_format = output_format
        self.check_for_unsupported_file()

    def check_for_unsupported_file(self):
        if (
            self.ret.get("shipper") == None
            or self.ret.get("consignee") == None
            or self.ret.get("DT") == None
            or self.ret.get("MAWB") == None
            or self.ret.get("OT") == None
            or self.ret.get("scac") == None
        ):
            raise UnintendedFileException

    def parse_output_format(self, **kwargs):
        for i in self.output_format:
            self.output_format[i] = None

        self.output_format['scac'] = 'OKOTRU'
        self.output_format['payment_method'] = 'PP'
        self.output_format["handling"] = 'PUD'

        self.output_format["shipment_identifier"] = self.ret.get("MAWB")
        self.output_format["MA"] = self.ret.get("MAWB")

        self.output_format["OT"] = self.ret.get("OT")
        self.output_format["DT"] = self.ret.get("DT")

        self.output_format["BM"] = self.ret.get("airbill")

        self.output_format["SI"] = self.ret.get("SI")

        self.output_format["delivery_date"] = self.ret.get("SI")
        self.output_format["SI"] = self.ret.get("SI")

        self.output_format["shipment_date"] = self.ret.get("ship_date")
        if self.output_format["shipment_date"]:
            self.output_format["shipment_date"] = self.output_format["shipment_date"].replace('-', '/')
        self.output_format['shipment_time'] = {
            'time': None,
            'meridien': None,
            'timezone': None
        }

        self.output_format['delivery_date'] = kwargs['delivery_date']['delivery_date']
        self.output_format['delivery_time'] = {
            'time': kwargs['delivery_date']['delivery_time'],
            'meridien': kwargs['delivery_date']['delivery_meridien'],
            'timezone': None
        }

        self.output_format['ready_date'] = kwargs['ready_date_and_time']['ready_date']
        self.output_format['ready_time'] = {
            'time': kwargs['ready_date_and_time']['ready_time'],
            'meridien': kwargs['ready_date_and_time']['ready_meridien'],
            'timezone': None
        }
        self.output_format['consignee'] = {
            "name": kwargs['consignee']['name'],
            "address": kwargs['consignee']['address'],
            "contact": kwargs['consignee']['contact'],
            "notes": None
        }

        self.output_format['carrier'] = {
            "name": self.ret.get("carrier"),
            "address": {
                "street": None,
                "city": None,
                "state": None,
                "postal_code": None,
                "country_code": None
            },
            "contact": {
                "name": None,
                "tel": self.ret.get("carrier_phone"),
                "fax": None,
            }
        }

        self.output_format['shipper'] = kwargs['shipper']

        self.output_format['goods'] = self.get_goods_from_table(self.ret.get("pieces_table", []))

    async def run(self):
        ready_date_and_time_prompt = self.get_eta_prompt(self.ret["ETA"])

        delivery_date_prompt = self.get_delivery_date_from_si_prompt(self.ret["SI"])

        consignee_prompt = self.get_consignee_prompt(self.ret['consignee'])

        shipper_prompt = self.get_shipper_prompt(self.ret['shipper'])

        resps = await call_llm_multiple_prompts_async(
            [ready_date_and_time_prompt, delivery_date_prompt, consignee_prompt, shipper_prompt]
        )

        ready_date_and_time = json.loads(resps[0])
        delivery_date = json.loads(resps[1])
        consignee = json.loads(resps[2])
        shipper = json.loads(resps[3])

        self.parse_output_format(
            ready_date_and_time=ready_date_and_time,
            delivery_date=delivery_date,
            consignee=consignee,
            shipper=shipper
        )
        self.output_format = self.replace_str_null_to_none(self.output_format)
        return self.output_format

    def get_eta_prompt(self, eta):
        prompt = f"""
        
        The following is the information about time and date. It's may be presented in two formats.
        The first format is "3:45 PM 01/21/2016". Here is time, meridien and date.
        The second format is "AM 01/21/2019". Here is only meridien and date. Parse following string
        
        "{eta}".
        """

        prompt += """

        From that, extract the following JSON:
        
        {
            "ready_date": "string // example: 01/21/2001. Format always should be mm/dd/yyyy. Default null",
            "ready_time": "string // example: 10:00. In case time be like 145, treat it like 1:45. If present than always before meridien. Default null",
            "ready_meridien": "string // example: AM or PM. Default null"
        }
        
        Do not invent information. If the information is not there, leave it as null, unless a default is specified.
        """

        return prompt

    def get_delivery_date_from_si_prompt(self, special_instructions):
        prompt = f"""Parse the following:
        
        {special_instructions}

        """
        prompt += r"""
        
        From that, extract the following JSON:

        {
            "delivery_date": "string, // example: 01/21/2001. Format always should be mm/dd/yyyy. Default null",
            "delivery_time": "string, // example: 10:00. In case time be like 145, treat it like 1:45. Default null",
            "delivery_meridien": "string // example: AM or PM. Default null"
        }
        
        Do not invent information. If the information is not there, leave it as null, unless a default is specified.
        """
        return prompt

    def get_consignee_prompt(self, consignee):
        prompt = f"""
        The following is the information of the consignee. It contains the name of the consignee, its address and contact information. Parse the following:

        {consignee}

        """

        prompt += r"""

        From that, extract the following JSON:

        {
            "name": "string",
            "address": {
                "street": "string. Only the steet address. May or may not contain a PO Number. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
                "city": "string",
                "state": "string. The code of the state",
                "postal_code": "string",
                "country_code": "string. Default is 'US'"
            },
            "contact": {
                "name": "string",
                "tel": "string",
                "fax": "string. Might not exist"
            },
            "notes": "string"
        }

        Do not invent information. If the information is not there, leave it as null, unless a default is specified.
        """

        return prompt

    def get_shipper_prompt(self, shipper):
        prompt = f"""
        The following is the information of the shipper of a shipment. It contains the name of the shipper, city and might contain state.

        {shipper}

        """

        prompt += r"""

        From that, extract the following JSON:

        {
            "name": "string",
            "address": {
                "street": "string. Only the steet address. May or may not contain a PO Number. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
                "city": "string",
                "state": "string. The code of the state",
                "postal_code": "string",
                "country_code": "string. Default is 'US'"
            },
            "contact": {
                "name": "string",
                "tel": "string",
                "fax": "string. Might not exist"
            },
            "notes": "string"
        }

        Do not invent information. If the information is not there, leave it as null, unless a default is specified.
        """

        return prompt

    def get_goods_from_table(self, goods_table):
        pieces = []
        no_of_pieces = 0
        weight = 0
        no_of_pieces_from_table = 0

        if goods_table:
            for i in range(len(goods_table)):
                dict_row = self.parse_1d_table_into_dict(goods_table[i])
                dimensions = re.findall(r'\d+X\d+X\d+', dict_row.get('DESCRIPTION OF CONTENTS', ''))
                description = dict_row.get('DESCRIPTION OF CONTENTS')

                for dim in dimensions:
                    description = description.replace(dim, '')

                if description:
                    description = description.strip()

                for dim in dimensions:
                    if not weight:
                        weight = dict_row.get('WEIGHT')

                    if not no_of_pieces_from_table:
                        no_of_pieces_from_table = dict_row.get('PIECES')

                    pieces_item = {
                        'description': description,
                        'dimensions': dim.replace(' ', '').replace('X', ' X '),
                        'weight': dict_row.get('WEIGHT'),
                        'package_type': 'PLT' if dict_row.get('PALLETS') else None,
                        'pieces': dict_row.get('PIECES')
                    }

                    if len(dimensions) > 1:
                        pieces_item['weight'] = None
                        pieces_item['pieces'] = '1'
                        no_of_pieces += 1

                    pieces.append(pieces_item)

        return {
            "net_weight": weight,
            "no_of_pieces": str(no_of_pieces) if len(dimensions) > 1 else no_of_pieces_from_table,
            "pieces": pieces
        }

    def parse_1d_table_into_dict(self, table):
        fields_dict = {}
        try:
            for key, field in table.value.items():
                fields_dict[key] = field.value

        except Exception as e:
            fields_dict = {}
        return fields_dict
