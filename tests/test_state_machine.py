import pytest
from unittest.mock import MagicMock
from enum import Enum
import json
from collections import OrderedDict
from transitions.core import EventData
from transitions import MachineError

from simobility.core.state_machine import StateMachine
from simobility.core import Clock


class TstStates(Enum):

    STATE1 = 'state1'
    STATE2 = 'state2'
    STATE3 = 'state3'


def create_state_machine():
    transitions = [
        ['set_state1', [TstStates.STATE3], TstStates.STATE1],
        ['set_state2', [TstStates.STATE1], TstStates.STATE2],
        ['set_state3', [TstStates.STATE1, TstStates.STATE2], TstStates.STATE3]
    ]

    states = [s for s in TstStates]

    return StateMachine(Clock(), transitions, states, TstStates.STATE1)


def test_basic():
    machine = create_state_machine()
    machine.process_state_change = MagicMock()

    assert machine.state == TstStates.STATE1

    machine.set_state2()
    assert machine.state == TstStates.STATE2

    with pytest.raises(MachineError):
        machine.set_state2()

    machine.set_state3()
    assert machine.state == TstStates.STATE3

    machine.set_state1()
    assert machine.state == TstStates.STATE1

    machine.set_state3()
    assert machine.state == TstStates.STATE3


def test_on_state_changed():
    machine = create_state_machine()
    machine.on_state_changed = MagicMock()
    machine.set_state2()

    machine.on_state_changed.assert_called_once()
    
    assert len(machine.on_state_changed.call_args[0]) == 1
    
    event_data = machine.on_state_changed.call_args[0][0]
    
    assert isinstance(event_data, EventData)
    assert event_data.transition.source == TstStates.STATE1.name
    assert event_data.transition.dest == TstStates.STATE2.name    
    assert event_data.kwargs == {}


def test_on_state_changed_params():
    machine = create_state_machine()
    machine.on_state_changed = MagicMock()
    machine.set_state3(param1=10)
    
    event_data = machine.on_state_changed.call_args[0][0]

    assert event_data.kwargs == {'param1': 10}


def test_process_state_change():
    machine = create_state_machine()
    machine.on_state_changed = MagicMock()
    machine.set_state2(val='123')

    event_data = machine.on_state_changed.call_args[0][0]
    event_data.kwargs['position'] = {'lat': 1, 'lon': 2}
    state_info = machine.process_state_change(event_data)
    
    assert isinstance(state_info, OrderedDict)
    assert len(state_info) == 9
    assert state_info['clock'] == 0
    assert state_info['class'] == machine.__class__.__name__.lower()
    assert state_info['id'] == machine.id
    assert state_info['it_id'] is None
    assert state_info['source'] == TstStates.STATE1.name
    assert state_info['dest'] == TstStates.STATE2.name
    assert state_info['arguments'] == {'val': '123'}
    assert state_info['lat'] == 1
    assert state_info['lon'] == 2


def test_itinerary_id():
    machine = create_state_machine()
    machine.on_state_changed = MagicMock()

    itinerary_id = 1234
    machine.set_state2(it_id=itinerary_id, val=23)

    event_data = machine.on_state_changed.call_args[0][0]
    event_data.kwargs['position'] = {'lat': 1, 'lon': 2}
    event_data.kwargs['it_id'] = 34

    state_info = machine.process_state_change(event_data)

    assert state_info['it_id'] == event_data.kwargs['it_id']
    assert 'it_id' not in state_info['arguments']

    assert state_info['arguments'] == {'val': 23}
    
    
def test_format_message():
    machine = create_state_machine()
    
    msg = machine.format_message({'1': 2})
    assert msg == '2'
    
    msg = machine.format_message({10: 'ads', '2': '4'})
    assert msg == 'ads;4'
    

def test_format_message_2():
    machine = create_state_machine()
    machine.on_state_changed = MagicMock()

    itinerary_id = 1234
    machine.set_state2(itinerary_id=itinerary_id)
    event_data = machine.on_state_changed.call_args[0][0]
    event_data.kwargs['position'] = {'lat': 1, 'lon': 2}
    state_info = machine.process_state_change(event_data)
    
    msg = machine.format_message(state_info)
    
    assert len(msg.split(';')) == len(state_info)
    assert msg.split(';') == [convert(v) for v in state_info.values()]
    

def convert(v):
    if v is None:
        v = ""
    elif isinstance(v, dict):
        v = json.dumps(v, separators=(",", ":"))
    else:
        v = str(v)
    return v