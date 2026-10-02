from database import get_connection


def save_products(items):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            for item in items:

                name = item["name"]
                quantity = item["quantity"]
                price = item["price"]

                # Check if product already exists
                cursor.execute(
                    """
                    SELECT id
                    FROM products
                    WHERE name = %s
                    """,
                    (name,)
                )

                product = cursor.fetchone()

                if product:

                    product_id = product[0]

                    # Update existing product
                    cursor.execute(
                        """
                        UPDATE products
                        SET quantity = quantity + %s,
                            price = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (
                            quantity,
                            price,
                            product_id
                        )
                    )

                    print(
                        f"Updated: {name} (+{quantity})"
                    )

                else:

                    # Insert new product
                    cursor.execute(
                        """
                        INSERT INTO products
                        (name, price, quantity)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            name,
                            price,
                            quantity
                        )
                    )

                    print(
                        f"Added: {name} "
                        f"(quantity={quantity})"
                    )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()