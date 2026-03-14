# Kiro Cost Hunter - RL-Powered AWS Cost Optimizer
> **Autonomous RL agent that hunts cloud waste 24/7 — and brings every finding directly into your IDE.**

![](hero-banner.png)

---

## 🏢 App Category

**Workplace Efficiency**

---

## 💡 My Vision

I remember staring at an AWS bill for $400 — for EC2 instances that had been stopped for two months. Nobody noticed. Nobody had a tool that told them. I clicked through dozens of instances manually to find the idle ones. One region. One service. One month.

**That pain built this.**

Kiro Cost Hunter is an autonomous reinforcement learning agent that hunts cloud waste 24/7 — and brings every finding directly into your IDE. No dashboards to open. No context switching. No forgotten bills.

Three ideas that exist separately, combined for the first time:

- 🤖 **RL Agent (PPO)** — learns which resources are genuinely wasteful vs legitimately idle, getting smarter with every decision
- ✋ **Human-in-the-Loop** — every recommendation needs your approve or reject, making the AI trustworthy enough to act on in production
- 🔌 **Native Kiro MCP** — the entire workflow lives inside Kiro. One command: *"Show me my cost dashboard."* Done.

> **Deployed live on AWS account `359289023438` — it found $25.50/month in waste on its very first day.**

---

## 🔥 Why This Matters

Most engineering teams check cloud costs once a month. By then, weeks of waste have already compounded. Kiro Cost Hunter inverts this — **the AI hunts, you approve, the system learns.**

| Scale of Problem | Current Reality | Cost Hunter | Impact |
|---|---|---|---|
| $147B wasted globally (Gartner) | $147B annually | Automated hourly detection | ↓ 40% |
| 32% of cloud spend is waste | Ignored till crisis | PPO agent scores every resource | ↓ 32% |
| Days to weeks to find manually | Manual Excel analysis | Real results in <60 seconds | 60× faster |
| Must leave IDE to check costs | Constant context switching | Native Kiro MCP integration | Zero friction |

Every approve/reject decision makes the model smarter. The system compounds in accuracy over time. **Month 2 is smarter than Month 1.**

---

## 🛠️ How I Built This

### Architecture

![Architecture](architecture.png)
*End-to-end flow: Hourly scan → PPO scoring → Bedrock explanation → human decision → feedback loop*

### Tech Stack

| Component | Details |
|---|---|
| **RL Agent** | PPO via stable-baselines3 · 51,200 timesteps · reward 47.5→105 (+121%) · converged at 12K steps |
| **Scanner Lambda** | Python 3.11 · reads EC2 state + CloudWatch CPU every hour via EventBridge · writes to DynamoDB |
| **Action Executor** | Amazon Bedrock (Claude Haiku 4.5) · plain-English explanations per recommendation |
| **RL Trainer** | Fine-tunes PPO on human feedback · versioned backups to S3 |
| **Feedback Collector** | Captures approve/reject · sends +1/−1 reward signals · triggers retraining |
| **Kiro MCP Server** | 5 tools: `get_cost_dashboard` · `approve_action` · `reject_action` · `explain_recommendation` · `adjust_priority` |
| **Dashboard** | HTML/CSS/JS · hosted on S3 · approve/reject cards · RL training curve · AI chat |
| **Security** | CloudTrail · AES-256 S3 · DynamoDB PITR 35 days · $5/mo budget alarm · IAM least-privilege |

### Why PPO Over DQN?

AWS cost patterns are non-stationary — costs shift as infrastructure evolves. DQN diverged in my experiments after ~30K steps when cost volatility increased. PPO's clipped surrogate objective prevents catastrophically large policy updates — significantly more stable for sparse, delayed reward signals like cloud billing data.

**Reward function:**

```
R = (cost_saved × 0.6) − (risk × 0.3) − (disruption × 0.1)
```

Human approve/reject → `+1` or `−1` reward → feeds next retraining cycle. **Human judgement becomes model improvement.**

### Key Milestones

1. **Infrastructure** — CDK stack live on `us-east-1`: 4 Lambda functions, 3 DynamoDB tables, S3, CloudTrail, SNS, EventBridge
2. **RL Training** — 51,200 timesteps, reward 47.5→105, converged at 12K steps
3. **Live AWS Integration** — Scanner hit real EC2 instances: `i-058a356c` (0.74% CPU), `i-0b8b76a8` (1.66%), `i-02890771` (2.71%)
4. **Bedrock Explanations** — Claude Haiku 4.5 generating plain-English reasoning per recommendation
5. **Kiro MCP Live** — *"Show me my cost dashboard"* in Kiro IDE returns real scan results
6. **Dashboard Deployed** — S3-hosted · approve/reject workflow · AI chat · 15+ question types

---

## 🎬 Demo

### 📉 The Cost Reduction in 4 Weeks

![](<Screenshot 2026-03-12 135015.png>)
*$487 → $292 in 28 days. 40% reduction. Zero manual work after setup.*

### 🤖 The Agent Actually Learning

![](<Screenshot 2026-03-12 135824.png>)
*Watch the reward climb from 47.5 → 105 — converging at just 12,000 steps out of 51,200. This isn't theory. The agent learned. The amber line is proof.*

### 📸 Live Dashboard Screenshots

**Overview — waste detected, recommendations ready**

![Dashboard Overview](dashboard-overview.png)

**Instances Tab — real account, real instance IDs, real CPU data**

![Instances Tab](dashboard-instances.png)

**RL Agent Tab — training curve + system pipeline**

![RL Agent Tab](dashboard-rlagent.png)

**Kiro MCP — live results inside the IDE**

![](<Screenshot 2026-03-12 135953.png>)

### 90-second walkthrough

1. Open dashboard → alert banner appears immediately
2. Click **"Run Scan"** → spinner animates, timestamp updates
3. Click **"Approve"** → savings tracker updates to $8.50, agent gets +1 reward
4. Ask AI chat *"How much will I save?"* → instant answer
5. Switch to RL Agent tab → the curve proves the AI learned

---

## 🧠 What I Learned

**01 — Human-in-the-loop is not a fallback. It IS the feature.**

I built this to be autonomous. The more I built, the more I understood: in cost optimisation — where one wrong termination can take down production — human approval isn't a weakness of the AI. It's what makes the AI trustworthy enough to deploy at all. And every approve/reject becomes training data. User trust literally becomes model improvement.

**02 — PPO's stability advantage is real and measurable.**

DQN diverged after ~30K steps under cost volatility. PPO held stable across all 51K steps and converged 75% faster than expected. Theory became proof.

**03 — Lambda + ML packaging is genuinely hard.**

Three problems hit at once: Windows/Linux binary mismatch, PyTorch exceeding Lambda's 250MB limit, 8+ second cold starts. Solution: Lambda Layers with `--platform manylinux2014_x86_64`. A lesson only learned through pain.

**04 — Kiro MCP is the correct model for developer tooling.**

Traditional cost tools: leave IDE → open browser → log in → context switch back. With Kiro MCP: one command, never leave your editor. The adoption barrier drops from *"when I have time"* to *"right now."*

**05 — Real data tells a humbling story.**

Synthetic training looked great. The moment the scanner hit real EC2 instances, observation space dimensions didn't match model expectations. Real ML deployment needs explicit data contracts between collection and training. You only learn this when the two meet in production for the first time.

> ⭐ **Biggest Architectural Insight:** Making DynamoDB the source of truth for the feedback loop — not passing signals directly between Lambdas — was the single most important decision. Scanner, trainer, and feedback collector are all independently retryable and replaceable. The pattern scales from 3 instances to 10,000 with zero architectural changes.

---

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
npm install -g aws-cdk
```

2. Train baseline agent locally:
```bash
python scripts/train_baseline.py
```

3. Configure AWS credentials:
```bash
aws configure
```

4. Deploy infrastructure:
```bash
cd cdk
cdk bootstrap  # First time only
cdk deploy
```

5. Upload trained model:
```bash
aws s3 cp models/ppo_agent_baseline.zip s3://cost-hunter-models/ppo_agent.zip
```

6. Open Kiro and start hunting:
   - *"Show me my cost dashboard"*
   - *"What are the top wasteful resources?"*
   - *"Approve action [action_id]"*
   - *"Prioritize cost savings"*

---

## 🔴 Live Demo
👉 **[Open Live Dashboard](http://cost-hunter-models-359289023438.s3-website-us-east-1.amazonaws.com/dashboard.html)**

## 🎬 Demo Video
👉 **[Watch 2-Min Demo](https://www.youtube.com/watch?v=s7dKyvWoJeE)**

## Safety Guardrails

- Dry-run mode by default — nothing executes without approval
- Actions >$100/month always require human sign-off
- 7-day monitoring after each action with automatic rollback if issues detected
- Human override always available
- Infrastructure cost alarm at $5/month

---

*Built for the Kiro AI Hackathon 2026*
*AWS Account: `359289023438` · Region: `us-east-1` · Stack: `CostHunterStack`*
*PPO (stable-baselines3) · Amazon Bedrock · AWS CDK · Kiro MCP · Python 3.11*

`#aideas-2025` `#workplace-efficiency` `#APJC`