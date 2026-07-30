import sys
from awsglue.utils import getResolvedOptions
from pyspark import SparkContext

from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.types import LongType, DoubleType, StructField, StringType, StructType
from pyspark.sql.functions import col, date_format, lit

args = getResolvedOptions(sys.argv, ["JOB_NAME", "BRONZE_SRC", "SILVER_DEST"])

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

job = Job(glueContext)

job.init(args["JOB_NAME"], args)


my_schema = StructType(
    [
        StructField("time_nano", LongType(), True),
        # GPS
        StructField("location_latitude", DoubleType(), True),
        StructField("location_longitude", DoubleType(), True),
        # Metadata
        StructField("location_name", StringType(), True),
        StructField("name", StringType(), True),
        # Air Quality
        StructField("pms7003Measurement_pm10Atmo", DoubleType(), True),
        StructField("pms7003Measurement_pm25Atmo", DoubleType(), True),
        StructField("pms7003Measurement_pm100Atmo", DoubleType(), True),
        # Weather
        StructField("bmp280Measurement_temperature", DoubleType(), True),
        StructField("bmp280Measurement_pressure", DoubleType(), True),
        StructField("dht11Measurement_humidity", DoubleType(), True),
    ]
)


# dynamic frame for reading only new values from bucket
dynamic_frame = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [args["BRONZE_SRC"]],
        "recurse": True,
        "groupFiles": "inPartition",  # Merges small input files inside the same prefix
        "groupSize": "10485760",  # Targets grouping files into 10MB chunks
    },
    format="csv",
    format_options={"withHeader": True},
    transformation_ctx="bronze_incremental_sensor_ctx",
)

# moving context to Pyspark DataFrame Api for fast manipulation
df = dynamic_frame.toDF()

if len(df.columns) == 0:
    print("### GLUE BOOKMARK INFO: Nema novih podataka za obradu u ovom trenutku. ###")
    job.commit()
else:
    select_exprs = []
    for field in my_schema.fields:
        if field.name in df.columns:
            select_exprs.append(col(field.name).cast(field.dataType))
        else:
            select_exprs.append(lit(None).cast(field.dataType).alias(field.name))

    df = df.select(*select_exprs)

    # df = df.select(*[col(field.name).cast(field.dataType) for field in my_schema.fields])

    # generating column for datetime then  formating the date directly from the dataset data so we can partition
    df = df.withColumn(
        "reading_time", (col("time_nano") / 1000000000).cast("timestamp")
    )
    df = df.withColumn(
        "date", date_format(col("reading_time"), "yyyy-MM-dd")
    )

    good_data = df.dropna(
        subset=[
            "time_nano",
            "location_latitude",
            "location_longitude",
            "location_name",
            "name",
        ]
    )

    # droping irelevant columns
    processed_silver_df = good_data.drop(
        "bmp280Measurement_temperature",
        "bmp280Measurement_pressure",
        "dht11Measurement_humidity",
    )

    processed_silver_df.write.mode("append").partitionBy("date").parquet(
        args["SILVER_DEST"]
    )

    # confir state updates to confirm file tracks inside bookmark registeries
    job.commit()
