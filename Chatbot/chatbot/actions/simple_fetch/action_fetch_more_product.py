from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from ..actions import get_db_connection
from rasa_sdk.events import SlotSet
import random


class ActionFetchMoreProducts(Action):
    def name(self) -> str:
        return "action_fetch_more_products"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain) -> list:
        # Get search criteria
        model_name = tracker.get_slot("model_name")
        common_name = tracker.get_slot("common_name")
        cpu = tracker.get_slot("cpu")
        ram = tracker.get_slot("ram")
        storage = tracker.get_slot("storage")

        # Get shown IDs
        shown_product_ids = tracker.get_slot("shown_product_ids") or []
        shown_product_cm_ids = tracker.get_slot("shown_product_cm_ids") or []
        all_shown_ids = list(set(shown_product_ids + shown_product_cm_ids))  # Combine and deduplicate

        connection = get_db_connection()
        if connection is None:
            dispatcher.utter_message(text="⚠️ Database unavailable. Please try again later.")
            return []

        cursor = connection.cursor(dictionary=True)

        # Base query with flexible conditions
        query = """
            SELECT DISTINCT p.id, p.model_name, p.common_name, p.category, p.screen_size, p.screen, 
                   p.cpu, p.ram, p.storage, p.gpu, p.weight, p.price, m.name as manufacturer, 
                   (SELECT image_url FROM images WHERE product_id = p.id LIMIT 1) as image_url
            FROM products p 
            JOIN manufacturers m ON p.manufacturer_id = m.id
            WHERE (%s IS NULL OR p.model_name = %s OR p.common_name = %s)
              AND (%s IS NULL OR p.cpu LIKE CONCAT('%%', %s, '%%'))
              AND (%s IS NULL OR p.ram = %s)
              AND (%s IS NULL OR p.storage = %s)
              {exclusion_clause}
            ORDER BY 
              CASE WHEN p.model_name = %s OR p.common_name = %s THEN 0 ELSE 1 END,
              p.price ASC
            LIMIT 5
        """

        # Prepare parameters
        params = [
            model_name or common_name, model_name, common_name,
            cpu, cpu,
            ram, ram,
            storage, storage
        ]

        # Add exclusion if needed
        exclusion_clause = ""
        if all_shown_ids:
            exclusion_clause = "AND p.id NOT IN ({})".format(",".join(["%s"] * len(all_shown_ids)))
            params.extend(all_shown_ids)

        # Add name matching for ordering at the end
        params.extend([model_name or common_name, model_name or common_name])

        try:
            cursor.execute(query.format(exclusion_clause=exclusion_clause), tuple(params))
            new_products = cursor.fetchall()

            if new_products:
                new_shown_ids = [str(product['id']) for product in new_products]

                # Update both slot lists
                response_events = [
                    SlotSet("shown_product_ids", shown_product_ids + new_shown_ids),
                    SlotSet("shown_product_cm_ids", shown_product_cm_ids + new_shown_ids)
                ]

                # Send introduction message
                intro = random.choice([
                    "Here are more options you might like:",
                    "Found additional matches for you:",
                    "More products that fit your criteria:",
                    "Additional options to consider:"
                ])
                dispatcher.utter_message(text=intro)

                # Display products
                for product in new_products:
                    if product['image_url']:
                        dispatcher.utter_message(image=product['image_url'])

                    dispatcher.utter_message(
                        text=f"■ {product['manufacturer']} {product['model_name']} \n"
                             f"○ Category: {product['category']}\n"
                             f"○ Price: ${product['price']}\n"
                             f"○ Display: {product['screen_size']}\" {product['screen']}\n"
                             f"○ Performance: {product['cpu']}, {product['ram']} RAM\n"
                             f"○ Storage: {product['storage']}\n"
                             f"○ Graphics: {product['gpu']}\n"
                             f"○ Weight: {product['weight']} kg\n"
                             f"🌐 More Info: https://www.ecidisti.com/department/Electronics"
                    )
            else:
                dispatcher.utter_message(
                    text="❌ No more matching products found. Try adjusting your search criteria."
                )
                return []

        except Exception as e:
            print(f"Database error: {str(e)}")
            dispatcher.utter_message(
                text="⚠️ An error occurred while searching for products. Please try again."
            )
            return []
        finally:
            cursor.close()
            connection.close()

        return response_events
