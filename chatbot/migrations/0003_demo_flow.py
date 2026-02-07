from django.db import migrations


def create_demo_flow(apps, schema_editor):
    ChatbotFlow = apps.get_model("chatbot", "ChatbotFlow")
    ChatbotNode = apps.get_model("chatbot", "ChatbotNode")
    ChatbotEdge = apps.get_model("chatbot", "ChatbotEdge")

    if ChatbotFlow.objects.filter(name="Demo WhatsApp Flow").exists():
        return

    flow = ChatbotFlow.objects.create(name="Demo WhatsApp Flow", is_active=True)

    ChatbotNode.objects.bulk_create([
        ChatbotNode(flow=flow, node_id="start", node_type="start", data={"text": "Start"}, position_x=40, position_y=40),
        ChatbotNode(flow=flow, node_id="welcome", node_type="message", data={"text": "Welcome! Type products to browse."}, position_x=260, position_y=40),
        ChatbotNode(flow=flow, node_id="catalog", node_type="message", data={"text": "Categories: Grocery, Dairy, Snacks"}, position_x=260, position_y=140),
        ChatbotNode(flow=flow, node_id="cart", node_type="message", data={"text": "Type cart to view total."}, position_x=260, position_y=240),
        ChatbotNode(flow=flow, node_id="payment", node_type="message", data={"text": "Pay: cash, paytm, cod, netbanking."}, position_x=260, position_y=340),
        ChatbotNode(flow=flow, node_id="done", node_type="end", data={"text": "Order placed. Thank you!"}, position_x=260, position_y=440),
    ])

    ChatbotEdge.objects.bulk_create([
        ChatbotEdge(flow=flow, source_id="start", target_id="welcome", condition_text="", is_default=True),
        ChatbotEdge(flow=flow, source_id="welcome", target_id="catalog", condition_text="products", is_default=False),
        ChatbotEdge(flow=flow, source_id="catalog", target_id="cart", condition_text="cart", is_default=False),
        ChatbotEdge(flow=flow, source_id="cart", target_id="payment", condition_text="checkout", is_default=False),
        ChatbotEdge(flow=flow, source_id="payment", target_id="done", condition_text="cash", is_default=False),
    ])


def remove_demo_flow(apps, schema_editor):
    ChatbotFlow = apps.get_model("chatbot", "ChatbotFlow")
    ChatbotFlow.objects.filter(name="Demo WhatsApp Flow").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0002_chatbotflow_chatbotedge_chatbotnode"),
    ]

    operations = [
        migrations.RunPython(create_demo_flow, reverse_code=remove_demo_flow),
    ]
