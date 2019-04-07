import sqlite3
import os.path
import os
import asyncio
import time
import pickle
from concurrent.futures import ThreadPoolExecutor

from misc import *


async def safe_cancel(task):
    """Cancel task without exceptions."""
    if not (task.done() or task.cancelled()):
        try:
            task.cancel()
        except asyncio.CancelledError:
            pass

###########################################
############## Local cache ################
###########################################

class Cache:
    """Core class that will search and write in cache asynchronously."""
    def __init__(self):
        """False constructor needed because it can't be asyn."""
        self.engine = None
        self.uci_pk = None
        self.writing = None
        self.ready = None
        self.reading_task = None
        self.writing_task = None
        self.found = None
        self.fetch = None
        self.writer = None
        self.reader = None
        self.engine_options = None
        self.filename = None

    def __del__(self):
        """Close DBs."""
        self.writer.close()
        self.reader.close()
        self.pool.shutdown()

    async def load(self, mio, filename, engine, engine_options):
        """Initialize cache. Real constructor.
            - mio : cache size in Mio
            - filename : filename of the cachefile
        """
        # Stored values to avoid copies
        self.filename = filename
        self.engine = engine
        self.engine_options = engine_options
        self.uci_pk = None
       
        kio = mio*1024
        init_needed = False

        # Create cache file if needed
        if not os.path.isfile(filename):
            open(filename, "w")
            init_needed = True

        # Needed to follow asynchronous op
        self.writing = False
        self.ready = True
        self.reading_task = None
        self.writing_tasks = None

        # Needed for search in cache
        self.found = None
        self.fetch = dict()

        # Separate I/O to optimize reading speed
        self.writer = sqlite3.connect(filename, isolation_level=None)
        self.writer.row_factory = sqlite3.Row # enable naming
        self.reader = sqlite3.connect(filename, isolation_level=None)
        self.reader.row_factory = sqlite3.Row # enable naming

        # Authorize multiple readers as long as there's only one writer
        self.writer.execute("PRAGMA journal_mode=wal")
        self.reader.execute("PRAGMA journal_mode=wal")

        # Increase cache size
        self.reader.execute("PRAGMA cache_size=-{:d}".format(kio))

        # Force one reader only
        self.writer.execute("begin exclusive")

        if init_needed:
            await self.reset()

        # Add engine to cache
        await self.register_engine()

    ##########
    # Reading functions
    ##########
    async def search_fen(self, nodes, fen_hash, multipv):
        """Start searching for the hash inside local cache. Asynchronous."""
        if nodes == None:
            return

        async def _search_fen():
            self._wait_ready()
            req = self.reader.execute(
                '''SELECT pvs_data FROM (SELECT fen_hash, pvs_data, nodes from 
                        pvs natural join uci_search
                        group by search_id, fen_hash
                        having uci_id=?
                        and nodes >= ?
                        and fen_hash=?
                        and multipv >= ?)
                    GROUP BY fen_hash having nodes=MAX(nodes)
                    ''', (self.get_uci_pk(), nodes, blobify(fen_hash), multipv))

            r = req.fetchone()
            if r != None: # We found datas !!
                self.fetch[fen_hash] = pickle.loads(r['pvs_data'])[:multipv] # Keep only as much pvs as needed
            ##########

        if self.reading_task != None: # We found before search finished
            await safe_cancel(self.reading_task)

        self.reading_task = await asyncio.create_task(_search_fen())
        

    def fen_found(self, hash_fen):
        """Returns whether the hash was found or not."""
        return hash_fen in self.fetch

    def fetch_pvs(self, hash_fen):
        """Returns latest pvs found."""
        return self.fetch[hash_fen]

    def get_uci_pk(self):
        """Returns uci_id of the current engine. None if it fails."""
        self._wait_ready()
        if self.uci_pk != None: # Not already defined
            return self.uci_pk

    ##########
    # Writing functions
    ##########
    async def reset(self):
        """Drop and reset all tables. Asynchronous"""
        self._wait() # Wait for writing
        self._lock()
        self.ready = False

        # drop tables
        for tb_name in ["key", "pair", "config", "appair", "engine", "uci_engine", "uci_search", "fen", "pv"]:
            self.writer.execute('''DROP TABLE IF EXISTS {:s}'''.format(tb_name))

        # Tables creation
        self.writer.execute(
            '''CREATE TABLE key (
            key_id INTEGER PRIMARY KEY,
            key_str VARCHAR(32) UNIQUE )''')
        self.writer.execute(
            '''CREATE TABLE pair (
            pair_id INTEGER PRIMARY KEY,
            key_id INTEGER,
            value VARCHAR(64),
            FOREIGN KEY(key_id) REFERENCES key(key_id),
            CONSTRAINT UC_pair UNIQUE (key_id, value) )''')
        self.writer.execute(
            '''CREATE TABLE config (
            conf_id INTEGER PRIMARY KEY,
            hash_opt BLOB UNIQUE);''')
        self.writer.execute(
            '''CREATE TABLE appair (
            conf_id INTEGER,
            pair_id INTEGER,
            PRIMARY KEY(conf_id,pair_id),
            FOREIGN KEY(conf_id) REFERENCES config(conf_id),
            FOREIGN KEY(pair_id) REFERENCES pair(pair_id) ) WITHOUT ROWID''')
        self.writer.execute(
            '''CREATE TABLE engine (
            eng_id INTEGER PRIMARY KEY,
            eng_name VARCHAR(32) UNIQUE );''')
        self.writer.execute(
            '''CREATE TABLE uci_engine (
            uci_id INTEGER PRIMARY KEY,
            eng_id INTEGER,
            conf_id INTEGER,
            FOREIGN KEY(eng_id) REFERENCES engine(eng_id),
            FOREIGN KEY(conf_id) REFERENCES config(conf_id) )''')
        self.writer.execute(
            '''CREATE TABLE uci_search (
            search_id INTEGER PRIMARY KEY,
            uci_id,
            nodes INTEGER,
            multipv INTEGER,
            FOREIGN KEY(uci_id) REFERENCES uci_engine(uci_id),
            CONSTRAINT CK_nodes CHECK (nodes > 0),
            CONSTRAINT UC_search UNIQUE (uci_id, nodes) )''')
        self.writer.execute(
            '''CREATE TABLE fen (
            fen_hash BLOB PRIMARY KEY,
            fen_str VARCHAR(128) UNIQUE )''')
        self.writer.execute(
            '''CREATE TABLE pvs (
            pv_id INTEGER PRIMARY KEY,
            fen_hash BLOB,
            search_id INTEGER,
            pvs_data BLOB,
            FOREIGN KEY(fen_hash) REFERENCES fen(fen_hash),
            FOREIGN KEY(search_id) REFERENCES uci_search(search_id)
            CONSTRAINT UC_pvs UNIQUE (fen_hash, search_id) )''')
        
        self.writer.execute("COMMIT")

        #unlock
        self.ready = True
        self._unlock()


    async def save_fen(self, fen, nodes, multipv, pvs):
        """Save pvs in local cache. Asynchronous."""
        async def _write_fen():
            self._wait()
            self._wait_ready()
            self._lock()

            hf = hash_fen(fen)
            hf_blob = blobify(hf)

            # Add fen to db
            self.writer.execute(
                '''INSERT OR IGNORE INTO fen(fen_hash, fen_str)
                VALUES (?,?)''', (hf_blob, fen))

            # Add search params
            self.writer.execute(
                '''INSERT OR IGNORE INTO uci_search(uci_id, nodes, multipv)
                VALUES (?,?,?)''', (self.get_uci_pk(), nodes, multipv))
            self.writer.commit()
            search_id = self.reader.execute(
                '''SELECT search_id FROM uci_search
                WHERE uci_id=? AND nodes=? AND multipv=?''', (self.get_uci_pk(), nodes, multipv)).fetchone()['search_id']

            # Insert pvs
            self.writer.execute('''
            INSERT OR IGNORE INTO pvs(fen_hash, search_id, pvs_data)
            VALUES (?,?,?)''', (hf_blob, search_id, pickle.dumps(pvs, protocol=pickle.HIGHEST_PROTOCOL)))
            self._unlock()

        if not (hash_fen(fen) in self.fetch):
            self.writing_task = asyncio.create_task(_write_fen())

    async def register_engine(self):
        """Register engine and its config in the cache. Asynchronous"""
        if self.get_uci_pk() == None: # uci_engine doesn't exists yet
            self._wait()
            self._wait_ready()
            self._lock()
            self.ready = False # We can't add pvs if engine is not set

            # engine name
            self.writer.execute(
                '''INSERT OR IGNORE INTO engine(eng_name)
                VALUES (?);''', (self.engine.name,))

            # pairs
            opt_hash = hash_opt(self.engine_options)
            pair_ids = []

            for key,value in self.engine_options.items():
                self.writer.execute(
                    '''INSERT OR IGNORE INTO key(key_str)
                    VALUES (?)''', (key,))
                key_id = self.reader.execute(
                '''SELECT key_id FROM key where key_str=?''', (key,)).fetchone()['key_id']

                self.writer.execute(
                    '''INSERT OR IGNORE INTO pair(key_id,value)
                    VALUES (?,?)''', (key_id, value))

                pair_id = self.reader.execute(
                    '''SELECT pair_id FROM pair
                    WHERE key_id=? AND value=?''', (key_id, value)).fetchone()['pair_id']

                pair_ids += [pair_id]
        
            # create config
            self.writer.execute(
                '''INSERT OR IGNORE INTO config (hash_opt)
                VALUES (?)''', (opt_hash,))
            conf_id = self.reader.execute(
                '''SELECT conf_id FROM config
                WHERE hash_opt=?''', (opt_hash,)).fetchone()['conf_id']

            # appair
            for pair_id in pair_ids:
                self.writer.execute(
                    '''INSERT OR IGNORE INTO appair(conf_id,pair_id)
                    VALUES (?,?)''', (conf_id, pair_id))

            # uci engine
            self.writer.execute(
                '''INSERT INTO uci_engine(eng_id,conf_id)
                VALUES (
                (SELECT eng_id FROM engine WHERE eng_name=?),
                ?)''', (self.engine.name, conf_id))

            # set uci_pk
            self.uci_pk = self.reader.execute('''SELECT uci_id 
                FROM (uci_engine NATURAL JOIN config) NATURAL JOIN engine
                WHERE eng_name=? AND hash_opt=?''', 
                (self.engine.name, opt_hash)).fetchone()['uci_id']

            self.ready = True
            self._unlock()

    ##########
    # Sync functions
    ##########
    def _wait(self):
        """Wait for db to be ready for writing."""
        while self.writing:
            time.sleep(0.00001) # Sleep for 10 µs to not use full core

    def _lock(self):
        """Lock writing."""
        self.writing = True

    def _unlock(self):
        """Unlock writing."""
        self.writing = False

    def _wait_ready(self):
        """Wait until db is ready for read/write."""
        while not self.ready:
            time.sleep(0.00001) # Sleep for 10 µs to not use full core

    async def wait_write(self):
        if self.writing_task != None and not self.writing_task.done():
            await self.writing_task
