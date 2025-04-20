import os
import io
import csv
import json
import time

from flask import Flask, jsonify, request, Response, send_file
from pymongo import MongoClient, ASCENDING, GEOSPHERE
from pymongo.errors import DuplicateKeyError
from web3 import Web3
from web3.exceptions import ContractLogicError
from reportlab.pdfgen import canvas as pdf_canvas

app = Flask(__name__)

# ─── MongoDB Setup ─────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client      = MongoClient(MONGODB_URI)
db          = client["chain_custody_db"]

# materials collection
materials_col = db["materials"]
materials_col.create_index([("materialId", ASCENDING)], name="materialId_1", unique=True)
materials_col.create_index([("location", GEOSPHERE)], name="location_2dsphere_idx")

# transfers history collection
transfers_col = db["transfers"]
transfers_col.create_index(
    [("materialId", ASCENDING), ("timestamp", ASCENDING)],
    name="material_ts_idx"
)

# hazardous‑waste collections
waste_col   = db["waste"]
waste_col.create_index(
    [("wasteId", ASCENDING)],
    name="wasteId_1",
    unique=True
)

history_col = db["waste_history"]
history_col.create_index(
    [("wasteId", ASCENDING), ("timestamp", ASCENDING)],
    name="waste_history_ts_idx"
)

# ─── Web3 / Ethereum Setup ─────────────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(os.getenv("HTTP_PROVIDER", "http://127.0.0.1:8545")))
w3.eth.default_account = w3.eth.accounts[0]

# ChainCustody contract
with open("artifacts/contracts/ChainCustody.sol/ChainCustody.json") as f:
    contract_json    = json.load(f)
chain_abi          = contract_json["abi"]
chain_address      = os.getenv("CONTRACT_ADDRESS")
contract           = w3.eth.contract(address=chain_address, abi=chain_abi)

# WasteChain contract
with open("artifacts/contracts/WasteChain.sol/WasteChain.json") as f:
    waste_json       = json.load(f)
waste_abi           = waste_json["abi"]
waste_address       = os.getenv("WASTE_CONTRACT_ADDRESS")
waste_contract      = w3.eth.contract(address=waste_address, abi=waste_abi)

# ─── Sample Users Endpoint ──────────────────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
def list_users():
    return jsonify([
        {"userId": "1", "username": "alice", "role": "manufacturer"},
        {"userId": "2", "username": "bob",   "role": "transporter"},
    ])

# ─── Materials CRUD Endpoints ──────────────────────────────────────────────────
@app.route("/api/materials", methods=["GET"])
def get_materials():
    docs = list(materials_col.find({}, {"_id": 0}))
    return jsonify(docs), 200

@app.route("/api/materials", methods=["POST"])
def create_material():
    data = request.json or {}
    if "materialId" not in data or "description" not in data:
        return jsonify({"error": "materialId and description are required"}), 400

    # build doc
    new_doc = {
        "materialId":   data["materialId"],
        "description":  data["description"],
        "metadata":     data.get("metadata", {}),
        "currentHolder": w3.eth.default_account,
        "lastSequence": 0,
        "status":       "Created",
        "createdAt":    int(time.time()),
    }
    if isinstance(data.get("location"), dict):
        lat = data["location"]["lat"]
    lng = data["location"]["lng"]
    new_doc["location"] = {
        "type": "Point",
        "coordinates": [lng, lat]
    }

    # ── 1A. initialize on‑chain ─────────────────
    try:
        tx = contract.functions.initializeMaterial(
         new_doc["materialId"],          # 1️⃣ first string
         new_doc["description"]          # 2️⃣ second string
     ).transact({"from": w3.eth.default_account})
        w3.eth.wait_for_transaction_receipt(tx)
    except ContractLogicError as e:
        return jsonify({"error": "on‑chain init failed", "reason": str(e)}), 400
    # ────────────────────────────────────────────

    # insert into Mongo
    result = materials_col.insert_one(new_doc)
    new_doc["_id"] = str(result.inserted_id)   # make _id JSON‑serialisable
    return jsonify(new_doc), 201


@app.route("/api/materials/<material_id>", methods=["GET"])
def get_material(material_id):
    m = materials_col.find_one({"materialId": material_id}, {"_id": 0})
    if not m:
        return jsonify({"error": "Not found"}), 404

    try:
        holder, seq, _, _ = contract.functions.getMaterial(material_id).call()
    except ContractLogicError:
        return jsonify(m), 200      # Mongo record only

    materials_col.update_one(
        {"materialId": material_id},
        {"$set": {"currentHolder": holder, "lastSequence": seq}}
    )
    m.update({"currentHolder": holder, "lastSequence": seq})
    return jsonify(m), 200


@app.route("/api/materials/<material_id>/status", methods=["GET"])
def get_status(material_id):
    m = materials_col.find_one(
        {"materialId": material_id},
        {"status": 1, "_id": 0}
    )
    if not m:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": m["status"]}), 200

def to_point(d):
    # helper to convert {lat, lng} → GeoJSON Point
    return {"type": "Point", "coordinates": [d["lng"], d["lat"]]}

@app.route("/api/materials/<material_id>/transfer", methods=["POST"])
def transfer_material(material_id):
    data = request.json or {}

    # 1. Validate inputs
    new_holder = data.get("newHolder")
    from_info  = data.get("from")  # {"lat": ..., "lng": ...}
    to_info    = data.get("to")    # {"lat": ..., "lng": ...}
    if not new_holder or not from_info or not to_info:
        return jsonify({"error": "newHolder, from and to are all required"}), 400

    # 2. Look up current holder
    existing = materials_col.find_one({"materialId": material_id}, {"_id": 0})
    if not existing:
        return jsonify({"error": "Not found"}), 404
    prev_holder = existing["currentHolder"]

    # 3. On‑chain transfer
    try:
        tx_hash = contract.functions.transferMaterial(material_id, new_holder)\
                          .transact({"from": prev_holder})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except ContractLogicError as e:
        return jsonify({"error": "Transfer failed", "reason": str(e)}), 409

    # 4. Fetch updated on‑chain state
    #    returns: (holder, sequence, description, status)
    holder, seq, _, _ = contract.functions.getMaterial(material_id).call()

    # 5. Update the Mongo “materials” record
    materials_col.update_one(
        {"materialId": material_id},
        {"$set": {
            "currentHolder": holder,
            "lastSequence": seq,
            "txHash": receipt.transactionHash.hex()
        }}
    )

    # 6. GeoJSON helpers
    def to_point(d):
        return {
            "type": "Point",
            "coordinates": [d["lng"], d["lat"]]
        }

    pt_from = to_point(from_info)
    pt_to   = to_point(to_info)
    line    = {
        "type": "LineString",
        "coordinates": [
            pt_from["coordinates"],
            pt_to["coordinates"]
        ]
    }
    path = {
        "type": "GeometryCollection",
        "geometries": [pt_from, line, pt_to]
    }

    # 7. Log the transfer step (point–line–point)
    transfers_col.insert_one({
        "materialId":   material_id,
        "from":         pt_from,
        "to":           pt_to,
        "transferPath": path,
        "timestamp":    int(time.time()),
        "txHash":       receipt.transactionHash.hex()
    })

    # 8. Return the fresh material record
    updated = materials_col.find_one({"materialId": material_id}, {"_id": 0})
    return jsonify(updated), 200



@app.route("/api/materials/<material_id>/transfers", methods=["GET"])
def list_transfers(material_id):
    if not materials_col.find_one({"materialId": material_id}):
        return jsonify({"error": "Not found"}), 404
    history = list(transfers_col.find(
        {"materialId": material_id},
        {"_id": 0}
    ))
    return jsonify(history), 200

@app.route("/api/materials/<material_id>/export/csv", methods=["GET"])
def export_csv(material_id):
    m = materials_col.find_one({"materialId": material_id}, {"_id": 0})
    if not m:
        return jsonify({"error": "Not found"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    headers = ["materialId", "description", "currentHolder",
               "lastSequence", "status", "txHash", "metadata"]
    writer.writerow(headers)
    writer.writerow([
        m["materialId"],
        m["description"],
        m["currentHolder"],
        m["lastSequence"],
        m["status"],
        m.get("txHash", ""),
        json.dumps(m["metadata"])
    ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={material_id}.csv"}
    ), 200

@app.route("/api/materials/<material_id>/export/pdf", methods=["GET"])
def export_pdf(material_id):
    m = materials_col.find_one({"materialId": material_id}, {"_id": 0})
    if not m:
        return jsonify({"error": "Not found"}), 404

    buffer = io.BytesIO()
    c = pdf_canvas(buffer)
    text = c.beginText(40, 800)
    text.setFont("Helvetica-Bold", 14)
    text.textLine(f"Material Report: {material_id}")
    text.setFont("Helvetica", 12)
    for line in [
        f"Description   : {m['description']}",
        f"Current Holder: {m['currentHolder']}",
        f"Sequence      : {m['lastSequence']}",
        f"Status        : {m['status']}",
        f"Transaction   : {m.get('txHash','')}",
        f"Metadata      : {json.dumps(m['metadata'])}"
    ]:
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{material_id}.pdf",
        mimetype="application/pdf"
    ), 200

# ─── Hazardous‑Waste Endpoints ────────────────────────────────────────────────
@app.route("/api/waste", methods=["POST"])
def create_waste():
    data = request.json or {}
    required = ["wasteId", "wasteType", "hazardClass", "quantity", "units"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing one of " + ", ".join(required)}), 400

    # on‑chain call
    try:
        tx = waste_contract.functions.createWaste(
            data["wasteId"],
            data["wasteType"],
            data["hazardClass"],
            int(data["quantity"]),
            data["units"]
        ).transact({"from": w3.eth.default_account})
        w3.eth.wait_for_transaction_receipt(tx)
    except Exception as e:
        return jsonify({"error": "on‑chain create failed", "reason": str(e)}), 400

    doc = {
        "wasteId":       data["wasteId"],
        "wasteType":     data["wasteType"],
        "hazardClass":   data["hazardClass"],
        "quantity":      int(data["quantity"]),
        "units":         data["units"],
        "currentHolder": w3.eth.default_account,
        "status":        "Created",
        "sequence":      1,
        "createdAt":     int(time.time())
    }

    result = waste_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)   # keep _id but as string

    return jsonify(doc), 201


@app.route("/api/waste/<waste_id>/transfer", methods=["POST"])
def transfer_waste(waste_id):
    body       = request.json or {}
    new_holder = body.get("newHolder")
    from_geo   = body.get("from")
    to_geo     = body.get("to")
    if not new_holder or not from_geo or not to_geo:
        return jsonify({"error": "newHolder, from and to are required"}), 400

    try:
        tx = waste_contract.functions.transferWaste(waste_id, new_holder)\
             .transact({"from": w3.eth.default_account})
        receipt = w3.eth.wait_for_transaction_receipt(tx)
    except Exception as e:
        return jsonify({"error":"transfer failed","reason":str(e)}), 409

    waste_col.update_one(
        {"wasteId": waste_id},
        {"$set": {"currentHolder": new_holder, "status": "InTransit"},
         "$inc": {"sequence": 1}}
    )
    history_col.insert_one({
        "wasteId":   waste_id,
        "from":      from_geo,
        "to":        to_geo,
        "timestamp": int(time.time()),
        "txHash":    receipt.transactionHash.hex()
    })
    updated = waste_col.find_one({"wasteId": waste_id}, {"_id": 0})
    return jsonify(updated), 200

@app.route("/api/waste/<waste_id>/deliver", methods=["POST"])
def deliver_waste(waste_id):
    try:
        tx = waste_contract.functions.deliverWaste(waste_id)\
             .transact({"from": w3.eth.default_account})
        receipt = w3.eth.wait_for_transaction_receipt(tx)
    except Exception as e:
        return jsonify({"error":"deliver failed","reason":str(e)}), 409

    waste_col.update_one(
        {"wasteId": waste_id},
        {"$set": {"status": "Delivered"}, "$inc": {"sequence": 1}}
    )
    history_col.insert_one({
        "wasteId":   waste_id,
        "event":     "Delivered",
        "timestamp": int(time.time()),
        "txHash":    receipt.transactionHash.hex()
    })
    return jsonify({"wasteId": waste_id, "status": "Delivered"}), 200

@app.route("/api/waste/<waste_id>/dispose", methods=["POST"])
def dispose_waste(waste_id):
    try:
        tx = waste_contract.functions.disposeWaste(waste_id)\
             .transact({"from": w3.eth.default_account})
        receipt = w3.eth.wait_for_transaction_receipt(tx)
    except Exception as e:
        return jsonify({"error":"dispose failed","reason":str(e)}), 409

    waste_col.update_one(
        {"wasteId": waste_id},
        {"$set": {"status": "Disposed"}, "$inc": {"sequence": 1}}
    )
    history_col.insert_one({
        "wasteId":   waste_id,
        "event":     "Disposed",
        "timestamp": int(time.time()),
        "txHash":    receipt.transactionHash.hex()
    })
    return jsonify({"wasteId": waste_id, "status": "Disposed"}), 200

@app.route("/api/waste/<waste_id>", methods=["GET"])
def get_waste(waste_id):
    m = waste_col.find_one({"wasteId": waste_id}, {"_id": 0})
    if not m:
        return jsonify({"error": "Not found"}), 404

    holder, status, wtype, hclass, qty, units, seq = \
        waste_contract.functions.getWaste(waste_id).call()
    m.update({
        "currentHolder": holder,
        "status":        status.name,
        "sequence":      seq
    })
    return jsonify(m), 200

from flask import jsonify

@app.route("/api/materials/<material_id>/featurecollection", methods=["GET"])
def material_featurecollection(material_id):
    # 1. Look up the material (for e.g. company metadata)
    material = materials_col.find_one({"materialId": material_id}, {"_id": 0})
    if not material:
        return jsonify({"error": "Material not found"}), 404

    company = material.get("metadata", {}).get("company", "Unknown Company")

    # 2. Load its transfers in chronological order
    transfers = list(transfers_col
                     .find({"materialId": material_id})
                     .sort("timestamp", 1))

    if not transfers:
        return jsonify({"type": "FeatureCollection", "features": []}), 200

    features = []

    # 3. Build Point features for each 'from' and 'to'
    for t in transfers:
        # departure Point
        features.append({
            "type": "Feature",
            "geometry": t["from"],
            "properties": {
                "company":        company,
                "status":         "In Transit",
                "description":    f"Departed at {t['timestamp']}",
                "transaction_id": t.get("txHash")
            }
        })
        # arrival Point
        features.append({
            "type": "Feature",
            "geometry": t["to"],
            "properties": {
                "company":        company,
                "status":         "Delivered",
                "description":    f"Arrived at {t['timestamp']}",
                "transaction_id": t.get("txHash")
            }
        })

    # 4. Build a LineString that strings all points together
    coords = []
    for t in transfers:
        frm = t["from"]["coordinates"]
        to  = t["to"]["coordinates"]
        # avoid duplicating the end of one step as the start of the next
        if not coords or coords[-1] != frm:
            coords.append(frm)
        coords.append(to)

    features.append({
        "type": "Feature",
        "geometry": {
            "type":        "LineString",
            "coordinates": coords
        },
        "properties": {
            "company":     company,
            "route_id":    f"route_{material_id}",
            "description": f"Route for {material_id}",
            "status":      "On Schedule"
        }
    })

    # 5. Return the FeatureCollection
    return jsonify({
        "type":     "FeatureCollection",
        "features": features
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=8888)
