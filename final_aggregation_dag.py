from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import pandas as pd
import numpy as np

default_args = {
    'start_date': datetime(2024, 9, 25),
    'catchup': False
}

@dag(schedule_interval=None, default_args=default_args, catchup=False, tags=['analysis'])
def final_aggregation_dag():

    @task()
    def run_analysis():
        # Load data from PostgreSQL
        postgres_hook = PostgresHook("postgres_dibimbing").get_sqlalchemy_engine()

        with postgres_hook.connect() as conn:
            # Membaca data dari tabel stores_sales_forecasting di schema dibimbing
            df = pd.read_sql("SELECT * FROM dibimbing.stores_sales_forecasting", con=conn)

        # Agregasi total untuk kolom Sales, Quantity, Discount, dan Profit
        aggregated_data = {
            'Metric': ['Total Sales', 'Total Quantity', 'Total Discount', 'Total Profit'],
            'Total': [
                df['Sales'].sum(),
                df['Quantity'].sum(),
                df['Discount'].sum(),
                df['Profit'].sum()
            ]
        }
        aggregated_df = pd.DataFrame(aggregated_data)

        # Simpan hasil analisis ke tabel baru di PostgreSQL
        with postgres_hook.connect() as conn:
            aggregated_df.to_sql(
                name="stores_sales_forecasting_result",
                con=conn,
                index=False,
                schema="dibimbing",
                if_exists="replace",
            )

        # Simpan hasil agregasi ke dalam format Parquet di staging area
        parquet_file = "/tmp/stores_sales_forecasting_result.parquet"
        aggregated_df.to_parquet(parquet_file, index=False)

        print("Analisis selesai dan disimpan ke tabel baru: stores_sales_forecasting_result")
        print(f"Hasil agregasi juga disimpan sebagai file Parquet di: {parquet_file}")

    # Define task
    run_analysis()

final_aggregation_dag = final_aggregation_dag()
