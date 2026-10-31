import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session

# Configurou-se para ler os HTMLs soltos na pasta principal (.)
app = Flask(__name__, template_folder='.')
app.secret_key = 'lcv_chave_secreta_super_segura'

# Mudança crucial: a base de dados fica guardada na pasta principal do projeto
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lcv_database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Criar as tabelas caso não existam
    conn.execute('''CREATE TABLE IF NOT EXISTS conteudos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        texto TEXT NOT NULL,
                        imagem_url TEXT NOT NULL)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS colaboradores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL,
                        cargo_turma TEXT NOT NULL,
                        presencas INTEGER DEFAULT 0)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS utilizadores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        nivel INTEGER NOT NULL)''')
    
    # Verificar se o Luis existe, se não, cria
    user = conn.execute('SELECT * FROM utilizadores WHERE username = ?', ('Luis',)).fetchone()
    if not user:
        conn.execute('DELETE FROM utilizadores')
        conn.execute("INSERT INTO utilizadores (username, password, nivel) VALUES (?, ?, ?)", ('Luis', '20671', 2))
    
    conn.commit()
    conn.close()

# FORÇAR A CRIAÇÃO IMEDIATA DAS TABELAS
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    conteudos = conn.execute('SELECT * FROM conteudos').fetchall()
    conn.close()
    return render_template('index.html', conteudos=conteudos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM utilizadores WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and str(user['password']) == str(password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nivel'] = user['nivel']
            return redirect(url_for('dashboard'))
            
        flash('Credenciais inválidas!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conteudos = conn.execute('SELECT * FROM conteudos').fetchall()
    colaboradores = conn.execute('SELECT * FROM colaboradores').fetchall()
    professores = conn.execute('SELECT * FROM utilizadores').fetchall() if session['nivel'] == 2 else []
    conn.close()
    
    return render_template('dashboard.html', conteudos=conteudos, colaboradores=colaboradores, professores=professores)

@app.route('/conteudo/adicionar', methods=['POST'])
def adicionar_conteudo():
    if 'user_id' not in session: return redirect(url_for('login'))
    texto = request.form['texto']
    imagem_url = request.form['imagem_url']
    conn = get_db_connection()
    conn.execute('INSERT INTO conteudos (texto, imagem_url) VALUES (?, ?)', (texto, imagem_url))
    conn.commit()
    conn.close()
    flash('Conteúdo adicionado!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/conteudo/remover/<int:id>')
def remover_conteudo(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM conteudos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/colaborador/adicionar', methods=['POST'])
def adicionar_colaborador():
    if 'user_id' not in session: return redirect(url_for('login'))
    nome = request.form['nome']
    cargo_turma = request.form['cargo_turma']
    conn = get_db_connection()
    conn.execute('INSERT INTO colaboradores (nome, cargo_turma) VALUES (?, ?)', (nome, cargo_turma))
    conn.commit()
    conn.close()
    flash('Colaborador adicionado!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/colaborador/editar/<int:id>', methods=['POST'])
def editar_colaborador(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nome = request.form['nome']
    cargo_turma = request.form['cargo_turma']
    conn = get_db_connection()
    conn.execute('UPDATE colaboradores SET nome = ?, cargo_turma = ? WHERE id = ?', (nome, cargo_turma, id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/colaborador/remover/<int:id>')
def remover_colaborador(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM colaboradores WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/colaborador/presenca/<int:id>')
def marcar_presenca(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('UPDATE colaboradores SET presencas = presencas + 1 WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/professor/criar', methods=['POST'])
def criar_professor():
    if 'user_id' not in session or session['nivel'] != 2:
        return redirect(url_for('dashboard'))
    username = request.form['username']
    password = request.form['password']
    nivel = int(request.form['nivel'])
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO utilizadores (username, password, nivel) VALUES (?, ?, ?)', (username, password, nivel))
        conn.commit()
        flash(f'Professor {username} criado!', 'success')
    except sqlite3.IntegrityError:
        flash('Esse utilizador já existe!', 'danger')
    finally:
        conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
