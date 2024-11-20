from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crochet.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        title = request.form['title']
        external_link = request.form['external_link']
        notes = request.form['notes']
        
        project = Project(title=title, external_link=external_link, notes=notes)
        
        # Handle thumbnail upload
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file.filename:
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                project.thumbnail = filename

        # Handle tags
        tags = request.form['tags'].split(',')
        for tag_name in tags:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                project.tags.append(tag)

        db.session.add(project)
        db.session.commit()
        return redirect(url_for('project_detail', project_id=project.id))

    return render_template('new_project.html')

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    # Order parts by position
    parts = Part.query.filter_by(project_id=project_id).order_by(Part.position).all()
    return render_template('project_detail.html', project=project, parts=parts)

@app.route('/project/<int:project_id>/add_part', methods=['POST'])
def add_part(project_id):
    project = Project.query.get_or_404(project_id)
    part_name = request.form['part_name']
    # Get the highest position and add 1
    max_position = db.session.query(db.func.max(Part.position)).filter_by(project_id=project_id).scalar() or -1
    part = Part(name=part_name, project=project, position=max_position + 1)
    db.session.add(part)
    db.session.commit()
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
    part = Part.query.get_or_404(part_id)
    round_number = request.form['round_number']
    instructions = request.form['instructions']
    step = Step(round_number=round_number, instructions=instructions, part=part)
    db.session.add(step)
    db.session.commit()
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
        material = MaterialType(
            brand=request.form['brand'],
            name=request.form['name'],
            description=request.form.get('description', ''),
            external_link=request.form.get('external_link', '')
        )
        db.session.add(material)
        db.session.commit()
        return redirect(url_for('materials_list'))
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

@app.route('/materials/<int:material_id>/delete', methods=['POST'])
def delete_material(material_id):
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
    project = Project.query.get_or_404(project_id)
    material_type_id = request.form.get('material_type_id')
    quantity = request.form['quantity']
    
    # If material_type_id is not provided, create a new MaterialType
    if not material_type_id:
        material_type = MaterialType(
            brand=request.form['brand'],
            name=request.form['name'],
            description=request.form.get('description', '')
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)