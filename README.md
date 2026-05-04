# LlamaChat-OASST1
**CISC 886 – Cloud Computing Project: End-to-End Cloud-Based Chat Assistant on AWS**

| Name | NetID | Student ID |
|------|-------|------------|
| Lamya Mamdouh Sayed | 25nfnx | 20596347 |
| Esraa Mohammed El sayed | 25htmp | 20596301 |
| Alaa Ehab Mohamed Elshenawy | 25fsvf | 20596313 |

**Date:** April 28, 2026
**GitHub Repository:** https://github.com/LamyaMamdouh/LlamaChat-OASST1

---

## Repository Structure

```
LlamaChat-OASST1/
├── README.md
├── architecture-diagram.png
├── architecture-diagram2.png
├── 25fsvf_oasst1_preprocessing.py   # PySpark preprocessing script (EMR)
└── 25fsvf_finetuning.ipynb          # Fine-tuning notebook (Google Colab)
```

---

## Prerequisites

### Accounts Required
- AWS Academy account with access to **us-east-1 (N. Virginia)**
- Google Colab account (free tier with T4 GPU)
- Hugging Face account
- GitHub account

### Tools Required
| Tool | Version | Install |
|------|---------|---------|
| AWS CLI | v2+ | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| Python | 3.10+ | https://www.python.org/downloads/ |
| Docker | latest | https://docs.docker.com/get-docker/ |
| Ollama | latest | https://ollama.com/download |
| SSH client | any | Built-in on Mac/Linux, use PuTTY on Windows |

### AWS CLI Configuration
```bash
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name: us-east-1
# Default output format: json
```

### Estimated AWS Cost
| Service | Usage | Estimated Cost |
|---------|-------|---------------|
| EC2 t3.xlarge | ~10 hours | ~$2.50 |
| EMR (t3.xlarge) | ~2 hours | ~$1.50 |
| S3 Storage | ~7 GB | ~$0.20 |
| Data Transfer | minimal | ~$0.10 |
| **Total** | | **~$4.30** |

> **Important:** Terminate all AWS resources immediately after use to avoid unexpected charges on the shared account.

---

## Section 1 — System Architecture

See `architecture-diagram.png` and `architecture-diagram2.png` in the repository root for the full end-to-end system diagram.

**Data flow summary:**
Raw OASST1 dataset → S3 bucket → EMR PySpark preprocessing → S3 processed output → Google Colab fine-tuning (LoRA/Unsloth) → GGUF export → S3 model storage → EC2 (Ollama runner) → OpenWebUI (port 3000) → User browser

---

## Section 2 — VPC & Networking

> All resources are provisioned via **AWS Console** in **us-east-1**.
> Resource naming prefix: `25fsvf-` (NetID prefix as required).

### Step 1: Create Custom VPC
```
AWS Console → VPC → Your VPCs → Create VPC

Settings:
  Name:             NetID-25fsvf-VPC-Lamya
  IPv4 CIDR:        10.0.0.0/16
  Tenancy:          Default
  DNS resolution:   Enabled
  DNS hostnames:    Enabled
```

### Step 2: Create Subnets (4 total across 2 AZs)
```
AWS Console → VPC → Subnets → Create subnet

Public Subnet 1:
  Name:              project-subnet-public1-us-east-1a
  Availability Zone: us-east-1a
  IPv4 CIDR:         10.0.0.0/20

Public Subnet 2:
  Name:              project-subnet-public2-us-east-1b
  Availability Zone: us-east-1b
  IPv4 CIDR:         10.0.16.0/20

Private Subnet 1:
  Name:              project-subnet-private1-us-east-1a
  Availability Zone: us-east-1a
  IPv4 CIDR:         10.0.128.0/20

Private Subnet 2:
  Name:              project-subnet-private2-us-east-1b
  Availability Zone: us-east-1b
  IPv4 CIDR:         10.0.144.0/20
```

> Public subnets host EC2 and EMR (require internet access).
> Private subnets are reserved for future internal resources and have no IGW route.

### Step 3: Create and Attach Internet Gateway
```
AWS Console → VPC → Internet Gateways → Create

  Name: 25fsvf-igw

After creation:
  Actions → Attach to VPC → Select: NetID-25fsvf-VPC-Lamya
```

### Step 4: Configure Public Route Table
```
AWS Console → VPC → Route Tables → Create route table

  Name: project-rtb-public
  VPC:  NetID-25fsvf-VPC-Lamya

Add route:
  Destination: 0.0.0.0/0
  Target:      25fsvf-igw (Internet Gateway)

Subnet associations → Edit → Associate:
  - project-subnet-public1-us-east-1a
  - project-subnet-public2-us-east-1b
```

### Step 5: Create Security Groups

**Security Group for EC2 (launch-wizard-3):**
```
AWS Console → EC2 → Security Groups → Create

  Name:        launch-wizard-3
  VPC:         NetID-25fsvf-VPC-Lamya
  Description: EC2 security group for Ollama and OpenWebUI

Inbound Rules:
  Type        Protocol  Port   Source
  SSH         TCP       22     0.0.0.0/0
  Custom TCP  TCP       3000   0.0.0.0/0    ← OpenWebUI
  Custom TCP  TCP       8501   0.0.0.0/0    ← Streamlit (optional)
  Custom TCP  TCP       11434  0.0.0.0/0    ← Ollama API

Outbound Rules:
  All traffic  All  All  0.0.0.0/0
```

**Security Group for EMR (launch-wizard-5):**
```
  Name:        launch-wizard-5
  VPC:         NetID-25fsvf-VPC-Lamya

Inbound Rules:
  Type        Protocol  Port   Source
  SSH         TCP       22     0.0.0.0/0
  Custom TCP  TCP       8501   0.0.0.0/0
  Custom TCP  TCP       11434  0.0.0.0/0

Outbound Rules:
  All traffic  All  All  0.0.0.0/0
```

---

## Section 3 — Model & Dataset Selection

| Property | Details |
|----------|---------|
| Model Name | Llama-3.2-3B-Instruct |
| Parameters | 3 Billion |
| Source | https://huggingface.co/unsloth/Llama-3.2-3B-Instruct |
| License | Llama 3.2 Community License (Meta) |
| Quantization | 4-bit QLoRA via Unsloth |
| Dataset | OpenAssistant Conversations (OASST1) |
| Dataset Source | https://huggingface.co/datasets/OpenAssistant/oasst1 |
| Dataset License | Apache 2.0 |
| Final Processed Pairs | 11,876 |
| Split | 70% train / 15% validation / 15% test (seed=42) |

---

## Section 4 — Data Preprocessing (EMR + Spark)

### Step 1: Create S3 Bucket and Upload Raw Data
```bash
# Create S3 bucket
aws s3 mb s3://25fsvf-oasst1-bucket --region us-east-1

# Upload raw OASST1 dataset files
aws s3 cp train.json s3://25fsvf-oasst1-bucket/raw/
aws s3 cp validation.json s3://25fsvf-oasst1-bucket/raw/

# Upload preprocessing script
aws s3 cp 25fsvf_oasst1_preprocessing.py s3://25fsvf-oasst1-bucket/scripts/

# Verify uploads
aws s3 ls s3://25fsvf-oasst1-bucket/raw/
```

### Step 2: Create EMR Cluster
```
AWS Console → EMR → Create Cluster

  Cluster Name:   25fsvf-emr-oasst1
  EMR Release:    emr-6.15.0
  Applications:   Spark 3.4.1
  Region:         us-east-1

Instance Configuration:
  Primary:  1x m5.xlarge
  Core:     2x m5.xlarge
  Task:     0

Networking:
  VPC:     NetID-25fsvf-VPC-Lamya
  Subnet:  project-subnet-public1-us-east-1a

Security:
  EC2 Key Pair: 25fsvf-key
```

### Step 3: Submit PySpark Preprocessing Job
```bash
# Get your cluster ID from the console, then submit the step
aws emr add-steps \
  --cluster-id <YOUR-CLUSTER-ID> \
  --steps Type=Spark,\
Name="25fsvf-preprocess-v2",\
ActionOnFailure=CONTINUE,\
Args=[s3://25fsvf-oasst1-bucket/scripts/25fsvf_oasst1_preprocessing.py] \
  --region us-east-1
```

### Step 4: Monitor Job Progress
```bash
# Check step status
aws emr describe-step \
  --cluster-id <YOUR-CLUSTER-ID> \
  --step-id <YOUR-STEP-ID> \
  --region us-east-1 \
  --query 'Step.Status.State'

# Expected output when done: "COMPLETED"
# Typical runtime: ~2-3 minutes
```

### Step 5: Verify Processed Output in S3
```bash
# Check processed Parquet output files
aws s3 ls s3://25fsvf-oasst1-bucket/processed/ --recursive

# Expected folders:
# processed/split=train/
# processed/split=validation/
# processed/split=test/

# Check EDA output CSV files
aws s3 ls s3://25fsvf-oasst1-bucket/eda/
```

### Step 6: Terminate EMR Cluster
```bash
# REQUIRED — terminate immediately after job completes to avoid charges
aws emr terminate-clusters \
  --cluster-ids <YOUR-CLUSTER-ID> \
  --region us-east-1

# Verify termination
aws emr describe-cluster \
  --cluster-id <YOUR-CLUSTER-ID> \
  --query 'Cluster.Status.State'
# Expected: "TERMINATED"
```


---

## Section 5 — Model Fine-Tuning

Fine-tuning is performed in **Google Colab** using the notebook `25fsvf_finetuning.ipynb`.

### Step 1: Open Notebook in Google Colab
```
1. Go to https://colab.research.google.com
2. File → Open notebook → GitHub tab
3. Enter: https://github.com/LamyaMamdouh/LlamaChat-OASST1
4. Select: 25fsvf_finetuning.ipynb
```

### Step 2: Configure Runtime
```
Runtime → Change runtime type
  Hardware accelerator: GPU
  GPU type: T4 (recommended — free tier)
```

### Step 3: Configure AWS Credentials in Notebook
```python
# Run this cell in Colab before executing the notebook
import os
os.environ['AWS_ACCESS_KEY_ID'] = '<your-access-key>'
os.environ['AWS_SECRET_ACCESS_KEY'] = '<your-secret-key>'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
```

### Step 4: Run All Cells in Order
The notebook performs the following steps automatically:
```
Cell 1:  Install Unsloth, boto3, and dependencies
Cell 2:  Import libraries and verify GPU (Tesla T4)
Cell 3:  Load base model with 4-bit quantization
         Model: unsloth/Llama-3.2-3B-Instruct
Cell 4:  Attach QLoRA adapters (rank=16, alpha=16)
Cell 5:  Load preprocessed training data from S3
         Source: s3://25fsvf-oasst1-bucket/processed/split=train/
Cell 6:  Format data into Llama-3 chat template
Cell 7:  Train with SFTTrainer
         - Learning rate: 2e-4
         - Batch size: 2 (effective: 8 with grad accumulation)
         - Epochs: 1
         - Total steps: 1,485
         - Final training loss: ~1.4568
Cell 8:  Export fine-tuned model to GGUF f16 format
         Output: llama-3.2-3b-instruct.F16.gguf
Cell 9:  Upload GGUF model to S3
```

### Step 5: Upload GGUF Model to S3 (inside notebook or manually)
```bash
aws s3 cp llama-3.2-3b-instruct.F16.gguf \
  s3://25fsvf-oasst1-bucket/model/ \
  --region us-east-1

# Verify upload (file should be ~6 GB)
aws s3 ls s3://25fsvf-oasst1-bucket/model/
```

### Hyperparameter Reference
| Hyperparameter | Value |
|----------------|-------|
| Method | QLoRA (PEFT) |
| LoRA rank (r) | 16 |
| LoRA alpha | 16 |
| LoRA dropout | 0 |
| Learning rate | 2e-4 |
| Batch size | 2 |
| Gradient accumulation | 4 |
| Effective batch size | 8 |
| Epochs | 1 |
| Max sequence length | 2048 |
| Optimizer | adamw_8bit |
| LR scheduler | linear |
| Warmup steps | 5 |
| Total steps | 1,485 |
| Quantization | 4-bit |
| Random seed | 42 |

---

## Section 6 — Model Deployment on EC2

### Step 1: Launch EC2 Instance
```
AWS Console → EC2 → Launch Instance

  Name:           25fsvf-ec2
  AMI:            Ubuntu Server 22.04 LTS (ami-0c7217cdde317cfec)
  Instance type:  t3.xlarge (4 vCPU, 16 GB RAM)
  Key pair:       25fsvf-key (create if not exists → download .pem file)
  VPC:            NetID-25fsvf-VPC-Lamya
  Subnet:         project-subnet-public1-us-east-1a
  Security group: launch-wizard-3
  Storage:        100 GB gp2

  Enable: Auto-assign public IP
```

### Step 2: SSH into EC2 Instance
```bash
# Fix key permissions (required on Mac/Linux)
chmod 400 25fsvf-key.pem

# Connect to instance
ssh -i 25fsvf-key.pem ubuntu@<EC2-PUBLIC-IP>

# Verify connection — you should see Ubuntu 22.04 welcome message
```

### Step 3: Install Ollama
```bash
# Install Ollama (creates systemd service automatically)
curl -fsSL https://ollama.com/install.sh | sh

# Verify Ollama is running
sudo systemctl status ollama

# Ollama API should be available at:
curl http://localhost:11434
# Expected response: "Ollama is running"
```

### Step 4: Download Fine-Tuned Model from S3
```bash
# Install AWS CLI on EC2
sudo apt-get install -y awscli

# Configure AWS credentials
aws configure
# Enter your AWS Academy credentials

# Download fine-tuned GGUF model from S3 (~6 GB, takes ~3-5 minutes)
aws s3 cp s3://25fsvf-oasst1-bucket/model/llama-3.2-3b-instruct.F16.gguf ~/
aws s3 cp s3://25fsvf-oasst1-bucket/model/Modelfile ~/

# Verify download
ls -lh ~/llama-3.2-3b-instruct.F16.gguf
# Expected: ~6.0 GB
```

### Step 5: Load Fine-Tuned Model into Ollama
```bash
# Create the model in Ollama using the Modelfile
ollama create 25fsvf-llama3-oasst1 -f ~/Modelfile

# Verify model is loaded
ollama list
# Expected output includes: 25fsvf-llama3-oasst1

# Quick test
ollama run 25fsvf-llama3-oasst1 "Hello, what can you help me with?"
```

### Step 6: Verify API via curl
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "25fsvf-llama3-oasst1",
  "prompt": "What is machine learning?",
  "stream": false
}'
# Expected: JSON response with "response" field containing model answer
```

---

## Section 7 — Web Interface (OpenWebUI)

### Step 1: Install Docker
```bash
sudo apt-get update -y
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Add ubuntu user to docker group (avoids needing sudo)
sudo usermod -aG docker ubuntu
newgrp docker

# Verify Docker is running
docker --version
```

### Step 2: Deploy OpenWebUI Container
```bash
sudo docker run -d \
  --name open-webui \
  --restart always \
  -p 3000:8080 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/open-webui:main

# --restart always ensures auto-start on EC2 reboot
```

### Step 3: Verify Container is Running
```bash
sudo docker ps | grep open-webui
# Expected: container status "healthy" or "Up X minutes"

# Check container logs if needed
sudo docker logs open-webui
```

### Step 4: Access the Web Interface
```
Open browser → http://<EC2-PUBLIC-IP>:3000

First-time setup:
  1. Create admin account (email + password)
  2. After login → click model selector (top left)
  3. Select: 25fsvf-llama3-oasst1
  4. Start chatting!
```

## Cleanup — Destroy All Resources

Run after completing all tasks to avoid ongoing charges:

```bash
# 1. Stop and remove Docker container
sudo docker stop open-webui
sudo docker rm open-webui

# 2. Stop Ollama service
sudo systemctl stop ollama

# 3. Terminate EC2 instance
aws ec2 terminate-instances \
  --instance-ids <YOUR-INSTANCE-ID> \
  --region us-east-1

# 4. Delete S3 bucket contents and bucket
aws s3 rm s3://25fsvf-oasst1-bucket --recursive
aws s3 rb s3://25fsvf-oasst1-bucket

# 5. Terminate EMR cluster (if still running)
aws emr terminate-clusters \
  --cluster-ids <YOUR-CLUSTER-ID> \
  --region us-east-1

# 6. Delete Internet Gateway
# AWS Console → VPC → Internet Gateways
# Detach from VPC → Delete

# 7. Delete VPC
# AWS Console → VPC → Your VPCs
# Select NetID-25fsvf-VPC-Lamya → Actions → Delete
```
