import numpy as np
import gymnasium as gym
from gymnasium import spaces


class AWSCostEnvironment(gym.Env):
    """Gymnasium environment simulating AWS resource cost optimisation."""

    metadata = {'render_modes': []}
    ACTION_NAMES = ['do_nothing', 'downsize', 'spot_instance', 'enable_autoscaling']

    def __init__(self, n_resources=10):
        super().__init__()
        self.n_resources = n_resources
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(n_resources * 5,), dtype=np.float32
        )
        self.action_space = spaces.MultiDiscrete([4] * n_resources)
        self.state = None
        self.step_count = 0
        self.max_steps = 30

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.state = self._random_state()
        self.step_count = 0
        return self.state.flatten(), {}

    def step(self, actions):
        rewards = [self._apply_action(i, a) for i, a in enumerate(actions)]
        total_reward = float(np.mean(rewards))
        self.step_count += 1
        terminated = self.step_count >= self.max_steps
        return self.state.flatten(), total_reward, terminated, False, {}

    def _apply_action(self, idx, action):
        cpu, mem, cost, uptime, is_spot = self.state[idx]
        if action == 0:
            return 0.0
        elif action == 1:  # downsize
            if cpu < 0.2:
                self.state[idx][2] *= 0.6
                self.state[idx][0] = min(cpu * 1.3, 1.0)
                return 0.6
            return -0.3
        elif action == 2:  # spot
            if uptime > 0.5:
                self.state[idx][2] *= 0.3
                return 0.8
            return 0.1
        elif action == 3:  # autoscaling
            self.state[idx][2] *= 0.85
            return 0.4
        return 0.0

    def _random_state(self):
        state = np.random.rand(self.n_resources, 5).astype(np.float32)
        for i in range(self.n_resources // 3):
            state[i][0] = np.random.uniform(0.01, 0.08)
            state[i][2] = np.random.uniform(0.5, 1.0)
        return state
