from rich.logging import RichHandler
import logging
import json

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")


with open("dbt/target/manifest.json") as f:
    manifest = json.load(f)

with open("dbt/target/run_results.json") as f:
    results = json.load(f)

for result in results["results"]:
    unique_id = result["unique_id"]
    metadata_fields = [
        "fqn",
        "name",
        "database",
        "schema",
        "file_key_name",
        "column_name",
    ]

    manifest_info = {i: None for i in metadata_fields}

    try:
        test_metadata = manifest["nodes"][unique_id]
    except:
        log.error(f"Manifest entry not found for unique_id: '{unique_id}'")
        continue

    for i in manifest_info.keys():
        try:
            manifest_info[i] = test_metadata[i]
        except:
            pass

    log.info(f"Metadata for unique_id '{unique_id}': {manifest_info}")

    # Now you have access to:
    # - test_metadata['attached_node'] (the model it tests)
    # - test_metadata['fqn'] (fully qualified name)
    # - test_metadata['file_key_name'] (test definition location)
    # - test_metadata['depends_on']['nodes'] (what it depends on)
