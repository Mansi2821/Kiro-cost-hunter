#!/usr/bin/env python3
"""Train the baseline PPO agent locally (takes 10-15 minutes)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rl_agent.agent import CostHunterAgent

os.makedirs('models', exist_ok=True)
print("Training baseline PPO agent for 50,000 timesteps...")
agent = CostHunterAgent(n_resources=10)
agent.train(timesteps=50_000)
agent.save('models/ppo_agent_baseline')
print("Done! Model saved to models/ppo_agent_baseline.zip")
