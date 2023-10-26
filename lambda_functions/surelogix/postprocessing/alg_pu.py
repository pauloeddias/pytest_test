# Postprocessing for ALG PU scac:ICAT data extraction

import json
from datetime import datetime
from .BasePostprocessor import BasePostprocessor
from ._common import UnintendedFileException


class ALGPickupAlert(BasePostprocessor):
    def __init__(self, ret, output_format):
        self.ret = ret
        self.output_format = output_format
        self.check_for_unsupported_file()

    def check_for_unsupported_file(self):
        if (
                self.ret.get('consignee') is None
                or self.ret.get('shipper') is None
                or self.ret.get('file_type') is None
                or self.ret.get('BM') is None
        ):
            raise UnintendedFileException

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
                    "ref": "string. Might not exist.",
                    "address": {
                        "street": "string. Only the street address. May or may not contain a PO Number. Do not put the full address here. Examples: '123 Main St', '123 Main St PO 557'",
                        "city": "string",
                        "state": "string. The code of the state",
                        "postal_code": "string",
                        "country_code": "string. Default is 'US'"
                    },
                    "contact": {
                        "name": "string.",
                        "tel": "string. Might not exist.",
                        "fax": "string. Might not exist."
                    }
                }

                Do not invent information. If the information is not there, leave it as null, unless a default is specified.
                """
        return prompt

    def get_time(self, str_time=""):
        result = {
            "time": None,
            "meridien": None,
            "timezone": None,
        }

        if str_time:
            str_time = str_time.strip()
            try:
                time_obj = datetime.strptime(f'{str_time}', '%H:%M')
                result["time"] = time_obj.strftime('%I:%M')
                result["meridien"] = time_obj.strftime('%p')
            except:
                pass

        return result

    def get_pieces_from_table(self, dims, dims_description):
        pieces = []

        if dims:
            try:
                dims = dims.split(',')
                for item in dims:
                    dims = item.split()
                    # '×' multiplication to alphabet 'x'
                    pieces.append({
                        'description': dims_description.replace('×', 'x') if dims_description else None,
                        'dimensions': ' X '.join(dims[0].replace('×', 'x').split('x')) if dims[0] else None,
                        'weight': None,
                        'package_type': None,
                        'pieces': dims[1].replace('(', '').replace(')', '')
                    })
            except:
                pass

        return pieces

    def parse_output_format(self, **kwargs):
        for i in self.output_format:
            self.output_format[i] = None

        # Required
        self.output_format["scac"] = "CCYE"
        self.output_format["shipment_identifier"] = self.ret.get("BM")
        self.output_format["shipment_date"] = None
        self.output_format["shipment_time"] = self.get_time()
        self.output_format["payment_method"] = "PP"

        # Identifiers and References
        self.output_format["PO"] = None
        self.output_format["MA"] = None
        self.output_format["SI"] = self.ret.get("SI")
        self.output_format["OT"] = None
        self.output_format["DT"] = None
        self.output_format["BM"] = self.ret.get("BM")

        # Delivery Specifics
        self.output_format["handling"] = "PUC"
        self.output_format["delivery_date"] = self.ret.get("delivery_date")
        self.output_format["delivery_time"] = self.get_time()
        self.output_format["ready_date"] = None
        self.output_format["ready_time"] = self.get_time()
        self.output_format["pickup_date"] = self.ret.get("pickup_date")
        self.output_format["pickup_time"] = self.get_time(self.ret.get("close_time", ""))

        # Contact Info
        self.output_format["shipper"] = kwargs.get("shipper"),
        self.output_format["consignee"] = kwargs.get("consignee"),
        self.output_format["carrier"] = {
            "name": None,
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

        # Goods table
        pieces = self.get_pieces_from_table(self.ret.get("dims", ""), self.ret.get("dims_description", ""))
        self.output_format["goods"] = {
            "net_weight": self.ret.get("net_weight", "").replace('(', '').replace(')', '') if self.ret.get("net_weight") else None,
            "no_of_pieces": self.ret.get("no_of_pieces", "").replace('(', '').replace(')', '') if self.ret.get("no_of_pieces") else None,
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
