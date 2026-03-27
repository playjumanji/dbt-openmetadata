from dotenv import load_dotenv
import dlt
import json
from pathlib import Path
from typing import Any, Iterator
from dbt_artifacts_parser.parser import parse_run_results_v6

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
    
    run_results = parse_run_results_v6(run_results=data)

    # Process each test result
    for result in run_results.results:
        record = result.model_dump()
        record.pop("timing")
        record.pop("adapter_response")
        record.update(run_results.metadata.model_dump())
        
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
