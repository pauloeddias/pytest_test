import json
import os
from typing import Dict, Any
from src.ml_engine._ml_engine import afr_process_document, get_message_bytes
from src.postprocess_engine.de_postprocess import postprocess_doc, get_output_format_and_base, dq_string_has_conditions
from src.postprocess_engine.llm_postprocess import parse_dimensions, parse_usa_cities


## ------------------------------------
model_info = {
    'model_name': "slx",
    'model_version': "v5",
    'model_meta_data': {
        'model_creator': "Masoud Shab",
        'model_description': """
            Used Baseline 'Slx-V4.1' Model + 
            Modular Components +
            OpenAI Parsers +
            QA Testing on DEV/DEPLOY Modes
        """,
        'latest_changes': "3 fixes: #Bug-Null & #Bug-Dimensions & #Bug-Cities"
    }
}
## ------------------------------------


## ------------------------------------
# Main Pipeline to run two Engines (DAGs: ml_engine >> postprocess_engine) sequentially
## ------------------------------------

def lambda_handler(event: Dict[str, Any], context: str, azure_endpoint: str = None, azure_key: str = None):
    if not azure_key:
        azure_endpoint = os.environ['AZURE_ENDPOINT']
        azure_key = os.environ['AZURE_KEY']

    # Process the document and create the "processed_result" object
    message_bytes = get_message_bytes(event, context)
    processed_result = afr_process_document(azure_endpoint, azure_key, message_bytes, model_id="prebuilt-document")

    # Post-process the "processed_result" object and create the final output
    output_format, output_base = get_output_format_and_base()
    order_list = postprocess_doc(processed_result, output_base)

    # TODO: Temp Output Fixes. Will be fixed once transitioned to OpenAI approach ------ 1
    try:
        for item in order_list[0]["goods"]["pieces"]:
            item["dimensions"] = parse_dimensions(item["dimensions"]).replace('"', '').lower()
    except:
        print(" ~~~ ERROR ~~~ openai failed on ", "dimensions")
    
    try:
        for party in ['shipper', 'consignee']:
            order_list[0][party]["address"]["city"] = parse_usa_cities(order_list[0][party]["address"]["city"]).replace('"', '')
    except:
        print(" ~~~ ERROR ~~~ openai failed on ", "cities")

    for party in ['shipper', 'consignee']:
        city = order_list[0][party]["address"]["city"]
        if "/" in city:
            for city_part in city.split("/"):
                if dq_string_has_conditions(city_part, conditions=["no-digit"], min_size=5, max_size=15):
                    city = city_part
        order_list[0][party]["address"]["city"] = city

    ### --------- 1


    # find sub_customer
    if order_list[0]["scac"] == 'OMNG':
        sub_customer = 'omni'
    else:
        sub_customer = None

    # main return of lambda
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "order_list": order_list
            }),
        "analytics": {
            "file_type": None,
            "quality_score": None
        },
        'customer_info': {
            'customer': 'surelogix',
            'tms': 'crown',
            'sub_customer': sub_customer,
        },
        'model_info': model_info
    }
