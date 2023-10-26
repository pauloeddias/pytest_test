# --- Fields Info
# - met fields = 28
# - req fields = 33
# - mna fields = 7  # may not found, if found necessary to have
# - ona fields = 18
# total fields = 59

slx_output_format = {
    "scac": "string, #req, #met", # // SCAC CODE=OMNG [ISA | GS | BOL.01] Will be gotten from SCAC list file depending on what kind of file it is (Omni, Larson etc, for e.g Omni's SCAC is OMNG)",
    "shipment_identifier": "string, #req, #met", # // BOL.03 || 1958, SO OP14512973 Required. Reference number, or waybill number, or PO number, or even container number if all else fails",
    "payment_method": "CD/PP/CC, #mna", # // Required. CC - Collect on Delivery. PP - Prepaid (default.) CC - Carrier Collect. Can be found anywhere in the file, if not found default to PP.",
    "handling": "PUC/PUD, #req", # // Required PUD || AT5.01 = DEL or PUD (Delivery Alert) if it is a delivery (alert) file, PUC otherwise.",

    "shipment_date": "string, #req, #met", # // BOL.04 + BOL.05 Required. MM/DD/YYYY or MM/DD/YY. Found at top right corner of first page.",
    "shipment_time.time": "string, #req", # // BOL.04 + BOL.05 Required. HH:MM or HH:MM:SS. Both work. Found at top right corner of first page under shipment_date.",
    "shipment_time.meridien": "str AM/PM, #req",

    "PO": "string, #ona", # // Found in last line in Shipper information. 4 digit number. E.G 1958.",
    "MA": "string, #req, #met", # // Labelled Master Air Waybill. Found as labelled around top left side of first page.",
    "BM": "string, #req, #met", # // Labelled 'Airbill #'. Found as labelled around top left side of first page under MA.",
    "SI": "string, #req", # // Special Instructions. Any additional notes like: FRAGILE - HANDLE WITH CARE! DO NOT DOUBLE STACK OR BREAK DOWN SKIDS.",
    "OT": "string, #req, #met", # // Origin Terminal. Found around top right corner.",
    "DT": "string, #req, #met", # // Destination Terminal. Found beside 'Origin Terminal'",

    "delivery_date": "string, #req, #met", # //G62.01 = 17 or 68 || 5/30/2023 date prefixed by 'Must Delivery by' in document. MM/DD/YYYY or MM/DD/YY are both accepted.",
    "delivery_time.time": "string, #req", # // Found next to 'delivery_date' // G62.04 - Required. HH:MM or HH:MM:SS. Both work. Found at top right corner of first page under shipment_date.",
    "delivery_time.meridien": "AM/PM, #req",
    "delivery_time.timezone": "string, #ona", 

    "ready_date": "string, #mna, #met", # // MM/DD/YYYY or MM/DD/YY. Labelled as ETA on top right corner.",
    "ready_time.time": "string, #mna", # // Found next to 'ready_date' // Required. HH:MM or HH:MM:SS. Both work. Found at top right corner of first page under shipment_date.",
    "ready_time.meridien": "AM/PM, #mna",
    "ready_time.timezone": "string, #ona", # // Expressed in UTC+/-"

    "shipper.name": "string, #req, #met", # // N1*SH*N1.02, Found in top left corner. e.g: 'SAVANNAH INTL TRADE'",
    "shipper.address.street": "string, #req, #met", # // N3.01, Found under 'shipper_name', e.g: 'ONE INTRERNATIONAL DRIVE ATTN: ENCORE-INHOUSE AV DEPT'",
    "shipper.address.city": "string, #req, #met", # // N4.01, Found under 'address', e.g 'SAVANNAH'",
    "shipper.address.state": "string, #req, #met", # // N4.02Found in same line as 'city' above e.g 'GA'",
    "shipper.address.postal_code": "int, #req, #met", # // N4.03, Found in same line as 'city' and 'state' above e.g 31421",
    "shipper.address.country_code": "string, #req", # // N4.04,Found in next line. If United States of America -> 'US' (also default.)",
    "shipper.contact.name": "string, #mna, #met", # // G61.01 = DE + G61.02, e.g 'Michael Faber'",
    "shipper.contact.tel": "string, #mna, #met", # // G61.03 = TE + G61.04",
    "shipper.contact.fax": "string, #ona",
    "shipper.notes": "string, #ona", # anything extra in address section

    "consignee.name": "string, #req, #met", # // N1*CN*N1.02,Found in top left corner. e.g: '3923 - ENCORE WAREHOUSE OPS NEW ORLEANS'",
    "consignee.address.street": "string, #req, #met", # // N3.01, Found under 'shipper_name', e.g: 'O2605 DELAWARE AVENUE'",
    "consignee.address.city": "string, #req, #met", # // N4.01, Found under 'address', e.g 'KENNER'",
    "consignee.address.state": "string, #req, #met", # // N4.02Found in same line as 'city' above e.g 'LA'",
    "consignee.address.postal_code": "int, #req, #met", # // N4.03 Found in same line as 'city' and 'state' above e.g 31421",
    "consignee.address.country_code": "string, #req", # // N4.04, Found in next line. If United States of America -> 'US' (also default.)"
    "consignee.contact.name": "string, #ona, #met", # // G61.01 = DE + G61.02, e.g 'Ken Jones'",
    "consignee.contact.tel": "string, #mna, #met", # // G61.03 = TE + G61.04",
    "consignee.contact.fax": "string, #ona",
    "consignee.notes": "string, #ona", # anything extra in address section
    
    "carrier.name": "string, #req", # // Found in top center. E.g 'FORWARD AIR, INC.'",
    "carrier.address.street": "string, #ona", # // Not found. Return ''",
    "carrier.address.city": "string, #ona", # // Not found. Return ''",
    "carrier.address.state": "string, #ona", # // Not found. Return ''",
    "carrier.address.postal_code": "int, #ona", # // Not found. Return ''",
    "carrier.address.country_code": "string, #ona", # // Not found. Return ''"
    "carrier.contact.name": "string, #ona", # // e.g 'Michael Faber'",
    "carrier.contact.tel": "string, #ona",
    "carrier.contact.fax": "string, #ona",

    "goods.net_weight": "int, #req, #met", # // AT.03 = P + AT.05, Found at top center.",
    "goods.no_of_pieces": "int, #req, #met", # // AT1.01,  Found at top center.",
    "goods.pieces": [
        {
            "goods.piece.description": "string, #req, #met", # // AT4.01",
            "goods.piece.dimensions": "string, #req, #met", # // AT4.01",
            "goods.piece.weight": "int, #req, #met", # // AT4.01"
        }
    ],

    "PRG": "string, #ona", # // Identifiers and References (NOT FOUND IN OMNI...) // Labelled 'prg' in file.",
    "REF": "string, #ona", #// Identifiers and References (NOT FOUND IN OMNI...) // Labelled as Reference or Ref#.",
    "CR": "string, #ona", # // Identifiers and References (NOT FOUND IN OMNI...) // Labelled as Customer Reference.",
    "BOL": "string, #ona", # // Identifiers and References (NOT FOUND IN OMNI...) // Lablled Master Bill of Lading number or Bill of Lading Number."
}