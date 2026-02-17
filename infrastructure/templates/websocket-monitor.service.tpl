[Unit]
Description=WebSocket Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/app
Environment="PYTHONUNBUFFERED=1"
Environment="ICEBERG_S3_BUCKET=${S3_BUCKET}"
Environment="AWS_REGION=${AWS_REGION}"
Environment="WEBSOCKET_URL=${WEBSOCKET_URL}"
ExecStart=websocket-monitor
Restart=always
RestartSec=10
StandardOutput=append:/var/log/app/websocket-monitor.log
StandardError=append:/var/log/app/websocket-monitor.error.log

[Install]
WantedBy=multi-user.target
