from enum import StrEnum

DOMAIN = "heatpump_controller"
CONTROLLER = "controller"


class ControlAlgorithm(StrEnum):
    MANUAL = "manual"
    WEIGHTED_AVERAGE = "weighted_average"

    @property
    def label(self):
        labels = {
            "manual": "Manual",
            "weighted_average": "Weighted Average",
        }
        return labels[self.value]
