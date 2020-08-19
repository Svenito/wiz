# :coding: utf-8

import copy
import datetime
import os
import platform
import time
import traceback

import ujson

from wiz.utility import Requirement, Version
from ._version import __version__

#: Indicate whether the history should be recorded.
_IS_HISTORY_RECORDED = False

#: Indicate whether actions should only include 'identifier' keyword.
_MINIMAL_ACTIONS_REQUIRED = False

#: Mapping containing the entire context resolution history report.
_HISTORY = {
    "version": __version__,
    "user": None,
    "hostname": None,
    "timestamp": None,
    "timezone": None,
    "command": None,
    "actions": []
}


def get(serialized=False):
    """Return recorded history mapping.

    :param serialized: Indicate whether the returned history should be
        serialized as a :term:`JSON` string. Default is False.

    :return: History mapping - serialized or not - in the form of
        ::

            {
                "version": "3.0.0",
                "user": "john-doe",
                "hostname": "ws123",
                "timestamp": "2020-08-14T10:56:58.529201",
                "timezone": "PDT",
                "command": "wiz --record /tmp use foo --view",
                "actions": [
                    ...
                ]
            }

    """
    if serialized:
        return ujson.dumps(_HISTORY, default=_json_default)
    return _HISTORY


def start_recording(command=None, minimal_actions=False):
    """Start recording the execution history.

    This command will add information about the execution context to the history
    mapping (username, hostname, time, timezone) and activate the recording
    of actions via :func:`record_action`.

    :param command: Indicate the command line which is being executed. Default
        is None.

    :param minimal_actions: Indicate whether actions should only include the
        'identifier' keyword and discard all other elements passed to
        :func:`record_action`. If False, the execution time will be longer when
        history is being recorded. Default is False.

    """
    global _IS_HISTORY_RECORDED
    _IS_HISTORY_RECORDED = True

    global _MINIMAL_ACTIONS_REQUIRED
    _MINIMAL_ACTIONS_REQUIRED = minimal_actions

    global _HISTORY
    _HISTORY = {
        "version": __version__,
        "user": os.environ.get("USER"),
        "hostname": platform.node(),
        "timestamp": datetime.datetime.now().isoformat(),
        "timezone": time.tzname[1],
        "command": None,
        "actions": []
    }

    if command is not None:
        _HISTORY["command"] = command


def stop_recording():
    """Stop recording the history."""
    global _IS_HISTORY_RECORDED
    _IS_HISTORY_RECORDED = False


def record_action(identifier, **kwargs):
    """Add an action to the history.

    The action is identified by its unique *identifier* and every relevant
    arguments which will be serialized to provide an accurate snapshot of the
    execution context.

    :param identifier: Unique identifier of the action.

    .. warning::

        This operation will be discarded if the history is not being
        :func:`recorded <start_recording>`.

    """
    if not _IS_HISTORY_RECORDED:
        return

    action = {"identifier": identifier}

    if not _MINIMAL_ACTIONS_REQUIRED:
        action.update(**kwargs)

        if isinstance(action.get("error"), Exception):
            action["traceback"] = traceback.format_exc().splitlines()

    global _HISTORY
    _HISTORY["actions"].append(copy.deepcopy(action))


def _json_default(_object):
    """Override :func:`JSONEncoder.default` to serialize all objects."""
    import wiz.graph

    if isinstance(_object, wiz.graph.Graph):
        return _object.to_dict()

    elif isinstance(_object, Requirement) or isinstance(_object, Version):
        return str(_object)

    elif isinstance(_object, Exception):
        return str(_object)

    elif isinstance(_object, set):
        return list(_object)

    raise TypeError("{} is not JSON serializable.".format(_object))
