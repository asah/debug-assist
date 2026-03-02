"""
Factory functions that build synthetic git repos with known bugs
for integration testing of the debug-assist skill.

Each builder:
1. Accepts a repo_dir (Path to an initialized git repo)
2. Creates source files with realistic code
3. Makes commits establishing a history
4. Returns a metadata dict with error_message, expected findings, etc.
"""

import subprocess
import textwrap
from pathlib import Path


def _run(cwd, cmd):
    """Run a shell command in the given directory."""
    return subprocess.run(
        cmd, shell=True, cwd=str(cwd),
        capture_output=True, text=True, check=True,
    )


def _commit(cwd, message):
    """Stage all changes and commit."""
    _run(cwd, "git add -A")
    _run(cwd, f'git commit -m "{message}"')


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 1: Null reference due to missing guard
# ──────────────────────────────────────────────────────────────────────────────

def build_null_reference_bug(repo_dir: Path) -> dict:
    """
    A Python function processes user data but doesn't guard against
    None being returned from a database lookup.
    """
    src = repo_dir / "src"
    src.mkdir(parents=True, exist_ok=True)

    # user_service.py — has a bug: get_user can return None
    (src / "user_service.py").write_text(textwrap.dedent("""\
        from db import get_user_by_id

        def process_user_order(user_id, order_data):
            user = get_user_by_id(user_id)
            # BUG: no check for user being None
            discount = calculate_discount(user.tier, order_data["total"])
            return {
                "user": user.name,
                "discount": discount,
                "final_total": order_data["total"] - discount,
            }

        def calculate_discount(tier, total):
            rates = {"gold": 0.15, "silver": 0.10, "bronze": 0.05}
            return total * rates.get(tier, 0)
    """))

    # db.py — returns None for unknown users
    (src / "db.py").write_text(textwrap.dedent("""\
        USERS = {
            1: type('User', (), {'name': 'Alice', 'tier': 'gold', 'id': 1}),
            2: type('User', (), {'name': 'Bob', 'tier': 'silver', 'id': 2}),
        }

        def get_user_by_id(user_id):
            return USERS.get(user_id)  # returns None if not found
    """))

    _commit(repo_dir, "Add user service with order processing")

    return {
        "error_message": (
            "AttributeError: 'NoneType' object has no attribute 'tier' "
            "in user_service.py:process_user_order when processing an order "
            "for user_id=999"
        ),
        "expected_mentions": ["get_user_by_id", "None", "user_id", "tier"],
        "expected_strategy": "logging",
        "buggy_file": "src/user_service.py",
        "alt_identifiers": ["process_user_order", "get_user_by_id"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 2: Race condition in concurrent counter
# ──────────────────────────────────────────────────────────────────────────────

def build_race_condition_bug(repo_dir: Path) -> dict:
    """
    A Go-style concurrent counter without synchronization.
    The counter sometimes reports wrong totals.
    """
    src = repo_dir / "src"
    src.mkdir(parents=True, exist_ok=True)

    (src / "counter.py").write_text(textwrap.dedent("""\
        import threading

        class RequestCounter:
            def __init__(self):
                self.count = 0
                self.errors = 0

            def record_request(self, success):
                # BUG: no lock protecting shared state
                if success:
                    self.count += 1
                else:
                    self.errors += 1

            def get_stats(self):
                return {"total": self.count + self.errors,
                        "success": self.count,
                        "errors": self.errors}
    """))

    (src / "server.py").write_text(textwrap.dedent("""\
        import threading
        from counter import RequestCounter

        counter = RequestCounter()

        def handle_request(data):
            try:
                result = process(data)
                counter.record_request(success=True)
                return result
            except Exception:
                counter.record_request(success=False)
                raise

        def process(data):
            return {"status": "ok", "data": data}

        def run_load_test():
            threads = []
            for i in range(1000):
                t = threading.Thread(target=handle_request, args=(f"req-{i}",))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            return counter.get_stats()
    """))

    _commit(repo_dir, "Add request counter and server")

    return {
        "error_message": (
            "After running 1000 requests with run_load_test(), "
            "counter.get_stats() reports total=987 instead of 1000. "
            "The count is different each run. The code is in src/counter.py "
            "and src/server.py."
        ),
        "expected_mentions": ["lock", "thread", "race", "count"],
        "expected_strategy": "logging",
        "buggy_file": "src/counter.py",
        "alt_identifiers": ["RequestCounter", "record_request"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 3: Silent error swallowing in API client
# ──────────────────────────────────────────────────────────────────────────────

def build_swallowed_error_bug(repo_dir: Path) -> dict:
    """
    An API client catches all exceptions and returns a default value,
    hiding the real error from callers.
    """
    src = repo_dir / "src"
    src.mkdir(parents=True, exist_ok=True)

    (src / "api_client.py").write_text(textwrap.dedent("""\
        import json
        import urllib.request

        def fetch_pricing(product_id):
            try:
                url = f"https://api.internal.example.com/pricing/{product_id}"
                response = urllib.request.urlopen(url, timeout=5)
                data = json.loads(response.read())
                return data["price"]
            except Exception:
                # BUG: silently returns 0 on ANY error (network, JSON parse, missing key)
                return 0

        def get_order_total(items):
            total = 0
            for item in items:
                price = fetch_pricing(item["product_id"])
                total += price * item["quantity"]
            return total
    """))

    (src / "checkout.py").write_text(textwrap.dedent("""\
        from api_client import fetch_pricing, get_order_total

        def process_checkout(cart):
            total = get_order_total(cart["items"])
            if total == 0 and len(cart["items"]) > 0:
                # Something is wrong but we don't know what
                raise ValueError("Order total is $0 but cart is not empty")
            return {"total": total, "status": "confirmed"}
    """))

    _commit(repo_dir, "Add pricing API client and checkout")

    return {
        "error_message": (
            "ValueError: Order total is $0 but cart is not empty. "
            "The cart has 3 items but get_order_total returns 0. "
            "Code is in src/api_client.py and src/checkout.py."
        ),
        "expected_mentions": ["except", "swallow", "error", "fetch_pricing"],
        "expected_strategy": "logging",
        "buggy_file": "src/api_client.py",
        "alt_identifiers": ["fetch_pricing", "get_order_total"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Scenario 4: Off-by-one in pagination
# ──────────────────────────────────────────────────────────────────────────────

def build_pagination_bug(repo_dir: Path) -> dict:
    """
    A pagination helper skips the last page of results due to
    an off-by-one error in the page count calculation.
    """
    src = repo_dir / "src"
    src.mkdir(parents=True, exist_ok=True)

    (src / "paginator.py").write_text(textwrap.dedent("""\
        def paginate(items, page_size=10):
            \"\"\"Split items into pages.\"\"\"
            # BUG: integer division truncates — should use ceil or add 1 for remainder
            total_pages = len(items) // page_size
            pages = []
            for page_num in range(total_pages):
                start = page_num * page_size
                end = start + page_size
                pages.append(items[start:end])
            return pages

        def get_all_results(items, page_size=10):
            \"\"\"Return all items across all pages.\"\"\"
            pages = paginate(items, page_size)
            all_items = []
            for page in pages:
                all_items.extend(page)
            return all_items
    """))

    _commit(repo_dir, "Add pagination utility")

    return {
        "error_message": (
            "When I have 25 items and page_size=10, get_all_results only returns "
            "20 items instead of 25. The last 5 items are missing. "
            "Code is in src/paginator.py."
        ),
        "expected_mentions": ["page", "ceil", "remainder", "25", "20"],
        "expected_strategy": "debugger",
        "buggy_file": "src/paginator.py",
        "alt_identifiers": ["paginate", "get_all_results", "total_pages"],
    }
