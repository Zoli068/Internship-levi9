# Query for calculating AVG aqi in the last 24h
AVG_AQI_QUERRY = """
SELECT location_name, avg_final_aqi, dominant_pollutant, start_date, end_date, avg_pm25_index,
        avg_pm10_index, avg_no2_index, avg_so2_index, avg_ozone_index, avg_co_index
FROM (
    SELECT 
        location_name, dominant_pollutant, avg_final_aqi, start_date, end_date, avg_pm25_index,
        avg_pm10_index, avg_no2_index, avg_so2_index, avg_ozone_index, avg_co_index,
        ROW_NUMBER() OVER(
            PARTITION BY location_name 
            ORDER BY occurrence_count DESC
        ) as rank_position
    FROM (
        SELECT 
            location_name, dominant_pollutant,
            COUNT(*) as occurrence_count,
            ROUND(AVG(final_aqi) OVER(PARTITION BY location_name), 2) as avg_final_aqi,
            MIN(hour_timestamp) OVER(PARTITION BY location_name) as start_date,
            MAX(hour_timestamp) OVER(PARTITION BY location_name) as end_date,
            ROUND(AVG(pm25_index) OVER(PARTITION BY location_name), 2) as avg_pm25_index,
            ROUND(AVG(pm10_index) OVER(PARTITION BY location_name), 2) as avg_pm10_index,
            ROUND(AVG(no2_index) OVER(PARTITION BY location_name), 2) as avg_no2_index,
            ROUND(AVG(so2_index) OVER(PARTITION BY location_name), 2) as avg_so2_index,
            ROUND(AVG(ozone_index) OVER(PARTITION BY location_name), 2) as avg_ozone_index,
            ROUND(AVG(co_index) OVER(PARTITION BY location_name), 2) as avg_co_index
        FROM {table_name}
        WHERE hour_timestamp >= now() - INTERVAL '24' HOUR 
        GROUP BY location_name, dominant_pollutant, final_aqi, hour_timestamp, pm25_index, pm10_index, no2_index, so2_index, ozone_index, co_index
    )
) 
WHERE rank_position = 1;
"""
