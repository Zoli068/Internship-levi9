import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, to_timestamp, date_format

args = getResolvedOptions(sys.argv, ["JOB_NAME", "BRONZE_PATH", "SILVER_PATH"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

job.init(args["JOB_NAME"], args)

# KONFIGURACIJA PUTANJA
BRONZE_S3_PATH = args["BRONZE_PATH"]
SILVER_S3_PATH = args["SILVER_PATH"]

# df_bronze = spark.read \
#     .option("recursiveFileLookup", "true") \
#     .option("multiLine", "true") \
#     .json(BRONZE_S3_PATH)

dynamic_frame = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [BRONZE_S3_PATH], "recurse": True},
    format="json",
    transformation_ctx="openmeteo_incremental_ctx",
)

df_bronze = dynamic_frame.toDF()

if len(df_bronze.columns) == 0:
    print("### GLUE BOOKMARK INFO: Nema novih OpenMeteo podataka za obradu. ###")
    job.commit()
else:
    df_silver = (
        df_bronze.select(
            col("latitude").cast("double"),
            col("longitude").cast("double"),
            col("carbon_monoxide").cast("double"),
            col("nitrogen_dioxide").cast("double"),
            col("sulphur_dioxide").cast("double"),
            col("ozone").cast("double"),
            to_timestamp(col("time"), "yyyy-MM-dd'T'HH:mm").alias("timestamp"),
        )
        .withColumn("date", date_format(col("timestamp"), "yyyy-MM-dd"))
        .distinct()
    ) 

    df_silver.repartition(1, "date").write.mode("append").partitionBy("date").format(
        "parquet"
    ).save(SILVER_S3_PATH)

    job.commit()
