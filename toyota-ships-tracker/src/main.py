import asyncio
import json
import pprint
from websockets.client import connect
import requests
import json
import re

AREA = {
    "spain":
    {
        "minLong": -9.39288367353,
        "minLat": 35.946850084,
        "maxLong": 3.03948408368,
        "maxLat": 43.7483377142
    },
    "turkey":
    {
        "minLong": 26.0433512713,
        "minLat": 36.6442752148,
        "maxLong": 41.72013409,
        "maxLat": 42.1414848903
    },
    "uk":
    {
        "minLong": -8.62138941888,
        "minLat": 49.911659884,
        "maxLong": 1.76891429291,
        "maxLat": 59.3606990054
    }
}

NAVIGATIONAL_STATUS = {
    0: "en ruta empleando motor",
    1: "fondeado",
    2: "sin gobierno (a la deriva)",
    3: "maniobrabilidad restringida",
    4: "restringido por su calado",
    5: "amarrado",
    6: "encallado",
    7: "dedicado a la pesca",
    8: "navegación a vela",
    9: "reservado para futuras modificaciones del estado de navegación para buques que transporten DG, HS o MP, o categoría de peligro o contaminante de la IMO, embarcaciones de alta velocidad (HSC)",
    10: "reservado para futuras modificaciones del estado de navegación para buques que transporten mercancías peligrosas (DG), sustancias nocivas (HS) o contaminantes marinos (MP), o categoría de peligro o contaminante de la IMO, ala en tierra (WIG)",
    11: "buque de motor remolcando hacia atrás (uso regional)",
    12: "buque de motor empujando hacia adelante o remolcando a lo largo (uso regional)",
    13: "reservado para uso futuro",
    14: "AIS-SART (activo), MOB-AIS, EPIRB-AIS",
    15: "indefinido=por defecto (también utilizado por AIS-SART, MOB-AIS y EPIRB-AIS en pruebas)",
}

PORTS = {
    "GBAVO": "Bristol",
    "GBPRU": "Portbury",
    "GBSOU": "Southampton",
    "TRDRC": "Derince",
    "ESSAG": "Sagunto",
    "ESVGO": "Vigo",
    "NLVLI": "Vlissingen",
    "DEBRV": "Bremerhaven",
    "TRAUT": "Avcilar",
    "GRPIR": "Piraeus",
    "ITLIV": "Livorno",
    "ITPAO": "Palermo",
    "BEZEE": "Zeebrugge",
    "QTLIV": "Livorno",
    "EGPSD": "Port Said",
    "THLCH": "Laem Chabang",
    "TRYEN": "Yenikoy",
    "ESSDR": "Santander",
    "ESPAS": "Pasajes"
}

BOATS = {
    308038000:
    {
        'Latitude': None,
        'Longitude': None,
        'NavigationalStatus': None,
        'UserID': 308038000,
        'Origin': None,
        'Destination': None,
        'MaximumStaticDraught': None,
        'Name': 'CORAL LEADER'
    },
    308688000:
    {
        'Latitude': None,
        'Longitude': None,
        'NavigationalStatus': None,
        'UserID': 308688000,
        'Origin': None,
        'Destination': None,
        'MaximumStaticDraught': None,
        'Name': 'EMERALD LEADER'
    },
    355948000:
    {
        'Latitude': None,
        'Longitude': None,
        'NavigationalStatus': None,
        'UserID': 355948000,
        'Origin': None,
        'Destination': None,
        'MaximumStaticDraught': None,
        'Name': 'VEGA LEADER'
    },
    538009723:
    {
        'Latitude': None,
        'Longitude': None,
        'NavigationalStatus': None,
        'UserID': 538009723,
        'Origin': None,
        'Destination': None,
        'MaximumStaticDraught': None,
        'Name': 'VIKING AMBER'
    },
    255805907:
    {
        'Latitude': None,
        'Longitude': None,
        'NavigationalStatus': None,
        'UserID': 255805907,
        'Origin': None,
        'Destination': None,
        'MaximumStaticDraught': None,
        'Name': 'AUTO ECO'
    },
}


def from_ports():
    """Ports from where the boats are coming"""
    return [PORTS["GBPRU"], PORTS["GBAVO"], PORTS["ESVGO"], PORTS["TRDRC"], PORTS["ITLIV"], PORTS["ITPAO"]]


def to_ports():
    """Ports to where the boats are going"""
    return [PORTS["ESVGO"], PORTS["ESSAG"], PORTS["GBPRU"], PORTS["GBAVO"]],


def process_destination(destination):
    """Process destination, the destination comes in different formats, this function tries to normalize it"""
    frm = None
    to = None
    if destination.count('>') == 1:
        frm = re.sub(r'\s+', '', destination.split('>')[0].strip())
        to = re.sub(r'\s+', '', destination.split('>')[1].strip())
        if frm in PORTS:
            frm = PORTS[frm]
        if to in PORTS:
            to = PORTS[to]
    elif len(destination) >= 10:
        frm = re.sub(r'\s+', '', destination.strip())[:5]
        to = re.sub(r'\s+', '', destination.strip())[-5:]
        if frm in PORTS:
            frm = PORTS[frm]
        if to in PORTS:
            to = PORTS[to]
    else:
        frm = re.sub(r'\s+', '', destination.strip())
        if frm in PORTS:
            frm = PORTS[frm]
    return frm, to


def process_position_report(message, boat_mmsi):
    """Process position report"""

    result = {}
    position_report = message['Message']['PositionReport']
    BOATS[boat_mmsi]['Latitude'] = position_report['Latitude']
    BOATS[boat_mmsi]['Longitude'] = position_report['Longitude']
    if BOATS[boat_mmsi]['NavigationalStatus'] != NAVIGATIONAL_STATUS[position_report['NavigationalStatus']]:
        BOATS[boat_mmsi]['NavigationalStatus'] = NAVIGATIONAL_STATUS[position_report['NavigationalStatus']]
        if BOATS[boat_mmsi]['Origin']:
            result.update(BOATS[boat_mmsi])
    return result


def process_ship_static_data(message, boat_mmsi):
    """Process ship static data"""
    result = {}
    ship_static_data = message['Message']['ShipStaticData']
    BOATS[boat_mmsi]['MaximumStaticDraught'] = ship_static_data['MaximumStaticDraught']
    frm, to = process_destination(ship_static_data['Destination'])
    if frm != BOATS[boat_mmsi]['Origin'] or to != BOATS[boat_mmsi]['Destination']:
        if frm:
            BOATS[boat_mmsi]['Origin'] = frm
        if to:
            BOATS[boat_mmsi]['Destination'] = to
        if BOATS[boat_mmsi]['Longitude'] and BOATS[boat_mmsi]['Latitude']:
            if frm in from_ports() and BOATS[boat_mmsi]['Destination'] and BOATS[boat_mmsi]['Destination'] in to_ports():
                result.update(BOATS[boat_mmsi])
    return result


async def connect_ais_stream():
    async with connect("wss://stream.aisstream.io/v0/stream") as websocket:
        subscribe_message = {
            "APIKey": "",  # you need to put your API key from https://aisstream.io here
            "BoundingBoxes": [
                # [[-50,  65],[-28, 75]]
                [[-90, -180], [90, 180]]
            ],
            "MessageTypes": [
                "PositionReport",
                "ShipStaticData"
            ]

        }

        subscribe_message_json = json.dumps(subscribe_message)

        await websocket.send(subscribe_message_json)

        async for message_json in websocket:
            message = json.loads(message_json)
            message_type = message["MessageType"]
            boat_mmsi = message['MetaData']['MMSI']

            result = {}
            if (message_type == "PositionReport") and boat_mmsi in BOATS:
                result = process_position_report(message, boat_mmsi)
            elif (message_type == "ShipStaticData") and boat_mmsi in BOATS:
                result = process_ship_static_data(message, boat_mmsi)
            if result:
                pprint.pprint(result)
                try:
                    # you need to put your endpoint here
                    requests.post('http://', json=result, timeout=30)
                except Exception as e:
                    raise e

if __name__ == "__main__":
    print("Starting...")
    asyncio.run(connect_ais_stream())
