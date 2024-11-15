from flask import Flask, render_template, request, redirect, url_for
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
    current_round = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.relationship('Tag', secondary=project_tags, backref='projects')
    materials = db.relationship('Material', backref='project', lazy=True)
    parts = db.relationship('Part', backref='project', lazy=True)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    steps = db.relationship('Step', backref='part', lazy=True)

class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.String(20))
    instructions = db.Column(db.Text, nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)

@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    if search_query:
        projects = Project.query.join(Project.tags).filter(
            db.or_(
                Project.title.ilike(f'%{search_query}%'),
                Tag.name.ilike(f'%{search_query}%')
            )
        ).distinct().order_by(Project.created_at.desc()).all()
    else:
        projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('index.html', projects=projects, search_query=search_query)

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
    return render_template('project_detail.html', project=project)

@app.route('/project/<int:project_id>/add_part', methods=['POST'])
def add_part(project_id):
    project = Project.query.get_or_404(project_id)
    part_name = request.form['part_name']
    part = Part(name=part_name, project=project)
    db.session.add(part)
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

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

@app.route('/project/<int:project_id>/update_round', methods=['POST'])
def update_round(project_id):
    project = Project.query.get_or_404(project_id)
    action = request.form.get('action')
    
    if action == 'increment':
        project.current_round += 1
    elif action == 'decrement' and project.current_round > 1:
        project.current_round -= 1
    elif action == 'reset':
        project.current_round = 1
    elif action == 'set':
        new_round = int(request.form.get('round_number', 1))
        if new_round > 0:
            project.current_round = new_round
    
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/update_notes', methods=['POST'])
def update_notes(project_id):
    project = Project.query.get_or_404(project_id)
    project.notes = request.form.get('notes', '')
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/project/<int:project_id>/add_material', methods=['POST'])
def add_material(project_id):
    project = Project.query.get_or_404(project_id)
    name = request.form['material_name']
    quantity = request.form['quantity']
    material = Material(name=name, quantity=quantity, project=project)
    db.session.add(material)
    db.session.commit()
    return redirect(url_for('project_detail', project_id=project_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)