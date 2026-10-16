from delta.tables import DeltaTable


def merge_into_delta(spark, df, table_name: str, business_key: str) -> dict:
    """Load or merge a DataFrame into a Delta table, keyed on business_key.

    Creates the table on first load; merges (update existing, insert new)
    on every run after that.
    """
    if business_key not in df.columns:
        raise ValueError(
            f"Business key '{business_key}' not found in '{table_name}'. "
            f"Available columns: {df.columns}"
        )

    duplicate_source_keys = (
        df.groupBy(business_key).count().filter("count > 1").count()
    )
    if duplicate_source_keys > 0:
        raise ValueError(
            f"Source data for '{table_name}' contains {duplicate_source_keys} "
            f"duplicate '{business_key}' values."
        )

    if not spark.catalog.tableExists(table_name):
        (
            df.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(table_name)
        )
        return {
            "table": table_name,
            "operation": "INITIAL_LOAD",
            "record_count": spark.table(table_name).count(),
        }

    delta_table = DeltaTable.forName(spark, table_name)
    merge_condition = f"target.{business_key} = source.{business_key}"

    (
        delta_table.alias("target")
        .merge(df.alias("source"), merge_condition)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )

    return {
        "table": table_name,
        "operation": "MERGE",
        "record_count": spark.table(table_name).count(),
    }