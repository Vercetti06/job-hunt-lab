# ============================================================
# YOUR BACKGROUND — Edit this file to keep it current.
# IMPORTANT: Confirm metric numbers (marked below) before
# relying on them in real applications.
# ============================================================

BACKGROUND = """
CANDIDATE: Yaswanth
CURRENT ROLE: DevOps Engineer
CURRENT COMPANY: Bosch Global Software Technologies (GCC)
EXPERIENCE: 3.5 years
LOCATIONS: Coimbatore (open to Bangalore, Hyderabad, Pune, Chennai)
NOTICE PERIOD: 30 days via buyout

CURRENT PLATFORM:
ESS Portal — Global SaaS HR platform running on AWS EKS, serving enterprise
users across multiple regions. Responsible for infrastructure, CI/CD, 
monitoring, and reliability of this platform end-to-end.

TECHNICAL SKILLS:
  Cloud:
    - AWS: EKS, ECR, RDS, S3, VPC, IAM, CloudWatch, CloudFront,
      ALB, Route53, Secrets Manager, Lambda
    - Designed and implemented VPC architecture: public/private subnets,
      IGW, NAT Gateway, security group chaining

  Infrastructure as Code:
    - Terraform: VPC architecture, S3 remote state backend, native locking
      (use_lockfile), security group chaining, modular structure

  Container Orchestration:
    - Kubernetes: EKS (production), minikube (development)
    - Kubernetes objects: Deployments, Services, Ingress, HPA, Secrets,
      PVCs, ConfigMaps, Probes (liveness, readiness, startup)
    - ArgoCD: GitOps with selfHeal and prune enabled

  CI/CD:
    - Jenkins: EC2-hosted, production-grade declarative pipelines
    - Pipeline stages: Checkout → Docker Build → SonarCloud SAST →
      Quality Gate → Trivy FS Scan → Unit Tests → Trivy Image Scan →
      Push to ECR → Update Manifest → Slack Notifications
    - GitHub Actions

  Security:
    - Trivy: filesystem scanning and container image scanning
    - SonarCloud: SAST (Static Application Security Testing)
    - IAM least privilege, AWS Secrets Manager

  Containers:
    - Docker: multi-stage builds, ECR registry management
    - Image optimisation and size reduction practices

  Monitoring:
    - Prometheus, Grafana, CloudWatch

  Scripting:
    - Bash/Shell scripting
    - Automation scripts: health checks, disk monitoring, log parsing,
      backup automation

  Version Control:
    - Git, GitHub, GitOps (monorepo pattern)

KEY ACHIEVEMENTS:
  # ⚠️  CONFIRM THESE NUMBERS before using in real applications
  - Reduced Mean Time to Detect (MTTD) by 35% by implementing
    Prometheus and Grafana monitoring stack with custom alerting
  - Reduced Mean Time to Recover (MTTR) by 30% through automated
    alerting workflows and runbook standardisation
  - Implemented GitOps deployment model using ArgoCD, reducing
    deployment failures through automated sync and drift correction
  - Built production-grade Jenkins CI/CD pipeline integrating SAST,
    container image scanning, and quality gates

TARGET ROLES: Senior DevOps Engineer, Senior SRE, Site Reliability Engineer,
              Platform Engineer, Cloud Engineer

TARGET COMPANIES: GE Vernova, JP Morgan, Goldman Sachs, Walmart Global Tech,
                  FIS Global, Optum, Deutsche Bank, ANZ, Amgen, Sanofi, Roku
"""
