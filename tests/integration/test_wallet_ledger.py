"""End-to-end integration tests for WalletLedger full flow:
Wallets, Deposits, Transfers, Holds, Ledger Entries, Idempotency, and Admin.
"""
from decimal import Decimal
import pytest
import httpx
from sqlalchemy import update

from app.models.user import User, UserRole

AUTH_BASE = "/api/v1/auth"
WALLETS_BASE = "/api/v1/wallets"
TRANSFERS_BASE = "/api/v1/transfers"
HOLDS_BASE = "/api/v1/holds"
TX_BASE = "/api/v1/transactions"
ADMIN_BASE = "/api/v1/admin"


async def get_token_for(client, name: str, email: str, password: str = "TestPass123!"):
    await client.post(f"{AUTH_BASE}/register", json={"name": name, "email": email, "password": password})
    r = await client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password})
    return r.json()["data"]["access_token"]


async def test_wallet_auto_created_and_deposit(client):
    token = await get_token_for(client, "Rohan", "rohan@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get wallet
    r = await client.get(f"{WALLETS_BASE}/me", headers=headers)
    assert r.status_code == 200
    w = r.json()["data"]
    assert w["currency"] == "INR"
    assert w["balance"] == 0.0
    assert w["available_balance"] == 0.0

    # 2. Deposit funds
    dep_r = await client.post(
        f"{WALLETS_BASE}/deposit",
        headers=headers,
        json={"amount": 10000.0, "description": "Salary deposit"},
    )
    assert dep_r.status_code == 200
    updated_w = dep_r.json()["data"]
    assert updated_w["balance"] == 10000.0
    assert updated_w["available_balance"] == 10000.0


async def test_transfer_flow_and_idempotency(client):
    alice_token = await get_token_for(client, "Alice", "alice@example.com")
    bob_token = await get_token_for(client, "Bob", "bob@example.com")

    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Top up Alice with 5,000 INR
    await client.post(
        f"{WALLETS_BASE}/deposit",
        headers=alice_headers,
        json={"amount": 5000.0},
    )

    # Bob's initial balance is 0
    bob_w = (await client.get(f"{WALLETS_BASE}/me", headers=bob_headers)).json()["data"]
    assert bob_w["balance"] == 0.0

    # Alice transfers 1,500 to Bob using Bob's email
    idemp_key = "test-idemp-key-001"
    headers_with_idemp = {**alice_headers, "Idempotency-Key": idemp_key}
    trf_r = await client.post(
        TRANSFERS_BASE,
        headers=headers_with_idemp,
        json={"recipient": "bob@example.com", "amount": 1500.0, "description": "Rent share"},
    )
    assert trf_r.status_code == 200
    trf_data = trf_r.json()["data"]
    assert trf_data["amount"] == 1500.0
    assert trf_data["status"] == "COMPLETED"

    # Alice balance now 3,500
    alice_w = (await client.get(f"{WALLETS_BASE}/me", headers=alice_headers)).json()["data"]
    assert alice_w["balance"] == 3500.0

    # Bob balance now 1,500
    bob_w = (await client.get(f"{WALLETS_BASE}/me", headers=bob_headers)).json()["data"]
    assert bob_w["balance"] == 1500.0

    # IDEMPOTENCY TEST: Repeat exact same request with same key
    repeat_r = await client.post(
        TRANSFERS_BASE,
        headers=headers_with_idemp,
        json={"recipient": "bob@example.com", "amount": 1500.0, "description": "Rent share"},
    )
    assert repeat_r.status_code == 200
    # Balance must NOT be deducted again!
    alice_w_after = (await client.get(f"{WALLETS_BASE}/me", headers=alice_headers)).json()["data"]
    assert alice_w_after["balance"] == 3500.0


async def test_transfer_insufficient_balance_rejected(client):
    token = await get_token_for(client, "PoorUser", "poor@example.com")
    await get_token_for(client, "TargetUser", "target@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        TRANSFERS_BASE,
        headers=headers,
        json={"recipient": "target@example.com", "amount": 99999.0},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


async def test_hold_reserve_capture_and_release(client):
    token = await get_token_for(client, "HoldUser", "holduser@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Deposit 10,000
    await client.post(f"{WALLETS_BASE}/deposit", headers=headers, json={"amount": 10000.0})

    # 1. Create Hold of 3,000
    hold_r = await client.post(
        HOLDS_BASE,
        headers=headers,
        json={"amount": 3000.0, "reason": "Hotel Pre-auth"},
    )
    assert hold_r.status_code == 201
    hold = hold_r.json()["data"]
    hold_id = hold["id"]
    assert hold["status"] == "ACTIVE"

    # Wallet balance remains 10,000, but available balance is 7,000
    w = (await client.get(f"{WALLETS_BASE}/me", headers=headers)).json()["data"]
    assert w["balance"] == 10000.0
    assert w["held_balance"] == 3000.0
    assert w["available_balance"] == 7000.0

    # 2. Release the hold
    rel_r = await client.post(f"{HOLDS_BASE}/{hold_id}/release", headers=headers)
    assert rel_r.status_code == 200
    assert rel_r.json()["data"]["status"] == "RELEASED"

    # Wallet available balance restored to 10,000
    w_rel = (await client.get(f"{WALLETS_BASE}/me", headers=headers)).json()["data"]
    assert w_rel["balance"] == 10000.0
    assert w_rel["held_balance"] == 0.0
    assert w_rel["available_balance"] == 10000.0

    # 3. Create another hold and capture it
    hold_r2 = await client.post(
        HOLDS_BASE,
        headers=headers,
        json={"amount": 4000.0, "reason": "Car Rental Deposit"},
    )
    hold2_id = hold_r2.json()["data"]["id"]

    cap_r = await client.post(f"{HOLDS_BASE}/{hold2_id}/capture", headers=headers)
    assert cap_r.status_code == 200
    assert cap_r.json()["data"]["status"] == "CAPTURED"

    # Wallet total balance deducted to 6,000
    w_cap = (await client.get(f"{WALLETS_BASE}/me", headers=headers)).json()["data"]
    assert w_cap["balance"] == 6000.0
    assert w_cap["held_balance"] == 0.0
    assert w_cap["available_balance"] == 6000.0


async def test_admin_dashboard_and_reconciliation(client, session_factory):
    # Register an admin user
    admin_token = await get_token_for(client, "SuperAdmin", "superadmin@example.com")
    async with session_factory() as s:
        await s.execute(update(User).where(User.email == "superadmin@example.com").values(role=UserRole.ADMIN))
        await s.commit()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin dashboard
    dash_r = await client.get(f"{ADMIN_BASE}/dashboard", headers=admin_headers)
    assert dash_r.status_code == 200
    stats = dash_r.json()["data"]
    assert stats["total_users"] >= 1
    assert stats["ledger_balanced"] is True

    # 2. Live reconciliation
    rec_r = await client.get(f"{ADMIN_BASE}/reconciliation", headers=admin_headers)
    assert rec_r.status_code == 200
    rec = rec_r.json()["data"]
    assert rec["status"] == "BALANCED"
    assert rec["discrepant_wallets"] == 0


async def test_transactions_query_and_details(client):
    token = await get_token_for(client, "TxUser", "txuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Deposit
    await client.post(
        f"{WALLETS_BASE}/deposit",
        headers=headers,
        json={"amount": 5000.0, "description": "Deposit to test"},
    )

    # 2. List transactions
    r = await client.get(TX_BASE, headers=headers)
    assert r.status_code == 200
    res_data = r.json()["data"]
    assert res_data["total"] == 1
    assert len(res_data["items"]) == 1
    tx = res_data["items"][0]
    assert tx["amount"] == 5000.0
    assert tx["type"] == "DEPOSIT"
    assert tx["status"] == "COMPLETED"
    assert tx["description"] == "Deposit to test"
    assert len(tx["ledger_entries"]) == 2

    # 3. Filter by type
    r_type = await client.get(f"{TX_BASE}?type=DEPOSIT", headers=headers)
    assert r_type.status_code == 200
    assert r_type.json()["data"]["total"] == 1

    r_type_none = await client.get(f"{TX_BASE}?type=TRANSFER", headers=headers)
    assert r_type_none.status_code == 200
    assert r_type_none.json()["data"]["total"] == 0

    # 4. Search
    r_search = await client.get(f"{TX_BASE}?search=Deposit", headers=headers)
    assert r_search.status_code == 200
    assert r_search.json()["data"]["total"] == 1

    # 4b. Date filters
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    future = (now + timedelta(days=1)).isoformat()
    far_past = (now - timedelta(days=5)).isoformat()

    r_date_match = await client.get(TX_BASE, params={"start_date": past, "end_date": future}, headers=headers)
    assert r_date_match.status_code == 200, f"Error: {r_date_match.json()}"
    assert r_date_match.json()["data"]["total"] == 1

    r_date_nomatch = await client.get(TX_BASE, params={"start_date": far_past, "end_date": past}, headers=headers)
    assert r_date_nomatch.status_code == 200, f"Error: {r_date_nomatch.json()}"
    assert r_date_nomatch.json()["data"]["total"] == 0

    # 5. Detail
    r_detail = await client.get(f"{TX_BASE}/{tx['id']}", headers=headers)
    assert r_detail.status_code == 200
    detail = r_detail.json()["data"]
    assert detail["id"] == tx["id"]
    assert detail["reference_id"] == tx["reference_id"]
    assert len(detail["ledger_entries"]) == 2

