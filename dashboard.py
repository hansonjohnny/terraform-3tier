#!/usr/bin/env python3
"""
Terraform 3-Tier Architecture Dashboard
========================================
A visual web dashboard to see your 3-tier AWS infrastructure.

Usage:
    python dashboard.py              # Open dashboard (LocalStack)
    python dashboard.py --aws        # Use real AWS credentials
    python dashboard.py --no-browser # Just start server
"""

import json
import subprocess
import sys
import os
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time
import argparse

# For Windows compatibility
if sys.platform == 'win32':
    os.system('color')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LOCALSTACK_ENDPOINT = "http://localhost:4566"
USE_AWS = False

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def run_aws_command(service, action, extra_args=None):
    """Run an AWS CLI command."""
    cmd = ["aws"]
    if not USE_AWS:
        cmd.extend(["--endpoint-url", LOCALSTACK_ENDPOINT])
    cmd.extend([service, action, "--output", "json"])
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout else {}
        return None
    except Exception:
        return None


def get_vpcs():
    """Get VPCs (filter out default)."""
    data = run_aws_command("ec2", "describe-vpcs")
    if not data:
        return []

    vpcs = []
    for vpc in data.get("Vpcs", []):
        if vpc.get("IsDefault", False):
            continue
        name = ""
        for tag in vpc.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
        if name:
            vpcs.append({
                "id": vpc["VpcId"],
                "cidr": vpc["CidrBlock"],
                "name": name
            })
    return vpcs


def get_subnets(vpc_ids=None):
    """Get subnets grouped by tier."""
    data = run_aws_command("ec2", "describe-subnets")
    if not data:
        return {"public": [], "app": [], "database": []}

    subnets = {"public": [], "app": [], "database": []}
    for subnet in data.get("Subnets", []):
        if vpc_ids and subnet["VpcId"] not in vpc_ids:
            continue

        name = ""
        tier = "app"
        for tag in subnet.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
            if tag["Key"] == "Tier":
                tier = tag["Value"]

        if not name:
            continue

        if "public" in name.lower():
            tier = "public"
        elif "db" in name.lower() or "database" in name.lower():
            tier = "database"

        if tier in subnets:
            subnets[tier].append({
                "id": subnet["SubnetId"],
                "cidr": subnet["CidrBlock"],
                "az": subnet.get("AvailabilityZone", ""),
                "name": name
            })
    return subnets


def get_instances(vpc_ids=None):
    """Get EC2 instances grouped by tier."""
    data = run_aws_command("ec2", "describe-instances")
    if not data:
        return {"web": [], "app": []}

    instances = {"web": [], "app": []}
    for reservation in data.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            if vpc_ids and instance.get("VpcId") not in vpc_ids:
                continue

            name = ""
            tier = "web"
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
                if tag["Key"] == "Tier":
                    tier = tag["Value"]

            if "app" in name.lower():
                tier = "app"

            if tier in instances:
                instances[tier].append({
                    "id": instance["InstanceId"],
                    "type": instance.get("InstanceType", ""),
                    "state": instance.get("State", {}).get("Name", "unknown"),
                    "private_ip": instance.get("PrivateIpAddress", ""),
                    "name": name or "(unnamed)"
                })
    return instances


def get_security_groups(vpc_ids=None):
    """Get security groups."""
    data = run_aws_command("ec2", "describe-security-groups")
    if not data:
        return []

    sgs = []
    for sg in data.get("SecurityGroups", []):
        if vpc_ids and sg.get("VpcId") not in vpc_ids:
            continue
        if sg.get("GroupName") == "default":
            continue

        ports = []
        for rule in sg.get("IpPermissions", []):
            port = rule.get("FromPort")
            if port:
                ports.append(str(port))

        sgs.append({
            "id": sg["GroupId"],
            "name": sg.get("GroupName", ""),
            "ports": ports
        })
    return sgs


def get_internet_gateways(vpc_ids=None):
    """Get internet gateways."""
    data = run_aws_command("ec2", "describe-internet-gateways")
    if not data:
        return []

    igws = []
    for igw in data.get("InternetGateways", []):
        vpc_id = ""
        for att in igw.get("Attachments", []):
            vpc_id = att.get("VpcId", "")
        if vpc_ids and vpc_id not in vpc_ids:
            continue
        name = ""
        for tag in igw.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
        if name or vpc_id:
            igws.append({"id": igw["InternetGatewayId"], "name": name})
    return igws


def generate_html():
    """Generate the dashboard HTML with clear 3-tier visualization."""
    vpcs = get_vpcs()
    vpc_ids = [v["id"] for v in vpcs] if vpcs else None

    subnets = get_subnets(vpc_ids)
    instances = get_instances(vpc_ids)
    security_groups = get_security_groups(vpc_ids)
    igws = get_internet_gateways(vpc_ids)

    mode = "Real AWS" if USE_AWS else "LocalStack"
    total_subnets = len(subnets["public"]) + len(subnets["app"]) + len(subnets["database"])
    total_instances = len(instances["web"]) + len(instances["app"])

    # Build instance cards HTML
    web_instances_html = ""
    for inst in instances["web"]:
        web_instances_html += f'''
            <div class="instance-card">
                <div class="instance-name">{inst["name"]}</div>
                <div class="instance-id">{inst["id"][:20]}</div>
                <div class="instance-details">
                    <span class="badge">{inst["type"]}</span>
                    <span class="badge status-{inst["state"]}">{inst["state"]}</span>
                </div>
                <div class="instance-ip">IP: {inst["private_ip"] or "N/A"}</div>
            </div>'''

    app_instances_html = ""
    for inst in instances["app"]:
        app_instances_html += f'''
            <div class="instance-card">
                <div class="instance-name">{inst["name"]}</div>
                <div class="instance-id">{inst["id"][:20]}</div>
                <div class="instance-details">
                    <span class="badge">{inst["type"]}</span>
                    <span class="badge status-{inst["state"]}">{inst["state"]}</span>
                </div>
                <div class="instance-ip">IP: {inst["private_ip"] or "N/A"}</div>
            </div>'''

    # Get VPC info
    vpc = vpcs[0] if vpcs else {"name": "No VPC", "cidr": "N/A", "id": "N/A"}
    igw = igws[0] if igws else {"id": "N/A", "name": "No IGW"}

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3-Tier Architecture Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}

        /* Modal Styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
            backdrop-filter: blur(5px);
        }}
        .modal.active {{ display: flex; align-items: center; justify-content: center; }}
        .modal-content {{
            background: linear-gradient(135deg, #1a1a3e, #2d2d44);
            border-radius: 16px;
            padding: 30px;
            max-width: 700px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .modal-close {{
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 28px;
            cursor: pointer;
            color: #888;
            transition: color 0.2s;
        }}
        .modal-close:hover {{ color: #fff; }}
        .modal-title {{
            font-size: 1.8em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .modal-section {{
            margin-bottom: 20px;
        }}
        .modal-section h4 {{
            color: #ff9900;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        .modal-section p {{
            line-height: 1.6;
            color: #ccc;
        }}
        .modal-section ul {{
            margin-left: 20px;
            line-height: 1.8;
            color: #ccc;
        }}
        .modal-section code {{
            background: rgba(0,0,0,0.4);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            color: #4ecdc4;
        }}
        .modal-diagram {{
            background: rgba(0,0,0,0.4);
            border-radius: 8px;
            padding: 15px;
            font-family: monospace;
            white-space: pre;
            overflow-x: auto;
            font-size: 0.85em;
            line-height: 1.4;
            color: #96ceb4;
        }}
        .modal-example {{
            background: rgba(255,153,0,0.1);
            border-left: 4px solid #ff9900;
            padding: 15px;
            border-radius: 0 8px 8px 0;
            margin-top: 15px;
        }}
        .modal-example strong {{ color: #ff9900; }}

        .tier {{ cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }}
        .tier:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }}

        .header {{
            text-align: center;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 2.2em;
            background: linear-gradient(90deg, #ff9900, #ffb84d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }}
        .header .subtitle {{ color: #888; }}
        .header .mode {{
            display: inline-block;
            background: {"#ff6b6b" if USE_AWS else "#00d9ff"};
            color: #000;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            margin-top: 8px;
            font-weight: 600;
        }}

        .stats {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 15px 25px;
            text-align: center;
            min-width: 100px;
        }}
        .stat-box .num {{ font-size: 2em; font-weight: bold; }}
        .stat-box .label {{ color: #888; font-size: 0.85em; }}
        .stat-box.vpc .num {{ color: #ff6b6b; }}
        .stat-box.subnet .num {{ color: #4ecdc4; }}
        .stat-box.ec2 .num {{ color: #45b7d1; }}
        .stat-box.sg .num {{ color: #96ceb4; }}

        .architecture {{
            max-width: 900px;
            margin: 0 auto;
        }}

        .tier {{
            margin-bottom: 15px;
            border-radius: 12px;
            overflow: hidden;
        }}

        .tier-header {{
            padding: 12px 20px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .tier-header .icon {{ font-size: 1.3em; }}
        .tier-header .count {{
            margin-left: auto;
            background: rgba(0,0,0,0.3);
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 0.85em;
        }}

        .tier-content {{
            padding: 15px 20px;
            background: rgba(0,0,0,0.2);
        }}

        .tier.internet {{
            background: linear-gradient(135deg, #2d2d44, #1a1a2e);
            border: 2px solid #666;
        }}
        .tier.internet .tier-header {{ background: rgba(255,255,255,0.1); }}

        .tier.public {{
            background: linear-gradient(135deg, #ff9900, #cc7a00);
        }}
        .tier.public .tier-header {{ background: rgba(0,0,0,0.2); }}

        .tier.web {{
            background: linear-gradient(135deg, #45b7d1, #2d8fa8);
        }}
        .tier.web .tier-header {{ background: rgba(0,0,0,0.2); }}

        .tier.app {{
            background: linear-gradient(135deg, #96ceb4, #6bab8f);
        }}
        .tier.app .tier-header {{ background: rgba(0,0,0,0.2); color: #1a1a2e; }}
        .tier.app .tier-content {{ color: #1a1a2e; }}

        .tier.database {{
            background: linear-gradient(135deg, #ff6b6b, #cc5555);
        }}
        .tier.database .tier-header {{ background: rgba(0,0,0,0.2); }}

        .vpc-info {{
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 10px;
            font-family: monospace;
            font-size: 0.9em;
        }}

        .instances-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
        }}

        .instance-card {{
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 12px;
        }}
        .instance-name {{ font-weight: 600; margin-bottom: 4px; }}
        .instance-id {{ font-family: monospace; font-size: 0.8em; color: rgba(255,255,255,0.7); }}
        .instance-details {{ margin: 8px 0; }}
        .instance-ip {{ font-size: 0.85em; color: rgba(255,255,255,0.8); }}

        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            background: rgba(255,255,255,0.2);
            margin-right: 5px;
        }}
        .status-running {{ background: #27ae60; }}
        .status-stopped {{ background: #e74c3c; }}

        .subnets-list {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .subnet-badge {{
            background: rgba(0,0,0,0.3);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85em;
        }}
        .subnet-badge .name {{ font-weight: 600; }}
        .subnet-badge .cidr {{ font-family: monospace; color: rgba(255,255,255,0.7); }}

        .arrow {{
            text-align: center;
            padding: 5px;
            font-size: 1.5em;
            color: #666;
        }}

        .security-groups {{
            max-width: 900px;
            margin: 30px auto 0;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 15px 20px;
        }}
        .security-groups h3 {{
            margin-bottom: 15px;
            color: #96ceb4;
        }}
        .sg-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
        }}
        .sg-card {{
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 12px;
            border-left: 3px solid #96ceb4;
        }}
        .sg-name {{ font-weight: 600; margin-bottom: 4px; }}
        .sg-id {{ font-family: monospace; font-size: 0.8em; color: #888; }}
        .sg-ports {{ margin-top: 8px; font-size: 0.85em; }}

        .empty {{ color: rgba(255,255,255,0.5); font-style: italic; padding: 10px; }}

        .refresh-btn {{
            position: fixed;
            bottom: 25px;
            right: 25px;
            background: #ff9900;
            color: #000;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(255,153,0,0.4);
        }}
        .refresh-btn:hover {{ background: #ffb84d; }}

        .note {{
            max-width: 900px;
            margin: 20px auto;
            padding: 15px;
            background: rgba(255,153,0,0.1);
            border-left: 4px solid #ff9900;
            border-radius: 0 8px 8px 0;
            font-size: 0.9em;
            color: #ccc;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>3-Tier Architecture Dashboard</h1>
        <p class="subtitle">AWS Infrastructure Visualization</p>
        <span class="mode">{mode}</span>
    </div>

    <div class="stats">
        <div class="stat-box vpc">
            <div class="num">{len(vpcs)}</div>
            <div class="label">VPCs</div>
        </div>
        <div class="stat-box subnet">
            <div class="num">{total_subnets}</div>
            <div class="label">Subnets</div>
        </div>
        <div class="stat-box ec2">
            <div class="num">{total_instances}</div>
            <div class="label">EC2 Instances</div>
        </div>
        <div class="stat-box sg">
            <div class="num">{len(security_groups)}</div>
            <div class="label">Security Groups</div>
        </div>
    </div>

    <div class="architecture">
        <!-- Internet -->
        <div class="tier internet" onclick="showModal('internet')">
            <div class="tier-header">
                <span class="icon">🌐</span>
                <span>INTERNET</span>
                <span style="margin-left:auto;font-size:0.8em;opacity:0.7;">Click to learn more</span>
            </div>
            <div class="tier-content">
                <div class="vpc-info">
                    Internet Gateway: {igw["id"]}
                </div>
            </div>
        </div>

        <div class="arrow">▼</div>

        <!-- Public Tier (ALB) -->
        <div class="tier public" onclick="showModal('public')">
            <div class="tier-header">
                <span class="icon">⚖️</span>
                <span>PUBLIC TIER - Load Balancer</span>
                <span class="count">{len(subnets["public"])} subnets</span>
            </div>
            <div class="tier-content">
                <div class="subnets-list">
                    {"".join(f'<div class="subnet-badge"><div class="name">{s["name"]}</div><div class="cidr">{s["cidr"]}</div></div>' for s in subnets["public"]) or '<span class="empty">No public subnets</span>'}
                </div>
                <div style="margin-top:10px;font-size:0.9em;opacity:0.8;">
                    Note: ALB requires LocalStack Pro. In production, ALB distributes traffic here.
                </div>
            </div>
        </div>

        <div class="arrow">▼</div>

        <!-- Web Tier -->
        <div class="tier web" onclick="showModal('web')">
            <div class="tier-header">
                <span class="icon">🖥️</span>
                <span>WEB TIER - Frontend Servers</span>
                <span class="count">{len(instances["web"])} instances</span>
            </div>
            <div class="tier-content">
                <div class="instances-grid">
                    {web_instances_html or '<span class="empty">No web instances</span>'}
                </div>
            </div>
        </div>

        <div class="arrow">▼</div>

        <!-- App Tier -->
        <div class="tier app" onclick="showModal('app')">
            <div class="tier-header">
                <span class="icon">⚙️</span>
                <span>APP TIER - Application Servers</span>
                <span class="count">{len(instances["app"])} instances</span>
            </div>
            <div class="tier-content">
                <div class="instances-grid">
                    {app_instances_html or '<span class="empty">No app instances</span>'}
                </div>
            </div>
        </div>

        <div class="arrow">▼</div>

        <!-- Database Tier -->
        <div class="tier database" onclick="showModal('database')">
            <div class="tier-header">
                <span class="icon">🗄️</span>
                <span>DATABASE TIER - RDS</span>
                <span class="count">{len(subnets["database"])} subnets</span>
            </div>
            <div class="tier-content">
                <div class="subnets-list">
                    {"".join(f'<div class="subnet-badge"><div class="name">{s["name"]}</div><div class="cidr">{s["cidr"]}</div></div>' for s in subnets["database"]) or '<span class="empty">No database subnets</span>'}
                </div>
                <div style="margin-top:10px;font-size:0.9em;opacity:0.8;">
                    Note: RDS requires LocalStack Pro. In production, MySQL/PostgreSQL runs here.
                </div>
            </div>
        </div>
    </div>

    <!-- VPC Info -->
    <div class="note">
        <strong>VPC:</strong> {vpc["name"]} ({vpc["id"]}) - CIDR: {vpc["cidr"]}
    </div>

    <!-- Security Groups -->
    <div class="security-groups">
        <h3>🔒 Security Groups</h3>
        <div class="sg-grid">
            {"".join(f'''<div class="sg-card">
                <div class="sg-name">{sg["name"]}</div>
                <div class="sg-id">{sg["id"]}</div>
                <div class="sg-ports">Ports: {", ".join(sg["ports"]) or "None"}</div>
            </div>''' for sg in security_groups) or '<span class="empty">No security groups</span>'}
        </div>
    </div>

    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>

    <!-- Modal Container -->
    <div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
        <div class="modal-content">
            <span class="modal-close" onclick="closeModal()">&times;</span>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        const explanations = {{
            internet: {{
                title: '🌐 Internet & Internet Gateway',
                content: `
                    <div class="modal-section">
                        <h4>What is the Internet Gateway?</h4>
                        <p>The Internet Gateway (IGW) is the doorway between your VPC and the public internet. It allows resources in public subnets to communicate with the outside world.</p>
                    </div>
                    <div class="modal-section">
                        <h4>How it Works</h4>
                        <div class="modal-diagram">User Request → Internet → IGW → Route Table → Public Subnet → ALB
                               ↑                                              ↓
               Response ← Internet ← IGW ← Route Table ← Public Subnet ← ALB</div>
                    </div>
                    <div class="modal-section">
                        <h4>Key Points</h4>
                        <ul>
                            <li><strong>One per VPC</strong> - Each VPC can have one IGW attached</li>
                            <li><strong>Horizontally scaled</strong> - AWS manages capacity automatically</li>
                            <li><strong>No bandwidth constraints</strong> - It doesn't limit your traffic</li>
                            <li><strong>Highly available</strong> - Built-in redundancy across AZs</li>
                        </ul>
                    </div>
                    <div class="modal-example">
                        <strong>Real-world analogy:</strong> Think of the IGW as the main entrance to a building. Everyone who wants to enter or leave must pass through it.
                    </div>
                `
            }},
            public: {{
                title: '⚖️ Public Tier & Load Balancer',
                content: `
                    <div class="modal-section">
                        <h4>What is the Public Tier?</h4>
                        <p>The Public Tier is the only layer directly accessible from the internet. It contains the Application Load Balancer (ALB) that receives all incoming traffic and distributes it to backend servers.</p>
                    </div>
                    <div class="modal-section">
                        <h4>Application Load Balancer (ALB)</h4>
                        <ul>
                            <li><strong>Traffic distribution</strong> - Spreads requests across multiple servers</li>
                            <li><strong>Health checks</strong> - Only sends traffic to healthy servers</li>
                            <li><strong>SSL termination</strong> - Handles HTTPS encryption/decryption</li>
                            <li><strong>Path-based routing</strong> - Route <code>/api</code> to app servers, <code>/</code> to web servers</li>
                        </ul>
                    </div>
                    <div class="modal-section">
                        <h4>Why Multi-AZ?</h4>
                        <div class="modal-diagram">    AZ-1a              AZ-1b
   ┌─────────┐       ┌─────────┐
   │ ALB     │       │ ALB     │
   │ Node    │◄─────►│ Node    │
   └─────────┘       └─────────┘
       ↓                 ↓
If AZ-1a fails, AZ-1b continues serving traffic!</div>
                    </div>
                    <div class="modal-section">
                        <h4>Security</h4>
                        <ul>
                            <li>Only ports <code>80</code> (HTTP) and <code>443</code> (HTTPS) are open</li>
                            <li>All other ports are blocked by the security group</li>
                            <li>Can integrate with AWS WAF for protection against attacks</li>
                        </ul>
                    </div>
                    <div class="modal-example">
                        <strong>Real-world analogy:</strong> The ALB is like a receptionist at a busy office. They greet everyone at the door, check if you have an appointment (health check), and direct you to the right person (routing).
                    </div>
                `
            }},
            web: {{
                title: '🖥️ Web Tier (Presentation Layer)',
                content: `
                    <div class="modal-section">
                        <h4>What is the Web Tier?</h4>
                        <p>The Web Tier handles the user interface - everything your users see and interact with. It serves static content (HTML, CSS, JavaScript, images) and forwards dynamic requests to the App Tier.</p>
                    </div>
                    <div class="modal-section">
                        <h4>What Runs Here?</h4>
                        <ul>
                            <li><strong>Web servers</strong> - Nginx, Apache, or IIS</li>
                            <li><strong>Frontend apps</strong> - React, Vue, Angular builds</li>
                            <li><strong>Static assets</strong> - Images, CSS, JavaScript files</li>
                            <li><strong>Reverse proxy</strong> - Forwards API calls to App Tier</li>
                        </ul>
                    </div>
                    <div class="modal-section">
                        <h4>Traffic Flow</h4>
                        <div class="modal-diagram">ALB → Web Server (Nginx)
         │
         ├── Static request (/style.css)
         │   └── Serve directly from disk/cache
         │
         └── Dynamic request (/api/users)
             └── Proxy to App Tier (port 8080)</div>
                    </div>
                    <div class="modal-section">
                        <h4>Security</h4>
                        <ul>
                            <li><strong>Private subnet</strong> - Not directly accessible from internet</li>
                            <li><strong>Security group</strong> - Only accepts traffic from ALB on port 80</li>
                            <li><strong>No public IP</strong> - Uses NAT Gateway for outbound internet</li>
                        </ul>
                    </div>
                    <div class="modal-example">
                        <strong>Real-world analogy:</strong> The Web Tier is like the front-of-house staff at a restaurant. They take your order (user input), show you the menu (UI), and pass your order to the kitchen (App Tier).
                    </div>
                `
            }},
            app: {{
                title: '⚙️ App Tier (Business Logic Layer)',
                content: `
                    <div class="modal-section">
                        <h4>What is the App Tier?</h4>
                        <p>The App Tier is the brain of your application. It processes business logic, validates data, enforces rules, and coordinates between the Web Tier and Database Tier.</p>
                    </div>
                    <div class="modal-section">
                        <h4>What Runs Here?</h4>
                        <ul>
                            <li><strong>Application servers</strong> - Node.js, Java Spring, Python Flask/Django</li>
                            <li><strong>API endpoints</strong> - REST APIs, GraphQL servers</li>
                            <li><strong>Business logic</strong> - Calculations, validations, workflows</li>
                            <li><strong>Authentication</strong> - JWT validation, session management</li>
                        </ul>
                    </div>
                    <div class="modal-section">
                        <h4>Example: Processing an Order</h4>
                        <div class="modal-diagram">1. Web Tier sends: POST /api/orders (user_id, product_id, qty)
                    ↓
2. App Tier validates:
   - Is user authenticated? ✓
   - Does product exist? ✓
   - Is quantity available? ✓
   - Calculate total price
                    ↓
3. App Tier queries Database:
   - INSERT INTO orders (...)
   - UPDATE inventory SET qty = qty - 1
                    ↓
4. App Tier returns: {{"order_id": 12345, "status": "confirmed"}}</div>
                    </div>
                    <div class="modal-section">
                        <h4>Security</h4>
                        <ul>
                            <li><strong>Private subnet</strong> - Completely isolated from internet</li>
                            <li><strong>Security group</strong> - Only accepts traffic from Web Tier on port 8080</li>
                            <li><strong>Secrets management</strong> - Database credentials stored in AWS Secrets Manager</li>
                        </ul>
                    </div>
                    <div class="modal-example">
                        <strong>Real-world analogy:</strong> The App Tier is like the kitchen in a restaurant. It receives orders from the waiters (Web Tier), prepares the food (processes requests), gets ingredients from the pantry (Database), and sends the finished dish back out.
                    </div>
                `
            }},
            database: {{
                title: '🗄️ Database Tier (Data Layer)',
                content: `
                    <div class="modal-section">
                        <h4>What is the Database Tier?</h4>
                        <p>The Database Tier stores all your application data. It's the most protected layer because losing data can be catastrophic. In AWS, this is typically Amazon RDS (Relational Database Service).</p>
                    </div>
                    <div class="modal-section">
                        <h4>What Runs Here?</h4>
                        <ul>
                            <li><strong>RDS databases</strong> - MySQL, PostgreSQL, MariaDB, Oracle, SQL Server</li>
                            <li><strong>Data storage</strong> - User accounts, orders, products, transactions</li>
                            <li><strong>Backups</strong> - Automated daily backups with point-in-time recovery</li>
                            <li><strong>Read replicas</strong> - Scale read operations across regions</li>
                        </ul>
                    </div>
                    <div class="modal-section">
                        <h4>Multi-AZ Deployment</h4>
                        <div class="modal-diagram">    AZ-1a                    AZ-1b
┌──────────────┐        ┌──────────────┐
│   PRIMARY    │  Sync  │   STANDBY    │
│    MySQL     │───────►│    MySQL     │
│              │  Repl. │              │
└──────────────┘        └──────────────┘
       ↑
All writes go here

If Primary fails → Automatic failover to Standby (< 60 seconds)</div>
                    </div>
                    <div class="modal-section">
                        <h4>Security (Most Protected!)</h4>
                        <ul>
                            <li><strong>Isolated subnet</strong> - Separate from even the App Tier subnets</li>
                            <li><strong>Security group</strong> - ONLY accepts traffic from App Tier on port 3306</li>
                            <li><strong>No internet access</strong> - Cannot reach or be reached from internet</li>
                            <li><strong>Encryption</strong> - Data encrypted at rest (AES-256) and in transit (TLS)</li>
                            <li><strong>IAM authentication</strong> - Optional: authenticate with IAM instead of passwords</li>
                        </ul>
                    </div>
                    <div class="modal-example">
                        <strong>Real-world analogy:</strong> The Database Tier is like a bank vault. Only authorized personnel (App Tier) can access it, there are multiple security layers, everything is backed up, and there's a redundant vault (standby) in case the primary fails.
                    </div>
                `
            }}
        }};

        function showModal(tier) {{
            const modal = document.getElementById('modal');
            const body = document.getElementById('modal-body');
            const data = explanations[tier];
            if (data) {{
                body.innerHTML = `<div class="modal-title">${{data.title}}</div>${{data.content}}`;
                modal.classList.add('active');
            }}
        }}

        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>'''
    return html


def check_localstack():
    """Check if LocalStack is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{LOCALSTACK_ENDPOINT}/_localstack/health"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False


def check_aws_credentials():
    """Check if AWS credentials are configured."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except:
        return False


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = generate_html()
            self.wfile.write(html.encode())
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass


def main():
    global USE_AWS

    parser = argparse.ArgumentParser(description="3-Tier Architecture Dashboard")
    parser.add_argument("--aws", action="store_true", help="Use real AWS instead of LocalStack")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    USE_AWS = args.aws

    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  3-Tier Architecture Dashboard{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")

    if USE_AWS:
        print(f"  Mode: {Colors.YELLOW}Real AWS{Colors.END}")
        print(f"  Checking AWS credentials... ", end="")
        if not check_aws_credentials():
            print(f"{Colors.RED}NOT CONFIGURED{Colors.END}")
            print(f"\n  {Colors.YELLOW}Configure AWS credentials first:{Colors.END}")
            print(f"  aws configure\n")
            sys.exit(1)
        print(f"{Colors.GREEN}OK{Colors.END}")
    else:
        print(f"  Mode: {Colors.CYAN}LocalStack{Colors.END}")
        print(f"  Checking LocalStack... ", end="")
        if not check_localstack():
            print(f"{Colors.RED}NOT RUNNING{Colors.END}")
            print(f"\n  {Colors.YELLOW}Start LocalStack first:{Colors.END}")
            print(f"  docker-compose up -d\n")
            sys.exit(1)
        print(f"{Colors.GREEN}OK{Colors.END}")

    port = 8080
    server = HTTPServer(("localhost", port), DashboardHandler)

    print(f"\n  {Colors.GREEN}Dashboard running at:{Colors.END}")
    print(f"  {Colors.BOLD}http://localhost:{port}{Colors.END}\n")
    print(f"  Press Ctrl+C to stop.\n")

    if not args.no_browser:
        def open_browser():
            time.sleep(1)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.YELLOW}Dashboard stopped.{Colors.END}\n")
        server.shutdown()


if __name__ == "__main__":
    main()
