from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-do-not-use-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crochet.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['THUMBNAIL_SIZE'] = (800, 800)  # Max dimensions for thumbnails
db = SQLAlchemy(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def resize_image(image_path, max_size=(800, 800)):
    """Resize image to fit within max_size while maintaining aspect ratio"""
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Resize maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save as JPEG with optimization
            img.save(image_path, 'JPEG', quality=85, optimize=True)
            return True
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False

# Association table for project tags
project_tags = db.Table('project_tags',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    thumbnail = db.Column(db.String(200))
    external_link = db.Column(db.String(500))
    notes = db.Column(db.Text)
    made_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.relationship('Tag', secondary=project_tags, backref='projects')
    materials = db.relationship('Material', backref='project', lazy=True, cascade='all, delete-orphan')
    parts = db.relationship('Part', backref='project', lazy=True, cascade='all, delete-orphan')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class MaterialType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    external_link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    materials = db.relationship('Material', backref='material_type', lazy=True)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.String(50))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    material_type_id = db.Column(db.Integer, db.ForeignKey('material_type.id'), nullable=False)

class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, default=0)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    steps = db.relationship('Step', backref='part', lazy=True, cascade='all, delete-orphan')

class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.String(20))
    instructions = db.Column(db.Text, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)

    @staticmethod
    def reset_steps_for_part(part_id):
        Step.query.filter_by(part_id=part_id).update({Step.completed: False})
        db.session.commit()

@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'date_desc')  # Default sort by date descending
    
    # Start building the query
    query = Project.query
    
    # Apply search filter if exists
    if search_query:
        query = query.join(Project.tags).filter(
            db.or_(
                Project.title.ilike(f'%{search_query}%'),
                Tag.name.ilike(f'%{search_query}%')
            )
        ).distinct()
    
    # Apply sorting
    if sort_by == 'date_desc':
        query = query.order_by(Project.created_at.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Project.created_at.asc())
    elif sort_by == 'title_asc':
        query = query.order_by(Project.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Project.title.desc())
    elif sort_by == 'made_desc':
        query = query.order_by(Project.made_count.desc())
    elif sort_by == 'made_asc':
        query = query.order_by(Project.made_count.asc())
    
    projects = query.all()
    return render_template('index.html', projects=projects, search_query=search_query, sort_by=sort_by)

@app.route('/project/new', methods=['GET', 'POST'])
def new_project():
    if request.method == 'POST':
        try:
            # Validate required fields
            title = request.form.get('title', '').strip()
            if not title:
                flash('Project title is required.', 'error')
                return redirect(url_for('new_project'))

            if len(title) > 100:
                flash('Project title must be 100 characters or less.', 'error')
                return redirect(url_for('new_project'))

            external_link = request.form.get('external_link', '').strip()
            notes = request.form.get('notes', '').strip()

            project = Project(title=title, external_link=external_link, notes=notes)

            # Handle thumbnail upload
            if 'thumbnail' in request.files:
                file = request.files['thumbnail']
                if file and file.filename:
                    if not allowed_file(file.filename):
                        flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, WEBP', 'error')
                        return redirect(url_for('new_project'))

                    # Secure the filename and add timestamp
                    original_filename = secure_filename(file.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_filename}"
                    # Always save as .jpg after processing
                    filename = filename.rsplit('.', 1)[0] + '.jpg'
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    # Save the file
                    file.save(filepath)

                    # Resize and optimize the image
                    if resize_image(filepath, app.config['THUMBNAIL_SIZE']):
                        project.thumbnail = filename
                    else:
                        # If resize fails, delete the file and continue without thumbnail
                        os.remove(filepath)
                        flash('Could not process image. Project created without thumbnail.', 'warning')

            # Handle tags
            tags_input = request.form.get('tags', '')
            tags = tags_input.split(',')
            for tag_name in tags:
                tag_name = tag_name.strip()
                if tag_name:
                    if len(tag_name) > 50:
                        flash(f'Tag "{tag_name}" is too long (max 50 characters). Skipped.', 'warning')
                        continue
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    project.tags.append(tag)

            db.session.add(project)
            db.session.commit()
            flash('Project created successfully!', 'success')
            return redirect(url_for('project_detail', project_id=project.id))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while creating the project: {str(e)}', 'error')
            return redirect(url_for('new_project'))

    return render_template('new_project.html')

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    # Order parts by position
    parts = Part.query.filter_by(project_id=project_id).order_by(Part.position).all()
    return render_template('project_detail.html', project=project, parts=parts)

@app.route('/project/<int:project_id>/add_part', methods=['POST'])
def add_part(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        part_name = request.form.get('part_name', '').strip()

        # Validate part name
        if not part_name:
            flash('Part name is required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        if len(part_name) > 100:
            flash('Part name must be 100 characters or less.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # Get the highest position and add 1
        max_position = db.session.query(db.func.max(Part.position)).filter_by(project_id=project_id).scalar() or -1
        part = Part(name=part_name, project=project, position=max_position + 1)
        db.session.add(part)
        db.session.commit()
        flash('Part added successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding part: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/part/<int:part_id>/delete', methods=['POST'])
def delete_part(part_id):
    part = Part.query.get_or_404(part_id)
    project_id = part.project_id
    
    # Get all parts with higher positions
    higher_parts = Part.query.filter(
        Part.project_id == project_id,
        Part.position > part.position
    ).all()
    
    # Decrement their positions
    for p in higher_parts:
        p.position -= 1
    
    db.session.delete(part)
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/part/<int:part_id>/move', methods=['POST'])
def move_part(part_id):
    part = Part.query.get_or_404(part_id)
    direction = request.form.get('direction')
    
    if direction not in ['up', 'down']:
        return redirect(url_for('project_detail', project_id=part.project_id))
    
    # Find the part to swap with
    if direction == 'up' and part.position > 0:
        other_part = Part.query.filter_by(
            project_id=part.project_id,
            position=part.position - 1
        ).first()
    elif direction == 'down':
        other_part = Part.query.filter_by(
            project_id=part.project_id,
            position=part.position + 1
        ).first()
    else:
        return redirect(url_for('project_detail', project_id=part.project_id))
    
    if other_part:
        # Swap positions
        part.position, other_part.position = other_part.position, part.position
        db.session.commit()
    
    return redirect(url_for('project_detail', project_id=part.project_id))

@app.route('/part/<int:part_id>/add_step', methods=['POST'])
def add_step(part_id):
    try:
        part = Part.query.get_or_404(part_id)
        round_number = request.form.get('round_number', '').strip()
        instructions = request.form.get('instructions', '').strip()

        # Validate inputs
        if not instructions:
            flash('Step instructions are required.', 'error')
            return redirect(url_for('project_detail', project_id=part.project_id))

        if len(round_number) > 20:
            flash('Round number must be 20 characters or less.', 'error')
            return redirect(url_for('project_detail', project_id=part.project_id))

        step = Step(round_number=round_number, instructions=instructions, part=part)
        db.session.add(step)
        db.session.commit()
        flash('Step added successfully!', 'success')
        return redirect(url_for('project_detail', project_id=part.project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding step: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=part.project_id))

@app.route('/step/<int:step_id>/edit', methods=['POST'])
def edit_step(step_id):
    step = Step.query.get_or_404(step_id)
    step.round_number = request.form['round_number']
    step.instructions = request.form['instructions']
    db.session.commit()
    return redirect(url_for('project_detail', project_id=step.part.project_id))

@app.route('/step/<int:step_id>/delete', methods=['POST'])
def delete_step(step_id):
    step = Step.query.get_or_404(step_id)
    project_id = step.part.project_id
    db.session.delete(step)
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/step/<int:step_id>/toggle', methods=['POST'])
def toggle_step(step_id):
    step = Step.query.get_or_404(step_id)
    step.completed = not step.completed
    db.session.commit()
    return redirect(url_for('project_detail', project_id=step.part.project_id))

@app.route('/part/<int:part_id>/reset_steps', methods=['POST'])
def reset_steps(part_id):
    part = Part.query.get_or_404(part_id)
    Step.reset_steps_for_part(part_id)
    return redirect(url_for('project_detail', project_id=part.project_id))

@app.route('/project/<int:project_id>/reset_all_steps', methods=['POST'])
def reset_all_steps(project_id):
    project = Project.query.get_or_404(project_id)
    for part in project.parts:
        Step.reset_steps_for_part(part.id)
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/update_made_count', methods=['POST'])
def update_made_count(project_id):
    project = Project.query.get_or_404(project_id)
    action = request.form.get('action')
    
    if action == 'increment':
        project.made_count += 1
    elif action == 'decrement' and project.made_count > 0:
        project.made_count -= 1
    elif action == 'reset':
        project.made_count = 0
    
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/update_notes', methods=['POST'])
def update_notes(project_id):
    project = Project.query.get_or_404(project_id)
    project.notes = request.form.get('notes', '')
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/update_tags', methods=['POST'])
def update_tags(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Clear existing tags
    project.tags.clear()
    
    # Add new tags
    tags = request.form.get('tags', '').split(',')
    for tag_name in tags:
        tag_name = tag_name.strip()
        if tag_name:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            project.tags.append(tag)
    
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/update_link', methods=['POST'])
def update_link(project_id):
    project = Project.query.get_or_404(project_id)
    project.external_link = request.form.get('external_link', '').strip()
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/materials')
def materials_list():
    materials = MaterialType.query.order_by(MaterialType.brand, MaterialType.name).all()
    return render_template('materials.html', materials=materials)

@app.route('/materials/new', methods=['GET', 'POST'])
def new_material():
    if request.method == 'POST':
        try:
            brand = request.form.get('brand', '').strip()
            name = request.form.get('name', '').strip()

            # Validate required fields
            if not brand or not name:
                flash('Brand and name are required.', 'error')
                return redirect(url_for('new_material'))

            if len(brand) > 100:
                flash('Brand must be 100 characters or less.', 'error')
                return redirect(url_for('new_material'))

            if len(name) > 100:
                flash('Name must be 100 characters or less.', 'error')
                return redirect(url_for('new_material'))

            material = MaterialType(
                brand=brand,
                name=name,
                description=request.form.get('description', '').strip(),
                external_link=request.form.get('external_link', '').strip()
            )
            db.session.add(material)
            db.session.commit()
            flash('Material created successfully!', 'success')
            return redirect(url_for('materials_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating material: {str(e)}', 'error')
            return redirect(url_for('new_material'))

    return render_template('new_material.html')

@app.route('/materials/<int:material_id>/edit', methods=['GET', 'POST'])
def edit_material(material_id):
    material = MaterialType.query.get_or_404(material_id)
    if request.method == 'POST':
        material.brand = request.form['brand']
        material.name = request.form['name']
        material.description = request.form.get('description', '')
        material.external_link = request.form.get('external_link', '')
        db.session.commit()
        return redirect(url_for('materials_list'))
    return render_template('edit_material.html', material=material)

@app.route('/project/<int:project_id>/material/<int:material_id>/delete', methods=['POST'])
def delete_project_material(project_id, material_id):
    material = Material.query.filter_by(id=material_id, project_id=project_id).first_or_404()
    db.session.delete(material)
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/materials/<int:material_id>/delete', methods=['POST'])
def delete_material_type(material_id):
    material_type = MaterialType.query.get_or_404(material_id)
    # First delete all Material records that reference this MaterialType
    Material.query.filter_by(material_type_id=material_id).delete()
    # Then delete the MaterialType
    db.session.delete(material_type)
    db.session.commit()
    return redirect(url_for('materials_list'))

@app.route('/materials/search')
def search_materials():
    query = request.args.get('q', '').strip()
    materials = MaterialType.query.filter(
        db.or_(
            MaterialType.name.ilike(f'%{query}%'),
            MaterialType.brand.ilike(f'%{query}%')
        )
    ).order_by(MaterialType.brand, MaterialType.name).all()
    
    return jsonify([{
        'id': m.id,
        'brand': m.brand,
        'name': m.name,
        'description': m.description
    } for m in materials])

@app.route('/project/<int:project_id>/add_material', methods=['POST'])
def add_material(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        material_type_id = request.form.get('material_type_id')
        quantity = request.form.get('quantity', '').strip()

        # Validate quantity
        if not quantity:
            flash('Quantity is required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        if len(quantity) > 50:
            flash('Quantity must be 50 characters or less.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # If material_type_id is not provided, create a new MaterialType
        if not material_type_id:
            brand = request.form.get('brand', '').strip()
            name = request.form.get('name', '').strip()

            if not brand or not name:
                flash('Brand and name are required for new materials.', 'error')
                return redirect(url_for('project_detail', project_id=project_id))

            material_type = MaterialType(
                brand=brand,
                name=name,
                description=request.form.get('description', '').strip()
            )
            db.session.add(material_type)
            db.session.flush()  # Get the ID of the new material type
            material_type_id = material_type.id

        material = Material(
            quantity=quantity,
            project=project,
            material_type_id=material_type_id
        )
        db.session.add(material)
        db.session.commit()
        flash('Material added successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding material: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Delete associated files
    if project.thumbnail:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], project.thumbnail))
        except OSError:
            pass  # File might not exist
    
    # SQLAlchemy will handle deleting related materials, parts, and steps
    # due to cascade relationships
    db.session.delete(project)
    db.session.commit()
    
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File is too large. Maximum file size is 16MB.', 'error')
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)