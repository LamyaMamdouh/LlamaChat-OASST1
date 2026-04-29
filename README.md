# 25fsvf-cloud-project
CISC 886 – Cloud Computing Project: End-to-End Cloud-Based Chat Assistant

## Prerequisites
- AWS Academy account with access to us-east-1
- Google Colab account
- Hugging Face account
- GitHub account
- Python 3.10+
- Terraform (optional)

---

## Section 1 — System Architecture
See `architecture-diagram.png` in the repository root.

---

## Section 2 — VPC & Networking

```bash
# Step 1: Create VPC
# Go to AWS Console → VPC → Create VPC
# VPC Name: 25fsvf-vpc
# IPv4 CIDR: 10.0.0.0/16

# Step 2: Create Subnet
# Subnet Name: 25fsvf-subnet
# Availability Zone: us-east-1a
# IPv4 CIDR: 10.0.0.0/20

# Step 3: Create Internet Gateway
# Name: 25fsvf-igw
# Attach to: 25fsvf-vpc

# Step 4: Create Route Table
# Name: 25fsvf-rt
# VPC: 25fsvf-vpc
# Add route: 0.0.0.0/0 → 25fsvf-igw
# Associate with: 25fsvf-subnet
```

---

## Section 3 — Model & Dataset Selection
- Model: LLaMA 3.2 3B Instruct (`unsloth/llama-3.2-3b-instruct-unsloth-bnb-4bit`)
- Dataset: OpenAssistant OASST1
- Source: Hugging Face

---
## Section 4 — Data Preprocessing (EMR + Spark)

```bash
# Step 1: Upload preprocessing script to S3
 aws s3 cp 25fsvf_oasst1_preprocessing.py 

# Step 2: Create EMR Cluster via AWS Console
# Cluster Name: 25fsvf-emr
# Region: us-east-1
# Release: emr-6.x (with Spark)
# Primary node:  1x t3.xlarge
# Core nodes:    2x t3.xlarge

# Step 3: Submit PySpark job
aws emr add-steps \
  --cluster-id <YOUR-CLUSTER-ID> \
  --steps Type=Spark,Name="OASST1 Preprocessing",\
ActionOnFailure=CONTINUE,\
Args=[...25fsvf_oasst1_preprocessing.py]

# Step 4: Monitor the step
aws emr describe-step \
  --cluster-id <YOUR-CLUSTER-ID> \
  --step-id <YOUR-STEP-ID>

# Step 5: Verify output in S3
aws s3 ls s3://25fsvf-oasst1-bucket/output/
```

## Section 5 — Model Fine-Tuning

Run the notebook: `fine_tuning.ipynb` in Google Colab

```bash
# Step 1: Open fine_tuning.ipynb in Google Colab
# Runtime → Change runtime type → GPU (T4 recommended)

# Step 2: Run all cells in order
# The notebook handles: loading the dataset, loading LLaMA 3.2 3B, LoRA fine-tuning, GGUF export

# Step 3: After fine-tuning, upload GGUF model to Hugging Face
# This is done inside the notebook via huggingface_hub push_to_hub()
# Model will be pushed to: lamya20/25fsvf-llama3-oasst1
```

---

## Section 6 — Model Deployment on EC2

```bash
# Step 1: Launch EC2 instance (t3.xlarge, Ubuntu 22.04, us-east-1)
# Open inbound ports: 22 (SSH), 11434 (Ollama), 3000 (OpenWebUI)

# Step 2: SSH into EC2
ssh -i 25fsvf-key.pem ubuntu@<EC2-PUBLIC-IP>

# Step 3: Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Step 4: Start Ollama service
ollama serve &

# Step 5: Pull and run the fine-tuned model from Hugging Face
ollama run hf.co/lamya20/25fsvf-llama3-oasst1

# Step 6: Verify model is responding
curl http://localhost:11434/api/generate -d '{
  "model": "hf.co/lamya20/25fsvf-llama3-oasst1",
  "prompt": "Hello!",
  "stream": false
}'
```

---

## Section 7 — Web Interface

```bash
# Step 1: Install Docker (if not already installed)
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Step 2: Run OpenWebUI container
sudo docker run -d \
  --name open-webui \
  --restart always \
  -p 3000:8080 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/open-webui:main

# Step 3: Verify container is running
sudo docker ps | grep open-webui

# Step 4: Access the web UI
# Open browser → http://<EC2-PUBLIC-IP>:3000
# Create an admin account on first login
```

---

## Cost Summary

| Service | Usage | Estimated Cost |
|---------|-------|---------------|
| EC2 t3.xlarge | ~10 hours | ~$2.50 |
| EMR (m5.xlarge) | ~2 hours | ~$1.50 |
| S3 Storage | ~7 GB | ~$0.20 |
| Data Transfer | minimal | ~$0.10 |
| **Total** | | **~$4.30** |

---

