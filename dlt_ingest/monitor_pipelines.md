Here are the **dlt CLI commands** for testing, monitoring, and gathering statistics about your pipeline:

## Testing & Validation

This shows detailed execution logs and any errors.

### Validate the pipeline configuration

```bash
dlt pipeline dbt_test_results info
```

Shows pipeline metadata, destination details, and dataset schema.

### Test the data loading without committing

```bash
dlt pipeline dbt_test_results run dbt_test_results_pipeline.py --dry-run
```

(Note: `--dry-run` may not be available in all dlt versions; alternatively, use `write_disposition="skip"` in your code temporarily)

---

## Monitoring & Statistics

### View pipeline load history

```bash
dlt pipeline dbt_test_results load-package
```

Shows all load packages and their status.

### Get detailed load statistics

```bash
dlt pipeline dbt_test_results info --load-id <LOAD_ID>
```

Replace `<LOAD_ID>` with the ID from your pipeline run output.

### List all loads for the pipeline

```bash
dlt pipeline dbt_test_results list-loads
```

Shows all historical loads with timestamps and row counts.

### View schema information

```bash
dlt pipeline dbt_test_results show-schema
```

Displays the inferred schema for all tables in the dataset.

### Check destination connection

```bash
dlt pipeline dbt_test_results verify-destination
```

Validates that the DuckDB destination is accessible and working.

---

## Programmatic Monitoring

For more control, modify your pipeline to capture and display statistics:

```python
from dotenv import load_dotenv
import dlt
import json
from pathlib import Path
from typing import Any, Iterator
from datetime import datetime

load_dotenv()

@dlt.resource(name="dbt_test_results", write_disposition="replace")
def load_dbt_test_results(run_results_path: str = "../../dbt/target/run_results.json") -> Iterator[dict[str, Any]]:
    """
    Load dbt test results from run_results.json and yield flattened records.
    """
    file_path = Path(__file__).parent.parent.parent / "dbt" / "target" / "run_results.json"
    
    if not file_path.exists():
        raise FileNotFoundError(f"run_results.json not found at {file_path}")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    metadata = {
        "generated_at": data.get("generated_at"),
        "elapsed_time": data.get("elapsed_time"),
        "dbt_version": data.get("metadata", {}).get("dbt_version"),
        "dbt_schema_version": data.get("metadata", {}).get("schema_version"),
    }
    
    for result in data.get("results", []):
        if result.get("resource_type") != "test":
            continue
        
        record = {
            "unique_id": result.get("unique_id"),
            "name": result.get("name"),
            "status": result.get("status"),
            "resource_type": result.get("resource_type"),
            "execution_time": result.get("execution_time"),
            "thread_id": result.get("thread_id"),
            "message": result.get("message"),
            "test_kwargs": result.get("kwargs"),
            "depends_on": result.get("depends_on"),
            "tags": result.get("tags"),
            "meta": result.get("meta"),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at"),
            "adapter_response": result.get("adapter_response"),
            **metadata,
        }
        
        yield record


def create_pipeline() -> dlt.Pipeline:
    """
    Create and configure the dlt pipeline for dbt test results.
    """
    pipeline = dlt.pipeline(
        pipeline_name="dbt_test_results",
        destination="duckdb",
        dataset_name="main",
        full_refresh=False,
    )
    
    return pipeline


def print_pipeline_statistics(load_info) -> None:
    """
    Print detailed statistics about the pipeline execution.
    """
    print("\n" + "="*60)
    print("PIPELINE EXECUTION STATISTICS")
    print("="*60)
    
    print(f"\n✓ Load ID: {load_info.loads_ids[0] if load_info.loads_ids else 'N/A'}")
    print(f"✓ Execution Time: {datetime.now().isoformat()}")
    
    # Table statistics
    if load_info.loads_ids:
        for load_id in load_info.loads_ids:
            print(f"\n📊 Load Package: {load_id}")
            
            for package in load_info.load_packages:
                if package.load_id == load_id:
                    for table_name, table_info in package.tables_loaded.items():
                        print(f"\n  Table: {table_name}")
                        print(f"    - Rows: {table_info.get('rows_loaded', 0)}")
                        print(f"    - Bytes: {table_info.get('bytes_loaded', 0)}")
    
    print("\n" + "="*60 + "\n")


def run_pipeline(run_results_path: str = "../../dbt/target/run_results.json") -> None:
    """
    Execute the pipeline to load dbt test results into DuckDB.
    """
    pipeline = create_pipeline()
    
    print(f"Starting pipeline execution at {datetime.now().isoformat()}")
    print(f"Reading from: {run_results_path}\n")
    
    try:
        load_info = pipeline.run(
            load_dbt_test_results(run_results_path),
            write_disposition="replace",
        )
        
        print_pipeline_statistics(load_info)
        
        # Query and display summary statistics
        import duckdb
        conn = duckdb.connect(".dlt/dbt_test_results.duckdb")
        
        # Test results summary
        summary = conn.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                ROUND(AVG(execution_time), 2) as avg_execution_time
            FROM main.dbt_test_results
            GROUP BY status
        """).fetchall()
        
        print("TEST RESULTS SUMMARY")
        print("="*60)
        for row in summary:
            status, count, avg_time = row
            print(f"{status.upper():12} | Count: {count:4} | Avg Time: {avg_time}s")
        print("="*60 + "\n")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")
        raise


if __name__ == "__main__":
    run_pipeline()
```

---

## Common dlt CLI Commands Summary

| Command | Purpose |
|---------|---------|
| `dlt pipeline dbt_test_results info` | View pipeline configuration and schema |
| `dlt pipeline dbt_test_results list-loads` | List all historical loads |
| `dlt pipeline dbt_test_results show-schema` | Display inferred table schema |
| `dlt pipeline dbt_test_results verify-destination` | Test destination connectivity |
| `dlt pipeline dbt_test_results run <script>` | Execute pipeline with logging |
| `dlt pipeline dbt_test_results run <script> --verbose` | Execute with detailed logs |

---

## Querying Statistics Directly

You can also query DuckDB directly for insights:

```bash
duckdb .dlt/dbt_test_results.duckdb

# Inside DuckDB shell:
SELECT status, COUNT(*) FROM main.dbt_test_results GROUP BY status;
SELECT name, MAX(execution_time) FROM main.dbt_test_results GROUP BY name ORDER BY 2 DESC;
SELECT generated_at, COUNT(*) FROM main.dbt_test_results GROUP BY generated_at;
```

This gives you **comprehensive monitoring and statistics** for your dlt pipeline!