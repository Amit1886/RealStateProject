from agents.services import agents_for_pincode, pick_agent_round_robin
from leads.services import assign_lead


def smart_assign(lead, company=None):
    return assign_lead(lead=lead)
