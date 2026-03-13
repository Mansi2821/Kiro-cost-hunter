#!/usr/bin/env python3
"""
Local demo of Cost Hunter — no AWS credentials required.
Uses synthetic data to simulate the full system.
"""
import json, random, uuid

INSTANCE_TYPES = ['t3.micro','t3.small','t3.medium','t3.large','m5.large','m5.xlarge']
SAVINGS_MAP = {'t3.micro':3.5,'t3.small':7.5,'t3.medium':15,'t3.large':30,'m5.large':35,'m5.xlarge':70}

def generate_resources(n=8):
    resources = []
    for i in range(n):
        itype = random.choice(INSTANCE_TYPES)
        cpu = random.uniform(1, 8) if i < n // 2 else random.uniform(40, 90)
        resources.append({
            'resource_id': f'i-{uuid.uuid4().hex[:8]}',
            'resource_type': 'EC2', 'instance_type': itype,
            'avg_cpu': round(cpu, 1),
            'estimated_savings': SAVINGS_MAP.get(itype, 10) * 0.5,
            'status': 'pending_review' if cpu < 15 else 'ok',
            'action_type': 'downsize',
            'risk_level': 'low' if cpu < 5 else 'medium',
        })
    for _ in range(2):
        size = random.choice([50, 100, 200])
        resources.append({
            'resource_id': f'vol-{uuid.uuid4().hex[:8]}',
            'resource_type': 'EBS', 'size_gb': size,
            'estimated_savings': round(size * 0.10, 2),
            'status': 'pending_review', 'action_type': 'delete_unused', 'risk_level': 'low',
        })
    return resources

def print_dashboard(resources):
    pending = [r for r in resources if r['status'] == 'pending_review']
    total = sum(r['estimated_savings'] for r in pending)
    print("\n" + "="*58)
    print("        COST HUNTER — LOCAL DEMO DASHBOARD")
    print("="*58)
    print(f"  Resources scanned       : {len(resources)}")
    print(f"  Pending recommendations : {len(pending)}")
    print(f"  Potential monthly saving: ${total:.2f}")
    print("="*58)
    print(f"\n  {'ID':<20} {'Type':<6} {'Action':<15} {'$/mo':>8}  {'Risk'}")
    print("  " + "-"*55)
    for r in pending:
        print(f"  {r['resource_id']:<20} {r['resource_type']:<6} {r['action_type']:<15} ${r['estimated_savings']:>6.2f}  {r['risk_level']}")
    print()

def main():
    print("\nStarting Cost Hunter local demo...")
    resources = generate_resources(10)
    print_dashboard(resources)
    pending = [r for r in resources if r['status'] == 'pending_review']
    if pending:
        r = pending[0]
        print(f"  Auto-approving: {r['resource_id']} ({r['action_type']})")
        print(f"  [DRY RUN] Would save ${r['estimated_savings']:.2f}/month")
    print("\nDemo complete. See DEPLOYMENT_GUIDE.md to deploy for real.\n")

if __name__ == '__main__':
    main()
