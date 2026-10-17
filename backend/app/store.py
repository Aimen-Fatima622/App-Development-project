"""Concurrency-safe store, inventory reservation, and PDF receipt generation per Section 5.12."""
import base64
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
from app.crypto import canonical, get_salt, sign
from app.errors import AppException, validation_error
from app.state import state


def build_minimal_pdf(order_id: str, formatted_total: str) -> bytes:
    """Generate a genuine, valid PDF document starting with %PDF containing order_id and formatted total."""
    text_content = f"Order ID: {order_id}\nTotal: {formatted_total}"
    # PDF stream content
    stream_data = (
        f"BT\n"
        f"/F1 14 Tf\n"
        f"50 750 Td\n"
        f"(NaSCon 26 Merchandise Receipt) Tj\n"
        f"0 -30 Td\n"
        f"(Order ID: {order_id}) Tj\n"
        f"0 -25 Td\n"
        f"(Total: {formatted_total}) Tj\n"
        f"ET\n"
    ).encode("latin1")
    stream_len = len(stream_data)

    # Assemble PDF objects
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
    )
    obj4 = (
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
        + stream_data
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.4\n"
    body = header
    offsets = [0]

    for obj in [obj1, obj2, obj3, obj4, obj5]:
        offsets.append(len(body))
        body += obj

    xref_offset = len(body)
    xref = f"xref\n0 6\n0000000000 65535 f \n".encode("latin1")
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("latin1")

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin1")

    return body + xref + trailer


def process_checkout(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    order_id = body.get("order_id")
    customer_id = body.get("customer_id")
    items = body.get("items")
    discount_code = body.get("discount_code")
    payment = body.get("payment")

    # Step 1: Validation (400)
    bad_fields = []
    if not order_id or not isinstance(order_id, str):
        bad_fields.append("order_id")
    if not customer_id or not isinstance(customer_id, str):
        bad_fields.append("customer_id")
    if not isinstance(items, list) or len(items) < 1 or len(items) > 10:
        bad_fields.append("items")
    else:
        seen_variants = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                bad_fields.append(f"items[{idx}]")
                continue
            vid = item.get("variant_id")
            qty = item.get("quantity")
            if not vid or not isinstance(vid, str):
                bad_fields.append(f"items[{idx}].variant_id")
            if vid in seen_variants:
                bad_fields.append(f"items[{idx}].variant_id")
            seen_variants.add(vid)
            if not isinstance(qty, int) or qty < 1 or qty > 10 or isinstance(qty, bool):
                bad_fields.append(f"items[{idx}].quantity")

    if not isinstance(payment, dict) or not payment.get("token"):
        bad_fields.append("payment.token")

    if bad_fields:
        raise validation_error("Validation failed for checkout.", fields=bad_fields)

    with state.lock:
        # Idempotency check
        if order_id in state.orders:
            stored = state.orders[order_id]
            if canonical(stored["body"]) == canonical(body):
                return 200, stored["response"]
            raise AppException(
                status_code=409,
                code="DUPLICATE_ORDER_ID",
                message=f"Order {order_id} already exists with a different body.",
                details={"order_id": order_id},
            )

        # Step 2: Variants exist (404)
        item_details = []
        subtotal_minor = 0
        for item in items:
            vid = item["variant_id"]
            if vid not in state.variants:
                raise AppException(
                    status_code=404,
                    code="VARIANT_NOT_FOUND",
                    message=f"Variant {vid} not found.",
                    details={"variant_id": vid},
                )
            v_obj = state.variants[vid]
            u_price = v_obj["price_minor"]
            subtotal_minor += u_price * item["quantity"]
            item_details.append({
                "variant_id": vid,
                "quantity": item["quantity"],
                "unit_price_minor": u_price,
            })

        # Step 3: Discount code (400)
        discount_minor = 0
        if discount_code is not None:
            if discount_code != "WELCOME10":
                raise AppException(
                    status_code=400,
                    code="INVALID_DISCOUNT_CODE",
                    message=f"Unknown discount code {discount_code}.",
                    details={"discount_code": discount_code},
                )
            discount_minor = math.floor(subtotal_minor * 10 / 100)

        total_minor = subtotal_minor - discount_minor

        # Step 4: Atomic stock reservation (409 OUT_OF_STOCK)
        for item in items:
            vid = item["variant_id"]
            qty = item["quantity"]
            if state.variants[vid]["stock"] < qty:
                raise AppException(
                    status_code=409,
                    code="OUT_OF_STOCK",
                    message=f"Variant {vid} has no stock left.",
                    details={"variant_id": vid},
                )

        # Reserve stock
        for item in items:
            vid = item["variant_id"]
            qty = item["quantity"]
            state.variants[vid]["stock"] -= qty
            state.variants[vid]["reserved"] += qty

        # Step 5: Mock Gateway Call
        token = payment.get("token")
        if token == "tok_declined":
            # Release reservation
            for item in items:
                vid = item["variant_id"]
                qty = item["quantity"]
                state.variants[vid]["stock"] += qty
                state.variants[vid]["reserved"] -= qty
            raise AppException(
                status_code=402,
                code="PAYMENT_DECLINED",
                message="Payment was declined by mock gateway.",
                details={"token": token},
            )
        elif token == "tok_capture_fail":
            # Release reservation
            for item in items:
                vid = item["variant_id"]
                qty = item["quantity"]
                state.variants[vid]["stock"] += qty
                state.variants[vid]["reserved"] -= qty
            raise AppException(
                status_code=402,
                code="PAYMENT_CAPTURE_FAILED",
                message="Payment capture failed.",
                details={"token": token},
            )

        # Step 6: Success — commit reservation permanently
        for item in items:
            vid = item["variant_id"]
            qty = item["quantity"]
            state.variants[vid]["reserved"] -= qty

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt_payload = {
            "order_id": order_id,
            "customer_id": customer_id,
            "items": item_details,
            "subtotal_minor": subtotal_minor,
            "discount_minor": discount_minor,
            "total_minor": total_minor,
            "currency": "PKR",
            "paid_at": now_str,
        }

        salt = get_salt()
        receipt_sig = sign(salt, order_id, receipt_payload)

        # Format total as PKR 4500.00 (major units, two decimals, no thousands separator)
        major_units = total_minor / 100.0
        formatted_total = f"PKR {major_units:.2f}"

        pdf_bytes = build_minimal_pdf(order_id, formatted_total)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("latin1")

        resp = {
            "order_id": order_id,
            "status": "paid",
            "currency": "PKR",
            "items": item_details,
            "subtotal_minor": subtotal_minor,
            "discount_minor": discount_minor,
            "total_minor": total_minor,
            "payment": {
                "authorization_id": "auth_1",
                "capture_id": "cap_1",
                "state": "captured",
            },
            "receipt": {
                "payload": receipt_payload,
                "signature": receipt_sig,
                "pdf_base64": pdf_base64,
            },
        }

        state.orders[order_id] = {"body": body, "response": resp}
        return 201, resp


def get_inventory(variant_id: str) -> Dict[str, Any]:
    with state.lock:
        if variant_id not in state.variants:
            raise AppException(
                status_code=404,
                code="VARIANT_NOT_FOUND",
                message=f"Variant {variant_id} not found.",
                details={"variant_id": variant_id},
            )
        v = state.variants[variant_id]
        return {
            "variant_id": variant_id,
            "stock": v["stock"],
            "reserved": v["reserved"],
        }
