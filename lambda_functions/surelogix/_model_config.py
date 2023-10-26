from .postprocessing.ace_forwarding import ACEForwardBOLPostprocessor
from .postprocessing.allstates_hawb import AllStatesHAWBPostprocessing
from .postprocessing.alg import ALGPostprocessing
from .postprocessing.pegasus_da import PegasusDAPostprocessor
from .postprocessing.pegasus_pickupalert import PegasusPickupAlert
from .postprocessing.sba import SBAPostprocessing, SBADRPostprocessing
from .postprocessing.tazmanian import TazmanianPostprocessing
from .postprocessing.trump_card import TrumpCardPostprocessing
from .postprocessing.teamworldwide import TeamWWPostprocessing
from .postprocessing.omni import OmniLogisticsHWABPostprocessing
from .postprocessing.larson import LarsonExecutor
from .postprocessing.dba import DBADeliveryAlertPostprocessing, DBAPickupAlertPostprocessing
from .postprocessing.pegasus_hawb import PegasusHAWB
from .postprocessing.sba_da import SBADA
from .postprocessing.icat_hawb import ICATHAWB
from .postprocessing.aircarego_hawb import AirCareGoHAWB
from .postprocessing.aeronet_hawb import AeronetHAWB
from .postprocessing.icat_da import ICATDA
from .postprocessing.stevens_da_dr import StevensDaDrExecutor
from .postprocessing.allstates_da import AllstatesDA
from .postprocessing.omni_da import OmniDA
from .postprocessing.alg_pu import ALGPickupAlert

import warnings

warnings.filterwarnings("ignore")

postprocessing_map = {
    'surelogix-sba-v2': SBAPostprocessing,
    'surelogix-da-trumpcard-v5': TrumpCardPostprocessing,
    'surelogix-da-teamworldwide-v2': TeamWWPostprocessing,
    'surelogix-am-alg-v1': ALGPostprocessing,
    'surelogix-hw-omni-v2': OmniLogisticsHWABPostprocessing,
    'surelogix-da-dba-v4': DBADeliveryAlertPostprocessing,
    'surelogix-mrgpod-larson-v1': LarsonExecutor,
    'surelogix-hawb-pegasus-v1': PegasusHAWB,
    'surelogix-dr-sba-v4': SBADRPostprocessing,
    'surelogix-da-sba-v2': SBADA,
    'surelogix-hawb-allstates-v3': AllStatesHAWBPostprocessing,
    'surelogix-hawb-icat-v2': ICATHAWB,
    'surelogix-da-tazmanian-v1': TazmanianPostprocessing,
    'surelogix-bol-aceforwarding-v1':ACEForwardBOLPostprocessor,
    'surelogix-da-pegasus-v4': PegasusDAPostprocessor,
    'surelogix-hawb-aircarego-v3': AirCareGoHAWB,
    'surelogix-hawb-aeronet-v6': AeronetHAWB,
    'surelogix-da-icat-v3': ICATDA,
    'surelogix-da-dr-stevens-v6': StevensDaDrExecutor,
    'surelogix-da-allstates-v3': AllstatesDA,
    'surelogix-da-omni-v5': OmniDA,
    'surelogix-pickupalert-dba-v2':DBAPickupAlertPostprocessing,
    'surelogix-pickupalert-pegasus-v3': PegasusPickupAlert,
    'surelogix-pu-alg-v3': ALGPickupAlert,

}
