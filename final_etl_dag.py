from airflow.decorators import dag, task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime

default_args = {
    'start_date': datetime(2024, 9, 25),
    'catchup': False
}

@dag(schedule_interval=None, default_args=default_args, catchup=False, tags=['etl'])
def final_etl_dag():

    @task
    def extract_from_mysql():
        import pandas as pd
        from datetime import datetime
        from airflow.providers.mysql.hooks.mysql import MySqlHook

        mysql_hook = MySqlHook("mysql_dibimbing").get_sqlalchemy_engine()

        with mysql_hook.connect() as conn:
            df = pd.read_sql(
                sql = "SELECT * FROM dibimbing.stores_sales_forecasting",
                con = conn,
            )
            df['extracted_at'] = datetime.utcnow()

        df.to_parquet("data/stores_sales_forecasting.parquet", index=False)
        print("data berhasil diextract")

    @task
    def load_to_postgres():
        import pandas as pd
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        postgres_hook = PostgresHook("postgres_dibimbing").get_sqlalchemy_engine()
        df            = pd.read_parquet("data/stores_sales_forecasting.parquet")

        with postgres_hook.connect() as conn:
            df.to_sql(
                name      = "stores_sales_forecasting",
                con       = conn,
                index     = False,
                schema    = "dibimbing",
                if_exists = "replace",
            )

        print("data berhasil diload")

    @task
    def trigger_aggregation(**kwargs):
        # Ambil task_instance dari kwargs
        task_instance = kwargs.get('task_instance')
        if not task_instance:
            raise KeyError("task_instance tidak ditemukan dalam kwargs")

        # Trigger DAG final_aggregation_dag
        trigger = TriggerDagRunOperator(
            task_id='trigger_aggregation_dag',
            trigger_dag_id='final_aggregation_dag',
            wait_for_completion=True,
            poke_interval=60 
        )
        trigger.execute(context=kwargs)

    extract_task = extract_from_mysql()
    load_task = load_to_postgres()

    extract_task >> load_task >> trigger_aggregation()

final_etl_dag = final_etl_dag()
