# Production Setup Guide for nft.vertex-art.ru

## VDS Requirements

- Ubuntu 22.04
- Docker and Docker Compose
- Certbot for Let's Encrypt SSL certificates

## Installation Steps

### 1. Prepare the VDS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group
sudo usermod -aG docker $USER
```

### 2. Clone the repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 3. Configure environment variables

Create `.env` file with the following content:

```env
DATABASE_URL=postgresql://admin:secret@localhost:5432/vertex_art
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
MINIO_BUCKET=vertex-art-bucket
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_very_long_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Configure domain DNS

Point the domain `nft.vertex-art.ru` to your VDS IP address using A record in your DNS settings.

### 5. Deploy the application

```bash
# Build and start the services
docker-compose up -d

# Wait for services to start
sleep 30
```

### 6. Configure SSL certificates

```bash
# Run the SSL setup script
./setup_ssl.sh
```

The script will:
- Install certbot if needed
- Obtain SSL certificates for nft.vertex-art.ru
- Configure nginx to use the certificates
- Set up automatic renewal

### 7. Configure MinIO

1. Access MinIO Console at `https://nft.vertex-art.ru:9001`
2. Create a bucket named `vertex-art-bucket`
3. Set up appropriate policies for the bucket

### 8. Verify the deployment

Check that all services are running:

```bash
docker-compose ps
```

Access the admin panel at `https://nft.vertex-art.ru/admin`

## Directory Structure

The application will be deployed with the following structure:

```
/var/www/nft.vertex-art.ru/
├── docker-compose.yml
├── nginx.conf
├── .env
├── ssl/ (for SSL certificates)
├── setup_ssl.sh
├── Dockerfile.app
├── vertex-ar/ (source code)
└── minio-data/ (MinIO data)
```

## Services

The deployment includes:

1. **PostgreSQL** - Database server
2. **MinIO** - S3-compatible object storage
3. **NFT Generator** - Python script for NFT marker generation
4. **FastAPI Application** - Backend API and admin panel
5. **Nginx** - Reverse proxy and static file serving

## Security Considerations

1. Use strong passwords in `.env` file
2. Keep SSL certificates updated
3. Regularly update system packages
4. Monitor access logs
5. Backup data regularly

## Backup and Maintenance

### Database Backup

```bash
docker exec vertex_art_postgres pg_dump -U admin vertex_art > backup.sql
```

### MinIO Backup

MinIO data is stored in the `minio-data/` directory and should be backed up regularly.

### Application Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose up -d --build
```

## Troubleshooting

### If Nginx fails to start
- Check if port 80/443 are available
- Verify SSL certificate paths

### If MinIO fails to start
- Check if port 9000/9001 are available
- Verify permissions on minio-data directory

### If application fails to connect to database
- Check PostgreSQL container status
- Verify DATABASE_URL in .env file

### If AR pages don't load
- Verify NFT marker files exist in MinIO
- Check CORS settings
- Verify video files are accessible