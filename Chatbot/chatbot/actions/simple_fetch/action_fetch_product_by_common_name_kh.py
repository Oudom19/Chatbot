from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from ..actions import get_db_connection
from rasa_sdk.events import SlotSet
import random

def clear_all_slots():
    return [
        SlotSet("manufacturer", None),
        SlotSet("category", None),
        SlotSet("common_name", None),
        SlotSet("cpu", None),
        SlotSet("ram", None)
    ]

class ActionFetchProduct(Action):
    def name(self) -> str:
        return "action_fetch_product_by_common_name_kh"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain) -> list:
        # Extracting slot values
        common_name = tracker.get_slot("common_name")
        cpu = tracker.get_slot("cpu")
        ram = tracker.get_slot("ram")
        storage = tracker.get_slot("storage")

        connection = get_db_connection()
        if connection is None:
            dispatcher.utter_message(
                text="⚠️ សូមអភ័យទោស ប៉ុន្តែខ្ញុំមិនអាចចូលប្រើទិន្នន័យផលិតផលបានទេ។ សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ ឬទាក់ទងក្រុមគាំទ្ររបស់យើងសម្រាប់ជំនួយ។"
            )
            return []

        cursor = connection.cursor(dictionary=True)

        # Define a list of conditions to try, prioritizing the most important combinations
        conditions = [
            # Match with common_name, ram, cpu, and storage (most specific)
            ("p.common_name = %s AND p.ram = %s AND p.cpu = %s AND p.storage = %s",
             [common_name, ram, cpu, storage]),
            # Match with common_name, ram, and cpu
            ("p.common_name = %s AND p.ram = %s AND p.cpu = %s",
             [common_name, ram, cpu]),
            # Match with common_name, ram, and storage
            ("p.common_name = %s AND p.ram = %s AND p.storage = %s",
             [common_name, ram, storage]),
            # Match with common_name, cpu, and storage
            ("p.common_name = %s AND p.cpu = %s AND p.storage = %s",
             [common_name, cpu, storage]),
            # Match with common_name and ram
            ("p.common_name = %s AND p.ram = %s",
             [common_name, ram]),
            # Match with common_name and cpu
            ("p.common_name = %s AND p.cpu = %s",
             [common_name, cpu]),
            # Match with common_name and storage
            ("p.common_name = %s AND p.storage = %s",
             [common_name, storage]),
            # Match with common_name only (least specific)
            ("p.common_name = %s", [common_name]),
        ]

        # Bilingual introductions
        intros = [
            "បាទ/ចាស នេះជាផលិតផលដែលត្រូវនឹងតម្រូវការរបស់អ្នក៖",
            "ដោយផ្អែកលើចំណូលចិត្តរបស់អ្នក ខ្ញុំណែនាំដូចខាងក្រោម៖",
            "ខ្ញុំបានរកឃើញផលិតផលមួយដែលត្រូវនឹងតម្រូវការរបស់អ្នក៖",
            "ជាការពិតណាស់ នេះជាជម្រើសល្អសម្រាប់អ្នក៖",
        ]

        for condition, values in conditions:
            if all(v is not None for v in values):
                query = f"""
                        SELECT p.id, p.common_name, p.category, p.screen_size, p.screen, p.cpu, p.ram, p.storage, 
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
                            f"ខ្ញុំបានរកឃើញ {len(products)} ជម្រើសដែលត្រូវនឹងលក្ខណៈរបស់អ្នក៖",
                            f"នេះជាផលិតផល {len(products)} ដែលត្រូវនឹងតម្រូវការរបស់អ្នក៖",
                        ]
                        intro_kh = random.choice(multi_intros)
                        dispatcher.utter_message(text=intro_kh)

                    for product in products:
                        if product['image_url']:
                            dispatcher.utter_message(image=product['image_url'])

                        dispatcher.utter_message(
                            text=f"■ {product['manufacturer']} {product['common_name']}\n"
                                 f"○ Category: {product['category']}\n"
                                 f"○ Price: ${product['price']}\n"
                                 f"○ Display: {product['screen_size']}\" {product['screen']}\n"
                                 f"○ Performance: {product['cpu']}, {product['ram']} RAM\n"
                                 f"○ Storage: {product['storage']}\n"
                                 f"○ Graphics: {product['gpu']}\n"
                                 f"○ Weight: {product['weight']} kg\n"
                                 f"🌐 ព័ត៌មានបន្ថែម: សូមមើលគេហទំព័ររបស់យើង https://www.ecidisti.com/department/Electronics"
                        )
                    cursor.close()
                    connection.close()
                    dispatcher.utter_message(text="Would you like to see more products?")
                    return [SlotSet("shown_product_ids", shown_ids)]

        # No products found message
        dispatcher.utter_message(
            text="❌ សូមអភ័យទោស ខ្ញុំមិនអាចរកផលិតផលដែលត្រូវនឹងលក្ខណៈរបស់អ្នកបានទេ។ សូមបញ្ជាក់លក្ខណៈស្វែងរករបស់អ្នក ឬទាក់ទងក្រុមគាំទ្ររបស់យើងសម្រាប់ជំនួយ។"
        )
        cursor.close()
        connection.close()
        return []