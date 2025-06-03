import json, os, stripe
from stripe_agent_toolkit.toolkit import StripeTooling
from utils.llama import chat_llama

stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe_tools   = StripeTooling(api_key=stripe.api_key).get_tools()

def cart_spec():
    return {
        "name": "get_cart",
        "description": "Return current cart lines & subtotals",
        "parameters": {"type": "object", "properties": {}}
    }

def shipping_spec():
    return {
        "name": "collect_shipping",
        "description": "Save shipping address and return shipping options",
        "parameters": {
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"]
        }
    }

def order_spec():
    return {
        "name": "confirm_order",
        "description": "Record the order after payment succeeded",
        "parameters": {
            "type": "object",
            "properties": {"payment_intent_id": {"type": "string"}},
            "required": ["payment_intent_id"]
        }
    }

TOOLS = stripe_tools + [cart_spec(), shipping_spec(), order_spec()]

SYSTEM_PROMPT = """
You are ShopLlama, a helpful checkout assistant.
Use the provided tools to:
1) show cart
2) collect shipping
3) create Stripe payment links
Always confirm order total before charging.
"""

def run_agent(session, user_text):
    # session = {"messages": [...], "state": {...}}
    session["messages"].append({"role": "user", "content": user_text})

    # prepend system once
    if not session["messages"] or session["messages"][0]["role"] != "system":
        session["messages"].insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    reply = chat_llama(session["messages"], tools=TOOLS)
    session["messages"].append(reply["choices"][0]["message"])

    return reply, session 