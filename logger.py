# -----------------------------------------------------------------------------
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# bit4hamster collection
#
# Hamster desktop server: logger
#
# Author: Alexey Fedoseev <aleksey@fedoseev.net>, 2020
# -----------------------------------------------------------------------------

import os
import datetime
import time
import hamstersheet
from debug import dprint

class EventLogger(object):

    DATA_DIR = 'data'
    PATH_TEMPLATE = '{}/{}.log'
    SHEETS_PATH_TEMPLATE = '{}/sheets.log'
    PATH_RENAME_TEMPLATE = '{}/{}-{:02d}.log'
    DAY_EVENT_LOG_NAME = 'events'
    DAY_SUMMARY_LOG_NAME = 'summary'

    def __init__(self, datadir=DATA_DIR):
        self.__datadir = datadir
        self.__save_logname = None
        self.__date = None
        self.__daydir = None
        self.__event_log = None
        self.__summary_log = None
        self.newday()

    def __save_sheet_address(self, date, sheet):
        logf = open(self.SHEETS_PATH_TEMPLATE.format(self.__datadir), 'a')
        logf.write('{} {}\n'.format(date, sheet))
        logf.close()

    def __sync_log_to_gsheets(self):
        try:
            sh = hamstersheet.HamsterSheet(self.__date,
                                           self.__event_log,
                                           self.__summary_log)
            url = sh.get_url()
            dprint('uploaded sheet {}'.format(url))
            self.__save_sheet_address(self.__date, url)
        except hamstersheet.SheetException as e:
            dprint('error while uploading sheet: {}'.format(e))

    def save(self):
        if self.__event_log != None:
            self.__sync_log_to_gsheets()

    def newday(self):
        self.save()
        self.__event_log = {}
        self.__summary_log = {}
        tt = datetime.datetime.now().timetuple()
        month = tt[1]
        day = tt[2]
        self.__date = '{:02d}.{:02d}'.format(day, month)
        self.__daydir = '{}/{}'.format(self.__datadir, self.__date)
        if not os.path.exists(self.__daydir):
            os.mkdir(self.__daydir)
        else:
            self.__rename_log(self.DAY_EVENT_LOG_NAME)
            self.__rename_log(self.DAY_SUMMARY_LOG_NAME)
        self.__day_event_log = self.PATH_TEMPLATE.format(self.__daydir,
                                                         self.DAY_EVENT_LOG_NAME)
        self.__day_summary_log = self.PATH_TEMPLATE.format(self.__daydir,
                                                           self.DAY_SUMMARY_LOG_NAME)

    def event(self, device, ts, num, temp, light):
        local_ts = time.time()
        self.__save_to_log(self.__day_event_log,
                           local_ts, device, ts, num, temp, light)
        if device not in self.__event_log:
            self.__event_log[device] = []
        evlog = self.__event_log[device]
        local_num = len(evlog)
        diff = num - local_num
        for _ in range(diff):
            evlog.append(local_ts)

    def summary(self, device, ts, num, temp, light):
        local_ts = time.time()
        self.__save_to_log(self.__day_summary_log,
                           local_ts, device, ts, num, temp, light)
        if device not in self.__summary_log:
            self.__summary_log[device] = []
        self.__summary_log[device].append((local_ts, ts, num, temp, light))

    def __correct_summary_log(self, device, ts, num, temp, light):
        local_ts = time.time()
        if device not in self.__summary_log:
            self.__summary_log[device] = [(local_ts, ts, num, temp, light)]
        else:
            sumlog = self.__summary_log[device]
            assert sumlog
            prev_ts = 0
            for i, log in enumerate(sumlog):
                remote_ts = log[1]
                if ts == remote_ts:
                    return
                if prev_ts < ts < remote_ts:
                    dprint('correcting log at position {} < {} < {}'.format(prev_ts, ts, remote_ts))
                    sumlog.insert(i, (log[0], ts, num, temp, light))
                    return
                prev_ts = remote_ts
            dprint('correcting log - appending data ts {}'.format(ts))
            sumlog.append((local_ts, ts, num, temp, light))

    @classmethod
    def __save_to_log(cls, logname, local_ts, device, ts, num, temp, light):
        logf = open(logname, 'a')
        logf.write('{} {} {} {} {} {}\n'.format(local_ts,
                                                device,
                                                ts,
                                                num,
                                                temp,
                                                light))
        logf.close()

    def __rename_log(self, checkname):
        checkpath = self.PATH_TEMPLATE.format(self.__daydir, checkname)
        if os.path.exists(checkpath):
            postfix = 0
            newname = checkpath
            while os.path.exists(newname):
                newname = self.PATH_RENAME_TEMPLATE.format(self.__daydir, checkname, postfix)
                postfix += 1
            os.rename(checkpath, newname)

    def start_log(self, logname):
        if self.__save_logname is not None:
            self.finish_log()
        self.__rename_log(logname)
        self.__save_logname = self.PATH_TEMPLATE.format(self.__daydir, logname)

    def log_data(self, device, ts, num, temp, light):
        self.__correct_summary_log(device, ts, num, temp, light)
        if self.__save_logname is None:
            dprint('cannot log to empty file')
        else:
            logf = open(self.__save_logname, 'a')
            logf.write('{} {} {} {}\n'.format(ts,
                                              num,
                                              temp,
                                              light))
            logf.close()

    def finish_log(self):
        self.__save_logname = None
