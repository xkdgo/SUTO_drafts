#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import glob
import logging
import collections
from optparse import OptionParser
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache
try:
    import queue as queue
except ImportError:
    import Queue as queue
import threading
import multiprocessing
from multiprocessing import Pool
import datetime


NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


class Counter(object):
    def __init__(self):
        self.processed = 0
        self.errors = 0


class LineProcessor(threading.Thread):
    def __init__(self, line_in_queue,
                 counter_instance,
                 device_memc,
                 memc_queues,
                 errors_lock,
                 processed_lock):
        threading.Thread.__init__(self)
        self.in_queue = line_in_queue
        self.counter = counter_instance
        self.errors_lock = errors_lock
        self.processed_lock = processed_lock
        self.device_memc = device_memc
        self.memc_queues = memc_queues

    def run(self):
        while True:
            # Get from queue job
            line = self.in_queue.get()
            self.process_line(line)
            # signals to queue job is done
            self.in_queue.task_done()

    def process_line(self, line):
        line = line.decode("utf-8")
        line = line.strip()
        if not line:
            return
        appsinstalled = self.parse_appsinstalled(line)
        if not appsinstalled:
            with self.errors_lock:
                self.counter.errors += 1
        memc_addr = self.device_memc.get(appsinstalled.dev_type)
        if not memc_addr:
            with self.errors_lock:
                self.counter.errors += 1
                logging.error("Unknow device type: %s" % appsinstalled.dev_type)
            return
        self.memc_queues[memc_addr].put(appsinstalled)


        # ok = insert_appsinstalled(memc_addr, appsinstalled, options.dry)
        # if ok:
        #     self.counter_instance.processed += 1
        # else:
        #     self.counter_instance.errors += 1

    def parse_appsinstalled(self, line):
        line_parts = line.strip().split("\t")
        if len(line_parts) < 5:
            return
        dev_type, dev_id, lat, lon, raw_apps = line_parts
        if not dev_type or not dev_id:
            return
        try:
            apps = [int(a.strip()) for a in raw_apps.split(",")]
        except ValueError:
            apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
            logging.info("Not all user apps are digits: `%s`" % line)
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            logging.info("Invalid geo coords: `%s`" % line)
        return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled_old(memc_addr, appsinstalled, dry_run=False):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    # @TODO persistent connection
    # @TODO retry and timeouts!
    try:
        if dry_run:
            logging.debug("%s - %s -> %s" % (memc_addr, key, str(ua).replace("\n", " ")))
        else:
            memc = memcache.Client([memc_addr])
            memc.set(key, packed)
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (memc_addr, e))
        return False
    return True


def insert_appsinstalled(memc_addr, memc_queue, errors_lock, processed_lock, counter, pool, dry_run=False):
    memc = memcache.Client([memc_addr], socket_timeout=1)
    while True:
        appsinstalled = memc_queue.get()
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
        ua.apps.extend(appsinstalled.apps)
        packed = pool.apply(ua.SerializeToString, ())
        # @TODO persistent connection
        # @TODO retry and timeouts!
        try:
            if dry_run:
                logging.debug("%s - %s -> %s" % (memc_addr, key, str(ua).replace("\n", " ")))
            else:
                memc.set(key, packed)
        except Exception as e:
            logging.exception("Cannot write to memc %s: %s" % (memc_addr, e))
            with errors_lock:
                counter.errors += 1
                memc_queue.task_done()
                continue
                # return False
        with processed_lock:
            counter.processed += 1
        memc_queue.task_done()
        # return True


def main(options):
    start_time = datetime.datetime.now()
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }
    for fn in glob.iglob(options.pattern):
        line_process_in_queue = queue.Queue(maxsize=100000)
        errors_lock = threading.RLock()
        processed_lock = threading.RLock()
        memc_queues = {memc_addr: queue.Queue(maxsize=100000)
                       for memc_addr in device_memc.values()}
        counter = Counter()
        writers = []
        pool = Pool()
        #(processes=2, maxtasksperchild=1000)
        n_thread = 20
        for _ in range(n_thread):
            t = LineProcessor(line_process_in_queue,
                              counter,
                              device_memc,
                              memc_queues,
                              errors_lock,
                              processed_lock)
            t.setDaemon(True)
            # Start thread
            t.start()
        for memc_addr, memc_queue in memc_queues.items():
            writer = threading.Thread(
                name='memc-writer-{}'.format(memc_addr),
                target=insert_appsinstalled,
                args=(memc_addr, memc_queue, errors_lock, processed_lock, counter, pool, options.dry)
            )
            writer.setDaemon(True)
            writer.start()
            writers.append(writer)

        logging.info('Processing %s' % fn)
        fd = gzip.open(fn)
        for line in fd:
            line_process_in_queue.put(line)
        line_process_in_queue.join()
        for q in memc_queues.values():
            q.join()

        if not counter.processed:
            fd.close()
            dot_rename(fn)
            continue
        # count statistics
        err_rate = float(counter.errors) / counter.processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
        fd.close()
        dot_rename(fn)
        logging.info('Total runtime: %s' % (datetime.datetime.now() - start_time))


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
