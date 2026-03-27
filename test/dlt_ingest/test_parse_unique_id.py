import pytest
from dlt_ingest.aux.parse_items import parse_unique_id

@pytest.fixture(params=[
    # 1: from user's example (column encoded in unique_id)
    ({
        "unique_id": "test.jaffle_shop.unique_stg_customers_customer_id.c7614daada",
        "compiled_code": ''
    }, ("jaffle_shop", "stg_customers", "customer_id")),

    # 2
    ({
        "unique_id": "test.jaffle_shop.unique_order_items_order_item_id.7d0a7e900a",
        "compiled_code": ''
    }, ("jaffle_shop", "order_items", "order_item_id")),

    # 3
    ({
        "unique_id": "test.jaffle_shop.unique_stg_locations_location_id.2e2fc58ecc",
        "compiled_code": ''
    }, ("jaffle_shop", "stg_locations", "location_id")),

    # 4: table-level test (no column in unique_id), compiled_code has FROM
    ({
        "unique_id": "test.jaffle_shop.not_a_column_test.e3b841c71a",
        "compiled_code": 'select count(*) from "postgres"."jaffle_shop"."orders"'
    }, ("jaffle_shop", "orders", None)),

    # 5: fallback to compiled_code parsing for column
    ({
        "unique_id": "",
        "compiled_code": '''
select
    customer_id as unique_field,
    count(*) as n_records
from "postgres"."jaffle_shop"."stg_customers"
where customer_id is not null
group by customer_id
having count(*) > 1
'''
    }, ("jaffle_shop", "stg_customers", "customer_id")),

    # 6: simple FROM "schema"."table" with no column alias
    ({
        "compiled_code": 'select 1 from "jaffle_shop"."products"'
    }, ("jaffle_shop", "products", None)),
])
def sample_case(request):
    return request.param


def test_parse_unique_id_samples(sample_case):
    inp, expected = sample_case
    assert parse_unique_id(inp) == expected