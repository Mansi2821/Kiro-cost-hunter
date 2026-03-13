import boto3
import json
import os
import zipfile
import numpy as np
from datetime import datetime
from boto3.dynamodb.conditions import Attr

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET = 'cost-hunter-models-359289023438'
MODEL_KEY = 'ppo_agent.zip'

def lambda_handler(event, context):
    """Retrain PPO agent based on human feedback stored in DynamoDB"""

    print("Starting RL retraining...")

    # ── STEP 1: Fetch feedback from DynamoDB ──
    table = dynamodb.Table('CostHunterActions')
    response = table.scan()
    all_items = response.get('Items', [])

    # Filter items that have a human_decision
    feedback_items = [i for i in all_items if 'human_decision' in i]

    print(f"Total items: {len(all_items)}, With feedback: {len(feedback_items)}")

    if len(feedback_items) < 1:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Not enough feedback yet — need at least 1 human decision',
                'feedback_count': len(feedback_items),
                'total_items': len(all_items)
            })
        }

    # ── STEP 2: Download existing model from S3 ──
    model_path = '/tmp/ppo_agent'
    zip_path = '/tmp/ppo_agent.zip'

    print(f"Downloading model from s3://{BUCKET}/{MODEL_KEY}...")
    s3_client.download_file(BUCKET, MODEL_KEY, zip_path)

    # Extract zip
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall('/tmp/ppo_extracted/')
    print("Model downloaded and extracted.")

    # ── STEP 3: Load model using stable-baselines3 ──
    try:
        from stable_baselines3 import PPO
        import gymnasium as gym
        from gymnasium import spaces

        # Define the same environment the model was trained on
        class CostEnv(gym.Env):
            def __init__(self):
                super().__init__()
                # Observation: [cpu_util, monthly_cost, is_stopped, uptime_hours, instance_type]
                self.observation_space = spaces.Box(
                    low=np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
                    high=np.array([100.0, 1000.0, 1.0, 8760.0, 10.0]),
                    dtype=np.float32
                )
                # Actions: 0=keep, 1=terminate, 2=downsize, 3=spot
                self.action_space = spaces.Discrete(4)
                self.current_step = 0
                self.feedback_data = []

            def set_feedback(self, feedback):
                self.feedback_data = feedback

            def reset(self, seed=None):
                self.current_step = 0
                obs = self._get_obs()
                return obs, {}

            def _get_obs(self):
                if self.feedback_data and self.current_step < len(self.feedback_data):
                    item = self.feedback_data[self.current_step % len(self.feedback_data)]
                    return np.array([
                        float(item.get('cpu_util', 1.0)),
                        float(item.get('monthly_cost', 8.50)),
                        1.0 if item.get('state', 'stopped') == 'stopped' else 0.0,
                        float(item.get('uptime_hours', 720.0)),
                        0.0  # t3.micro = 0
                    ], dtype=np.float32)
                return np.array([1.0, 8.50, 1.0, 720.0, 0.0], dtype=np.float32)

            def step(self, action):
                reward = 0.0
                if self.feedback_data and self.current_step < len(self.feedback_data):
                    item = self.feedback_data[self.current_step % len(self.feedback_data)]
                    decision = item.get('human_decision', 'approved')
                    stored_reward = float(item.get('reward', 1))

                    # Map action to recommendation
                    action_map = {0: 'keep', 1: 'terminate_if_unused', 2: 'downsize', 3: 'switch_to_spot_or_downsize'}
                    chosen = action_map.get(action, 'keep')
                    recommended = item.get('action', 'terminate_if_unused')

                    if decision == 'approved' and chosen == recommended:
                        reward = stored_reward * 10.0   # strong positive
                    elif decision == 'approved':
                        reward = stored_reward * 5.0    # mild positive
                    elif decision == 'rejected':
                        reward = -50.0                  # strong negative

                self.current_step += 1
                done = self.current_step >= max(len(self.feedback_data), 1) * 3
                obs = self._get_obs()
                return obs, reward, done, False, {}

        # Load model
        model_file = '/tmp/ppo_extracted/ppo_agent_baseline'
        if not os.path.exists(model_file + '.zip') and not os.path.exists(model_file):
            # Try finding any .zip in extracted folder
            for root, dirs, files in os.walk('/tmp/ppo_extracted/'):
                for f in files:
                    print(f"Found extracted file: {os.path.join(root, f)}")

        env = CostEnv()
        env.set_feedback(feedback_items)

        # Load existing model
        try:
            model = PPO.load(model_file, env=env)
            print("Loaded existing model for fine-tuning.")
        except Exception as e:
            print(f"Could not load existing model ({e}), creating fresh model.")
            model = PPO('MlpPolicy', env, verbose=0,
                       learning_rate=0.0003, n_steps=64, batch_size=32)

        # ── STEP 4: Fine-tune with feedback ──
        timesteps = max(len(feedback_items) * 500, 2000)
        print(f"Fine-tuning for {timesteps} timesteps on {len(feedback_items)} feedback items...")
        model.learn(total_timesteps=timesteps, reset_num_timesteps=False)
        print("Fine-tuning complete.")

        # Save updated model
        updated_path = '/tmp/ppo_agent_updated'
        model.save(updated_path)

        # Upload back to S3 with timestamp backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Upload as new versioned backup
        s3_client.upload_file(
            f'{updated_path}.zip',
            BUCKET,
            f'models/ppo_agent_{timestamp}.zip'
        )
        # Overwrite the main model
        s3_client.upload_file(
            f'{updated_path}.zip',
            BUCKET,
            MODEL_KEY
        )
        print(f"Model saved to S3: models/ppo_agent_{timestamp}.zip")

        # ── STEP 5: Log training metrics ──
        approved = sum(1 for i in feedback_items if i.get('human_decision') == 'approved')
        rejected = sum(1 for i in feedback_items if i.get('human_decision') == 'rejected')
        avg_reward = sum(float(i.get('reward', 1)) for i in feedback_items) / len(feedback_items)

        metrics = {
            'training_date': datetime.now().isoformat(),
            'feedback_items_used': len(feedback_items),
            'approved_count': approved,
            'rejected_count': rejected,
            'avg_reward': round(avg_reward, 3),
            'timesteps': timesteps,
            'model_version': timestamp,
            'status': 'success'
        }

        s3_client.put_object(
            Bucket=BUCKET,
            Key=f'training_logs/{timestamp}.json',
            Body=json.dumps(metrics, indent=2)
        )

        print(f"Metrics logged. Training complete!")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Model retrained successfully',
                'feedback_used': len(feedback_items),
                'approved': approved,
                'rejected': rejected,
                'timesteps': timesteps,
                'model_version': timestamp,
                'model_saved_to': f's3://{BUCKET}/models/ppo_agent_{timestamp}.zip'
            })
        }

    except ImportError as e:
        # stable-baselines3 not in Lambda — do lightweight reward-based scoring instead
        print(f"stable-baselines3 not available ({e}). Running lightweight retraining.")
        return _lightweight_retrain(feedback_items)

    except Exception as e:
        print(f"Error during retraining: {e}")
        return _lightweight_retrain(feedback_items)


def _lightweight_retrain(feedback_items):
    """
    Fallback: compute updated Q-values from feedback without ML libraries.
    Stores updated policy weights as JSON in S3.
    """
    print("Running lightweight Q-value update...")

    # Simple Q-table update based on human feedback
    # Actions: terminate=0, downsize=1, spot=2, keep=3
    action_map = {
        'terminate_if_unused': 0,
        'switch_to_spot_or_downsize': 1,
        'downsize': 2,
        'keep': 3
    }

    # Initialize Q-values (or load existing)
    q_values = {a: 0.0 for a in action_map.keys()}
    action_counts = {a: 0 for a in action_map.keys()}

    # Load existing Q-values from S3 if available
    try:
        obj = s3_client.get_object(Bucket=BUCKET, Key='models/q_values.json')
        existing = json.loads(obj['Body'].read())
        q_values = existing.get('q_values', q_values)
        action_counts = existing.get('action_counts', action_counts)
        print("Loaded existing Q-values.")
    except:
        print("No existing Q-values found, starting fresh.")

    # Update Q-values from feedback (incremental mean)
    for item in feedback_items:
        action = item.get('action', 'terminate_if_unused')
        decision = item.get('human_decision', 'approved')
        reward = float(item.get('reward', 1))

        if action not in q_values:
            q_values[action] = 0.0
            action_counts[action] = 0

        # Apply reward: approved=positive, rejected=negative
        actual_reward = reward if decision == 'approved' else -50.0
        n = action_counts[action] + 1
        q_values[action] = ((q_values[action] * action_counts[action]) + actual_reward) / n
        action_counts[action] = n

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    policy = {
        'updated_at': datetime.now().isoformat(),
        'model_version': timestamp,
        'feedback_items': len(feedback_items),
        'q_values': q_values,
        'action_counts': action_counts,
        'best_action': max(q_values, key=q_values.get),
        'policy_type': 'lightweight_q_table'
    }

    # Save updated policy
    s3_client.put_object(
        Bucket=BUCKET,
        Key='models/q_values.json',
        Body=json.dumps(policy, indent=2)
    )
    s3_client.put_object(
        Bucket=BUCKET,
        Key=f'training_logs/{timestamp}.json',
        Body=json.dumps(policy, indent=2)
    )

    print(f"Lightweight policy updated. Best action: {policy['best_action']}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Policy updated via lightweight Q-learning',
            'feedback_used': len(feedback_items),
            'q_values': q_values,
            'best_action': policy['best_action'],
            'model_version': timestamp,
            'saved_to': f's3://{BUCKET}/models/q_values.json'
        })
    }
