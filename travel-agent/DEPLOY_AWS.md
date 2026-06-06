# Deploy Travel Agent on AWS

Step-by-step guide to deploy the AI Travel Planning Agent on AWS using **EC2 + Docker Compose**. The app and PostgreSQL run in containers; data is stored in a Docker volume and persists across restarts.

---

## Prerequisites

- An AWS account
- (Optional) A domain name for a clean URL and HTTPS

---

## Step 1: Launch an EC2 Instance

1. In **AWS Console**, go to **EC2 → Launch Instance**.
2. Configure:
   - **Name**: `travel-agent`
   - **AMI**: Amazon Linux 2023 (or Ubuntu 22.04)
   - **Instance type**: `t3.medium` (2 vCPU, 4 GB RAM — required for Streamlit + Postgres)
   - **Key pair**: Create or select a key pair (you need this to SSH)
   - **Network / Security group**:
     - Allow **SSH** (port 22) from your IP
     - Allow **HTTP** (80) and **HTTPS** (443) if using Nginx
     - Allow **Custom TCP port 8501** (Streamlit) from `0.0.0.0/0` or your IP
   - **Storage**: 30 GB gp3
3. Click **Launch Instance**.
4. (Recommended) Allocate an **Elastic IP** and associate it with the instance so the public IP does not change on reboot.

---

## Step 2: SSH Into the EC2 Instance

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ec2-user@<YOUR_EC2_PUBLIC_IP>
```

Use `ubuntu@` instead of `ec2-user@` if you chose an Ubuntu AMI.

---

## Step 3: Install Docker and Docker Compose on EC2

**Amazon Linux 2023:**

```bash
sudo yum update -y
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Install Docker Buildx (required for `docker compose build`)
sudo curl -SL https://github.com/docker/buildx/releases/latest/download/buildx-v0.19.3.linux-amd64 -o /usr/local/lib/docker/cli-plugins/docker-buildx
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
```

Log out and back in so the `docker` group is applied:

```bash
exit
```

Then SSH in again:

```bash
ssh -i your-key.pem ec2-user@<YOUR_EC2_PUBLIC_IP>
docker --version
docker compose version
docker buildx version
```

---

## Step 4: Get the Code onto EC2

**Option A — Git (recommended):**

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git
cd travel-agent
```

**Option B — SCP from your local machine:**

From your **local** machine:

```bash
scp -i your-key.pem -r /path/to/travel-agent ec2-user@<YOUR_EC2_PUBLIC_IP>:~/travel-agent
```

Then on EC2:

```bash
cd ~/travel-agent
```

---

## Step 5: Create the Production `.env` on EC2

Do **not** commit `.env` or copy it via Git. Create it on the server:

```bash
cd ~/travel-agent
nano .env
```

Paste your environment variables (same keys as local). Ensure these are set for production:

```env
APP_ENV=production
DEBUG=false

# Database — use the Docker service name "postgres" as host
DATABASE_URL=postgresql://travel_agent:YOUR_STRONG_PASSWORD@postgres:5432/travel_agent
POSTGRES_USER=travel_agent
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD
POSTGRES_DB=travel_agent
```

Use a **strong password** for `POSTGRES_PASSWORD` (not the default `travel_agent_secret`). Include all other keys (e.g. `OPENAI_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_PLACES_API_KEY`, etc.) as needed. Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

**Restrict who can read the file** (do this immediately after creating `.env`):

```bash
chmod 600 .env
```

Only the file owner (`ec2-user`) can read or write it; other users on the system cannot. Verify:

```bash
ls -la .env
# Should show: -rw------- 1 ec2-user ec2-user ... .env
```

For stronger protection (no secrets stored on disk), use **AWS Secrets Manager** — see [Securing secrets](#securing-secrets) below.

---

## Securing secrets

Storing `.env` on EC2 is a risk if others can log in or if the disk is exposed. Reduce the risk as follows.

### 1. Limit who can access the EC2 instance

**If you can't change the shared security group** (e.g. multiple users in the account use it):

- **Option A — New security group for this instance only**  
  Create a *new* security group (e.g. `travel-agent-sg`) with only the rules you need: SSH (22) from your IP, port 8501 (and 80/443 if using Nginx). Attach this new SG to the travel-agent EC2 instance and, if desired, remove the shared SG from this instance. Other instances keep using the existing SG; only this one is locked down.

- **Option B — Don't change security groups; harden the instance itself**  
  Keep the existing security group. Restrict access by:
  - **SSH key only**: Use key-based login and do **not** share this instance’s `.pem` with others. Only people with the private key can SSH. Disable password login so no one can log in without the key:
    ```bash
    sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
    sudo systemctl restart sshd
    ```
  - **One owner on the box**: Run the app as a single OS user (e.g. `ec2-user`). Use `chmod 600 .env` so only that user can read it. Don’t add other users’ SSH keys to this instance if you want to be the only one with access.
  - **IAM role for the instance**: Attach a minimal IAM role to *this* EC2 (e.g. for Secrets Manager). That doesn’t grant other account users access to the instance; it only lets this machine read secrets. Other users still need the SSH key to get in.

**If you can change the security group** (e.g. it’s used only by this instance):

- Allow SSH (22) only from your IP or a bastion, not `0.0.0.0/0`.
- **IAM**: Prefer an IAM role for the instance over putting long‑lived AWS keys in `.env`.

### 2. Restrict the `.env` file (if you keep it on disk)

```bash
chmod 600 ~/travel-agent/.env
```

Only the owner can read it. Do not use `chmod 644` or any mode that lets other users read the file.

### 3. (Recommended) Use AWS Secrets Manager — no `.env` on disk

Store secrets in **AWS Secrets Manager** and inject them when starting the app so the EC2 instance does not keep a plain-text `.env` file.

**3a. Create a secret in AWS**

1. In **AWS Console** go to **Secrets Manager → Store a new secret**.
2. Choose **Other type of secret**.
3. Add key/value pairs for each env var (e.g. `OPENAI_API_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`, `TAVILY_API_KEY`, etc.). Use the same names your app expects.
4. Name the secret e.g. `travel-agent/production`.
5. Complete the wizard (no rotation needed for this use).

**3b. Allow the EC2 instance to read the secret**

- Create an IAM role (e.g. `TravelAgentEC2Role`) with a policy that allows `secretsmanager:GetSecretValue` for `travel-agent/production`.
- Attach this role to your EC2 instance (EC2 → instance → Actions → Security → Modify IAM role).

**3c. Fetch secrets at startup and run the app**

Install the AWS CLI and jq (if not already), then use a small script that fetches the secret and passes env vars into Docker without writing a long-lived `.env` file:

```bash
# One-time: install AWS CLI and jq (Amazon Linux 2023)
sudo yum install -y aws-cli jq
```

Create a startup script that fetches the secret and starts the stack (no long-lived `.env` on disk):

```bash
# ~/travel-agent/start-with-secrets.sh
#!/bin/bash
set -e
cd ~/travel-agent

# Fetch secret from AWS, write to a temp file with strict permissions
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id travel-agent/production --query SecretString --output text)
echo "$SECRET_JSON" | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' > .env.prod
chmod 600 .env.prod

# Start stack; Compose substitutes variables from .env.prod and travel-agent service uses it (ENV_FILE)
export ENV_FILE=.env.prod
docker compose --env-file .env.prod up -d --build
unset ENV_FILE

# Remove the file so secrets are not left on disk
rm -f .env.prod
```

Make it executable and run it instead of `docker compose up`:

```bash
chmod +x ~/travel-agent/start-with-secrets.sh
~/travel-agent/start-with-secrets.sh
```

The secret is fetched on each run; any existing `.env` on the server can be removed so only Secrets Manager holds the canonical values. To change a value, update it in Secrets Manager and run the script again.

**Alternative: AWS Systems Manager Parameter Store**

For a free option, use **Parameter Store** (Standard parameters) instead of Secrets Manager. Store each variable as a separate parameter under e.g. `/travel-agent/prod/OPENAI_API_KEY`, then in your script:

```bash
# Example: export parameters under /travel-agent/prod/
for key in $(aws ssm get-parameters-by-path --path /travel-agent/prod --recursive --query 'Parameters[].Name' --output text); do
  name=$(basename "$key")
  value=$(aws ssm get-parameter --name "$key" --with-decryption --query Parameter.Value --output text)
  export "$name=$value"
done
docker compose up -d --build
```

(You would still need to build the full env or a temporary `.env` file for Docker Compose’s `env_file` if you use it.)

---

## Step 6: Build and Run with Docker Compose

```bash
cd ~/travel-agent
docker compose up -d --build
```

This will:

1. Build the `travel-agent` Docker image
2. Pull the Postgres image
3. Start Postgres and wait for it to be healthy
4. Start the Streamlit app with `DATABASE_URL` pointing at Postgres
5. Auto-create the `trips` table on first use (see `app/db/trips.py`)

**If you see:** `compose build requires buildx 0.17.0 or later`:

- Ensure Buildx is installed (Step 3) and run `docker buildx version`.
- Or build the image manually and then start compose:

  ```bash
  docker build -t travel-agent-travel-agent .
  docker compose up -d
  ```

Check that containers are running:

```bash
docker compose ps
```

Both `postgres` and `travel-agent` should show as **Up** (and healthy for the app).

View logs:

```bash
docker compose logs -f
docker compose logs -f travel-agent
docker compose logs -f postgres
```

---

## Step 7: Access the App

In your browser:

```
http://<YOUR_EC2_PUBLIC_IP>:8501
```

Confirm port **8501** is allowed in the EC2 security group (Step 1).

---

## Step 8: Verify Database Persistence

1. In the app, complete a full trip (all checkpoints).
2. On EC2, check that the trip was stored:

```bash
docker compose exec postgres psql -U travel_agent -d travel_agent -c "SELECT id, thread_id, updated_at, state->>'destination' AS dest FROM trips ORDER BY updated_at DESC LIMIT 5;"
```

You should see your trip row(s). The `trips` table is created automatically when the first trip is saved.

---

## Step 9 (Optional): Nginx Reverse Proxy and HTTPS

To serve the app on port 80/443 (no `:8501`) and optionally add HTTPS:

**Install Nginx:**

```bash
# Amazon Linux 2023
sudo yum install -y nginx

# Ubuntu
# sudo apt update && sudo apt install -y nginx
```

**Create config** (replace `YOUR_DOMAIN_OR_IP` with your domain or EC2 public IP):

```bash
sudo tee /etc/nginx/conf.d/travel-agent.conf << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
EOF

sudo systemctl start nginx
sudo systemctl enable nginx
```

Then open: `http://YOUR_DOMAIN_OR_IP` (port 80).

**HTTPS with a domain (Certbot):**

```bash
# Amazon Linux 2023
sudo yum install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# Ubuntu
# sudo apt install -y certbot python3-certbot-nginx
# sudo certbot --nginx -d yourdomain.com
```

---

## Quick Reference — Commands on EC2

| Task | Command |
|------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Rebuild after code change | `docker compose up -d --build` |
| View logs | `docker compose logs -f` |
| Status | `docker compose ps` |
| Restart app only | `docker compose restart travel-agent` |
| Postgres shell | `docker compose exec postgres psql -U travel_agent -d travel_agent` |
| Count trips | `docker compose exec postgres psql -U travel_agent -d travel_agent -c "SELECT count(*) FROM trips;"` |
| Update code (git) | `git pull && docker compose up -d --build` |

---

## Database Backup and Restore

**Backup:**

```bash
docker compose exec postgres pg_dump -U travel_agent travel_agent > backup.sql
```

**Restore:**

```bash
docker compose exec -T postgres psql -U travel_agent travel_agent < backup.sql
```

Data lives in the Docker volume `postgres_data` and persists across `docker compose down` and restarts.

---

## Summary

- **EC2**: Host for Docker (Postgres + Streamlit).
- **Docker Compose**: Runs `postgres` and `travel-agent`; `DATABASE_URL` uses hostname `postgres`.
- **Postgres**: Port 5432 is bound to `127.0.0.1` only; only the app container and localhost can connect.
- **Streamlit**: Runs on port 8501; optional Nginx in front for port 80/443 and HTTPS.
- **Secrets**: Set in `.env` on the server; never commit `.env` or share it.
