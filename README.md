Below is a **practical, end-to-end setup** to run:

* **dbt (jaffle_shop) on DuckDB**
* **OpenMetadata (Docker)**
* **dbt → OpenMetadata ingestion (lineage + metadata)**

This is the **simplest working local stack** with minimal overhead.

---

# 🧱 Architecture (what you’ll build)

```text
dbt (DuckDB + jaffle_shop)
        ↓ (artifacts: manifest.json, etc.)
OpenMetadata Ingestion
        ↓
OpenMetadata (Docker UI + API)
```

---

# 1) Start OpenMetadata locally (Docker)

Download docker compose to `infra_setup` folder:
```bash 
wget https://github.com/open-metadata/OpenMetadata/releases/download/1.12.0-release/docker-compose-postgres.yml
```
Rename it to `docker-compose.yml`

Run:
```
docker compose up -d
```

## ✅ Run OpenMetadata


👉 Open UI:

* [http://localhost:8585](http://localhost:8585)

Default login:

```text
Username: admin@open-metadata.org
Password: admin
```

---

## ⏳ Wait for services

Give it ~1–2 minutes, then verify:

```bash
curl http://localhost:8585/api/v1/system/version
```

---

# 2) Setup dbt with DuckDB + jaffle_shop locally

Well, to start you must have [UV](https://docs.astral.sh/uv/getting-started/installation/) pre-installed. 

To install all dependencies, just do:
```bash
uv sync
```

Now got o dbt folder:
```bash
cd dbt
```

## ✅ Install dependencies

```bash
dbt deps
```

## ✅ Check everything is in place

```bash
dbt debug
```

## ✅ Seed files from jaffle shop

```bash
dbt seed --full-refresh --vars '{"load_source_data": true}'
```

## ✅ Run and test jaffle_shop models

```bash
dbt run
dbt test
```

## ✅ Generate docs:
```bash
dbt docs generate
```

## 📁 dbt generated target atifacts:

```text
target/
  manifest.json
  catalog.json
  run_results.json
```

These are what OpenMetadata will ingest.

---

# 3) Create OpenMetadata service (UI step)

Go to:

* [http://localhost:8585](http://localhost:8585)

### ➜ Create Database Service

1. Settings → Services → Databases → Add
2. Choose: **postgres**
3. Name: `local_postgres_dbt`
4. Connection:
    host: `postgresql:5432`

---

# 4) Edit openmetadata-ingestion.yml file

## 🔑 Get OpenMetadata JWT token

Run:

```bash
curl -X POST "http://localhost:8585/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@open-metadata.org","password":"YWRtaW4="}'
```
Copy:

```json
"accessToken": "eyJraWQ..."
```

Paste into `dbt_project,yml` in session:

```yaml
vars:
nmetadata_jwt_token: <PASTE TOKEN HERE>
  openmetadata_host_port: 'http://localhost:8585/api'
  openmetadata_service_name: 'local_postgres_dbt'
```
---

# 5) Run ingestion
In dbt folder:

```bash
cd dbt
metadata ingest-dbt
```

# 8) What you’ll see in OpenMetadata UI

## 📊 Lineage graph

![Image](https://opengraph.githubassets.com/94fbed90ac89876fc28e120012d8109d5637a882ca5d29ecd7e365015e1e007a/dbt-labs/jaffle_shop_duckdb)

![Image](https://miro.medium.com/v2/resize%3Afit%3A1400/1%2AThkpFqh3EewOaKmTePBpNA.gif)

![Image](https://mintcdn.com/openmetadata/oaTZzo76cVYQrwnS/public/images/features/ingestion/lineage/lineage-ingestion.gif?s=fb25b29fd090641a67f034815bef6dad)

![Image](https://website-assets.atlan.com/img/open-metadata-lineage.webp)

* `raw_customers` → `stg_customers` → `customers`
* Full DAG from dbt

---

## 🔎 Dataset exploration

Click a table:

* Schema
* Columns
* Tags
* Tests (from dbt)

---

## 🔐 Add classification

Example:

* Go to column `email`
* Add tag: `PII`

---

## 🧬 Column lineage

You’ll see:

```text
raw_customers.email → customers.email
```

---

# 9) Common pitfalls (you will likely hit one)

### ❌ DuckDB path not found

✔ Fix: use absolute path

---

### ❌ No lineage appears

✔ Fix:

* Ensure both:

  * dbt ingestion ✅
  * database ingestion ✅

---

### ❌ Empty schemas

✔ Fix:

```bash
dbt docs generate
```

---

### ❌ Token expired

✔ Re-run login API

---

# 10) Minimal version (if you want fastest setup)

You can skip DB ingestion and only run:

```text
dbt → manifest.json → OpenMetadata
```

But:

❌ weaker lineage
❌ missing schemas

---

# 🎯 Final result

You now have:

* ✅ dbt running locally (DuckDB)
* ✅ OpenMetadata UI
* ✅ Lineage graph
* ✅ Column-level lineage
* ✅ Metadata catalog
* ✅ Ready for classification/governance

---

# 🚀 Next step (if you want)

I can help you:

* Turn this into a **docker-compose (1 command setup)**
* Add **Airflow orchestration**
* Add **data quality + alerts**
* Or compare this vs **DataHub vs OpenLineage stack**

Just tell me 👍
