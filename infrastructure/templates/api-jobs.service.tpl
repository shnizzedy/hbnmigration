[Unit]
Description=API Jobs Scheduler
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/app
Environment="PYTHONUNBUFFERED=1"
Environment="ICEBERG_S3_BUCKET=${S3_BUCKET}"
Environment="AWS_REGION=${AWS_REGION}"
ExecStart=/usr/local/bin/api-scheduler
Restart=always
RestartSec=10
StandardOutput=append:/var/log/app/api-jobs.log
StandardError=append:/var/log/app/api-jobs.error.log

[Install]
WantedBy=multi-user.target
