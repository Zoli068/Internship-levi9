import sys
from awsglue.utils import getResolvedOptions
from pyspark import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    DoubleType,
    StringType,
    TimestampType,
)

args = getResolvedOptions(
    sys.argv, ["JOB_NAME", "SILVER_SRC_SENSOR", "SILVER_SRC_OPEN", "GOLD_DEST"]
)

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

job = Job(glueContext)

job.init(args["JOB_NAME"], args)

spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

# ignore the difference between uppercase and lowercase letters when resolving column names and table names in your queries
spark.conf.set("spark.sql.caseSensitive", "false")

my_schema = StructType(
    [
        StructField("time_nano", LongType(), True),
        StructField("location_latitude", DoubleType(), True),
        StructField("location_longitude", DoubleType(), True),
        StructField("location_name", StringType(), True),
        StructField("name", StringType(), True),
        StructField("pms7003Measurement_pm10Atmo", DoubleType(), True),
        StructField("pms7003Measurement_pm25Atmo", DoubleType(), True),
        StructField("pms7003Measurement_pm100Atmo", DoubleType(), True),
        StructField("reading_time", TimestampType(), True),
    ]
)

# open_meteo schema
my_schema_open = StructType(
    [
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("carbon_monoxide", DoubleType(), True),
        StructField("nitrogen_dioxide", DoubleType(), True),
        StructField("sulphur_dioxide", DoubleType(), True),
        StructField("ozone", DoubleType(), True),
        StructField("timestamp", TimestampType(), True),
    ]
)

sensor_df = spark.read.schema(my_schema).parquet(args["SILVER_SRC_SENSOR"])
meteo_df = spark.read.schema(my_schema_open).parquet(args["SILVER_SRC_OPEN"])

# getting new column hour_timestamp that we will need for avg hours data
sensor_df = sensor_df.withColumn(
    "hour_timestamp", F.date_trunc("hour", F.col("reading_time"))
) 

# creating new column date by converting string reading_time to date
sensor_df = sensor_df.withColumn("date", F.to_date(F.col("reading_time")))
# Used as common integer join key
sensor_df = sensor_df.withColumn("hour_of_day", F.hour(F.col("reading_time")))

sensor_hourly_avg = sensor_df.groupBy(
    "location_name", "name", "date", "hour_timestamp", "hour_of_day"
).agg(
    F.round(F.avg("pms7003Measurement_pm10Atmo"), 2).alias("avg_pm1_0"),  # 1.0
    F.round(F.avg("pms7003Measurement_pm25Atmo"), 2).alias("avg_pm2_5"),  # 2.5
    F.round(F.avg("pms7003Measurement_pm100Atmo"), 2).alias("avg_pm10_0"),  # 100
)

# Extract date and hour keys from weather raw timestamp column
meteo_df = meteo_df.withColumn("date", F.to_date(F.col("timestamp"))).withColumn(
    "hour_of_day", F.hour(F.col("timestamp"))
)

# Meteo clean up
meteo_cleaned = meteo_df.select(
    F.col("date"),
    F.col("hour_of_day"),
    F.col("carbon_monoxide"),
    F.col("nitrogen_dioxide"),
    F.col("ozone"),
    F.col("sulphur_dioxide"),
).dropDuplicates(["date", "hour_of_day"])

# Joining sensor & open_meteo dataFrames on Hour
gold_hourly_metrics = sensor_hourly_avg.join(
    meteo_cleaned, on=["date", "hour_of_day"], how="left"
)
gold_hourly_metrics = gold_hourly_metrics.drop("hour_of_day")

# --- CONVERSIONS TO EPA STANDARD UNITS ---
# CO: ug/m3 -> mg/m3 (1:1 with ppm approximation)
gold_with_aqi = gold_hourly_metrics.withColumn(
    "co_mg", F.col("carbon_monoxide") / 1000.0
)

# O3: ug/m3 -> ppb
gold_with_aqi = gold_with_aqi.withColumn("ozone_ppb", F.col("ozone") * 0.5094)

# NO2: ug/m3 -> ppb (MW = 46.01) -> conversion factor = 24.45 / 46.01 = 0.5314
gold_with_aqi = gold_with_aqi.withColumn("no2_ppb", F.col("nitrogen_dioxide") * 0.5314)

# SO2: ug/m3 -> ppb (MW = 64.06) -> conversion factor = 24.45 / 64.06 = 0.3816
gold_with_aqi = gold_with_aqi.withColumn("so2_ppb", F.col("sulphur_dioxide") * 0.3816)

# --- SUB-INDICES CALCULATIONS ---

# A. PM2.5 Sub-Index
gold_with_aqi = gold_with_aqi.withColumn(
    "pm25_index",
    F.round(
        F.when(F.col("avg_pm2_5") <= 12.0, (50 / 12.0) * F.col("avg_pm2_5"))
        .when(
            F.col("avg_pm2_5") <= 35.4,
            ((100 - 51) / (35.4 - 12.1)) * (F.col("avg_pm2_5") - 12.1) + 51,
        )
        .when(
            F.col("avg_pm2_5") <= 55.4,
            ((150 - 101) / (55.4 - 35.5)) * (F.col("avg_pm2_5") - 35.5) + 101,
        )
        .otherwise(200)
    ),
)

# B. PM10 Sub-Index
gold_with_aqi = gold_with_aqi.withColumn(
    "pm10_index",
    F.round(
        F.when(F.col("avg_pm10_0") <= 54.0, (50 / 54.0) * F.col("avg_pm10_0"))
        .when(
            F.col("avg_pm10_0") <= 154.0,
            ((100 - 51) / (154.0 - 55.0)) * (F.col("avg_pm10_0") - 55.0) + 51,
        )
        .when(
            F.col("avg_pm10_0") <= 254.0,
            ((150 - 101) / (254.0 - 155.0)) * (F.col("avg_pm10_0") - 155.0) + 101,
        )
        .otherwise(200)
    ),
)

# C. Nitrogen Dioxide (NO2) Sub-Index (Using converted ppb)
gold_with_aqi = gold_with_aqi.withColumn(
    "no2_index",
    F.round(
        F.when(F.col("no2_ppb") <= 53.0, (50 / 53.0) * F.col("no2_ppb"))
        .when(
            F.col("no2_ppb") <= 100.0,
            ((100 - 51) / (100.0 - 54.0)) * (F.col("no2_ppb") - 54.0) + 51,
        )
        .otherwise(150)
    ),
)

# D. Ozone (O3) Sub-Index
gold_with_aqi = gold_with_aqi.withColumn(
    "ozone_index",
    F.round(
        F.when(F.col("ozone_ppb") <= 54.0, (50.0 / 54.0) * F.col("ozone_ppb"))
        .when(
            F.col("ozone_ppb") <= 70.0,
            ((100.0 - 51.0) / (70.0 - 55.0)) * (F.col("ozone_ppb") - 55.0) + 51.0,
        )
        .when(
            F.col("ozone_ppb") <= 85.0,
            ((150.0 - 101.0) / (85.0 - 71.0)) * (F.col("ozone_ppb") - 71.0) + 101.0,
        )
        .when(
            F.col("ozone_ppb") <= 105.0,
            ((200.0 - 151.0) / (105.0 - 86.0)) * (F.col("ozone_ppb") - 86.0) + 151.0,
        )
        .otherwise(201.0)
    ),
)

# E. Carbon Monoxide (CO) Sub-Index
gold_with_aqi = gold_with_aqi.withColumn(
    "co_index",
    F.round(
        F.when(F.col("co_mg") <= 4.4, (50 / 4.4) * F.col("co_mg"))
        .when(
            F.col("co_mg") <= 9.4,
            ((100 - 51) / (9.4 - 4.5)) * (F.col("co_mg") - 4.5) + 51,
        )
        .otherwise(150)
    ),
)

# F. Sulphur Dioxide (SO2) Sub-Index
gold_with_aqi = gold_with_aqi.withColumn(
    "so2_index",
    F.round(
        F.when(F.col("so2_ppb") <= 35.0, (50 / 35.0) * F.col("so2_ppb"))
        .when(
            F.col("so2_ppb") <= 75.0,
            ((100 - 51) / (75.0 - 36.0)) * (F.col("so2_ppb") - 36.0) + 51,
        )
        .when(
            F.col("so2_ppb") <= 185.0,
            ((150 - 101) / (185.0 - 76.0)) * (F.col("so2_ppb") - 76.0) + 101,
        )
        .otherwise(200)
    ),
)

# Clean up temporary conversion columns
gold_with_aqi = gold_with_aqi.drop("co_mg", "ozone_ppb", "no2_ppb", "so2_ppb")

# --- FINAL METRICS & DOMINANT POLLUTANT ---
gold_with_aqi = gold_with_aqi.withColumn(
    "final_aqi",
    F.greatest(
        "pm25_index", "pm10_index", "no2_index", "ozone_index", "co_index", "so2_index"
    ),
)

gold_with_aqi = gold_with_aqi.withColumn(
    "aqi_health_category",
    F.when(F.col("final_aqi") <= 50, "Good")
    .when(F.col("final_aqi") <= 100, "Moderate")
    .when(F.col("final_aqi") <= 150, "Unhealthy for Sensitive Groups")
    .otherwise("Unhealthy"),
)

gold_with_aqi = gold_with_aqi.withColumn(
    "dominant_pollutant",
    F.when(F.col("final_aqi") == F.col("pm25_index"), "PM2.5")
    .when(F.col("final_aqi") == F.col("pm10_index"), "PM10")
    .when(F.col("final_aqi") == F.col("no2_index"), "NO2")
    .when(F.col("final_aqi") == F.col("ozone_index"), "O3")
    .when(F.col("final_aqi") == F.col("so2_index"), "SO2")
    .otherwise("CO"),
)

gold_production_final = gold_with_aqi.select(
    "location_name",
    "name",
    "hour_timestamp",
    "avg_pm1_0",
    "avg_pm2_5",
    "avg_pm10_0",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "ozone",
    "sulphur_dioxide",
    "pm25_index",
    "pm10_index",
    "no2_index",
    "so2_index",
    "ozone_index",
    "co_index",
    "final_aqi",
    "aqi_health_category",
    "dominant_pollutant",
    "date",
)

gold_production_final.write.mode("overwrite").partitionBy("date").parquet(
    args["GOLD_DEST"]
)
job.commit()
