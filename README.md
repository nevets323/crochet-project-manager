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

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

### Development

The application uses SQLite as its database (configured as 'sqlite:///crochet.db') and includes a static file upload system for project thumbnails. It follows MVC patterns and includes features for organizing and tracking crochet projects, their materials, and progress through different steps.