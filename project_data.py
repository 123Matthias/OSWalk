from typing import Tuple
import psutil

class ProjectData:

    _physical_cores = None
    _logical_cores = None
    

    @classmethod
    def _get_physical_and_logical_cores(cls) -> Tuple[int, int]:
        """Gibt Tuple (physische, logische) Kerne zurück"""
        if cls._physical_cores is not None and cls._logical_cores is not None:
            return cls._physical_cores, cls._logical_cores

        phys = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True) or 1

        cls._physical_cores = phys
        cls._logical_cores = logical

        return phys, logical

    @classmethod
    def get_process_cores(cls) -> int:
        """Gibt die Anzahl der CPU-Kerne für Prozesse zurück (physisch bevorzugt)"""
        physical_cores, logical_cores = cls._get_physical_and_logical_cores()
        process_cores = 1
        if physical_cores is not None:
            process_cores = physical_cores
        elif logical_cores is not None:
            process_cores = logical_cores
        print(
            f"Physische Kerne: {physical_cores or 'nicht erkannt'}\n"
            f"Logische Kerne: {logical_cores or 'nicht erkannt'}\n"
            f"Verwende für Prozesse: {process_cores}"
        )
        return process_cores