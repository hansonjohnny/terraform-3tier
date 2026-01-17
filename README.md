# Terraform 3-Tier Architecture

> **What you'll create:** Build a production-ready 3-tier web application infrastructure on AWS using Terraform - including load balancer, web/app servers, and database.

---

## Quick Start

```bash
# 1. Fork and clone this repo

# 2. Install Terraform (see Step 0)

# 3. Choose your approach:
#    - EC2 (traditional) - simpler, start here
#    - ECS (containerized) - modern, learn containers

# 4. Complete the .tf files

# 5. Test locally with LocalStack
docker-compose up -d
terraform init
terraform apply

# 6. Push and check your score!
git push origin main
```

---

## Understanding 3-Tier Architecture

### What is it?

A **3-tier architecture** is a software design pattern that separates an application into three logical layers, each with a specific responsibility. Think of it like a restaurant:

| Tier | Restaurant Analogy | Application Role |
|------|-------------------|------------------|
| **Presentation (Web)** | Dining room & waiters | User interface - what users see and interact with |
| **Application (App)** | Kitchen & chefs | Business logic - processes requests, makes decisions |
| **Data (Database)** | Pantry & storage | Data storage - stores and retrieves information |

### Why Use 3-Tier Architecture?

**1. Security (Defense in Depth)**
```
Internet → [Firewall] → Web Tier → [Firewall] → App Tier → [Firewall] → Database
                ↑                       ↑                        ↑
         Only ports 80/443      Only from Web Tier       Only from App Tier
```
- Database is **never** directly exposed to the internet
- Each tier has its own security rules
- Attackers must breach multiple layers

**2. Scalability (Scale What You Need)**
```
High traffic day?                    Complex calculations?
        ↓                                    ↓
Add more Web servers              Add more App servers
(Database stays same)             (Web tier stays same)
```
- Scale each tier independently based on load
- Cost-effective: only pay for what you need

**3. Maintainability (Change Without Breaking)**
```
Update the UI?          Change business rules?       Switch databases?
      ↓                         ↓                          ↓
Only touch Web Tier     Only touch App Tier        Only touch Data Tier
(App & DB unchanged)    (Web & DB unchanged)       (Web & App unchanged)
```
- Teams can work on different tiers simultaneously
- Updates to one tier don't affect others

**4. Reliability (Failure Isolation)**
```
Web server crashes?     App server overloaded?      DB maintenance?
        ↓                       ↓                        ↓
Load balancer routes    Other app servers           Failover to
to healthy servers      handle requests             standby DB
```

---

## AWS Architecture Diagram

Here's how the 3-tier architecture maps to AWS services:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   INTERNET                                       │
│                                      🌐                                          │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                        ROUTE 53 (DNS)                                     │  │
│  │                    myapp.example.com → ALB                                │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────────┐
│                              VPC (10.0.0.0/16)                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                    PUBLIC SUBNETS (10.0.1.0/24, 10.0.2.0/24)               │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │              APPLICATION LOAD BALANCER (ALB)                         │  │ │
│  │  │     ┌─────────────┐                        ┌─────────────┐           │  │ │
│  │  │     │   AZ-1a     │                        │   AZ-1b     │           │  │ │
│  │  │     │  ┌───────┐  │                        │  ┌───────┐  │           │  │ │
│  │  │     │  │  ALB  │  │◄── Health Checks ────► │  │  ALB  │  │           │  │ │
│  │  │     │  │ Node  │  │    (Multi-AZ)          │  │ Node  │  │           │  │ │
│  │  │     │  └───────┘  │                        │  └───────┘  │           │  │ │
│  │  │     └─────────────┘                        └─────────────┘           │  │ │
│  │  └──────────────────────────────┬───────────────────────────────────────┘  │ │
│  │                                 │ Port 80                                  │ │
│  │  ┌──────────────────────────────▼───────────────────────────────────────┐  │ │
│  │  │                         NAT GATEWAY                                  │  │ │
│  │  │              (Allows private subnets to reach internet)              │  │ │
│  │  └──────────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                             │
│  ┌─────────────────────────────────▼──────────────────────────────────────────┐ │
│  │              PRIVATE SUBNETS - APP (10.0.10.0/24, 10.0.11.0/24)            │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                      WEB TIER (EC2 / ECS)                           │   │ │
│  │  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │ │
│  │  │   │  ┌───────┐  │    │  ┌───────┐  │    │  ┌───────┐  │             │   │ │
│  │  │   │  │ Web 1 │  │    │  │ Web 2 │  │    │  │ Web 3 │  │  Auto       │   │ │
│  │  │   │  │ Nginx │  │    │  │ Nginx │  │    │  │ Nginx │  │  Scaling    │   │ │
│  │  │   │  └───────┘  │    │  └───────┘  │    │  └───────┘  │  Group      │   │ │
│  │  │   └─────────────┘    └─────────────┘    └─────────────┘             │   │ │
│  │  └─────────────────────────────┬───────────────────────────────────────┘   │ │
│  │                                │ Port 8080                                 │ │
│  │  ┌─────────────────────────────▼───────────────────────────────────────┐   │ │
│  │  │                      APP TIER (EC2 / ECS)                           │   │ │
│  │  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │ │
│  │  │   │  ┌───────┐  │    │  ┌───────┐  │    │  ┌───────┐  │             │   │ │
│  │  │   │  │ App 1 │  │    │  │ App 2 │  │    │  │ App 3 │  │  Auto       │   │ │
│  │  │   │  │ Node  │  │    │  │ Node  │  │    │  │ Node  │  │  Scaling    │   │ │
│  │  │   │  └───────┘  │    │  └───────┘  │    │  └───────┘  │  Group      │   │ │
│  │  │   └─────────────┘    └─────────────┘    └─────────────┘             │   │ │
│  │  └─────────────────────────────┬───────────────────────────────────────┘   │ │
│  └────────────────────────────────┼───────────────────────────────────────────┘ │
│                                   │ Port 3306                                    │
│  ┌────────────────────────────────▼───────────────────────────────────────────┐ │
│  │            PRIVATE SUBNETS - DB (10.0.20.0/24, 10.0.21.0/24)               │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                    DATABASE TIER (RDS)                              │   │ │
│  │  │      ┌─────────────────┐              ┌─────────────────┐           │   │ │
│  │  │      │     AZ-1a       │   Sync       │      AZ-1b      │           │   │ │
│  │  │      │  ┌───────────┐  │   Repl.      │  ┌───────────┐  │           │   │ │
│  │  │      │  │  PRIMARY  │  │◄──────────►  │  │  STANDBY  │  │           │   │ │
│  │  │      │  │   MySQL   │  │              │  │   MySQL   │  │           │   │ │
│  │  │      │  └───────────┘  │              │  └───────────┘  │           │   │ │
│  │  │      └─────────────────┘              └─────────────────┘           │   │ │
│  │  │                         Multi-AZ RDS                                │   │ │
│  │  └─────────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘

SECURITY GROUPS FLOW:
━━━━━━━━━━━━━━━━━━━━━
Internet ──► ALB-SG (80, 443) ──► Web-SG (80 from ALB) ──► App-SG (8080 from Web) ──► DB-SG (3306 from App)
```

---

## Real-World Examples

### Example 1: E-Commerce Website (Amazon-like)

```
USER JOURNEY: "I want to buy a laptop"

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────►│  Web Tier   │────►│  App Tier   │────►│  Database   │
│             │     │             │     │             │     │             │
│ Shows product     │ Serves HTML │     │ Checks      │     │ Stores      │
│ page, images      │ CSS, JS     │     │ inventory   │     │ products,   │
│                   │ React app   │     │ processes   │     │ orders,     │
│                   │             │     │ payment     │     │ users       │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Real Companies Using This:**
- **Amazon**: Web (CloudFront + S3), App (EC2 + Lambda), DB (Aurora + DynamoDB)
- **Shopify**: Web (Nginx), App (Ruby on Rails), DB (MySQL + Redis)
- **Etsy**: Web (Apache), App (PHP), DB (MySQL + Memcached)

### Example 2: Social Media Platform (Instagram-like)

```
USER JOURNEY: "I want to post a photo"

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Mobile    │────►│  Web Tier   │────►│  App Tier   │────►│  Database   │
│    App      │     │             │     │             │     │             │
│             │     │ API Gateway │     │ Image       │     │ PostgreSQL  │
│ Takes photo │     │ REST/GraphQL│     │ processing  │     │ (posts)     │
│ uploads     │     │             │     │ Feed algo   │     │ S3 (images) │
│             │     │             │     │ Notifications│    │ Redis(cache)│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Real Companies Using This:**
- **Instagram**: Web (Django), App (Python + Go), DB (PostgreSQL + Cassandra)
- **Twitter/X**: Web (Scala), App (Java + Scala), DB (MySQL + Manhattan)
- **TikTok**: Web (Go), App (Go + Python), DB (MySQL + Redis)

### Example 3: Banking Application

```
USER JOURNEY: "I want to transfer $100"

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────►│  Web Tier   │────►│  App Tier   │────►│  Database   │
│             │     │             │     │             │     │             │
│ Login page  │     │ HTTPS only  │     │ Auth service│     │ Encrypted   │
│ Dashboard   │     │ WAF protect │     │ Fraud check │     │ at rest     │
│ Transfer UI │     │ Rate limit  │     │ Transaction │     │ Audit logs  │
│             │     │             │     │ processing  │     │ Compliance  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Real Companies Using This:**
- **Chase**: Web (Angular), App (Java Spring), DB (Oracle + DB2)
- **Capital One**: Web (React), App (Java + Python), DB (AWS Aurora)
- **Stripe**: Web (Ruby), App (Ruby + Go), DB (MongoDB + PostgreSQL)

### Example 4: Video Streaming (Netflix-like)

```
USER JOURNEY: "I want to watch a movie"

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Smart TV  │────►│  Web Tier   │────►│  App Tier   │────►│  Database   │
│             │     │             │     │             │     │             │
│ Netflix app │     │ CDN (video) │     │ Recommend   │     │ User prefs  │
│ UI/playback │     │ API Gateway │     │ engine      │     │ Watch hist  │
│             │     │             │     │ Encoding    │     │ Video meta  │
│             │     │             │     │ DRM         │     │ S3 (videos) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Real Companies Using This:**
- **Netflix**: Web (Node.js), App (Java + Python), DB (Cassandra + S3)
- **Disney+**: Web (React), App (Java), DB (AWS services)
- **YouTube**: Web (Python), App (C++ + Python), DB (Bigtable + Spanner)

---

## How Traffic Flows Through 3-Tier

Let's trace a real request step by step:

```
1. USER types "myapp.com" in browser
   │
   ▼
2. DNS (Route 53) resolves to ALB IP address
   │
   ▼
3. REQUEST hits Application Load Balancer
   │  - SSL termination (HTTPS → HTTP)
   │  - Health check: which servers are alive?
   │  - Load balancing: pick least busy server
   │
   ▼
4. ALB forwards to WEB TIER (port 80)
   │  - Web server (Nginx/Apache) receives request
   │  - Serves static files (HTML, CSS, JS, images)
   │  - For dynamic content, calls App Tier
   │
   ▼
5. Web Tier calls APP TIER (port 8080)
   │  - Application server processes business logic
   │  - Validates user input
   │  - Checks permissions
   │  - Needs data? Calls Database
   │
   ▼
6. App Tier queries DATABASE (port 3306)
   │  - SQL query executed
   │  - Data retrieved/stored
   │  - Results returned to App Tier
   │
   ▼
7. RESPONSE travels back
   Database → App Tier → Web Tier → ALB → User
```

---

## Security in 3-Tier Architecture

### The "Onion" Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
│   Attackers are HERE - trying to get to your data               │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   LAYER 1: WAF    │  ← Blocks SQL injection,
                    │   Web App Firewall │    XSS, bad bots
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  LAYER 2: ALB     │  ← Only ports 80/443 open
                    │  Security Group   │    Rate limiting
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  LAYER 3: Web SG  │  ← Only accepts from ALB
                    │  (Private subnet) │    No direct internet
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  LAYER 4: App SG  │  ← Only accepts from Web
                    │  (Private subnet) │    Business logic here
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  LAYER 5: DB SG   │  ← Only accepts from App
                    │  (Isolated subnet)│    Encrypted at rest
                    └───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    YOUR DATA      │  ← Protected by 5 layers!
                    │  (The treasure)   │
                    └───────────────────┘
```

---

## Do I Need Prior Knowledge?

**You need:**
- ✅ Completed the Terraform Basics challenge (or equivalent)
- ✅ Understanding of VPCs, subnets, security groups
- ✅ Basic networking concepts (public vs private)

**You don't need:**
- ❌ AWS account (we'll use LocalStack)
- ❌ Prior load balancer or RDS experience
- ❌ Container experience (for EC2 path)

**You'll learn:**
- Multi-tier architecture design
- Application Load Balancer (ALB)
- RDS database setup
- Public/private subnet networking
- Security group chaining
- (Optional) ECS/Fargate containers

---

## Choose Your Path

| Path | Difficulty | What You'll Use | Best For |
|------|------------|-----------------|----------|
| **EC2 (Traditional)** | Intermediate | EC2, ALB, RDS | Learning infrastructure basics |
| **ECS (Containerized)** | Advanced | ECS, Fargate, ALB, RDS | Modern cloud-native apps |

**Recommendation:** Start with EC2, then try ECS after.

---

## What You'll Build

### EC2 Path (Traditional)

| File | What You Create | Points |
|------|-----------------|--------|
| `main.tf` | Provider + backend config | 5 |
| `vpc.tf` | VPC, subnets, NAT gateway | 20 |
| `alb.tf` | Application Load Balancer | 20 |
| `ec2.tf` | Web + App tier EC2 instances | 25 |
| `rds.tf` | RDS database | 15 |
| `security.tf` | Security groups for all tiers | 10 |
| `variables.tf` | Input variables | 5 |

### ECS Path (Containerized)

| File | What You Create | Points |
|------|-----------------|--------|
| `main.tf` | Provider + backend config | 5 |
| `vpc.tf` | VPC, subnets, NAT gateway | 20 |
| `alb.tf` | Application Load Balancer | 15 |
| `ecs.tf` | ECS cluster + services | 30 |
| `rds.tf` | RDS database | 15 |
| `security.tf` | Security groups for all tiers | 10 |
| `variables.tf` | Input variables | 5 |

---

## Step 0: Prerequisites

### Install Required Tools

<details>
<summary>🪟 Windows</summary>

```powershell
# Terraform
choco install terraform

# Docker Desktop (for LocalStack)
# Download from https://docker.com/products/docker-desktop

# AWS CLI
choco install awscli

# Verify
terraform --version
docker --version
aws --version
```

</details>

<details>
<summary>🍎 Mac</summary>

```bash
# Terraform
brew install terraform

# Docker Desktop
brew install --cask docker

# AWS CLI
brew install awscli

# Verify
terraform --version
docker --version
aws --version
```

</details>

<details>
<summary>🐧 Linux</summary>

```bash
# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Docker
curl -fsSL https://get.docker.com | sh

# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Verify
terraform --version
docker --version
aws --version
```

</details>

### Configure AWS CLI for LocalStack

```bash
# Set dummy credentials for LocalStack
aws configure
# Access Key ID: test
# Secret Access Key: test
# Region: us-east-1
# Output format: json
```

---

## Step 1: Understanding the Architecture

> ⏱️ **Time:** 15-20 minutes (reading)

### Network Design

```
VPC: 10.0.0.0/16
│
├── Public Subnets (Internet-facing)
│   ├── 10.0.1.0/24 (AZ-a) ─── ALB, NAT Gateway
│   └── 10.0.2.0/24 (AZ-b) ─── ALB (multi-AZ)
│
├── Private Subnets - App (No direct internet)
│   ├── 10.0.10.0/24 (AZ-a) ─── Web/App servers
│   └── 10.0.11.0/24 (AZ-b) ─── Web/App servers
│
└── Private Subnets - Data (Isolated)
    ├── 10.0.20.0/24 (AZ-a) ─── RDS Primary
    └── 10.0.21.0/24 (AZ-b) ─── RDS Standby
```

### Security Group Rules

```
Internet ──► ALB (port 80/443)
             │
             ▼
         Web Tier SG ◄── Only ALB can access (port 80)
             │
             ▼
         App Tier SG ◄── Only Web Tier can access (port 8080)
             │
             ▼
          RDS SG ◄── Only App Tier can access (port 3306/5432)
```

---

## Step 2: Set Up LocalStack

> ⏱️ **Time:** 10 minutes

Start LocalStack to simulate AWS locally:

```bash
# Start LocalStack
docker-compose up -d

# Wait for it to be ready (about 30 seconds)
docker-compose logs -f
# Look for "Ready." message, then Ctrl+C

# Verify LocalStack is running
curl http://localhost:4566/_localstack/health
```

**Expected output:**
```json
{"services": {"ec2": "running", "elbv2": "running", "rds": "running", ...}}
```

---

## EC2 Path: Traditional 3-Tier

### Step 3: Create the VPC and Networking

> ⏱️ **Time:** 30-40 minutes

Complete `vpc.tf`:

**Requirements:**
- [ ] VPC with CIDR 10.0.0.0/16
- [ ] 2 public subnets (different AZs)
- [ ] 2 private subnets for app tier
- [ ] 2 private subnets for database tier
- [ ] Internet Gateway for public subnets
- [ ] NAT Gateway for private subnet internet access
- [ ] Route tables for each subnet type

<details>
<summary>💡 Hint 1: VPC and Subnets</summary>

```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
    Tier = "public"
  }
}
```

</details>

<details>
<summary>💡 Hint 2: NAT Gateway</summary>

```hcl
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${var.project_name}-nat"
  }

  depends_on = [aws_internet_gateway.main]
}
```

</details>

<details>
<summary>🎯 Full VPC Solution</summary>

```hcl
# Data source for AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
    Tier = "public"
  }
}

# Private Subnets - App Tier
resource "aws_subnet" "private_app" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-app-${count.index + 1}"
    Tier = "app"
  }
}

# Private Subnets - Database Tier
resource "aws_subnet" "private_db" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 20)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-db-${count.index + 1}"
    Tier = "database"
  }
}

# Elastic IP for NAT
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${var.project_name}-nat"
  }

  depends_on = [aws_internet_gateway.main]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Private Route Table
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_app" {
  count          = 2
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_db" {
  count          = 2
  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private.id
}
```

</details>

---

### Step 4: Create Security Groups

> ⏱️ **Time:** 20-25 minutes

Complete `security.tf`:

**Requirements:**
- [ ] ALB security group (allow 80, 443 from internet)
- [ ] Web tier security group (allow from ALB only)
- [ ] App tier security group (allow from web tier only)
- [ ] Database security group (allow from app tier only)

<details>
<summary>💡 Hint: Security Group Chain</summary>

```hcl
# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# Web Tier - Only from ALB
resource "aws_security_group" "web" {
  name        = "${var.project_name}-web-sg"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # Only ALB!
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}
```

</details>

<details>
<summary>🎯 Full Security Groups Solution</summary>

```hcl
# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
    Tier = "public"
  }
}

# Web Tier Security Group
resource "aws_security_group" "web" {
  name        = "${var.project_name}-web-sg"
  description = "Security group for Web tier"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description = "SSH for management"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
    Tier = "web"
  }
}

# App Tier Security Group
resource "aws_security_group" "app" {
  name        = "${var.project_name}-app-sg"
  description = "Security group for App tier"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "App port from Web tier"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }

  ingress {
    description = "SSH for management"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
    Tier = "app"
  }
}

# Database Tier Security Group
resource "aws_security_group" "db" {
  name        = "${var.project_name}-db-sg"
  description = "Security group for Database tier"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MySQL from App tier"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-db-sg"
    Tier = "database"
  }
}
```

</details>

---

### Step 5: Create the Application Load Balancer

> ⏱️ **Time:** 25-30 minutes

Complete `alb.tf`:

**Requirements:**
- [ ] Application Load Balancer in public subnets
- [ ] Target group for web tier instances
- [ ] HTTP listener on port 80
- [ ] Health check configuration

<details>
<summary>💡 Hint: ALB Components</summary>

```hcl
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_lb_target_group" "web" {
  name     = "${var.project_name}-web-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    path                = "/"
    timeout             = 5
    unhealthy_threshold = 2
  }
}
```

</details>

<details>
<summary>🎯 Full ALB Solution</summary>

```hcl
# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
    Tier = "public"
  }
}

# Target Group for Web Tier
resource "aws_lb_target_group" "web" {
  name     = "${var.project_name}-web-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-web-tg"
  }
}

# HTTP Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# Attach EC2 instances to target group
resource "aws_lb_target_group_attachment" "web" {
  count            = var.web_instance_count
  target_group_arn = aws_lb_target_group.web.arn
  target_id        = aws_instance.web[count.index].id
  port             = 80
}
```

</details>

---

### Step 6: Create EC2 Instances

> ⏱️ **Time:** 30-35 minutes

Complete `ec2.tf`:

**Requirements:**
- [ ] Web tier EC2 instances (2) in private app subnets
- [ ] App tier EC2 instances (2) in private app subnets
- [ ] User data scripts to install web server / app server
- [ ] Proper security group attachments

<details>
<summary>💡 Hint: EC2 with User Data</summary>

```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "web" {
  count                  = var.web_instance_count
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.web_instance_type
  subnet_id              = aws_subnet.private_app[count.index % 2].id
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y httpd
              systemctl start httpd
              systemctl enable httpd
              echo "<h1>Web Server ${count.index + 1}</h1>" > /var/www/html/index.html
              EOF

  tags = {
    Name = "${var.project_name}-web-${count.index + 1}"
    Tier = "web"
  }
}
```

</details>

<details>
<summary>🎯 Full EC2 Solution</summary>

```hcl
# Find latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Web Tier Instances
resource "aws_instance" "web" {
  count                  = var.web_instance_count
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.web_instance_type
  subnet_id              = aws_subnet.private_app[count.index % 2].id
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y httpd
              systemctl start httpd
              systemctl enable httpd

              # Create web page
              cat <<'HTML' > /var/www/html/index.html
              <!DOCTYPE html>
              <html>
              <head><title>Web Tier</title></head>
              <body>
                <h1>Web Server ${count.index + 1}</h1>
                <p>Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>
                <p>Availability Zone: $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</p>
              </body>
              </html>
              HTML
              EOF

  tags = {
    Name = "${var.project_name}-web-${count.index + 1}"
    Tier = "web"
  }
}

# App Tier Instances
resource "aws_instance" "app" {
  count                  = var.app_instance_count
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.private_app[count.index % 2].id
  vpc_security_group_ids = [aws_security_group.app.id]

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y java-11-amazon-corretto

              # Simple app server simulation
              mkdir -p /opt/app
              cat <<'JAVA' > /opt/app/SimpleServer.java
              import com.sun.net.httpserver.*;
              import java.io.*;
              import java.net.*;
              public class SimpleServer {
                public static void main(String[] args) throws Exception {
                  HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
                  server.createContext("/health", exchange -> {
                    String response = "{\"status\":\"healthy\",\"server\":\"app-${count.index + 1}\"}";
                    exchange.sendResponseHeaders(200, response.length());
                    exchange.getResponseBody().write(response.getBytes());
                    exchange.close();
                  });
                  server.start();
                }
              }
              JAVA

              cd /opt/app && javac SimpleServer.java && java SimpleServer &
              EOF

  tags = {
    Name = "${var.project_name}-app-${count.index + 1}"
    Tier = "app"
  }
}
```

</details>

---

### Step 7: Create RDS Database

> ⏱️ **Time:** 20-25 minutes

Complete `rds.tf`:

**Requirements:**
- [ ] DB subnet group using private database subnets
- [ ] RDS MySQL instance
- [ ] Proper security group attachment
- [ ] Multi-AZ for high availability (optional)

<details>
<summary>💡 Hint: RDS Setup</summary>

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private_db[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  identifier           = "${var.project_name}-db"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = var.db_instance_class
  allocated_storage    = 20
  storage_type         = "gp2"

  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  skip_final_snapshot  = true

  tags = {
    Name = "${var.project_name}-db"
    Tier = "database"
  }
}
```

</details>

<details>
<summary>🎯 Full RDS Solution</summary>

```hcl
# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  description = "Database subnet group for ${var.project_name}"
  subnet_ids  = aws_subnet.private_db[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# RDS MySQL Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  multi_az               = var.db_multi_az
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  tags = {
    Name = "${var.project_name}-db"
    Tier = "database"
  }
}
```

</details>

---

### Step 8: Variables and Outputs

Complete `variables.tf`:

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "terraform-3tier"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "web_instance_count" {
  description = "Number of web tier instances"
  type        = number
  default     = 2
}

variable "web_instance_type" {
  description = "Web tier instance type"
  type        = string
  default     = "t2.micro"
}

variable "app_instance_count" {
  description = "Number of app tier instances"
  type        = number
  default     = 2
}

variable "app_instance_type" {
  description = "App tier instance type"
  type        = string
  default     = "t2.micro"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
  default     = "changeme123!"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = false
}

variable "allowed_ssh_cidr" {
  description = "CIDR blocks allowed for SSH"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}
```

Complete `outputs.tf`:

```hcl
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Application URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "web_instance_ids" {
  description = "Web tier instance IDs"
  value       = aws_instance.web[*].id
}

output "app_instance_ids" {
  description = "App tier instance IDs"
  value       = aws_instance.app[*].id
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}
```

---

## ECS Path: Containerized 3-Tier

> **Note:** Complete the VPC and security group steps from EC2 path first!

### Step 9: Create ECS Cluster and Services

> ⏱️ **Time:** 40-50 minutes

Complete `ecs.tf`:

**Requirements:**
- [ ] ECS cluster
- [ ] Task definitions for web and app tiers
- [ ] ECS services with Fargate launch type
- [ ] Service discovery (optional)

<details>
<summary>💡 Hint: ECS Fargate Setup</summary>

```hcl
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${var.project_name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = "nginx:latest"
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]
    }
  ])
}
```

</details>

<details>
<summary>🎯 Full ECS Solution</summary>

```hcl
# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# ECS Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Web Tier Task Definition
resource "aws_ecs_task_definition" "web" {
  family                   = "${var.project_name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = "nginx:latest"
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${var.project_name}-web"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-web-task"
    Tier = "web"
  }
}

# App Tier Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = "node:18-alpine"
      essential = true
      command   = ["node", "-e", "require('http').createServer((req,res)=>{res.end(JSON.stringify({status:'healthy'}))}).listen(8080)"]
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DB_HOST"
          value = aws_db_instance.main.endpoint
        },
        {
          name  = "DB_NAME"
          value = var.db_name
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${var.project_name}-app"
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-app-task"
    Tier = "app"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${var.project_name}-web"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}-app"
  retention_in_days = 7
}

# Web Tier ECS Service
resource "aws_ecs_service" "web" {
  name            = "${var.project_name}-web-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.web_instance_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_app[*].id
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web_ecs.arn
    container_name   = "web"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${var.project_name}-web-service"
    Tier = "web"
  }
}

# App Tier ECS Service
resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-app-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_instance_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_app[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  tags = {
    Name = "${var.project_name}-app-service"
    Tier = "app"
  }
}

# Target Group for ECS (different health check)
resource "aws_lb_target_group" "web_ecs" {
  name        = "${var.project_name}-web-ecs-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"  # Required for Fargate

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-web-ecs-tg"
  }
}
```

</details>

---

## Testing Locally with LocalStack

### Run Terraform

```bash
# 1. Start LocalStack
docker-compose up -d

# 2. Copy LocalStack provider override
cp provider_override.tf.example provider_override.tf

# 3. Initialize Terraform
terraform init

# 4. Preview resources
terraform plan

# 5. Create resources
terraform apply
# Type "yes" to confirm
```

**Expected output:**
```
Apply complete! Resources: 25 added, 0 changed, 0 destroyed.

Outputs:

alb_dns_name = "terraform-3tier-alb-123456789.us-east-1.elb.localhost.localstack.cloud"
alb_url = "http://terraform-3tier-alb-123456789.us-east-1.elb.localhost.localstack.cloud"
db_endpoint = "terraform-3tier-db.xyz123.us-east-1.rds.localhost.localstack.cloud:3306"
vpc_id = "vpc-abc123"
web_instance_ids = ["i-web1", "i-web2"]
```

### Verify with CLI

```bash
# List all VPCs
aws --endpoint-url=http://localhost:4566 ec2 describe-vpcs \
  --query "Vpcs[*].{VpcId:VpcId,CIDR:CidrBlock,Name:Tags[?Key=='Name']|[0].Value}" \
  --output table

# List all subnets
aws --endpoint-url=http://localhost:4566 ec2 describe-subnets \
  --query "Subnets[*].{SubnetId:SubnetId,CIDR:CidrBlock,AZ:AvailabilityZone,Tier:Tags[?Key=='Tier']|[0].Value}" \
  --output table

# List EC2 instances
aws --endpoint-url=http://localhost:4566 ec2 describe-instances \
  --query "Reservations[*].Instances[*].{InstanceId:InstanceId,Type:InstanceType,Tier:Tags[?Key=='Tier']|[0].Value,State:State.Name}" \
  --output table

# List Load Balancers
aws --endpoint-url=http://localhost:4566 elbv2 describe-load-balancers \
  --query "LoadBalancers[*].{Name:LoadBalancerName,DNS:DNSName,Type:Type}" \
  --output table

# List RDS instances
aws --endpoint-url=http://localhost:4566 rds describe-db-instances \
  --query "DBInstances[*].{Identifier:DBInstanceIdentifier,Engine:Engine,Status:DBInstanceStatus}" \
  --output table
```

### Visual Dashboard

```bash
python dashboard.py
```

Opens a web page at http://localhost:8080 showing:
- Architecture diagram with all 3 tiers
- VPC and subnet visualization
- ALB with target group status
- EC2/ECS instances per tier
- RDS database status

---

## Deploying to Real AWS

### Prerequisites

1. **AWS Account with billing enabled**
2. **IAM User with these permissions:**
   - `AmazonVPCFullAccess`
   - `AmazonEC2FullAccess`
   - `ElasticLoadBalancingFullAccess`
   - `AmazonRDSFullAccess`
   - `AmazonECS_FullAccess` (for ECS path)

3. **Configure AWS CLI:**
   ```bash
   aws configure
   # Enter your real Access Key ID
   # Enter your real Secret Access Key
   # Region: us-east-1
   ```

### Deploy

```bash
# 1. Remove LocalStack override
rm provider_override.tf

# 2. Reinitialize
terraform init

# 3. Update variables for production
# Edit terraform.tfvars or use -var flags

# 4. Plan and Apply
terraform plan
terraform apply

# ⚠️ This creates REAL resources that cost money!
```

### Verify in AWS Console

1. **VPC** - Check VPC dashboard for new VPC and subnets
2. **EC2** - Check running instances in each tier
3. **RDS** - Check database instance
4. **Load Balancer** - Get the ALB URL and test

### Access Your Application

```bash
# Get the ALB URL
terraform output alb_url

# Test the application
curl $(terraform output -raw alb_url)
```

### ⚠️ IMPORTANT: Clean Up!

```bash
# Destroy all resources when done
terraform destroy
# Type "yes" to confirm

# Verify cleanup
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=terraform-3tier"
# Should return empty
```

### Cost Estimate

| Resource | Free Tier | After Free Tier |
|----------|-----------|-----------------|
| t2.micro EC2 (x4) | 750 hrs/month free | ~$34/month |
| ALB | Not free tier | ~$16/month |
| NAT Gateway | Not free tier | ~$32/month |
| RDS db.t3.micro | 750 hrs free | ~$12/month |
| Data transfer | 100GB free | $0.09/GB |

**Estimated monthly cost: ~$95/month** (after free tier)

**Tip:** Run `terraform destroy` immediately after testing!

---

## Run the Progress Checker

```bash
python run.py
```

**Expected output when complete (EC2 path):**
```
============================================================
  🏗️  Terraform 3-Tier Architecture Challenge
============================================================

  Path: EC2 (Traditional)

  ✅ Provider Config (5/5 points)
  ✅ VPC & Networking (20/20 points)
  ✅ Security Groups (10/10 points)
  ✅ Application Load Balancer (20/20 points)
  ✅ EC2 Instances (25/25 points)
  ✅ RDS Database (15/15 points)
  ✅ Variables (5/5 points)

============================================================
  🎯 Total Score: 100/100
  🎉 CHALLENGE COMPLETE!
============================================================
```

---

## What You Learned

- ✅ **3-tier architecture** - Separation of concerns
- ✅ **VPC design** - Public/private subnets, NAT gateway
- ✅ **Security groups** - Layered security
- ✅ **Load balancing** - ALB with target groups
- ✅ **Database tier** - RDS in private subnet
- ✅ **High availability** - Multi-AZ deployment
- ✅ **(Optional) Containers** - ECS/Fargate deployment

---

## Interview Talking Points

> "I built a 3-tier architecture on AWS using Terraform, including a VPC with public and private subnets, an Application Load Balancer for traffic distribution, EC2 instances for web and app tiers, and RDS MySQL for the database tier. Security groups were configured in a chain pattern where each tier only accepts traffic from the tier above it. I also implemented NAT Gateway for private subnet internet access and tested locally using LocalStack before deploying to AWS."

---

## Next Steps

- **2.4 CI/CD Pipeline** - Automate deployments with GitHub Actions
- **2.5 Monitoring Stack** - Add CloudWatch, alerts, and dashboards

Good luck! 🏗️
