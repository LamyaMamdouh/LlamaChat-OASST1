"""
CISC 886 - Cloud Computing | Queen's University
Section 4: Data Preprocessing with Apache Spark on EMR
Dataset : OpenAssistant Conversations (OASST1)
Author  : 25fsvf
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import boto3
import os

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BUCKET           = "25fsvf-oasst1-bucket"
S3_RAW_TRAIN     = f"s3://{BUCKET}/raw/train.json"
S3_RAW_VAL       = f"s3://{BUCKET}/raw/validation.json"
S3_PROCESSED     = f"s3://{BUCKET}/processed/"
S3_EDA           = f"s3://{BUCKET}/eda/"

MIN_TOKENS       = 10
MAX_TOKENS       = 512
MIN_QUALITY      = 0.5
SEED             = 42

# ─────────────────────────────────────────────
# STEP 1 — Build Spark Session
# ─────────────────────────────────────────────
print("=" * 50)
print("[Step 1] Starting Spark session...")

spark = (
    SparkSession.builder
    .appName("25fsvf-oasst1-preprocessing")
    .config("spark.sql.shuffle.partitions", "50")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")
print("[Step 1] Spark session started.")

# ─────────────────────────────────────────────
# STEP 2 — Load raw JSON from S3
# ─────────────────────────────────────────────
print("\n[Step 2] Loading raw JSON from S3...")

train_df = spark.read.json(S3_RAW_TRAIN)
val_df   = spark.read.json(S3_RAW_VAL)

# Combine both splits into one DataFrame
raw_df = train_df.unionByName(val_df, allowMissingColumns=True)

total = raw_df.count()
print(f"[Step 2] Total raw messages loaded: {total:,}")
raw_df.printSchema()

# ─────────────────────────────────────────────
# STEP 3 — Flatten conversation tree
# ─────────────────────────────────────────────
print("\n[Step 3] Flattening conversation trees...")

# Prompter messages (human turn)
human_df = (
    raw_df
    .filter(F.col("role") == "prompter")
    .select(
        F.col("message_id").alias("human_id"),
        F.col("text").alias("prompt"),
        F.col("lang"),
    )
)

# Assistant replies
assistant_df = (
    raw_df
    .filter(F.col("role") == "assistant")
    .select(
        F.col("parent_id").alias("human_id"),
        F.col("text").alias("response"),
        F.col("rank"),
        F.col("message_id").alias("response_id"),
    )
)

# Join to get (prompt, response) pairs
pairs = human_df.join(assistant_df, on="human_id", how="inner")

# Quality score: rank=0 is best reply → score=1.0
pairs = pairs.withColumn(
    "quality_score",
    F.when(F.col("rank").isNull(), 0.5)
     .otherwise(1.0 / (F.col("rank") + 1))
)

pair_count = pairs.count()
print(f"[Step 3] Total (prompt, response) pairs: {pair_count:,}")

# ─────────────────────────────────────────────
# STEP 4 — Filter
# ─────────────────────────────────────────────
print("\n[Step 4] Applying filters...")

# Add token length (whitespace approximation)
pairs = (
    pairs
    .withColumn("prompt_tokens",   F.size(F.split(F.trim(F.col("prompt")),   r"\s+")))
    .withColumn("response_tokens", F.size(F.split(F.trim(F.col("response")), r"\s+")))
)

before = pairs.count()

filtered = pairs.filter(
    (F.col("lang") == "en") &
    (F.col("quality_score") >= MIN_QUALITY) &
    (F.col("prompt_tokens")   >= MIN_TOKENS) &
    (F.col("prompt_tokens")   <= MAX_TOKENS) &
    (F.col("response_tokens") >= MIN_TOKENS) &
    (F.col("response_tokens") <= MAX_TOKENS)
)

after = filtered.count()
print(f"[Step 4] Before filter : {before:,}")
print(f"[Step 4] After filter  : {after:,}  (removed {before - after:,} rows)")

# ─────────────────────────────────────────────
# STEP 5 — EDA stats (saved as CSV to S3)
# ─────────────────────────────────────────────
print("\n[Step 5] Computing EDA statistics...")

# EDA 1: Token length stats
token_stats = filtered.select(
    F.mean("prompt_tokens").alias("avg_prompt_tokens"),
    F.mean("response_tokens").alias("avg_response_tokens"),
    F.min("prompt_tokens").alias("min_prompt_tokens"),
    F.max("prompt_tokens").alias("max_prompt_tokens"),
    F.min("response_tokens").alias("min_response_tokens"),
    F.max("response_tokens").alias("max_response_tokens"),
)
token_stats.show()
token_stats.coalesce(1).write.mode("overwrite").csv(f"{S3_EDA}token_stats/", header=True)
print("[Step 5] EDA 1 - Token stats saved.")

# EDA 2: Language distribution (before English filter)
lang_dist = (
    pairs
    .groupBy("lang")
    .count()
    .orderBy(F.desc("count"))
    .limit(15)
)
lang_dist.show()
lang_dist.coalesce(1).write.mode("overwrite").csv(f"{S3_EDA}language_distribution/", header=True)
print("[Step 5] EDA 2 - Language distribution saved.")

# EDA 3: Quality score distribution
quality_dist = (
    filtered
    .withColumn("quality_bucket", F.round(F.col("quality_score"), 1))
    .groupBy("quality_bucket")
    .count()
    .orderBy("quality_bucket")
)
quality_dist.show()
quality_dist.coalesce(1).write.mode("overwrite").csv(f"{S3_EDA}quality_distribution/", header=True)
print("[Step 5] EDA 3 - Quality distribution saved.")

# ─────────────────────────────────────────────
# STEP 6 — Train / Val / Test split (70/15/15)
# ─────────────────────────────────────────────
print("\n[Step 6] Splitting data 70 / 15 / 15...")

train_df, val_df, test_df = filtered.randomSplit([0.70, 0.15, 0.15], seed=SEED)

train_df = train_df.withColumn("split", F.lit("train"))
val_df   = val_df.withColumn("split",   F.lit("val"))
test_df  = test_df.withColumn("split",  F.lit("test"))

train_count = train_df.count()
val_count   = val_df.count()
test_count  = test_df.count()

print(f"[Step 6] train : {train_count:,}")
print(f"[Step 6] val   : {val_count:,}")
print(f"[Step 6] test  : {test_count:,}")

combined = train_df.unionByName(val_df).unionByName(test_df)

# ─────────────────────────────────────────────
# STEP 7 — Save to S3 as Parquet
# ─────────────────────────────────────────────
print("\n[Step 7] Saving Parquet to S3...")

output_cols = [
    "human_id", "response_id", "prompt", "response",
    "quality_score", "prompt_tokens", "response_tokens", "split"
]

(
    combined
    .select(output_cols)
    .repartition(10, "split")
    .write
    .mode("overwrite")
    .partitionBy("split")
    .parquet(S3_PROCESSED)
)

print(f"[Step 7] Done! Output saved to {S3_PROCESSED}")
print("\n=== Preprocessing Complete ===")
print(f"  Processed pairs : {after:,}")
print(f"  Train           : {train_count:,}")
print(f"  Val             : {val_count:,}")
print(f"  Test            : {test_count:,}")
print(f"  S3 output       : {S3_PROCESSED}")
print(f"  EDA stats       : {S3_EDA}")

spark.stop()
