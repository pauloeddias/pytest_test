###------------------------------------
# Model Info
model_info = {
    'model_name': 'slx',
    'model_version': 'v7',
    'azure_custom_model_name': 'slx-v8-4subcustomers-da-cm1',
    'model_meta_data': {
        'model_creator': 'Masoud Shab',
        'model_description': """
            + Azure Custom Model
            + Modular Components (reading from oko-doc-ai/src/<modules>)
            + LLM-Based Post-Process (OpenAI Parsers)
            + QA Testing on DEV/DEPLOY Modes
        """,
        'latest_changes': ''
    }
}
#--------------------------------------

import openai
import os
import base64
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import json
from typing import Dict, Any
from src.postprocess_engine.llm_postprocess import parse_dimensions, parse_address_section_into_parts, parse_address_part_name_and_street
from src.postprocess_engine.llm_postprocess import parse_address_part_city_and_state_and_postal_code, parse_address_part_contact_name_and_contact_phone
from src.postprocess_engine.de_postprocess import dq_string_has_conditions
import traceback


###----------------------------------
# Project-Specific Post-Process Functions. 
# Project Name: surelogix
# --
# Ml-Engine Type: Custom-Model
# Post-Process Type: LLM-Based
#------------------------------------

## init
customer_info = {
    'customer': 'surelogix',
    'tms': 'crown',
    'sub_customer': '',
    'valid_values': {
        'terminals': ['EWR', 'MSY']
        }
    }


## parsing helper funcs
def extract_country_code(text):
    country_variations = {
        "United States": "USA",
        "United States of America": "USA",
        "USA": "USA",
        "U.S.": "USA",
        "U.S.A.": "USA",
        "US": "USA",
        "U.S.A": "USA"
    }
    for country_name in country_variations:
        if country_name.lower() in text.lower():
            return country_variations[country_name]
    return ""


def extract_terminal_code(text):
    valid_terminal = ""
    for terminal_option in text.split(" "):
        if terminal_option in customer_info["valid_values"]["terminals"]:
            valid_terminal = terminal_option
        elif dq_string_has_conditions(terminal_option, conditions=['capital'], min_size=3, max_size=3):
            valid_terminal = terminal_option
    return valid_terminal


## postprocess
def get_fields_dict_from_custom_model_result(custom_model_result):
    fields_dict = {}
    try:
        for name, field in custom_model_result.documents[0].fields.items():
            if name in ['shipper', 'consignee']:
                field_value = field.content if field.content else field.value
            else:
                field_value = field.value if field.value else field.content
            if isinstance(field_value, str):
                fields_dict[name] = field_value
            elif isinstance(field_value, list):
                fields_dict[name] = []
                for sub_item in field_value:
                    sub_items_dict = {}
                    for sub_name, sub_filed in sub_item.value.items():
                        sub_field_value = sub_filed.value if sub_filed.value else sub_filed.content
                        sub_items_dict[sub_name] = sub_field_value
                    fields_dict[name].append(sub_items_dict)
    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")
    return fields_dict


def get_output_from_fields_dict_surelogix(fields_dict):
    output = {
        "scac": "",
        "shipment_identifier": "",
        "shipment_date": "",
        "shipment_time": {
            "time": "",
            "meridien": ""
        },
        "payment_method": "",
        "PO": "",
        "MA": "",
        "BM": "",
        "SI": "",
        "OT": "",
        "DT": "",
        "handling": "",
        "delivery_date": "",
        "delivery_time": {
            "time": "",
            "meridien": "",
            "timezone": ""
        },
        "ready_date": "",
        "ready_time": {
            "time": "",
            "meridien": "",
            "timezone": ""
        },
        "shipper": {
            "name": "",
            "address": {
                "street": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country_code": "",
            },
            "contact": {
                "name": "",
                "tel": "",
                "fax": "",
            },
            "notes": ""
        },
        "consignee": {
            "name": "",
            "address": {
                "street": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country_code": "",
            },
            "contact": {
                "name": "",
                "tel": "",
                "fax": "",
            },
            "notes": ""
        },
        "carrier": {
            "name": "",
            "address": {
                "street": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country_code": "",
            },
            "contact": {
                "name": "",
                "tel": "",
                "fax": ""
            }
        },
        "goods": {
            "net_weight": "",
            "no_of_pieces": "",
            "pieces": []
        },
        "PRG": "",
        "REF": "",
        "CR": "",
        "BOL": ""
    }
    
    ## condition fields
    if 'omni' in fields_dict.get("scac", "").lower():
        customer_info['sub_customer'] = 'omni'
        output['scac'] = "OMNG"
        output['payment_method'] = 'PP'
    elif 'allstate' in fields_dict.get("scac", "").lower():
        customer_info['sub_customer'] = 'allstate'
        output['scac'] = "ASAQ"
        output['payment_method'] = 'PP'
    elif 'icat' in fields_dict.get("scac", "").lower():
        customer_info['sub_customer'] = 'icat'
        output['scac'] = "ICAT"
        output['payment_method'] = 'PP'
    elif 'pegasus' in fields_dict.get("scac", "").lower():
        customer_info['sub_customer'] = 'pegasus'
        output['scac'] = "PGAA"
        output['payment_method'] = 'PP'
    #TODO this needs to be fixed by ECM SLX-V8
    else:
        customer_info['customer'] = ''
        customer_info['sub_customer'] = ''
        output['scac'] = "TBD"
        output['payment_method'] = 'TBD'

    

    if 'delivery' in fields_dict.get("deliver_alert", "").lower():
        output['handling'] = "PUD"

    ## easy fields
    try:
        output['shipment_identifier'] = fields_dict.get("ship_id", "")
        output['MA'] = fields_dict.get("ship_id", "")
        output['BM'] = fields_dict.get("airbill", "")
        output['SI'] = fields_dict.get("SI", "")
        output['OT'] = fields_dict.get("OT", "") 
        output['DT'] = fields_dict.get("DT", "")
        output['carrier']['name'] = fields_dict.get("carrier", "")
        output['goods']['net_weight'] = fields_dict.get("weight", "")
        output['goods']['no_of_pieces'] = fields_dict.get("pcs", "")
    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")

    ## date_time fields
    output['shipment_date'] = fields_dict.get("ship_date", "")
    try:
        output['shipment_time']['time'] = fields_dict.get("ship_time", "").split(' ')[0]
        output['shipment_time']['meridien'] = fields_dict.get("ship_time", "").split(' ')[1]
    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")

    output['delivery_date'] = fields_dict.get("deliver_date", "")
    try:
        output['delivery_time']['time'] = fields_dict.get("deliver_time", "").split(' ')[0]
        output['delivery_time']['meridien'] = fields_dict.get("deliver_time", "").split(' ')[1]
    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")

    output['ready_date'] = fields_dict.get("ETA", "").split(' ')[0]
    try:
        output['ready_time']['time'] = fields_dict.get("ETA", "").split(' ')[1] if " " in fields_dict.get("ETA", "") else ""
        output['ready_time']['meridien'] = fields_dict.get("ETA", "").split(' ')[2] if " " in fields_dict.get("ETA", "") else ""
    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")

    ## items fields
    try:
        for item in fields_dict.get("pieces_table", []):
            output_item = {
                'description': item.get("DESCRIPTION", ""),
                'dimensions': item.get("DIMENSIONS", ""),
                'weight': item.get("WEIGHT", ""),
            }
            output_item["dimensions"] = parse_dimensions(output_item["dimensions"]).replace('"', '').lower()
            output['goods']['pieces'].append(output_item)
    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")

    ## openai parsed fields
    address_parts = {}
    address_parts_edge_case = {}
    for party in ['shipper', 'consignee']:
        # parse address_section into parts
        try:
            address_parts = parse_address_section_into_parts(fields_dict.get(f"{party}", ""))

            #TODO-P1-Bug-InnerGrove--------
            if 'INVER GROVE HEIGHTS, MN ' in address_parts.get('name_and_street') and len(address_parts.get('city_and_state_and_postal_code')) <= 10:
                inner_grove_list = fields_dict.get(f"{party}", '').split('INVER GROVE HEIGHTS, MN ')
                inner_grove_postal_code = inner_grove_list[1].split(' ')[0]
                address_parts['name_and_street'] = inner_grove_list[0]
                address_parts['city_and_state_and_postal_code'] = 'INVER GROVE HEIGHTS, MN ' + inner_grove_postal_code
                address_parts['country_name'] = 'USA'
                address_parts['contact_name_and_contact_phone'] = inner_grove_list[1].replace(inner_grove_postal_code, '').replace('USA', '')
            if party == 'shipper':
                address_parts_edge_case['shipper_name_street'] = address_parts.get('name_and_street', '')
            elif party == 'consignee':
                address_parts_edge_case['consignee_name_street'] = address_parts.get('name_and_street', '')
            #Bug-InnerGrove--------

        except Exception as e:
            traceback.print_exc()
            print(f" ~~~ ERROR ~~~ '{e}!")

        # parse address_part into "name" and "street"
        try:
            address_part_name_and_street = parse_address_part_name_and_street(address_parts.get("name_and_street", "").replace("\n", " "))
            output[party]['name'] = address_part_name_and_street.get("name", "")
            output[party]['address']['street'] = address_part_name_and_street.get("street", "")
        except Exception as e:
            traceback.print_exc()
            print(f" ~~~ ERROR ~~~ '{e}!")
        
        # parse address_part into "city", "state", "postal_code" and "country_code"
        try:
            address_part_city_and_state_and_postal_code = parse_address_part_city_and_state_and_postal_code(address_parts.get("city_and_state_and_postal_code", ""))
            output[party]['address']['city'] = address_part_city_and_state_and_postal_code.get("city", "")
            output[party]['address']['state'] = address_part_city_and_state_and_postal_code.get("state", "")
            output[party]['address']['postal_code'] = address_part_city_and_state_and_postal_code.get("postal_code", "")
        except Exception as e:
            traceback.print_exc()
            print(f" ~~~ ERROR ~~~ '{e}!")
        try:
            output[party]['address']['country_code'] = extract_country_code(address_parts.get("country_name", ""))
        except Exception as e:
            traceback.print_exc()
            print(f" ~~~ ERROR ~~~ '{e}!")

        # parse address_part into "contact-name" and "contact-tel"
        try:
            address_part_contact_name_and_contact_phone = parse_address_part_contact_name_and_contact_phone(address_parts.get("contact_name_and_contact_phone", ""))
            output[party]['contact']['name'] = address_part_contact_name_and_contact_phone.get("contact_name", "")
            output[party]['contact']['tel'] = address_part_contact_name_and_contact_phone.get("contact_phone", "")
            output[party]['notes'] = address_part_contact_name_and_contact_phone.get("contact_phone", "")
            if output[party]['contact']['tel'] == '1234567890':
                output[party]['contact']['tel'] = ''
        except Exception as e:
            traceback.print_exc()
            print(f' ~~~ ERROR ~~~ "{e}"!')
        
    #TODO-P1-Feat-Final-Validations----- 
    # fix & generalize Edge Cases in SLX-V8
    # DQs & Edge Cases:
    try:
        if len(output['OT']) > 3:
            output['OT'] = extract_terminal_code(output['OT'])
        for party in ['shipper', 'consignee']:
            # modify 'name' & 'street' if needed:
            name = output[party]['name']
            street_ind = 0
            if len(name.split(" ")) > 1:
                for ind, val in enumerate(name.split(" ")):
                    if dq_string_has_conditions(val, conditions=['all-digit']):
                        street_ind = ind
            if street_ind:
                output[party]['name'] = " ".join(name.split(" ")[:street_ind])
                output[party]['address']['street'] = " ".join(name.split(" ")[street_ind:]) + output[party]['address']['street']
            
            #TODO-P1-Bug-Num-in-Name---------
            if '\n' in address_parts_edge_case[f'{party}_name_street']:
                output[party]['name'] = address_parts_edge_case[f'{party}_name_street'].split('\n')[0]
                output[party]['address']['street'] = address_parts_edge_case[f'{party}_name_street'].replace(output[party]['name'], '').replace('\n', ' ')
            #Bug-Num-in-Name---------
            
            # modify 'street' if needed:
            street = output[party]['address']['street']
            USA_ind = 0
            AVE_ind = 0
            if len(street.split(" ")) > 1:
                for ind, val in enumerate(street.split(" ")):
                    if customer_info['sub_customer'] == 'allstate' and val == 'USA':
                        USA_ind = ind
            if USA_ind >= 3:
                output[party]['address']['street'] = " ".join(street.split(" ")[:USA_ind])
            
            #TODO-P2 better rule in future models 
            output[party]['address']['street'] = output[party]['address']['street'].replace("Unknown", "").replace("UNKNOWN", "") 

            # modify 'tel' and 'contact' if needed:
            tel = output[party]['contact']['tel'].replace("-", "").replace(' ', '')
            if dq_string_has_conditions(tel, conditions=['all-digit'], min_size=10, max_size=10):
                output[party]['contact']['tel'] = tel[:3] + "-" + tel[3:6] + "-" + tel[6:]
            else:
                output[party]['contact']['tel'] = ""
            contact_name = output[party]['contact']['name'].replace("-", "").replace(' ', '')
            if not output[party]['contact']['tel'] and dq_string_has_conditions(contact_name, conditions=['all-digit'], min_size=10, max_size=10):
                output[party]['contact']['tel'] = contact_name[:3] + "-" + contact_name[3:6] + "-" + contact_name[6:]
                output[party]['contact']['name'] = ''

            # remove dummy values
            output[party]['contact']['name'] = output[party]['contact']['name'].replace('CONTACTNAME CONTACTLASTNAME', '').replace('UNITED STATES OF AMERICA', '')
        
        if len(output['goods']['pieces']) == 1 and not output['goods']['pieces'][0]['weight']:
            output['goods']['pieces'][0]['weight'] = output['goods']['net_weight']

        for ind, piece in enumerate(output['goods']['pieces']):
            if 'there is not enough information' in piece.get('dimensions') or "i'm sorry, but i cannot parse" in piece.get('dimensions'):
                output['goods']['pieces'][ind]['dimension'] = ''
        #Feat-Final-Validations-----

    except Exception as e:
        traceback.print_exc()
        print(f' ~~~ ERROR ~~~ "{e}"!')

    return output
        

### ------------------------------------
# Main Pipeline to run two Engines (DAGs: ml_engine >> postprocess_engine) sequentially
### ------------------------------------

def lambda_handler(event: Dict[str, Any], context=None):
    try:
        azure_custom_model_name = model_info['azure_custom_model_name']

        azure_endpoint = os.environ['AZURE_ENDPOINT']
        azure_key = os.environ['AZURE_KEY']
        openai.api_key = os.environ['OPENAI_API_KEY']

        doc_bytes = event['doc_bytes']
        base64_bytes = doc_bytes.encode('utf8')
        message_bytes = base64.b64decode(base64_bytes)

        # Call Azure Custom Model API & get `afr_result`
        poller = DocumentAnalysisClient(
            endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key)
            ).begin_analyze_document(model_id=azure_custom_model_name, document=message_bytes)
        afr_result = poller.result()

        # Transfer 'afr_result' Object to 'fields_dict' Dictionary
        fields_dict = get_fields_dict_from_custom_model_result(custom_model_result=afr_result)

        # Post-Process by diff fields parsing
        output = get_output_from_fields_dict_surelogix(fields_dict)
        output_body = {
            'order_list': [output]
        }

        return {
            "statusCode": 200,
            "model_info": model_info,
            "body": json.dumps(output_body),
            "customer_info": customer_info
        }

    except Exception as e:
        traceback.print_exc()
        print(f" ~~~ ERROR ~~~ '{e}!")
        return {
            "statusCode": 500,
            "model_info": None,
            "body": json.dumps(None),
        }
