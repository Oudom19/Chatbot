from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from ..actions import get_db_connection
from rasa_sdk.events import SlotSet
import random


def clear_all_slots():
    return [
        SlotSet("manufacturer", None),
        SlotSet("category", None),
        SlotSet("model_name", None),
        SlotSet("cpu", None),
        SlotSet("ram", None)
    ]

class ActionFetchProduct(Action):
    def name(self) -> str:
        return "action_fetch_product_by_name"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain) -> list:
        # Extracting slot values
        model_name = tracker.get_slot("model_name")
        cpu = tracker.get_slot("cpu")
        ram = tracker.get_slot("ram")
        storage = tracker.get_slot("storage")

        connection = get_db_connection()
        if connection is None:
            dispatcher.utter_message(
                text="⚠️ Apologies, but I'm currently unable to access the product database. Please try again later or contact our support team for assistance."
            )
            return []

        cursor = connection.cursor(dictionary=True)

        # Define a list of conditions to try, prioritizing the most important combinations
        conditions = [
            # Match with model_name, ram, cpu, and storage (most specific)
            ("p.model_name = %s AND p.ram = %s AND p.cpu = %s AND p.storage = %s",
             [model_name, ram, cpu, storage]),
            # Match with model_name, ram, and cpu
            ("p.model_name = %s AND p.ram = %s AND p.cpu = %s",
             [model_name, ram, cpu]),
            # Match with model_name, ram, and storage
            ("p.model_name = %s AND p.ram = %s AND p.storage = %s",
             [model_name, ram, storage]),
            # Match with model_name, cpu, and storage
            ("p.model_name = %s AND p.cpu = %s AND p.storage = %s",
             [model_name, cpu, storage]),
            # Match with model_name and ram
            ("p.model_name = %s AND p.ram = %s",
             [model_name, ram]),
            # Match with model_name and cpu
            ("p.model_name = %s AND p.cpu = %s",
             [model_name, cpu]),
            # Match with model_name and storage
            ("p.model_name = %s AND p.storage = %s",
             [model_name, storage]),
            # Match with model_name only (least specific)
            ("p.model_name = %s", [model_name]),
        ]

        # Add some variety to product introductions
        intros = [
            "Yes, here's a product that matches your requirements:",
            "Based on your preferences, I recommend the following:",
            "I've found a product that suits your needs:",
            "Of course, here's a great option for you:",
            "This product aligns with your specifications:",
            "I recommend this product based on your criteria:",
            "Here's a top pick for you:",
            "This product might be exactly what you're looking for:",
        ]

        for condition, values in conditions:
            if all(v is not None for v in values):
                query = f"""
                            SELECT p.id, p.model_name, p.category, p.screen_size, p.screen, p.cpu, p.ram, p.storage, 
                                   p.gpu, p.weight, p.price, m.name as manufacturer, 
                                   (SELECT image_url FROM images WHERE product_id = p.id LIMIT 1) as image_url
                            FROM products p 
                            JOIN manufacturers m ON p.manufacturer_id = m.id
                            WHERE {condition} 
                            LIMIT 5
                        """
                cursor.execute(query, tuple(values))
                products = cursor.fetchall()

                if products:
                    # Track shown product IDs
                    shown_ids = [str(product['id']) for product in products]

                    if len(products) == 1:
                        intro = random.choice(intros)
                        dispatcher.utter_message(text=intro)
                    else:
                        multi_intros = [
                            f"I found {len(products)} options that match your criteria:",
                            f"Here are {len(products)} products that meet your requirements:",
                            f"I've identified {len(products)} products that fit your needs:",
                            f"Here are {len(products)} recommendations based on your preferences:",
                            f"I found {len(products)} products that align with your specifications:",
                        ]
                        intro = random.choice(multi_intros)  # Randomly select an intro
                        dispatcher.utter_message(text=intro)

                    for product in products:
                        if product['image_url']:
                            dispatcher.utter_message(image=product['image_url'])

                        dispatcher.utter_message(
                            text=f"■ {product['manufacturer']} {product['model_name']}\n"
                                 f"○ Category: {product['category']}\n"
                                 f"○ Price: ${product['price']}\n"
                                 f"○ Display: {product['screen_size']}\" {product['screen']}\n"
                                 f"○ Performance: {product['cpu']}, {product['ram']} RAM\n"
                                 f"○ Storage: {product['storage']}\n"
                                 f"○ Graphics: {product['gpu']}\n"
                                 f"○ Weight: {product['weight']} kg\n"
                                 f"🌐 More Info: Visit our website` https://www.ecidisti.com/department/Electronics"
                        )
                    cursor.close()
                    connection.close()
                    dispatcher.utter_message(text="Would you like to see more products?")
                    return [SlotSet("shown_product_ids", shown_ids)]

        dispatcher.utter_message(
            text="❌ Unfortunately, I couldn't find any products matching your specifications. Please refine your search criteria or contact our support team for further assistance."
        )
        cursor.close()
        connection.close()
        return []