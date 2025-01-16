#! python3

# Copyright Tomer Figenblat.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Python script for controlling Switcher devices."""

import asyncio
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import timedelta
from pprint import PrettyPrinter
from typing import Any, Dict, List, Union

from aioswitcher.api import Command, SwitcherApi
from aioswitcher.api.remotes import SwitcherBreezeRemoteManager
from aioswitcher.device import (
    DeviceState,
    DeviceType,
    ShutterChildLock,
    ThermostatFanLevel,
    ThermostatMode,
    ThermostatSwing,
)
from aioswitcher.schedule import Days

printer = PrettyPrinter(indent=4)

DEVICES = {
    "mini": DeviceType.MINI,
    "plug": DeviceType.POWER_PLUG,
    "touch": DeviceType.TOUCH,
    "v2esp": DeviceType.V2_ESP,
    "v2qual": DeviceType.V2_QCA,
    "v4": DeviceType.V4,
    "breeze": DeviceType.BREEZE,
    "runner": DeviceType.RUNNER,
    "runnermini": DeviceType.RUNNER_MINI,
    "runners11": DeviceType.RUNNER_S11,
    "runners12": DeviceType.RUNNER_S12,
    "light01": DeviceType.LIGHT_SL01,
    "light01mini": DeviceType.LIGHT_SL01_MINI,
    "light02": DeviceType.LIGHT_SL02,
    "light02mini": DeviceType.LIGHT_SL02_MINI,
    "light03": DeviceType.LIGHT_SL03,
}

# shared parse
shared_parser = ArgumentParser(add_help=False)
shared_parser.add_argument(
    "-v",
    "--verbose",
    default=False,
    action="store_true",
    help="include the raw message",
)
possible_types = [t for t in DEVICES]
shared_parser.add_argument(
    "-c",
    "--device-type",
    type=str,
    choices=possible_types,
    required=True,
    help="the type of the device",
)
shared_parser.add_argument(
    "-k",
    "--token",
    default=None,
    type=str,
    help="the token for communicating with the new switcher devices",
)
shared_parser.add_argument(
    "-d",
    "--device-id",
    type=str,
    required=True,
    help="the identification of the device",
)
shared_parser.add_argument(
    "-l",
    "--device-key",
    type=str,
    required=False,
    default="00",
    help="the login key of the device",
)
shared_parser.add_argument(
    "-i",
    "--ip-address",
    type=str,
    required=True,
    help="the ip address assigned to the device",
)

# parent parser
main_parser = ArgumentParser(
    description="Control your Switcher device",
    formatter_class=RawDescriptionHelpFormatter,
)

subparsers = main_parser.add_subparsers(dest="action", description="supported actions")

# control_thermostat parser
_control_thermostat_examples = """example usage:

poetry run control_device control_thermostat -c "breeze" -d 3a20b7 -i "192.168.50.77" -r ELEC7001 -s on\n
poetry run control_device control_thermostat -c "breeze" -d 3a20b7 -i "192.168.50.77" -r ELEC7001 -m cool -f high -t 24\n
poetry run control_device control_thermostat -c "breeze" -d 3a20b7 -i "192.168.50.77" -r ELEC7001 -m cool -f high -t 24 -u\n
poetry run control_device control_thermostat -c "breeze" -d 3a20b7 -i "192.168.50.77" -r ELEC7001 -m dry\n
poetry run control_device control_thermostat -c "breeze" -d 3a20b7 -i "192.168.50.77" -r ELEC7001 -s off\n
"""  # noqa E501
control_thermostat_parser = subparsers.add_parser(
    "control_thermostat",
    help="control a breeze device",
    epilog=_control_thermostat_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
control_thermostat_parser.add_argument(
    "-r", "--remote-id", required=True, type=str, help="remote id of your device"
)
possible_states = dict(map(lambda s: (s.display, s), DeviceState))
control_thermostat_parser.add_argument(
    "-s",
    "--state",
    choices=possible_states.keys(),
    help="thermostat state",
)
possible_modes = dict(map(lambda s: (s.display, s), ThermostatMode))
control_thermostat_parser.add_argument(
    "-m",
    "--mode",
    choices=possible_modes.keys(),
    help="thermostat mode",
)
possible_fan_level = dict(map(lambda s: (s.display, s), ThermostatFanLevel))
control_thermostat_parser.add_argument(
    "-f",
    "--fan-level",
    choices=possible_fan_level.keys(),
    help="thermostat fan level",
)
possible_swing = dict(map(lambda s: (s.display, s), ThermostatSwing))
control_thermostat_parser.add_argument(
    "-w",
    "--swing",
    choices=possible_swing.keys(),
    help="thermostat swing",
)
control_thermostat_parser.add_argument(
    "-t",
    "--temperature",
    type=int,
    help="thermostat temperature, a positive integer",
)
control_thermostat_parser.add_argument(
    "-u",
    "--update",
    default=False,
    action="store_true",
    help="update state without control",
)

# create_schedule parser
_create_schedule_examples = """example usage:

poetry run control_device create_schedule -c "touch" -d ab1c2d -i "111.222.11.22" -n "14:00" -f "14:30"\n
poetry run control_device create_schedule -c "touch" -d ab1c2d -i "111.222.11.22" -n "17:30" -f "18:30" -w Sunday Monday Friday\n
"""  # noqa E501
create_schedule_parser = subparsers.add_parser(
    "create_schedule",
    help="create a new schedule",
    epilog=_create_schedule_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
create_schedule_parser.add_argument(
    "-n",
    "--start-time",
    type=str,
    required=True,
    help="the on time for the schedule, e.g. 13:00",
)
create_schedule_parser.add_argument(
    "-f",
    "--end-time",
    type=str,
    required=True,
    help="the off time for the schedule, e.g. 13:30",
)
possible_weekdays = [d.value for d in Days]
create_schedule_parser.add_argument(
    "-w",
    "--weekdays",
    choices=possible_weekdays,
    nargs="*",
    required=False,
    help="days for recurring schedules",
    default=list(),
)

# delete_schedule parser
_delete_schedule_examples = """example usage:

poetry run control_device delete_schedule -c "touch" -d ab1c2d -i "111.222.11.22" -s 3\n
"""  # noqa E501
delete_schedule_parser = subparsers.add_parser(
    "delete_schedule",
    help="delete a device schedule",
    epilog=_delete_schedule_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
delete_schedule_parser.add_argument(
    "-s",
    "--schedule-id",
    type=str,
    required=True,
    help="the id of the schedule for deletion",
)

# get_schedules parser
_get_schedules_examples = """example usage:

poetry run control_device get_schedules -c "touch" -d ab1c2d -i "111.222.11.22"\n
"""  # noqa E501
subparsers.add_parser(
    "get_schedules",
    help="retrieve a device schedules",
    epilog=_get_schedules_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)

# get_state parser
_get_state_examples = """example usage:

poetry run control_device get_state -c "touch" -d ab1c2d -i "111.222.11.22"\n
"""  # noqa E501
subparsers.add_parser(
    "get_state",
    help="get the current state of a device",
    epilog=_get_state_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)

# get_thermostat_state parser
_get_thermostat_state_examples = """example usage:

poetry run control_device get_thermostat_state -c "breeze" -d 3a20b7 -i "192.168.50.77"\n
"""  # noqa E501
subparsers.add_parser(
    "get_thermostat_state",
    help="get the current state a thermostat (breeze) device",
    epilog=_get_thermostat_state_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)

# set_auto_shutdown parser
_set_auto_shutdown_examples = """example usage:

poetry run control_device set_auto_shutdown -c "touch" -d ab1c2d -i "111.222.11.22" -r 2 -m 30\n
"""  # noqa E501
set_auto_shutdown_parser = subparsers.add_parser(
    "set_auto_shutdown",
    help="set the auto shutdown property (1h-24h)",
    epilog=_set_auto_shutdown_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
set_auto_shutdown_parser.add_argument(
    "-r",
    "--hours",
    type=int,
    required=True,
    help="number hours for the auto shutdown",
)
set_auto_shutdown_parser.add_argument(
    "-m",
    "--minutes",
    type=int,
    nargs="?",
    default=0,
    help="number hours for the auto shutdown",
)

# set_name parser
_set_name_examples = """example usage:

poetry run control_device set_name -c "touch" -d ab1c2d -i "111.222.11.22" -n "My Boiler"\n
"""  # noqa E501
set_name_parser = subparsers.add_parser(
    "set_name",
    help="set the name of the device",
    epilog=_set_name_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
set_name_parser.add_argument(
    "-n",
    "--name",
    type=str,
    required=True,
    help="new name for the device",
)

# get_shutter_state parser
_get_shutter_state_examples = """example usage:

poetry run control_device get_shutter_state -c "runner" -d f2239a -i "192.168.50.98"\n
poetry run control_device get_shutter_state -c "runnermini" -d f2239a -i "192.168.50.98"\n
poetry run control_device get_shutter_state -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98"\n
poetry run control_device get_shutter_state -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -x 0\n
poetry run control_device get_shutter_state -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -x 1\n
"""  # noqa E501
get_shutter_state_parser = subparsers.add_parser(
    "get_shutter_state",
    help="get the current shutter state of a device",
    epilog=_get_shutter_state_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
get_shutter_state_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to operate",
)

# stop shutter parser
_set_shutter_position_examples = """example usage:

poetry run control_device set_shutter_position -c "runner" -d f2239a -i "192.168.50.98" -p 50\n
poetry run control_device set_shutter_position -c "runnermini" -d f2239a -i "192.168.50.98" -p 50\n
poetry run control_device set_shutter_position -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -p 50\n
poetry run control_device set_shutter_position -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -p 50 -x 0\n
poetry run control_device set_shutter_position -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -p 50 -x 1\n
"""  # noqa E501
set_shutter_position_parser = subparsers.add_parser(
    "set_shutter_position",
    help="set shutter position",
    epilog=_set_shutter_position_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
set_shutter_position_parser.add_argument(
    "-p",
    "--position",
    required=True,
    type=int,
    help="Shutter position percentage",
)
set_shutter_position_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to operate",
)

# stop shutter parser
_stop_shutter_examples = """example usage:

poetry run control_device stop_shutter -c "runner" -d f2239a -i "192.168.50.98"\n
poetry run control_device stop_shutter -c "runnermini" -d f2239a -i "192.168.50.98"\n
poetry run control_device stop_shutter -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98"\n
poetry run control_device stop_shutter -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -x 0\n
poetry run control_device stop_shutter -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d f2239a -i "192.168.50.98" -x 1\n
"""  # noqa E501
stop_shutter_parser = subparsers.add_parser(
    "stop_shutter",
    help="stop shutter",
    epilog=_stop_shutter_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
stop_shutter_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to operate",
)

# turn_off_shutter_child_lock parser
_turn_off_shutter_child_lock_examples = """example usage:

poetry run control_device turn_off_shutter_child_lock -c "runner" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_off_shutter_child_lock -c "runnermini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_off_shutter_child_lock -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_off_shutter_child_lock -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_off_shutter_child_lock -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
"""  # noqa E501
turn_off_shutter_child_lock_parser = subparsers.add_parser(
    "turn_off_shutter_child_lock",
    help="turn off shutter child lock",
    epilog=_turn_off_shutter_child_lock_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
turn_off_shutter_child_lock_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to turn off",
)

# turn_on_shutter_child_lock parser
_turn_on_shutter_child_lock_examples = """example usage:

poetry run control_device turn_on_shutter_child_lock -c "runner" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_on_shutter_child_lock -c "runnermini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_on_shutter_child_lock -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_on_shutter_child_lock -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_on_shutter_child_lock -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
"""  # noqa E501
turn_on_shutter_child_lock_parser = subparsers.add_parser(
    "turn_on_shutter_child_lock",
    help="turn on shutter child lock",
    epilog=_turn_on_shutter_child_lock_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
turn_on_shutter_child_lock_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to turn on",
)

# turn_off parser
_turn_off_examples = """example usage:

poetry run control_device turn_off -c "touch" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_off -c "touch" -d ab1c2d -l 18 -i "111.222.11.22"\n
"""  # noqa E501
turn_off_parser = subparsers.add_parser(
    "turn_off",
    help="turn off the device",
    epilog=_turn_off_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)

# turn_on parser
_turn_on_examples = """example usage:

poetry run control_device turn_on -c "touch" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_on -c "touch" -d ab1c2d -l 18 -i "111.222.11.22"\n
poetry run control_device turn_on -c "touch" -d ab1c2d -i "111.222.11.22" -t 15\n
"""  # noqa E501
turn_on_parser = subparsers.add_parser(
    "turn_on",
    help="turn on the device",
    epilog=_turn_on_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
turn_on_parser.add_argument(
    "-t",
    "--timer",
    type=int,
    nargs="?",
    default=0,
    help="set minutes timer for turn on operation",
)

# get_light_state parser
_get_light_state_examples = """example usage:

poetry run control_device get_light_state -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device get_light_state -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device get_light_state -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device get_light_state -c "light01" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device get_light_state -c "light01mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device get_light_state -c "light02" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device get_light_state -c "light02" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device get_light_state -c "light02mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device get_light_state -c "light02mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device get_light_state -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device get_light_state -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device get_light_state -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 2\n
"""  # noqa E501
get_light_state_parser = subparsers.add_parser(
    "get_light_state",
    help="get the current light state of a device",
    epilog=_get_light_state_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
get_light_state_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to turn off",
)

# turn_off_light parser
_turn_off_light_examples = """example usage:

poetry run control_device turn_off_light -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_off_light -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_off_light -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_off_light -c "light01" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_off_light -c "light01mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_off_light -c "light02" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_off_light -c "light02" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_off_light -c "light02mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_off_light -c "light02mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_off_light -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_off_light -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_off_light -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 2\n
"""  # noqa E501
turn_off_light_parser = subparsers.add_parser(
    "turn_off_light",
    help="turn off light",
    epilog=_turn_off_light_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
turn_off_light_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to turn off",
)

# turn_on_light parser
_turn_on_light_examples = """example usage:

poetry run control_device turn_on_light -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_on_light -c "runners11" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_on_light -c "runners12" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_on_light -c "light01" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_on_light -c "light01mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22"\n
poetry run control_device turn_on_light -c "light02" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_on_light -c "light02" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_on_light -c "light02mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_on_light -c "light02mini" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_on_light -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 0\n
poetry run control_device turn_on_light -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 1\n
poetry run control_device turn_on_light -c "light03" -k "zvVvd7JxtN7CgvkD1Psujw==" -d ab1c2d -i "111.222.11.22" -x 2\n
"""  # noqa E501
turn_on_light_parser = subparsers.add_parser(
    "turn_on_light",
    help="turn on light",
    epilog=_turn_on_light_examples,
    formatter_class=RawDescriptionHelpFormatter,
    parents=[shared_parser],
)
turn_on_light_parser.add_argument(
    "-x",
    "--index",
    required=False,
    type=int,
    default=0,
    help="the circuit number to turn on",
)


def asdict(dc: object, verbose: bool = False) -> Dict[str, Any]:
    """Use as custom implementation of the asdict utility method."""
    return {
        k: v
        for k, v in dc.__dict__.items()
        if not (not verbose and k == "unparsed_response")
    }


async def get_thermostat_state(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use to launch a get_breeze_state request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(asdict(await api.get_breeze_state(), verbose))


async def get_shutter_state(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use to launch a get_shutter_state request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(asdict(await api.get_shutter_state(index), verbose))


async def get_state(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    verbose: bool,
) -> None:
    """Use to launch a get_state request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(asdict(await api.get_state(), verbose))


async def control_thermostat(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    remote_id: str,
    state: str,
    mode: Union[str, None] = None,
    target_temp: int = 0,
    fan_level: Union[str, None] = None,
    swing: Union[str, None] = None,
    update_state: bool = False,
    verbose: bool = False,
    token: Union[str, None] = None,
) -> None:
    """Control Breeze device."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(
            asdict(
                await api.control_breeze_device(
                    SwitcherBreezeRemoteManager().get_remote(remote_id),
                    possible_states[state] if state else None,
                    possible_modes[mode] if mode else None,
                    target_temp,
                    possible_fan_level[fan_level] if fan_level else None,
                    possible_swing[swing] if swing else None,
                    update_state,
                ),
                verbose,
            )
        )


async def turn_on(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    timer: int,
    verbose: bool,
) -> None:
    """Use to launch a turn_on request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(asdict(await api.control_device(Command.ON, timer), verbose))


async def turn_off(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    verbose: bool,
) -> None:
    """Use to launch a turn_off request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(asdict(await api.control_device(Command.OFF), verbose))


async def set_name(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    name: str,
    verbose: bool,
) -> None:
    """Use to launch a set_name request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(asdict(await api.set_device_name(name), verbose))


async def set_auto_shutdown(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    hours: int,
    minutes: int,
    verbose: bool,
) -> None:
    """Use to launch a set_auto_shutdown request."""
    td_val = timedelta(hours=hours, minutes=minutes)
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(asdict(await api.set_auto_shutdown(td_val), verbose))


async def get_schedules(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    verbose: bool,
) -> None:
    """Use to launch a get_schedules request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        response = await api.get_schedules()
        if verbose:
            printer.pprint({"unparsed_response": response.unparsed_response})
            print()
        for schedule in response.schedules:
            printer.pprint(asdict(schedule))
            print()


async def delete_schedule(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    schedule_id: str,
    verbose: bool,
) -> None:
    """Use to launch a delete_schedule request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(asdict(await api.delete_schedule(schedule_id), verbose))


async def create_schedule(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    start_time: str,
    end_time: str,
    weekdays: List[str],
    verbose: bool,
) -> None:
    """Use to launch a create_schedule request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key) as api:
        printer.pprint(
            asdict(
                await api.create_schedule(
                    start_time,
                    end_time,
                    set([Days(w) for w in weekdays]),  # type: ignore
                ),
                verbose,
            )
        )


async def stop_shutter(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Stop shutter."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(
            asdict(
                await api.stop_shutter(index),
                verbose,
            )
        )


async def set_shutter_position(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    position: int,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use to set the shutter position."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(
            asdict(
                await api.set_position(position, index),
                verbose,
            )
        )


async def turn_on_shutter_child_lock(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use for turn on shutter child lock."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(
            asdict(
                await api.set_shutter_child_lock(ShutterChildLock.ON, index), verbose
            )
        )


async def turn_off_shutter_child_lock(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use for turn off shutter child lock."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(
            asdict(
                await api.set_shutter_child_lock(ShutterChildLock.OFF, index), verbose
            )
        )


async def get_light_state(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use to launch a get_light_state request."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(asdict(await api.get_light_state(index), verbose))


async def turn_on_light(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use for turn on light."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(asdict(await api.set_light(DeviceState.ON, index), verbose))


async def turn_off_light(
    device_type: DeviceType,
    device_id: str,
    device_key: str,
    device_ip: str,
    index: int,
    verbose: bool,
    token: Union[str, None] = None,
) -> None:
    """Use for turn off light."""
    async with SwitcherApi(device_type, device_ip, device_id, device_key, token) as api:
        printer.pprint(asdict(await api.set_light(DeviceState.OFF, index), verbose))


def main() -> None:
    """Run the device controller script."""
    try:
        args = main_parser.parse_args()

        if "device_type" in args and type(args.device_type) is not DeviceType:
            device_type = DEVICES[args.device_type.lower()]
        else:
            device_type = args.device_type

        if args.action == "get_state":
            asyncio.run(
                get_state(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.verbose,
                )
            )
        elif args.action == "turn_on":
            asyncio.run(
                turn_on(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.timer,
                    args.verbose,
                )
            )
        elif args.action == "turn_off":
            asyncio.run(
                turn_off(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.verbose,
                )
            )
        elif args.action == "set_name":
            asyncio.run(
                set_name(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.name,
                    args.verbose,
                )
            )
        elif args.action == "set_auto_shutdown":
            asyncio.run(
                set_auto_shutdown(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.hours,
                    args.minutes,
                    args.verbose,
                )
            )
        elif args.action == "get_schedules":
            asyncio.run(
                get_schedules(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.verbose,
                )
            )
        elif args.action == "delete_schedule":
            asyncio.run(
                delete_schedule(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.schedule_id,
                    args.verbose,
                )
            )
        elif args.action == "create_schedule":
            asyncio.run(
                create_schedule(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.start_time,
                    args.end_time,
                    args.weekdays,
                    args.verbose,
                )
            )

        elif args.action == "get_shutter_state":
            asyncio.run(
                get_shutter_state(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "stop_shutter":
            asyncio.run(
                stop_shutter(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "set_shutter_position":
            asyncio.run(
                set_shutter_position(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.position,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "turn_on_shutter_child_lock":
            asyncio.run(
                turn_on_shutter_child_lock(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "turn_off_shutter_child_lock":
            asyncio.run(
                turn_off_shutter_child_lock(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "control_thermostat":
            asyncio.run(
                control_thermostat(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.remote_id,
                    args.state,
                    args.mode,
                    args.temperature,
                    args.fan_level,
                    args.swing,
                    args.update,
                    args.verbose,
                    args.token,
                )
            )
        elif args.action == "get_thermostat_state":
            asyncio.run(
                get_thermostat_state(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "get_light_state":
            asyncio.run(
                get_light_state(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "turn_on_light":
            asyncio.run(
                turn_on_light(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

        elif args.action == "turn_off_light":
            asyncio.run(
                turn_off_light(
                    device_type,
                    args.device_id,
                    args.device_key,
                    args.ip_address,
                    args.index,
                    args.verbose,
                    args.token,
                )
            )

    except KeyboardInterrupt:
        exit()


if __name__ == "__main__":
    main()
