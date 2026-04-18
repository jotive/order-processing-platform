import pytest

from app.schemas.order import OrderStatus
from app.services.order_repository import _TRANSITIONS


@pytest.mark.parametrize(
    "current,target,allowed",
    [
        (OrderStatus.PENDING, OrderStatus.CONFIRMED, True),
        (OrderStatus.PENDING, OrderStatus.CANCELLED, True),
        (OrderStatus.PENDING, OrderStatus.SHIPPED, False),
        (OrderStatus.CONFIRMED, OrderStatus.PROCESSING, True),
        (OrderStatus.CONFIRMED, OrderStatus.PENDING, False),
        (OrderStatus.PROCESSING, OrderStatus.SHIPPED, True),
        (OrderStatus.SHIPPED, OrderStatus.DELIVERED, True),
        (OrderStatus.SHIPPED, OrderStatus.CANCELLED, False),
        (OrderStatus.DELIVERED, OrderStatus.CANCELLED, False),
        (OrderStatus.CANCELLED, OrderStatus.PENDING, False),
    ],
)
def test_status_transition_rules(current: OrderStatus, target: OrderStatus, allowed: bool):
    actual = target.value in _TRANSITIONS[current.value]
    assert actual is allowed


def test_terminal_states_have_no_outgoing_transitions():
    assert _TRANSITIONS[OrderStatus.DELIVERED.value] == set()
    assert _TRANSITIONS[OrderStatus.CANCELLED.value] == set()
