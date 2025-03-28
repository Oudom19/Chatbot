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
        cpu = tracker.get_slot("cpu")
        ram = tracker.get_slot("ram")
        storage = tracker.get_slot("storage")
        shown_product_ids = tracker.get_slot("shown_product_ids") or []

        connection = get_db_connection()
        if connection is None:
            dispatcher.utter_message(text="⚠️ Database unavailable. Please try again later.")
            return []

        cursor = connection.cursor(dictionary=True)

        # Define the base query with proper exclusion
        base_query = """
            SELECT DISTINCT p.id, p.model_name, p.category, p.screen_size, p.screen, p.cpu, p.ram, p.storage, 
                   p.gpu, p.weight, p.price, m.name as manufacturer, 
                   (SELECT image_url FROM images WHERE product_id = p.id LIMIT 1) as image_url
            FROM products p 
            JOIN manufacturers m ON p.manufacturer_id = m.id
            WHERE {condition}
            {exclusion_clause}
            ORDER BY p.price ASC
            LIMIT 5
        """

        # Define search conditions with priority
        conditions = [
            ("p.model_name = %s AND p.ram = %s AND p.cpu = %s AND p.storage = %s",
             [model_name, ram, cpu, storage]),
            ("p.model_name = %s AND p.ram = %s AND p.cpu = %s",
             [model_name, ram, cpu]),
            ("p.model_name = %s AND p.ram = %s AND p.storage = %s",
             [model_name, ram, storage]),
            ("p.model_name = %s AND p.cpu = %s AND p.storage = %s",
             [model_name, cpu, storage]),
            ("p.model_name = %s AND p.ram = %s",
             [model_name, ram]),
            ("p.model_name = %s AND p.cpu = %s",
             [model_name, cpu]),
            ("p.model_name = %s AND p.storage = %s",
             [model_name, storage]),
            ("p.model_name = %s",
             [model_name]),
        ]

        found_products = False
        response_events = []

        for condition, values in conditions:
            # Skip conditions with missing values
            if not all(v is not None for v in values):
                continue

            # Prepare the exclusion clause
            exclusion_clause = ""
            query_params = values.copy()

            if shown_product_ids:
                exclusion_clause = "AND p.id NOT IN (%s)" % ",".join(["%s"] * len(shown_product_ids))
                query_params.extend(shown_product_ids)

            # Build and execute the query
            query = base_query.format(
                condition=condition,
                exclusion_clause=exclusion_clause
            )

            try:
                cursor.execute(query, tuple(query_params))
                new_products = cursor.fetchall()

                if new_products:
                    found_products = True
                    new_shown_ids = [str(product['id']) for product in new_products]
                    response_events.append(SlotSet("shown_product_ids", shown_product_ids + new_shown_ids))

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
                            text=f"■ {product['manufacturer']} {product['model_name']}\n"
                                 f"○ Category: {product['category']}\n"
                                 f"○ Price: ${product['price']}\n"
                                 f"○ Display: {product['screen_size']}\" {product['screen']}\n"
                                 f"○ Performance: {product['cpu']}, {product['ram']} RAM\n"
                                 f"○ Storage: {product['storage']}\n"
                                 f"○ Graphics: {product['gpu']}\n"
                                 f"○ Weight: {product['weight']} kg\n"
                                 f"🌐 More Info: https://www.ecidisti.com/department/Electronics"
                        )
                    break  # Stop after first successful match

            except Exception as e:
                print(f"Database error: {str(e)}")
                continue

        if not found_products:
            dispatcher.utter_message(
                text="❌ No more matching products found. Try adjusting your search criteria."
            )

        cursor.close()
        connection.close()
        return response_events