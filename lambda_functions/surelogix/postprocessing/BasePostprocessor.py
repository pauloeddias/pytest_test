import asyncio
import openai
class BasePostprocessor:
    async def call_llm_async(self,prompt, temperature=0.0):
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

    async def call_llm_multiple_prompts_async(self,prompts):
        tasks = []
        for prompt in prompts:
            tasks.append(asyncio.create_task(self.call_llm_async(prompt)))
        resp = await asyncio.gather(*tasks)
        return resp

    def check_for_unsupported_file(self):
        raise NotImplementedError

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

    def get_delivery_date_and_time_prompt(self, delivery_date, shipment_date):
        prompt = f"""The following is the information of the delivery date and time of a shipment. It contains the delivery date and possibly the delivery time.

                {delivery_date}

                Given that the shipment date is the following:

                {shipment_date}

                """
        prompt += r"""
                From that, extract the following JSON:

                {
                    "delivery_date": "string. The date of delivery. Format: MM/DD/YYYY",
                    "delivery_time": {
                            "time": "string. The time of delivery. Format: HH:MM. Always pad the hour to 2 digits. For example, return 09:20, not 9:20. Never put AM or PM",",
                            "meridien": "If it's AM or PM",
                            "timezone": "New Orleans time zone for that date. Format: 'UTC-5'",
                        }

                }

                Do not invent information. If the information is not there, leave it as null.
                """

        return prompt

    def get_shipment_date_and_time_prompt(self, shipment_date):
        prompt = f"""The following is the information of the shipment date and time of a shipment. It contains the shipment date and possibly the shipment time.

                {shipment_date}

                """
        prompt += r"""
                From that, extract the following JSON:

                {
                    "shipment_date": "string. The date of delivery. Format: MM/DD/YYYY",
                    "shipment_time": {
                            "time": "string. The time of delivery. Format: HH:MM. Always pad the hour to 2 digits.For example, return 09:20, not 9:20. Never put AM or PM",
                            "meridien": "If it's AM or PM",
                            "timezone": "New Orleans time zone for that date. Format: 'UTC-5'",
                        }

                }

                Do not invent information. If the information is not there, leave it as null.
                """

        return prompt

    def convert_dict_values_to_none(self,data: dict) -> dict:
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
                data_copy[key] = self.convert_dict_values_to_none(value)

        elif isinstance(data, list):
            data_copy = data.copy()
            tmp_list = []
            for item in data_copy:
                tmp_list.append(self.convert_dict_values_to_none(item))
            data_copy = tmp_list
        else:
            data_copy = None
        return data_copy

    def replace_str_null_to_none(self, test_dict):

        # checking for dictionary and replacing if 'null'
        if isinstance(test_dict, dict):
            for key in test_dict:
                if test_dict[key] in ['null', '']:
                    test_dict[key] = None
                else:
                    self.replace_str_null_to_none(test_dict[key])

        # checking for list, and testing for each value
        elif isinstance(test_dict, list):
            for val in test_dict:
                self.replace_str_null_to_none(val)

        return test_dict
