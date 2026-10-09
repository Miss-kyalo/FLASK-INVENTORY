import requests


API_URL = "http://127.0.0.1:5000"


def send_request(method, path, data=None, params=None):
    try:
        response = requests.request(
            method, API_URL + path, json=data, params=params, timeout=10
        )
        print(response.json())
    except requests.RequestException as error:
        print("Could not reach the API:", error)


def main():
    print("Inventory manager")
    print("1. List items")
    print("2. Add item")
    print("3. Update item")
    print("4. Delete item")
    print("5. Look up a product")
    print("6. Import a product")

    choice = input("Choose an option: ")

    if choice == "1":
        send_request("GET", "/api/items")
    elif choice == "2":
        name = input("Product name: ")
        quantity = int(input("Quantity: "))
        price = float(input("Price: "))
        send_request(
            "POST",
            "/api/items",
            {"name": name, "quantity": quantity, "price": price},
        )
    elif choice == "3":
        item_id = input("Item ID: ")
        quantity = int(input("New quantity: "))
        send_request("PATCH", f"/api/items/{item_id}", {"quantity": quantity})
    elif choice == "4":
        item_id = input("Item ID: ")
        send_request("DELETE", f"/api/items/{item_id}")
    elif choice == "5":
        barcode = input("Barcode (leave blank to search by name): ")
        if barcode:
            params = {"barcode": barcode}
        else:
            params = {"name": input("Product name: ")}
        send_request("GET", "/api/products/lookup", params=params)
    elif choice == "6":
        barcode = input("Barcode (leave blank to search by name): ")
        quantity = int(input("Quantity: "))
        price = float(input("Price: "))
        if barcode:
            data = {"barcode": barcode, "quantity": quantity, "price": price}
        else:
            data = {
                "name": input("Product name: "),
                "quantity": quantity,
                "price": price,
            }
        send_request("POST", "/api/items/import", data)
    else:
        print("Please choose a number from 1 to 6.")


if __name__ == "__main__":
    main()
