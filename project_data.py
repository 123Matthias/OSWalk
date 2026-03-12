import math
from typing import Tuple
import psutil

class ProjectData:

    _physical_cores = None
    _logical_cores = None

    keyword_weight = False
    search_depth = 4000
    snippet_size = 250
    default_search_path = "~"
    language = "English"

    @classmethod
    def set_language(cls, language):
        cls.language = language

    @classmethod
    def set_settings(cls, keyword_weight, search_depth, snippet_size, default_search_path, language):
        cls.keyword_weight = keyword_weight
        cls.search_depth = search_depth
        cls.snippet_size = snippet_size
        cls.default_search_path = default_search_path
        cls.language = language
    

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
        return process_cores

    @classmethod
    def get_used_cores(cls):
        """80% der verfügbaren Cores nutzen, mindestens 1"""
        used = math.floor(cls.get_process_cores() * 0.8)
        used = 1 if used < 1 else used
        return used

    @classmethod
    def get_threads_count(cls):
        return 4