from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.email import EmailOperator
from datetime import datetime
import pandas as pd

default_args = {
    'start_date': datetime(2024, 9, 25),
    'catchup': False
}

@dag(schedule_interval='0 9 * * *', default_args=default_args, catchup=False, tags=['report'])
def final_report_dag():

    @task()
    def generate_report():
        # Mengambil data dari PostgreSQL
        postgres_hook = PostgresHook(postgres_conn_id="postgres_dibimbing").get_sqlalchemy_engine()

        with postgres_hook.connect() as conn:
            # Membaca data dari tabel stores_sales_forecasting_result
            df = pd.read_sql("SELECT * FROM dibimbing.stores_sales_forecasting_result", con=conn)

        # Simpan laporan ke file CSV
        report_file = "/tmp/stores_sales_forecasting_report.csv"
        df.to_csv(report_file, index=False)

        # Simpan hasil ke dalam format Parquet di staging area
        parquet_file = "/tmp/stores_sales_forecasting_result.parquet"
        df.to_parquet(parquet_file, index=False)

        # Mengganti visualisasi dengan deskripsi teks
        description = ""
        for index, row in df.iterrows():
            description += f"Metric: {row['Metric']}, Total: {row['Total']}\n"

        # Kembalikan path file report dan deskripsi teks sebagai tuple
        return report_file, parquet_file, description

    @task()
    def send_email(file_paths):
        report_file, parquet_file, description = file_paths  # Unpack di sini

        # Operator untuk mengirim email
        email_task = EmailOperator(
            task_id='send_email',
            to='faruq.abdurrahman2022@gmail.com',
            subject='Laporan Harian Hasil Agregasi Data',
            html_content=f"""<h3>Laporan Harian Hasil Agregasi Data</h3>
            <p>Berikut terlampir file CSV yang berisi hasil agregasi data terbaru.</p>
            <p>File Parquet juga disertakan untuk keperluan staging area.</p>
            <p>Deskripsi Total Sales, Quantity, Discount, dan Profit:</p>
            <pre>{description}</pre>
            """,
            files=[report_file, parquet_file],  # Melampirkan file laporan CSV dan Parquet
        )
        email_task.execute(context={})
        print(f"Laporan berhasil dikirim ke {email_task.to}")

    # Mendefinisikan dependensi antar tugas
    file_paths = generate_report()
    send_email(file_paths)

final_report_dag = final_report_dag()
