import os
from dataclasses import asdict
import bios
import dacite
from govee_api_laggat import GoveeAbstractLearningStorage, GoveeLearnedInfo
import logging

_LOGGER = logging.getLogger("lights_debug")


class YamlLearningStorage(GoveeAbstractLearningStorage):
    """Storage for govee_api_laggat to Save/Restore learned information for lamps."""

    def __init__(self, *args, **kwargs):
        """If you override __init__, call super."""
        self._filename = os.path.expanduser("./.govee_learning.yaml")
        self._changing_devices = []
        super().__init__(*args, **kwargs)

    async def read(self) -> dict[str, GoveeLearnedInfo]:
        """get the last saved learning information from disk, database, ... and return it."""
        learned_info = {}
        try:
            device_dict = bios.read(self._filename)

            learned_info = {
                device_str: dacite.from_dict(
                    data_class=GoveeLearnedInfo,
                    data=device_dict[device_str]
                )
                for device_str in device_dict
            }
            _LOGGER.info(
                "-- Loaded learning information from %s.",
                self._filename,
            )
        except Exception as ex:
            _LOGGER.warning(
                "-- Unable to load govee learned config from %s: %s. This is normal on first use.",
                self._filename, ex,
            )

        return learned_info

    async def write(self, learned_info: dict[str, GoveeLearnedInfo]):
        """Save this dictionary to disk."""
        leaned_dict = {device: asdict(learned_info[device]) for device in learned_info}
        bios.write(self._filename, leaned_dict)

        _LOGGER.info(
            "-- Saved learning information to %s.",
            self._filename,
        )
