import os
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from .environment import AWSCostEnvironment


class CostHunterAgent:
    def __init__(self, model_path=None, n_resources=10):
        self.n_resources = n_resources
        env = make_vec_env(lambda: AWSCostEnvironment(n_resources), n_envs=4)

        if model_path and os.path.exists(model_path):
            self.model = PPO.load(model_path, env=env)
            print(f"Loaded model from {model_path}")
        else:
            self.model = PPO(
                'MlpPolicy', env,
                learning_rate=3e-4, n_steps=2048,
                batch_size=64, n_epochs=10,
                gamma=0.99, verbose=1
            )
            print("Created new PPO model")

    def train(self, timesteps=50_000):
        self.model.learn(total_timesteps=timesteps)

    def save(self, path):
        self.model.save(path)
        print(f"Model saved to {path}")

    def predict(self, observation):
        action, _ = self.model.predict(observation, deterministic=True)
        return action
