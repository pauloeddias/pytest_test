# Postprocessing for iCat DA scac:ICAT data extraction

import json
from datetime import datetime
from .BasePostprocessor import BasePostprocessor
from ._common import UnintendedFileException


class OmniDA(BasePostprocessor):
    def __init__(self, ret, output_format):
        self.ret = ret
        self.output_format = output_format
        self.check_for_unsupported_file()

    def check_for_unsupported_file(self):
        if (
                self.ret.get('sub_customer_name') is None
                or self.ret.get('sub_customer_name', '').lower().strip() != 'omni logistics all in.'
                or self.ret.get('consignee') is None
                or self.ret.get('shipper') is None
                or self.ret.get('airbill') is None
        ):
            raise UnintendedFileException

    def get_pieces_from_table(self, goods_table):
        pieces = []

        if goods_table:
            no_of_pieces = 0
            net_weight = 0
            for i in range(len(goods_table)):
                dict_row = self.parse_1d_table_into_dict(goods_table[i])
                try:
                    no_of_pieces += int(dict_row.get('Pieces', 1))
                    net_weight += int(dict_row.get('Weight', 0))
                    pieces_item = {
                        'description': dict_row.get('Description'),
                        'pieces': dict_row.get('Pieces'),
                        'dimensions': dict_row.get('Dimensions'),
                        'weight': dict_row.get('Weight'),
                        'package_type': dict_row.get('PackageType'),
                    }
                finally:
                    # ignore completely empty pieces_item
                    res = sum(map(lambda x: 1 if x else 0, pieces_item.values()))

                if res > 0:
                    pieces.append(pieces_item)

        return pieces, no_of_pieces, net_weight

    def parse_1d_table_into_dict(self, table):
        fields_dict = {}
        try:
            for key, field in table.value.items():
                fields_dict[key] = field.value
        except:
            pass
        return fields_dict

    def get_shipper_prompt(self, shipper):
        prompt = f"""The following is the information of the shipper of a shipment. It contains the name of the shipper, its address and contact information.

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
                    }
                }

                Do not invent information. If the information is not there, leave it as null, unless a default is specified.
                """

        return prompt

    def get_consignee_prompt(self, consignee):
        prompt = f"""The following is the information of the consignee of a shipment. It contains the name of the consignee, its address and contact information.

                {consignee}

                """
        prompt += r"""
                From that, extract the following JSON:

                {
                    "name": "string",
                    "ref": "string",
                    "address": {
                        "street": "string. Only the street address. May or may not contain a PO Number. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
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

    def get_time(self, str_time):
        result = {
            "time": None,
            "meridien": None,
            "timezone": None,
        }

        if str_time:
            try:
                if 'and' in str_time and 'between' in str_time:
                    split_time = str_time.replace('between', '').strip().split('and')
                    result["time"] = split_time[1].split()[0]
                    result["meridien"] = split_time[1].split()[1]
                else:
                    result["time"] = str_time.split()[0]
                    result["meridien"] = str_time.split()[1]
            except:
                pass

        return result

    def parse_output_format(self, **kwargs):
        for i in self.output_format:
            self.output_format[i] = None

        self.output_format["scac"] = "OMNG"
        self.output_format["shipment_identifier"] = self.ret.get("airbill")
        self.output_format["shipment_date"] = self.ret.get("shipment_date")
        self.output_format["shipment_time"] = self.get_time(self.ret.get("shipment_time"))
        self.output_format["payment_method"] = "PP"

        # Identifiers and References
        self.output_format["PO"] = None
        self.output_format["MA"] = self.ret.get("MAWB")
        self.output_format["SI"] = self.ret.get("SI")
        self.output_format["OT"] = self.ret.get("OT")
        self.output_format["DT"] = self.ret.get("DT")
        self.output_format["BM"] = self.ret.get("airbill")

        # Delivery Specifics
        self.output_format["handling"] = "PUD"
        self.output_format["delivery_date"] = self.ret.get("delivery_date")
        self.output_format["delivery_time"] = self.get_time(self.ret.get("delivery_time"))
        self.output_format["ready_date"] = self.ret.get("ready_date")
        self.output_format["ready_time"] = self.get_time(self.ret.get("ready_time"))

        # Contact Info
        self.output_format["shipper"] = kwargs.get("shipper"),
        self.output_format["consignee"] = kwargs.get("consignee"),
        self.output_format["carrier"] = {
            "name": self.ret.get("carrier"),
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
                "fax": None
            }
        }

        # Goods
        pieces, no_of_pieces, net_weight = self.get_pieces_from_table(self.ret["goods_table"])
        self.output_format["goods"] = {
            "net_weight": self.ret.get("net_weight") if self.ret.get("net_weight") else net_weight,
            "no_of_pieces": self.ret.get("no_of_pieces") if self.ret.get("no_of_pieces") else no_of_pieces,
            "pieces": pieces,
        }

        # Identifiers and References
        self.output_format["PRG"] = None
        self.output_format["REF"] = None
        self.output_format["CR"] = None
        self.output_format["BOL"] = None

    async def run(self):
        shipper_prompt = self.get_shipper_prompt(self.ret.get('shipper'))
        consignee_prompt = self.get_consignee_prompt(self.ret.get('consignee'))

        resps = await self.call_llm_multiple_prompts_async([shipper_prompt, consignee_prompt])

        shipper = json.loads(resps[0])
        consignee = json.loads(resps[1])

        self.parse_output_format(
            consignee=consignee,
            shipper=shipper
        )

        return self.output_format
