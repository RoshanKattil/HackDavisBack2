OLD READ ME OUT DATED THIS WAS JUST FOR SAMPLEAPI.PY Below is a **README.md** you can drop into your `sample-chain-of-custody-api/` repo and share with your front‑end developer.

```markdown
# Chain‑of‑Custody Sample API

This is a **Flask**‑based sample API that returns **static JSON** for all endpoints.  
Your front‑end team can build UI & map overlays now, while the real Solana backend is in progress.

---

## 📁 Project Structure

```
sample-chain-of-custody-api/
├── app.py
└── requirements.txt
```

---

## ⚙️ Prerequisites

- Python 3.7+
- `pip`

---

## 🚀 Getting Started

1. **Clone & install**  
   ```bash
   git clone <repo-url>
   cd sample-chain-of-custody-api
   pip install -r requirements.txt
   ```

2. **Run the server**  
   ```bash
   python app.py
   ```
   By default, it listens on `http://127.0.0.1:8888/`

---

## 🔌 API Endpoints

All responses are static JSON shapes—no real Solana calls yet.

### 1. Authentication

| Method | Path                  | Notes                                      |
| ------ | --------------------- | ------------------------------------------ |
| POST   | `/api/auth/login`     | Returns a static JWT for use in headers.   |

**Request**

```bash
curl -i -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password"}'
```

**Response**

```json
HTTP/1.1 200 OK
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sample"
}
```

---

### 2. Users (RBAC Stub)

| Method | Path           | Notes                          |
| ------ | -------------- | ------------------------------ |
| GET    | `/api/users`   | Lists sample users & roles.    |

```bash
curl -i http://localhost:8888/api/users
```

---

### 3. Materials

| Method | Path                   | Notes                                         |
| ------ | ---------------------- | --------------------------------------------- |
| GET    | `/api/materials`       | List all materials                            |
| POST   | `/api/materials`       | Create new material (static echo)             |
| GET    | `/api/materials/:id`   | Get single material by `materialId`           |

```bash
# List
curl -i http://localhost:8888/api/materials

# Create
curl -i -X POST http://localhost:8888/api/materials \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "description":"Uranium oxide pellets, 10 kg",
    "metadata":{"hazardClass":"7","batch":"U456"},
    "initialHolder":"Nuclear_Fab"
  }'

# Get one
curl -i http://localhost:8888/api/materials/MatA123
```

---

### 4. Custody Transfers

| Method | Path                                            | Notes                                 |
| ------ | ----------------------------------------------- | ------------------------------------- |
| GET    | `/api/materials/:id/transfers`                  | List all transfers for one material   |
| POST   | `/api/materials/:id/transfers`                  | Append a new transfer entry           |

```bash
# List transfers
curl -i http://localhost:8888/api/materials/MatA123/transfers

# Add transfer
curl -i -X POST http://localhost:8888/api/materials/MatA123/transfers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "from": {
      "name":"Regional_Lab",
      "location":{"lat":33.45,"lng":-112.07}
    },
    "to": {
      "name":"Disposal_Facility",
      "location":{"lat":32.22,"lng":-110.97}
    },
    "timestamp":1713772800,
    "notes":"Shipped for disposal",
    "status":"In-Transit"
  }'
```

---

### 5. Status & Quarantine

| Method | Path                                   | Notes                                 |
| ------ | -------------------------------------- | ------------------------------------- |
| GET    | `/api/materials/:id/status`            | Returns `{ status: "In‑Transit"… }`   |
| POST   | `/api/materials/:id/quarantine`        | Manually set status to `"Quarantined"`|

```bash
# Check status
curl -i http://localhost:8888/api/materials/MatA123/status

# Trigger quarantine
curl -i -X POST http://localhost:8888/api/materials/MatA123/quarantine \
  -H "Authorization: Bearer <token>"
```

---

### 6. Signers (Multisig Registry)

| Method | Path           | Notes                            |
| ------ | -------------- | -------------------------------- |
| GET    | `/api/signers` | List authorized signer pubkeys   |
| POST   | `/api/signers` | Add a new signer entry           |

```bash
# List
curl -i http://localhost:8888/api/signers

# Add
curl -i -X POST http://localhost:8888/api/signers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"pubkey":"NewSignerPubKey","role":"safety_officer"}'
```

---

### 7. Reporting / Exports

| Method | Path                                             | Notes                          |
| ------ | ------------------------------------------------ | ------------------------------ |
| GET    | `/api/materials/:id/export/csv`                  | Returns `{ url: "/downloads/…"}`
| GET    | `/api/materials/:id/export/pdf`                  | Returns `{ url: "/downloads/…"}`
| GET    | `/api/materials/:id/map-data` (optional)         | Bundled `nodes` & `edges`      |

```bash
curl -i http://localhost:8888/api/materials/MatA123/export/csv
curl -i http://localhost:8888/api/materials/MatA123/export/pdf

# Optional combined map data
curl -i http://localhost:8888/api/materials/MatA123/map-data
```

---

## 🔧 Notes for Front‑End

- All endpoints return **static** data.  
- Use the sample JSON shapes to wire up your components (maps, tables, dashboards).  
- Authentication header is **required** on POST routes—just reuse the static token.  
- Once the Solana backend is ready, you’ll replace the stub logic in `app.py` with real RPC calls.

---

With this README, your front‑end developer has everything needed to start building the map overlay, data grids, and UI flows—independent of the Solana work in progress.