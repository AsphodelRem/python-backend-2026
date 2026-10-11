import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen


def request(base_url, method, path, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = Request(base_url.rstrip("/") + path, data=payload, headers=headers, method=method)
    with urlopen(req, timeout=5) as response:
        content = response.read()
    return json.loads(content) if content else {}


def pause(started):
    time.sleep(0.1 if int((time.monotonic() - started) // 12) % 2 == 0 else 0.5)


def create_items(base_url, started, deadline, worker_id):
    cart_id = request(base_url, "POST", "/cart")["id"]
    created = 0
    while time.monotonic() < deadline:
        item_id = request(
            base_url,
            "POST",
            "/item",
            {"name": f"Товар {worker_id}-{created}", "price": 100 + created % 50},
        )["id"]
        request(base_url, "POST", f"/cart/{cart_id}/add/{item_id}")
        request(base_url, "PUT", f"/item/{item_id}", {"name": "Товар дня", "price": 90})
        request(base_url, "PATCH", f"/item/{item_id}", {"price": 80 + created % 30})
        request(base_url, "GET", f"/cart/{cart_id}")
        request(base_url, "DELETE", f"/item/{item_id}")
        created += 1
        pause(started)
    return created


def get_items(base_url, started, deadline, item_ids):
    reads = 0
    while time.monotonic() < deadline:
        request(base_url, "GET", "/item?min_price=50&limit=5")
        request(base_url, "GET", f"/item/{item_ids[reads % len(item_ids)]}")
        request(base_url, "GET", "/cart?min_quantity=1")
        reads += 1
        pause(started)
    return reads


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    item_ids = [
        request(args.base_url, "POST", "/item", {"name": name, "price": price})["id"]
        for name, price in (("Молоко", 89.9), ("Кофе", 349), ("Хлеб", 59.5))
    ]
    started = time.monotonic()
    deadline = started + args.duration
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(create_items, args.base_url, started, deadline, worker_id): f"create-{worker_id}"
            for worker_id in range(2)
        }
        for worker_id in range(2):
            futures[executor.submit(get_items, args.base_url, started, deadline, item_ids)] = f"get-{worker_id}"
        for future in as_completed(futures):
            print(f"{futures[future]}: {future.result()} cycles")


if __name__ == "__main__":
    main()
