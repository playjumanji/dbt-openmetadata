import pytest
from dlt_ingest.aux.parse_items import parse_from_compiled


@pytest.fixture(params=[
    # 1: compiled code uses adapter.schema.table and 'as unique_field'
    ({
        "unique_id": "test.jaffle_shop.unique_stg_customers_customer_id.c7614daada",
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

    # 2: simple schema.table and no alias column (table-level expectation)
    ({
        "unique_id": "test.jaffle_shop.some_table_level_test.e3b841c71a",
        "compiled_code": 'select count(*) from "jaffle_shop"."orders"'
    }, ("jaffle_shop", "orders", None)),

    # 3: quoted identifiers, adapter.schema.table with whitespace
    ({
        "compiled_code": 'select 1 from  "postgres"  .  "jaffle_shop"  .  "products"  '
    }, ("jaffle_shop", "products", None)),

    # 4: FROM clause is a subquery; main table is earlier FROM (in WITH)
    ({
        "compiled_code": '''
with x as (
  select * from "jaffle_shop"."base_table"
)
select a.col as unique_field from (select * from other) t
'''
    }, ("jaffle_shop", "base_table", "col")),

    # 5: dotted column reference with alias
    ({
        "compiled_code": '''
select src.customer_id as unique_field
from schema_name.table_name src
'''
    }, ("schema_name", "table_name", "customer_id")),
])
def compiled_sample(request):
    return request.param


def test_parse_from_compiled_samples(compiled_sample):
    inp, expected = compiled_sample
    out = parse_from_compiled(inp.get("compiled_code", ""))
    assert out == expected