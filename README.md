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
# Create VPC via AWS Console
# VPC Name: 25fsvf-vpc
# CIDR: 10.0.0.0/16
# Subnet: 10.0.1.0/24 (us-east-1a)
# Internet Gateway: 25fsvf-igw
# Route Table: 25fsvf-rt
```

---

## Section 3 — Model & Dataset Selection
- Model: LLaMA 3.2 3B Instruct (unsloth/llama-3.2-3b-instruct-unsloth-bnb-4bit)
- Dataset: OpenAssistant OASST1
- Source: Hugging Face

---

## Section 4 — Data Preprocessing (EMR + Spark)
```bash
# Upload script to S3
aws s3 cp preprocessing.py s3://25fsvf-oasst1-bucket/scripts/

# Submit PySpark job on EMR
# EMR Cluster: 25fsvf-emr
# Instance type: m5.xlarge
# Region: us-east-1
```

---

## Section 5 — Model Fine-Tuning
Run the notebook: `fine_tuning.ipynb` in Google Colab

```bash
# After fine-tuning, upload GGUF to Hugging Face
# Model: lamya20/25fsvf-llama3-oasst1
```

---

## Section 6 — Model Deployment on EC2
```bash
# SSH into EC2
ssh -i 25fsvf-key.pem ubuntu@<EC2-PUBLIC-IP>

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model from Hugging Face
ollama run hf.co/lamya20/25fsvf-llama3-oasst1

# Verify model is running
curl http://localhost:11434/api/generate -d '{
  "model": "25fsvf-llama3-oasst1",
  "prompt": "Hello!"
}'
```

---

## Section 7 — Web Interface
```bash
# Install OpenWebUI
docker run -d \
  --network=host \
  --restart always \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main

# Access at: http://<EC2-PUBLIC-IP>:3000
```

---

## Cost Summary

| Service | Usage | Estimated Cost |
|---------|-------|---------------|
| EC2 t3.large | ~10 hours | ~$2.50 |
| EMR (m5.xlarge) | ~2 hours | ~$1.50 |
| S3 Storage | ~7 GB | ~$0.20 |
| Data Transfer | minimal | ~$0.10 |
| **Total** | | **~$4.30** |
