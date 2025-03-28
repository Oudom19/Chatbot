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
        return "action_fetch_product_by_name_kh"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain) -> list:
        # Extracting slot values
        model_name = tracker.get_slot("model_name")
        cpu = tracker.get_slot("cpu")
        ram = tracker.get_slot("ram")
        storage = tracker.get_slot("storage")

        connection = get_db_connection()
        if connection is None:
            dispatcher.utter_message(
                text="⚠️ ខ្ញុំសូមទោស, ប៉ុន្តែខ្ញុំមិនអាចតភ្ជាប់ទៅនឹងឯកសារ​ទិន្នន័យផលិតផលបានទេ។ សូមព្យាយាមម្តងទៀតក្រោយនេះ ឬទំនាក់ទំនងការគាំទ្រដើម្បីជួយ។"
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
        # បន្ថែមភាពចម្រុះទៅការណែនាំផលិតផល
        intros = [
            "បាទ/ចាស, នេះគឺជាផលិតផលមួយដែលស្របតាមតម្រូវការរបស់អ្នក៖",
            "ដោយផ្អែកលើការជ្រើសរើសរបស់អ្នក, ខ្ញុំស្នើសុំផលិតផលដូចតទៅ៖",
            "ខ្ញុំបានស្វែងរកផលិតផលមួយដែលសមនឹងតម្រូវការរបស់អ្នក៖",
            "ត្រឹមត្រូវ, នេះគឺជាជម្រើសល្អសម្រាប់អ្នក៖",
            "ផលិតផលនេះស្របតាមលក្ខណៈបញ្ជាក់របស់អ្នក៖",
            "ខ្ញុំស្នើសុំផលិតផលនេះផ្អែកលើលក្ខណៈកម្រិតរបស់អ្នក៖",
            "នេះគឺជាជម្រើសល្អសម្រាប់អ្នក៖",
            "ផលិតផលនេះអាចជារបស់ដែលអ្នកកំពុងស្វែងរកបានទេ៖",
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
                            f"ខ្ញុំបានស្វែងរក {len(products)} ជម្រើសដែលស្របតាមតម្រូវការរបស់អ្នក៖",
                            f"នេះគឺជាផលិតផល {len(products)} ដែលផ្អែកលើតម្រូវការរបស់អ្នក៖",
                            f"ខ្ញុំបានស្វែងរក {len(products)} ផលិតផលដែលសមនឹងតម្រូវការរបស់អ្នក៖",
                            f"នេះគឺជាការណែនាំ {len(products)} ដែលស្របតាមការជ្រើសរើសរបស់អ្នក៖",
                            f"ខ្ញុំបានស្វែងរក {len(products)} ផលិតផលដែលសមនឹងលក្ខណៈបញ្ជាក់របស់អ្នក៖",
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
                                 f"🌐 ព័ត៌មានបន្ថែម: ទៅកាន់គេហទំព័ររបស់យើង` https://www.ecidisti.com/department/Electronics"
                        )
                        cursor.close()
                        connection.close()
                        dispatcher.utter_message(text="តើអ្នកចង់ដឹងអំពីផលិតផលបន្ថែមទៀតទេ?")
                        return [SlotSet("shown_product_ids", shown_ids)]

        dispatcher.utter_message(
            text="❌ សូមអភ័យទោស, ខ្ញុំមិនអាចស្វែងរកផលិតផលដែលស្របតាមលក្ខខណ្ឌរបស់អ្នកបានទេ។ សូមពិចារណាអំពីការកែតម្រូវលក្ខខណ្ឌស្វែងរករបស់អ្នក ឬទំនាក់ទំនងទៅកាន់ក្រុមគាំទ្ររបស់យើងសម្រាប់ជំនួយបន្ថែម។"
        )
        cursor.close()
        connection.close()
        return []