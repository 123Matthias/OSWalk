#####################################################################################################################
# Statische Hilfsfunktionen für Multiprocessing in Python                                                           #
# Threads haben GIL (Global Interpreter Lock, darum sind CPU lastige Aufgaben mit Threads nicht parallel            #
# Threads sind nur bei I/O lastigen Dingen echte Beschleunigung da sie an der gleichen Interpreter Instanz laufen   #
# Multiprocessing erstellt eigene Interpreter Instance für jeden Process                                            #
#####################################################################################################################
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


class SearchProcess:

    @staticmethod
    def process_chunk_static(dateien_chunk, keywords, search_depth, threads_per_process, chunk_id, basis_pfad, progress_queue):
        """OPTIMIERT: Mit besseren Werten für Threads"""
        try:
            from Service.reader_service import ReaderService
            reader = ReaderService()
            keyword_list = [k.strip().lower() for k in keywords.replace(',', ' ').split()]
            treffer = []
            chunk_size = len(dateien_chunk)

            # Thread Executor
            with ThreadPoolExecutor(max_workers=threads_per_process) as executor:
                futures = {}  # dictionary
                for dateipfad in dateien_chunk:
                    future = executor.submit(
                        SearchProcess._process_single_file_static,
                        dateipfad,
                        keyword_list,
                        reader,
                        search_depth,
                        basis_pfad
                    )
                    futures[future] = dateipfad

                verarbeitet_im_chunk = 0
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        treffer.append(result)
                        progress_queue.put(('treffer', result))

                    verarbeitet_im_chunk += 1
                    # Progress nur alle 5 Dateien (reduziert Queue-Last)
                    if verarbeitet_im_chunk % 5 == 0 or verarbeitet_im_chunk == chunk_size:
                        progress_queue.put(('progress', chunk_id, verarbeitet_im_chunk, chunk_size))

            return []

        except Exception as e:
            print(f"❌ KRITISCHER FEHLER in Prozess {chunk_id}: {e}")
            return []

    @staticmethod
    def _process_single_file_static(dateipfad, keyword_list, reader, search_depth, basis_pfad):
        """Schnellere Textsuche"""
        try:
            # 🔥 max_chars erhöht für bessere Trefferquote
            text = reader.extract_text(dateipfad, search_depth)
            if not text:
                return None

            # 🔥 Einmal lower() für alle Keywords
            text_lower = text.lower()
            found = False
            priority = 0
            dateiname = None
            kontext = None
            is_text_generated = False
            # 🔥 Keyword-Check in einem Durchgang
            for i, keyword in enumerate(keyword_list, start=0):
                if keyword in text_lower:
                    found = True
                    priority += len(keyword_list) - i
                    if not is_text_generated: # Kontext wird aus erstem treffer erzeugt.
                        kontext = SearchProcess._make_body_text_static(text, keyword, ctx=250)
                        dateiname = os.path.basename(dateipfad)
                        is_text_generated = True
            if found:
                return priority, "content", dateiname, dateipfad, kontext

        except Exception as e:
            print(f"❌ FEHLER in main_page_controller in Method process_single_file_static {e}")
        return None

    @staticmethod
    def _make_body_text_static(text, keyword, ctx=300):
        """Keine Instance Methoden für Multiprocessing in Python (Ansonsten Pickling fehler) """
        if not text or not keyword:
            return None

        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return None

        start = max(0, idx - ctx)
        end = min(len(text), idx + len(keyword) + ctx)

        kontext = text[start:end].replace("\n", " ").replace("\r", " ")
        kontext = ' '.join(kontext.split())
        return kontext
