slx_output_format = {
    "scac": "string, req, // SCAC CODE=OMNG [ISA | GS | BOL.01] Will be gotten from SCAC list file depending on what kind of file it is (Omni, Larson etc, for e.g Omni's SCAC is OMNG)",
    "shipment_identifier": "string, req, // BOL.03 || 1958, SO OP14512973 Required. Reference number, or waybill number, or PO number, or even container number if all else fails",
    "shipment_date": "string, req, // BOL.04 + BOL.05 Required. MM/DD/YYYY or MM/DD/YY. Found at top right corner of first page.",
    "shipment_time": {
        "time": "string, req, // BOL.04 + BOL.05 Required. HH:MM or HH:MM:SS. Both work. Found at top right corner of first page under shipment_date.",
        "meridien": "AM | PM, req",
        "timezone": "string, req // Expressed in UTC+/-"
    },
    "payment_method": "CD | PP | CC, req, mna, // Required. CC - Collect on Delivery. PP - Prepaid (default.) CC - Carrier Collect. Can be found anywhere in the file, if not found default to PP.",

    "PO": "string, // Found in last line in Shipper information. 4 digit number. E.G 1958.",
    "MA": "string, req, // Labelled Master Air Waybill. Found as labelled around top left side of first page.",
    "BM": "string, req, // Labelled 'Airbill #'. Found as labelled around top left side of first page under MA.",
    "SI": "string, req, // Special Instructions. Any additional notes like: FRAGILE - HANDLE WITH CARE! DO NOT DOUBLE STACK OR BREAK DOWN SKIDS.",
    "OT": "string, req, // Origin Terminal. Found around top right corner.",
    "DT": "string, req, // Destination Terminal. Found beside 'Origin Terminal'",

    "handling": "PUC | PUD, req, // Required PUD || AT5.01 = DEL or PUD (Delivery Alert) if it is a delivery (alert) file, PUC otherwise.",
    "delivery_date": "string, req, //G62.01 = 17 or 68 || 5/30/2023 date prefixed by 'Must Delivery by' in document. MM/DD/YYYY or MM/DD/YY are both accepted.",
    "delivery_time": {
        "time": "string, req, // Found next to 'delivery_date' // G62.04 - Required. HH:MM or HH:MM:SS. Both work. Found at top right corner of first page under shipment_date.",
        "meridien": "AM | PM",
        "timezone": "string, // Expressed in UTC+/-"
    },
    "ready_date": "string, // MM/DD/YYYY or MM/DD/YY. Labelled as ETA on top right corner.",
    "ready_time": {
        "time": "string, req, // Found next to 'ready_date' // Required. HH:MM or HH:MM:SS. Both work. Found at top right corner of first page under shipment_date.",
        "meridien": "AM | PM",
        "timezone": "string, // Expressed in UTC+/-"
    },

    "shipper": {
        "name": "string, req, // N1*SH*N1.02, Found in top left corner. e.g: 'SAVANNAH INTL TRADE'",
        "address": {
            "street": "string, req, // N3.01, Found under 'shipper_name', e.g: 'ONE INTRERNATIONAL DRIVE ATTN: ENCORE-INHOUSE AV DEPT'",
            "city": "string, req, // N4.01, Found under 'address', e.g 'SAVANNAH'",
            "state": "string, req, // N4.02Found in same line as 'city' above e.g 'GA'",
            "postal_code": "number, req, // N4.03, Found in same line as 'city' and 'state' above e.g 31421",
            "country_code": "string, req, // N4.04,Found in next line. If United States of America -> 'US' (also default.)"
        },
        "contact": {
            "name": "string, req, // G61.01 = DE + G61.02, e.g 'Michael Faber'",
            "tel": "string, req, // G61.03 = TE + G61.04",
            "fax": "string, ona"
        },
        "notes": ""
    },

    "consignee": {
        "name": "string, req, // N1*CN*N1.02,Found in top left corner. e.g: '3923 - ENCORE WAREHOUSE OPS NEW ORLEANS'",
        "address": {
            "street": "string, req, // N3.01, Found under 'shipper_name', e.g: 'O2605 DELAWARE AVENUE'",
            "city": "string, req, // N4.01, Found under 'address', e.g 'KENNER'",
            "state": "string, req, // N4.02Found in same line as 'city' above e.g 'LA'",
            "postal_code": "number, req, // N4.03 Found in same line as 'city' and 'state' above e.g 31421",
            "country_code": "string, req, // N4.04, Found in next line. If United States of America -> 'US' (also default.)"
        },
        "contact": {
            "name": "string, ona, // G61.01 = DE + G61.02, e.g 'Ken Jones'",
            "tel": "string, req, // G61.03 = TE + G61.04",
            "fax": "string, ona"
        },
        "notes": ""
    },

    "carrier": {
        "name": "string, req, // Found in top center. E.g 'FORWARD AIR, INC.'",
        "address": {
            "street": "string, ona, // Not found. Return ''",
            "city": "string, ona, // Not found. Return ''",
            "state": "string, ona, // Not found. Return ''",
            "postal_code": "number, ona, // Not found. Return ''",
            "country_code": "string, ona, // Not found. Return ''"
        },
        "contact": {
            "name": "string, // e.g 'Michael Faber'",
            "tel": "string",
            "fax": "string"
        }
    },

    "goods": {
        "net_weight": "number, req, // AT.03 = P + AT.05, Found at top center.",
        "no_of_pieces": "number, req, // AT1.01,  Found at top center.",
        "pieces": [
        {
            "description": "string, req, // AT4.01",
            "dimensions": "string, req, // AT4.01",
            "weight": "number, req, // AT4.01"
        },
        {
            "description": "string, req, // AT4.01",
            "dimensions": "string, req, // AT4.01",
            "weight": "number, req, // AT4.01"
        }
        ]
    },

    "PRG": "string, ona, // Identifiers and References (NOT FOUND IN OMNI...) // Labelled 'prg' in file.",
    "REF": "string, ona, // Identifiers and References (NOT FOUND IN OMNI...) // Labelled as Reference or Ref#.",
    "CR": "string, ona, // Identifiers and References (NOT FOUND IN OMNI...) // Labelled as Customer Reference.",
    "BOL": "string, ona, // Identifiers and References (NOT FOUND IN OMNI...) // Lablled Master Bill of Lading number or Bill of Lading Number."
}