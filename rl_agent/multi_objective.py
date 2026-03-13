class MultiObjectiveReward:
    """Combine cost, performance, and availability into a single reward signal."""

    PRESETS = {
        'cost':        {'cost': 0.8, 'performance': 0.15, 'availability': 0.05},
        'balanced':    {'cost': 0.6, 'performance': 0.30, 'availability': 0.10},
        'performance': {'cost': 0.3, 'performance': 0.60, 'availability': 0.10},
    }

    def __init__(self, preset='balanced'):
        self.weights = self.PRESETS[preset]

    def compute(self, cost_saving, performance_impact, availability_impact):
        """All inputs in [-1, 1]. Returns combined scalar reward."""
        return (
            self.weights['cost']          * cost_saving +
            self.weights['performance']   * performance_impact +
            self.weights['availability']  * availability_impact
        )

    def set_preset(self, preset):
        if preset not in self.PRESETS:
            raise ValueError(f"Unknown preset '{preset}'. Choose: {list(self.PRESETS)}")
        self.weights = self.PRESETS[preset]
