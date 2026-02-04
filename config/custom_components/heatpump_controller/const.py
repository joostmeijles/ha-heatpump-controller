from enum import StrEnum

DOMAIN = "heatpump_controller"
CONTROLLER = "controller"

HEATPUMP_CONTROLLER_FRIENDLY_NAME = "Heatpump Controller"


class ControlAlgorithm(StrEnum):
    MANUAL = "manual"
    WEIGHTED_AVERAGE = "weighted_average"
    WEIGHTED_AVERAGE_OUTDOOR_TEMP = "weighted_average_outdoor_temp"
    LWT_CONTROL = "lwt_control"

    @property
    def label(self):
        labels = {
            "manual": "Manual",
            "weighted_average": "Weighted Average",
            "weighted_average_outdoor_temp": "Weighted Average with Outdoor Temp",
            "lwt_control": "LWT Control",
        }
        return labels[self.value]
