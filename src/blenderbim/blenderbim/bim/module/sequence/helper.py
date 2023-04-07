# BlenderBIM Add-on - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of BlenderBIM Add-on.
#
# BlenderBIM Add-on is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BlenderBIM Add-on is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BlenderBIM Add-on.  If not, see <http://www.gnu.org/licenses/>.

import isodate
from dateutil import parser
import ifcopenshell.util.date as ifcdateutils
from datetime import timedelta


def parse_datetime(value):
    try:
        return parser.isoparse(value)
    except:
        try:
            return parser.parse(value, dayfirst=True, fuzzy=True)
        except:
            return None


def parse_duration(value):
    try:
        return isodate.parse_duration(value)
    except:
        return None


def canonicalise_time(time):
    if not time:
        return "-"
    return time.strftime("%d/%m/%y")


def parse_duration_as_blender_props(dt, simplify=True):
    if simplify:
        if isinstance(dt, str):
            dt = ifcdateutils.ifc2datetime(dt)

        seconds = getattr(dt, "seconds", 0)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        days = getattr(dt, "days", 0)
        months = int(getattr(dt, "months", 0))
        years = int(getattr(dt, "years", 0))
        return {
            "years": years,
            "months": months,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
        }


def simplify_duration(durations_attributes, duration_type, prop_name):
    for item in durations_attributes:
        if item.name == prop_name:
            duration_props = item
    if duration_props and not duration_type or duration_type == "ELAPSEDTIME":
        duration_string = "P{}Y{}M{}DT{}H{}M{}S".format(
            duration_props.years if duration_props.years else 0,
            duration_props.months if duration_props.months else 0,
            duration_props.days if duration_props.days else 0,
            duration_props.hours if duration_props.hours else 0,
            duration_props.minutes if duration_props.minutes else 0,
            duration_props.seconds if duration_props.seconds else 0,
        )
        duration_object = ifcdateutils.ifc2datetime(duration_string)
    elif duration_props and duration_type == "WORKTIME":
        years = (duration_props.years * 365 * 24 * 60 * 60) if duration_props.years else 0
        months = (duration_props.months * 30 * 24 * 60 * 60) if duration_props.months else 0
        days = (duration_props.days * 24 * 60 * 60) if duration_props.days else 0
        days_subtotal = (years + months + days) / (24 * 60 * 60)

        hours = (duration_props.hours * 60 * 60) if duration_props.hours else 0
        minutes = (duration_props.minutes * 60) if duration_props.minutes else 0
        seconds = duration_props.seconds if duration_props.seconds else 0
        total_seconds = hours + minutes + seconds

        # TODO: implement actual calendar worktime
        calendar_seconds_per_day = 8 * 60 * 60
        extra_days, seconds_left = divmod(total_seconds, calendar_seconds_per_day)
        total_days = days_subtotal + extra_days
        duration_object = timedelta(days=total_days, seconds=seconds_left)
    if duration_object:
        total_days = int(duration_object.days)
        seconds_left = int(duration_object.seconds)
        years, days = divmod(total_days, 365)
        if hasattr(duration_object, "years"):
            years += duration_object.years

        months, days = divmod(days, 30)
        if hasattr(duration_object, "months"):
            months += duration_object.months

        if months >= 12:
            extra_years, months = divmod(months, 12)
            years += extra_years

        hours, seconds = divmod(seconds_left, 3600)
        minutes, seconds = divmod(seconds, 60)

        return "P{}Y{}M{}DT{}H{}M{}S".format(
            int(years),
            int(months),
            int(days),
            int(hours),
            int(minutes),
            int(seconds),
        )
