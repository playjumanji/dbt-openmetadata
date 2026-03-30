import dlt
import json
import logging
import argparse
from rich.logging import RichHandler
from pathlib import Path
from typing import Any, Iterator
from dbt_artifacts_parser.parser import parse_run_results_v6


@dlt.resource(name="dbt_test_results", write_disposition="replace")
def load_dbt_test_results(dbt_project_name: str = None) -> Iterator[dict[str, Any]]:
    """
    Load dbt test results from run_results.json and yield flattened records.
    dlt will automatically denormalize nested structures.
    """
    # Convert to absolute path to avoid issues with working directory
    target_path = Path(__file__).parent.parent / dbt_project_name / "target"
    manifest_file = target_path / "manifest.json"
    run_results_file = target_path / "run_results.json"

    if not manifest_file.exists():
        raise FileNotFoundError(f"'{manifest_file}' not found at {target_path}")

    if not run_results_file.exists():
        raise FileNotFoundError(f"'{run_results_file}' not found at {target_path}")

    with open(run_results_file, "r") as f:
        data_tests = json.load(f)

    with open(manifest_file, "r") as f:
        manifest = json.load(f)

    run_results = parse_run_results_v6(run_results=data_tests)

    for result in run_results.results:
        # Basic result infor and metadata
        record = result.model_dump()
        record.pop("timing")
        record.pop("adapter_response")
        record.update(run_results.metadata.model_dump())

        unique_id = result.unique_id
        metadata_fields = [
            "fqn",
            "name",
            "database",
            "schema",
            "file_key_name",
            "column_name",
        ]
        manifest_info = {i: None for i in metadata_fields}
        test_metadata = None

        # Has no manifest info about this test run. All fields will be empty/None
        try:
            test_metadata = manifest["nodes"][unique_id]
        except:
            log.error(f"Manifest entry not found for unique_id: '{unique_id}'")
            record.update(manifest_info)
            yield record

        # Has manifest info about this test run
        if test_metadata is not None:
            for i in manifest_info.keys():
                manifest_info[i] = test_metadata[i]
            manifest_info["fqn"] = ".".join(manifest_info["fqn"])
            record.update(manifest_info)

        log.info(f"Metadata for unique_id '{unique_id}': {manifest_info}")
        yield record


def create_pipeline() -> dlt.Pipeline:
    """
    Create and configure the dlt pipeline for dbt test results.
    """
    pipeline = dlt.pipeline(
        pipeline_name="dbt_test_results",
        destination="duckdb",
        dataset_name="dq",
        # dev_mode=True,
    )
    return pipeline


def run_pipeline(dbt_project_name: str = None) -> None:
    """
    Execute the pipeline to load dbt test results into destination DB.
    """
    pipeline = create_pipeline()

    # Load the data
    load_info = pipeline.run(
        load_dbt_test_results(dbt_project_name),
        write_disposition="append",
    )

    pipeline.drop()

    # Print summary
    print(f"Pipeline completed: {load_info}")
    print(f"Load ID: {load_info.loads_ids}")


if __name__ == "__main__":

    FORMAT = "%(message)s"
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )
    log = logging.getLogger("rich")

    parser = argparse.ArgumentParser(
        description="Selects a dbt project to parse data tests results"
    )

    parser.add_argument(
        "--dbt-project-name",
        type=str,
        help="name of dbt project to parse",
        default="dbt",
    )

    args = parser.parse_args()

    run_pipeline(args.dbt_project_name)
