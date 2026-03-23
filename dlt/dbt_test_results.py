from dotenv import load_dotenv
import dlt
import json
from pathlib import Path
from typing import Any, Iterator

# Load .env file
load_dotenv()

@dlt.resource(name="dbt_test_results", write_disposition="replace")
def load_dbt_test_results(run_results_path: str = "../../dbt/target/run_results.json") -> Iterator[dict[str, Any]]:
    """
    Load dbt test results from run_results.json and yield flattened records.
    dlt will automatically denormalize nested structures.
    """
    # Convert to absolute path to avoid issues with working directory
    file_path = Path(__file__).parent.parent / "dbt" / "target" / "run_results.json"
    
    if not file_path.exists():
        raise FileNotFoundError(f"run_results.json not found at {file_path}")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    # Extract metadata
    metadata = {
        "generated_at": data.get("metadata", {}).get("generated_at"),
        "invocation_id": data.get("metadata", {}).get("elapsed_time"),
        "invocation_started_at": data.get("metadata", {}).get("invocation_started_at"),
        "dbt_version": data.get("metadata", {}).get("dbt_version"),
        "dbt_schema_version": data.get("metadata", {}).get("schema_version"),
        "elapsed_time":  data.get("elapsed_time"),

    }
    
    # Process each test result
    for result in data.get("results", []):
        record = {
            # Test metadata
            "unique_id": result.get("unique_id"),
            "status": result.get("status"),
            "execution_time": result.get("execution_time"),
            "thread_id": result.get("thread_id"),
            "compiled": result.get("compiled"),
            "compiled_code": result.get("compiled_code"),
            "message": result.get("message"),
            "failures": result.get("failures"),
            "relation_name": result.get("relation_name"),
            "batch_results": result.get("batch_results"),

            # Pipeline metadata
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
        dataset_name="dq",
        
    )
    
    return pipeline


def run_pipeline(run_results_path: str = "../../dbt/target/run_results.json") -> None:
    """
    Execute the pipeline to load dbt test results into DuckDB.
    """
    pipeline = create_pipeline()
    
    # Load the data
    load_info = pipeline.run(
        load_dbt_test_results(run_results_path),
        write_disposition="append",
    )
    
    # Print summary
    print(f"Pipeline completed: {load_info}")
    print(f"Load ID: {load_info.loads_ids}")


if __name__ == "__main__":
    run_pipeline()
