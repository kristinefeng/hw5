"""The Campus Customs agent team, one file per role.

    boss  <->  inventory  <->  accounting  <->  facilities  <->  customer_service

Every agent has the delegate() tool, so any agent can ask any other.
"""

from backend.agents import accounting, boss, customer_service, facilities, inventory
from backend.models import Role

AGENTS = {
    "boss": boss.agent,
    "inventory": inventory.agent,
    "accounting": accounting.agent,
    "facilities": facilities.agent,
    "customer_service": customer_service.agent,
}
assert set(AGENTS) == set(Role.__args__)
