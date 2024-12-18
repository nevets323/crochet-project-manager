# Crochet Project Manager

A Flask web application to help crocheters manage their projects, materials, and track progress.

## Features

- **Project Management**
  - Create and organize crochet projects
  - Track project completion with step-by-step instructions
  - Upload project thumbnails
  - Add notes and external pattern links
  - Track how many times you've made each project

- **Materials Library**
  - Maintain a catalog of your crochet materials
  - Search materials with autocomplete
  - Add materials to projects with quantities
  - Create new materials on the fly while adding to projects

- **Project Organization**
  - Break down projects into parts
  - Reorder parts as needed
  - Track completion of individual steps
  - Reset progress for parts or entire projects

- **Tagging System**
  - Tag projects for easy organization
  - Search projects by tags
  - Filter and sort projects

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/crochet-project-manager.git
   cd crochet-project-manager
   ```

2. Create required directories:
   ```bash
   mkdir -p static/uploads instance
   ```

3. Create a .env file with a secure secret key:

   **On Linux/Mac:**
   ```bash
   # Generate a secure key
   python3 -c "import secrets; print(f'FLASK_SECRET_KEY={secrets.token_hex(32)}')" > .env
   ```

   **On Windows:**
   ```powershell
   # Option 1: Using PowerShell (recommended)
   python -c "import secrets; print(f'FLASK_SECRET_KEY={secrets.token_hex(32)}')" | Out-File -Encoding utf8 .env

   # Option 2: Create manually in Notepad
   # 1. Open Notepad
   # 2. Type or paste the content below
   # 3. Save as ".env" (with quotes) and select "UTF-8" encoding
   ```

   Example .env file format:
   ```env
   # Required
   FLASK_SECRET_KEY=your-generated-secret-key-here

   # Optional - defaults shown
   # FLASK_ENV=production
   # FLASK_APP=app.py
   ```

   **Important Note for Windows Users:**
   - Ensure the .env file is saved with UTF-8 encoding
   - Avoid using Notepad++ or other editors that might add a BOM marker
   - If you see strange characters in the file, recreate it using one of the methods above

4. Build and start the container:
   ```bash
   docker-compose up -d
   ```

The application will be available at `http://localhost:5000`

To view logs:
```bash
docker-compose logs -f
```

To stop the container:
```bash
docker-compose down
```

### Windows-Specific Setup

1. Prerequisites:
   - Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - Ensure Docker Desktop is running (check the system tray)
   - Enable WSL 2 (Windows Subsystem for Linux) if prompted

2. Common Issues and Solutions:

   a. "docker-compose" command not found:
   ```bash
   # Use docker compose (with a space) instead
   docker compose up -d
   ```

   b. Permission issues:
   - Run Command Prompt or PowerShell as Administrator
   - Ensure Docker Desktop has Windows permissions

   c. Port 5000 already in use:
   - Windows may use port 5000 for "Windows Phone IP over USB Transport"
   - Edit docker-compose.yml to use a different port:
     ```yaml
     ports:
       - "5001:5000"  # Change 5001 to any available port
     ```

   d. Path issues:
   - Use forward slashes (/) in paths
   - Avoid spaces in directory names
   - Use full paths if needed

3. Checking Docker status:
   ```bash
   # Verify Docker is running
   docker info

   # Check container status
   docker ps

   # View container logs
   docker compose logs
   ```

### Manual Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   export FLASK_APP=app.py
   export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   ```
4. Run the application:
   ```bash
   python app.py
   ```

## Production Deployment

For production deployment, consider the following:

1. Use HTTPS:
   - Set up a reverse proxy (like Nginx)
   - Configure SSL/TLS certificates

2. Security:
   - Generate a new secret key for production
   - Keep the .env file secure and never commit it
   - Regularly update dependencies

3. Example Nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. Example Docker deployment with custom port and domain:
   ```bash
   # Update docker-compose.yml ports
   ports:
     - "8080:5000"  # Change 8080 to your desired port

   # Start the container
   docker-compose up -d
   ```

## Technical Details

### Dependencies

- Flask 2.3.3
- Flask-SQLAlchemy 3.1.1
- Pillow 10.0.0 (for image handling)
- Flask-WTF 1.1.1

### Database Structure

- **Project**: Main project details including title, thumbnail, and notes
- **Tag**: For categorizing projects
- **MaterialType**: Defines types of materials (brand, name)
- **Material**: Links materials to projects with quantities
- **Part**: Represents different parts of a project
- **Step**: Individual steps within each part

### Development

The application uses SQLite as its database (configured as 'sqlite:///crochet.db') and includes a static file upload system for project thumbnails. It follows MVC patterns and includes features for organizing and tracking crochet projects, their materials, and progress through different steps.

### Docker Volume Management

The Docker setup includes two persistent volumes:
- `static/uploads`: Stores project thumbnails
- `instance`: Contains the SQLite database

To backup these volumes:
```bash
# Stop the container
docker-compose down

# Backup the data
tar -czf crochet-backup.tar.gz static/uploads instance/

# Restart the container
docker-compose up -d
```

To restore from backup:
```bash
# Stop the container
docker-compose down

# Restore the data
tar -xzf crochet-backup.tar.gz

# Restart the container
docker-compose up -d
```