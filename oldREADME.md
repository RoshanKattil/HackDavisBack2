Below is a **ready‑to‑paste** section you can drop straight into your `README.md`—it walks a new developer from clone to running API + Hardhat + Mongo in ~10 minutes, plus an optional Docker one‑liner.

```markdown
---

## 🚦 Quick‑Start for New Developers

> Time to first successful `curl` ≈ **10 min**

### 0  Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Git**          | any modern | clone repo |
| **Node.js**      | 16 – 18 LTS | Hardhat warns on v20+ |
| **npm** / **yarn** | bundled with Node | package manager |
| **Python**       | 3.8 + | Flask back‑end |
| **pip**          |   | install requirements |
| **MongoDB**      | local Community Server **or** Atlas URI | database |
| *(optional)* **Docker** | for one‑liner setup | |
| *(optional)* **Poetry / venv** | isolate Python deps | |

---

### 1  Clone

```bash
git clone https://github.com/RoshanKattil/HackDavisBack2.git
cd HackDavisBack2
```

---

### 2  Install JS workspace (Hardhat)

```bash
cd contracts
npm install          # hardhat, ethers, etc.
```

---

### 3  Install Python back‑end

```bash
cd ../backend
python3 -m venv venv      # (optional)
source venv/bin/activate
pip install -r requirements.txt
```

---

### 4  Create `.env`

```bash
# in backend/
cat > .env <<'EOF'
MONGO_URI=mongodb://localhost:27017/custody
HTTP_PROVIDER=http://127.0.0.1:8545
CONTRACT_ADDRESS=
WASTE_CONTRACT=
EOF
```

You’ll fill the two addresses after deployment (step 7).

---

### 5  Run local Hardhat node

```bash
cd ../contracts
npm run node              # JSON‑RPC at 127.0.0.1:8545
```

Keep this terminal open (it prints 20 funded accounts).

---

### 6  Deploy contracts

```bash
cd contracts
npm run deploy                              # ChainCustody
npx hardhat run scripts/deploy_waste.js --network localhost
```

Copy both contract addresses.

---

### 7  Paste addresses into `.env`

```env
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
WASTE_CONTRACT=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
```

---

### 8  Initialise Mongo

```bash
cd backend
python init_db.py          # drops/creates DB & indexes
```

---

### 9  Run Flask back‑end

```bash
export HTTP_PROVIDER=http://127.0.0.1:8545   # if not in .env
python app.py                # http://127.0.0.1:8888
```

---

### 10  Smoke test

```bash
# create a material
curl -X POST http://127.0.0.1:8888/api/materials \
  -H "Content-Type: application/json" \
  -d '{"materialId":"M100","description":"Hello"}'

# transfer it
curl -X POST http://127.0.0.1:8888/api/materials/M100/transfer \
  -H "Content-Type: application/json" \
  -d '{"newHolder":"0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
       "from":{"lat":34.05,"lng":-118.25},
       "to":  {"lat":33.45,"lng":-112.07}}'
```

Both should return **201/200 OK**.

---

### 🚀 Docker one‑liner (optional)

```bash
docker compose up --build
```

Spins up `mongo`, `hardhat-node`, and `backend` containers automatically.  
See `docker-compose.yml` for ports and volumes.

---

### Common Gotchas

* **“Only holder” revert** → transfer must be signed by current on‑chain holder (default account 0).
* **Mismatched ABI** → `initializeMaterial` now takes **two** strings: id & description.
* Port conflicts: change `HTTP_PROVIDER` or use Docker to isolate.

Happy hacking! 🚀
```

Add that block at the end (or in its own **“Quick‑Start”** section) and your front‑end teammate will have everything they need.
