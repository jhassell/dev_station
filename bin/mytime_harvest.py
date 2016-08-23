#!/usr/bin/env python

from collections import Counter, defaultdict
import datetime
import getpass
from itertools import chain
import json
import os
import sys

import requests

PROJECT_ID = ""

ONE_DAY = datetime.timedelta(days=1)

HIRE_DATE = datetime.date(2015, 7, 20)

EXPECTED_HOURS_PER_DAY = 8

DATE_FORMAT_HARVEST_ENTRIES = "%Y%m%d"

WEEKDAY_NUMS = range(5)

now = datetime.datetime.now()
today = now.date()

pto_filename = "{}_pto.json".format(os.path.splitext(os.path.realpath(
    sys.argv[0]))[0])
if os.path.exists(pto_filename):
    with open(pto_filename) as pto_file:
        raw_pto_dict = json.load(pto_file)
else:
    raw_pto_dict = {}

class PTO_TYPE:
    HOLIDAY = 'holiday'
    SICK = 'sick'
    VACATION = 'vacation'
    ALL = (HOLIDAY, SICK, VACATION)
    REVOLVING = frozenset([SICK, VACATION])

MAX_PTO_TYPE_WIDTH = max((len(pto_type) for pto_type in PTO_TYPE.ALL))


pto_dict = defaultdict(list)


def pto_time():
    return {
        'total': 0,
        'per_month': defaultdict(int),
    }


pto_time_dict = defaultdict(pto_time)

for pto_type in PTO_TYPE.ALL:
    pto_type_hours_total = 0
    for raw_pto_date, pto_value in raw_pto_dict.get(pto_type, {}).iteritems():
        pto_date = datetime.datetime.strptime(raw_pto_date, "%Y-%m-%d").date()
        if pto_date >= today:
            # We are only interested in time from days in the past
            continue

        if isinstance(pto_value, dict):
            pto_hours = pto_value["hours"]
            raw_description = pto_value["description"]
        else:
            pto_hours = EXPECTED_HOURS_PER_DAY
            raw_description = pto_value

        pto_description = ": ".join(filter(None, (pto_type.title(),
            raw_description)))

        month_key = datetime.date(pto_date.year, pto_date.month, 1)

        pto_dict[month_key].append((pto_date, pto_description, pto_hours))

        pto_type_month_hours = pto_time_dict[pto_type]['per_month'][month_key]
        pto_type_month_hours += pto_hours
        pto_time_dict[pto_type]['per_month'][month_key] = pto_type_month_hours

        pto_type_hours_total += pto_hours

    pto_time_dict[pto_type]['total'] = pto_type_hours_total

response = requests.get("http://wandrsmith.harvestapp.com/projects/{project_id}"
    "/entries?from={from_date}&to={to_date}".format(project_id=PROJECT_ID,
    from_date=HIRE_DATE.strftime(DATE_FORMAT_HARVEST_ENTRIES),
    to_date=today.strftime(DATE_FORMAT_HARVEST_ENTRIES)),
    auth=('warren@wandrsmith.net', getpass.getpass()), headers={
        "Accept":"application/json",
        "Content-Type":"application/json",
    })

data = response.json()

actual_time_dict = {}
for entry_date, hours in ((
        datetime.datetime.strptime(item["day_entry"]["spent_at"], "%Y-%m-%d"),
        item["day_entry"]["hours"],
        ) for item in data):

    if entry_date.date() >= today:
        # We are only interested in time from days in the past
        continue

    month_key = datetime.date(entry_date.year, entry_date.month, 1)

    actual_time_dict[month_key] = actual_time_dict.get(month_key, 0) + hours

expected_time_dict = {}
cur_date = HIRE_DATE
while cur_date < today: # Only calculate expected time for days in the past
    if cur_date.weekday() in WEEKDAY_NUMS:
        month_key = datetime.date(cur_date.year, cur_date.month, 1)
        expected_time_dict[month_key] = expected_time_dict.get(month_key, 0
            ) + EXPECTED_HOURS_PER_DAY
    cur_date += ONE_DAY

total_actual_hours = 0
total_pto_revolving_hours = 0
total_effective_hours = 0
total_expected_hours = 0

for index, expected_time_item in enumerate(sorted(
        expected_time_dict.iteritems(), key=lambda x: x[0])):
    month_key, expected_hours = expected_time_item
    actual_hours = actual_time_dict.get(month_key, 0)
    pto_hours = sum(
        pto_time_dict[pto_type]['per_month'][month_key]
        for pto_type in PTO_TYPE.ALL
    )
    pto_revolving_hours = sum(
        pto_time_dict[pto_type]['per_month'][month_key]
        for pto_type in PTO_TYPE.REVOLVING
    )
    effective_hours = actual_hours + pto_hours
    month_diff = effective_hours - expected_hours

    total_actual_hours += actual_hours
    total_effective_hours += effective_hours
    total_pto_revolving_hours += pto_revolving_hours
    total_expected_hours += expected_hours
    total_diff = total_effective_hours - total_expected_hours


    print
    print "=" * 26
    print "{:%Y, %B}:".format(month_key)
    print "         Expected: {expected_hours:>7.2f}".format(
        expected_hours=expected_hours)
    print "           Actual: {actual_hours:>7.2f}".format(
        actual_hours=actual_hours)

    pto_items = sorted(pto_dict[month_key])
    if pto_items:
        print
        for pto_date, pto_description, pto_item_hours in pto_items:
            print "    {:13}: {:>7.2f} {}".format("{:%d, %A}".format(pto_date),
                pto_item_hours, pto_description)
        for pto_type in PTO_TYPE.ALL:
            pto_type_month_hours = pto_time_dict[pto_type]['per_month'][month_key]
            if pto_type_month_hours:
                print "         {pto_type:>{pto_type_width}}: {pto_hours:>7.2f}".format(
                    pto_type=pto_type.title(),
                    pto_type_width=MAX_PTO_TYPE_WIDTH,
                    pto_hours=pto_type_month_hours,
                )
        print
        print "        Revolving: {:>7.2f}".format(pto_revolving_hours)

        print
        print "        Effective: {effective_hours:>7.2f}".format(
            effective_hours=effective_hours)

    print "       Difference: {month_diff:>7.2f}".format(month_diff=month_diff)

    if index > 0:
        print
        print "-" * 26
        for pto_type in PTO_TYPE.ALL:
            print "   Total {pto_type:>{pto_type_width}}: {total_pto_hours:>7.2f}".format(
                pto_type=pto_type.title(),
                pto_type_width=MAX_PTO_TYPE_WIDTH,
                total_pto_hours=pto_time_dict[pto_type]['total'],
            )
        print
        print "  Total Revolving: {:>7.2f}".format(total_pto_revolving_hours)
        print

        print "   Total Expected: {total_expected_hours:>7.2f}".format(
            total_expected_hours=total_expected_hours)
        if total_actual_hours == total_effective_hours:
            print "     Total Actual: {total_actual_hours:>7.2f}".format(
                total_actual_hours=total_actual_hours)
        else:
            print "  Total Effective: {total_effective_hours:>7.2f}".format(
                total_effective_hours=total_effective_hours)
        print " Total Difference: {total_diff:>7.2f}".format(
            total_diff=total_diff)
