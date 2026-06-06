"""
UC3 — Apache Spark Analytics & ML Pipeline
Reads from MongoDB, runs aggregations and MLlib forecast, saves results back.

Run:
    python spark/spark_analytics.py --asset_id <uuid> --source_id <uuid>

Install:
    pip install pyspark pymongo python-dotenv
"""

from __future__ import annotations
import argparse, os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator
import pymongo

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/financial_dw")
MONGO_DB  = os.getenv("MONGO_DB",  "financial_dw")

SCHEMA = StructType([
    StructField("assetId",       StringType(),    True),
    StructField("dataSourceId",  StringType(),    True),
    StructField("symbol",        StringType(),    True),
    StructField("date",          TimestampType(), True),
    StructField("open",          DoubleType(),    True),
    StructField("high",          DoubleType(),    True),
    StructField("low",           DoubleType(),    True),
    StructField("close",         DoubleType(),    True),
    StructField("volume",        DoubleType(),    True),
    StructField("adjustedClose", DoubleType(),    True),
])

def get_spark():
    return SparkSession.builder.appName("AcmeFinancialDWH").config("spark.driver.memory","2g").getOrCreate()

def load_from_mongo(spark, asset_id, source_id):
    client = pymongo.MongoClient(MONGO_URI)
    docs = list(client[MONGO_DB].time_series.find(
        {"assetId": asset_id, "dataSourceId": source_id},
        {"_id":0,"assetId":1,"dataSourceId":1,"symbol":1,"date":1,
         "open":1,"high":1,"low":1,"close":1,"volume":1,"adjustedClose":1}
    ).sort("date", 1))
    client.close()
    if not docs:
        raise ValueError("No data found.")
    rows = [{
        "assetId": d.get("assetId"), "dataSourceId": d.get("dataSourceId"),
        "symbol": d.get("symbol"),   "date": d.get("date"),
        "open":   float(d["open"])   if d.get("open")   else None,
        "high":   float(d["high"])   if d.get("high")   else None,
        "low":    float(d["low"])    if d.get("low")    else None,
        "close":  float(d["close"])  if d.get("close")  else None,
        "volume": float(d["volume"]) if d.get("volume") else None,
        "adjustedClose": float(d["adjustedClose"]) if d.get("adjustedClose") else None,
    } for d in docs]
    df = spark.createDataFrame(rows, schema=SCHEMA)
    print(f"Loaded {df.count()} records for {docs[0]['symbol']}")
    return df

def run_aggregations(df):
    print("\n── Spark Aggregations ──")
    agg = df.agg(
        F.count("close").alias("count"),
        F.min("close").alias("min_close"),
        F.max("close").alias("max_close"),
        F.avg("close").alias("avg_close"),
        F.stddev("close").alias("std_close"),
        F.first("close").alias("first_close"),
        F.last("close").alias("last_close"),
    ).collect()[0]
    change_pct = round((agg["last_close"] - agg["first_close"]) / agg["first_close"] * 100, 2)
    result = {"count": int(agg["count"]), "min": round(agg["min_close"],4),
              "max": round(agg["max_close"],4), "avg": round(agg["avg_close"],4),
              "std": round(agg["std_close"],4), "change_pct": change_pct}
    print(f"Aggregation result: {result}")
    monthly = (df.withColumn("year_month", F.date_format("date","yyyy-MM"))
               .groupBy("year_month")
               .agg(F.first("open").alias("open"), F.max("high").alias("high"),
                    F.min("low").alias("low"), F.last("close").alias("close"),
                    F.sum("volume").alias("volume"))
               .orderBy("year_month"))
    print("\nMonthly aggregation:")
    monthly.show()
    return result

def run_ml_forecast(df):
    print("\n── Spark MLlib Linear Regression ──")
    from pyspark.sql.window import Window
    w = Window.orderBy("date")
    df_ml = df.withColumn("day_idx", F.row_number().over(w).cast(DoubleType()))
    df_ml = df_ml.dropna(subset=["close","open","high","low","volume"])
    assembler = VectorAssembler(inputCols=["day_idx","open","high","low","volume"], outputCol="features")
    df_feat = assembler.transform(df_ml).select("features", F.col("close").alias("label"), "day_idx")
    train, test = df_feat.randomSplit([0.8, 0.2], seed=42)
    model = LinearRegression(featuresCol="features", labelCol="label", maxIter=100, regParam=0.1).fit(train)
    preds = model.transform(test)
    rmse = round(RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="rmse").evaluate(preds), 4)
    r2   = round(RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="r2").evaluate(preds), 4)
    last = df_ml.orderBy(F.desc("date")).first()
    next_pred = float(model.predict(
        VectorAssembler(inputCols=["day_idx","open","high","low","volume"], outputCol="features")
        .__class__
    )) if False else model.intercept + sum(c*v for c,v in zip(model.coefficients,
        [float(df_ml.count()+1), float(last["open"]), float(last["high"]),
         float(last["low"]), float(last["volume"])]))
    result = {"model": "Spark MLlib LinearRegression", "rmse": rmse, "r2": r2,
              "last_close": round(float(last["close"]),4),
              "predicted_next_close": round(next_pred, 4),
              "disclaimer": "Statistical model only. Not financial advice."}
    print(f"ML result: {result}")
    return result

def save_results(asset_id, source_id, symbol, agg, ml):
    client = pymongo.MongoClient(MONGO_URI)
    client[MONGO_DB].spark_results.insert_one({
        "assetId": asset_id, "dataSourceId": source_id, "symbol": symbol,
        "computedAt": datetime.now(timezone.utc),
        "aggregations": agg, "mlForecast": ml,
        "engine": "Apache Spark (PySpark)"
    })
    client.close()
    print("Results saved to spark_results collection.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset_id",  required=True)
    parser.add_argument("--source_id", required=True)
    args = parser.parse_args()
    spark = get_spark()
    spark.sparkContext.setLogLevel("ERROR")
    df = load_from_mongo(spark, args.asset_id, args.source_id)
    symbol = df.select("symbol").first()[0]
    agg = run_aggregations(df)
    ml  = run_ml_forecast(df)
    save_results(args.asset_id, args.source_id, symbol, agg, ml)
    spark.stop()
    print("Spark pipeline complete!")