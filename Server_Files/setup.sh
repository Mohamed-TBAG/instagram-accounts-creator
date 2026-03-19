#!/bin/bash
set -e

echo ">>> Starting Fresh Server Setup..."

# 1. Install Dependencies
apt update
apt install -y wireguard qrencode python3-fastapi uvicorn python3-pip ndppd iptables-persistent

# 2. Clean up old mess
systemctl stop wg-quick@wg0 || true
ip link delete wg0 || true
pkill -f main.py || true

# 3. Configure sysctl (Forwarding & Proxy NDP)
cat > /etc/sysctl.d/99-wireguard.conf <<SYSCTL
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
net.ipv6.conf.all.proxy_ndp=1
net.ipv6.conf.enp6s18.proxy_ndp=1
SYSCTL
sysctl -p /etc/sysctl.d/99-wireguard.conf

# 4. Install Config Files
cp wg0.conf /etc/wireguard/wg0.conf

# 4.1 Setup Bridge to Hetzner
cat > /etc/wireguard/wg-hub.conf <<EOF
[Interface]
PrivateKey = CC1TjvuAN8IwT8gV6JWg9Oa//xFXTkRg+L73l/yfCEA=
Address = fd00:aced:aced::2/64

[Peer]
PublicKey = 2MefqKd2ZctPeC12hb3ANTjcO//FO93Tj5PCv6pZGk8=
Endpoint = 65.108.211.167:51821
AllowedIPs = fd00:aced:aced::1/128, 2a01:4f9:c010:91e9:f000::/68, ::/0
PersistentKeepalive = 25
EOF

# 5. Start Services
systemctl enable --now wg-quick@wg-hub
systemctl enable --now wg-quick@wg0
# Note: ndppd is not needed locally as we are routing via hub.

# 6. Start API Backend
mkdir -p /root/backend/api
cp main.py /root/backend/api/main.py
nohup python3 /root/backend/api/main.py > /root/backend.log 2>&1 &

echo ">>> Setup Complete!"
echo ">>> Bridge is established."
echo ">>> API is running on port 8000."
echo ">>> WireGuard is running on port 51820."
