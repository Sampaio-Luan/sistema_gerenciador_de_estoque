# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file 
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime
from flask.json import jsonify 
import json
import zipfile
import io
import requests

app = Flask(__name__)
app.secret_key = 'segredo123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque.db'
db = SQLAlchemy(app)

# region  TABELAS


# MODELOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin ou user


class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)


class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    quantidade = db.Column(db.Integer, default=0)
    preco = db.Column(db.Integer, default=0)  # preço em centavos
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    categoria = db.relationship('Categoria')


class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10))  # Entrada ou Saída
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    produto = db.relationship('Produto')
    quantidade = db.Column(db.Integer)
    preco = db.Column(db.Integer, default=0)
    data = db.Column(db.DateTime, default=datetime.utcnow)


class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)


class ProdutoImportado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    categoria = db.Column(db.String(100))
    quantidade = db.Column(db.Integer)
    preco = db.Column(db.Integer, default=0)


class LogImportacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(20))  # 'novo' ou 'atualizado'
    nome_produto = db.Column(db.String(100))
    categoria = db.Column(db.String(100))
    quantidade = db.Column(db.Integer)
    preco = db.Column(db.Integer, default=0)
    detalhe = db.Column(db.String(200))
# endregion

# region ROTAS

# region DADOS


@app.route('/exportar_dados')
def exportar_dados():
    dados = {
        'usuarios': [
            {'id': u.id, 'nome': u.nome, 'email': u.email}
            for u in Usuario.query.all()
        ],
        'categorias': [
            {'id': c.id, 'nome': c.nome}
            for c in Categoria.query.all()
        ],
        'produtos': [
            {
                'id': p.id,
                'nome': p.nome,
                'descricao': p.descricao,
                'quantidade': p.quantidade,
                'preco': p.preco,
                'categoria': p.categoria.nome if p.categoria else None
            }
            for p in Produto.query.all()
        ],
        'movimentacoes': [
            {
                'id': m.id,
                'tipo': m.tipo,
                'produto': m.produto.nome if m.produto else None,
                'quantidade': m.quantidade,
                'preco': m.preco,
                'data': m.data.strftime('%Y-%m-%d %H:%M:%S')
            }
            for m in Movimentacao.query.all()
        ],
        
    }

    json_bytes = json.dumps(dados, indent=4).encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('dados_exportados.json', json_bytes)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='dados_exportados.zip'
    )


@app.route('/importar_url', methods=['GET', 'POST'])
def importar_url():
    if request.method == 'POST':
        url = request.form['url']
        try:
            response = requests.get(url)
            response.raise_for_status()
            content = response.content

            # Verifica se é JSON puro ou ZIP
            if url.endswith('.json'):
                dados = json.loads(content.decode('utf-8'))
            elif url.endswith('.zip'):
                zip_buffer = io.BytesIO(content)
                with zipfile.ZipFile(zip_buffer) as zipf:
                    dados = json.loads(zipf.read('dados_exportados.json').decode('utf-8'))
            else:
                flash('Formato não suportado. Use um arquivo .json ou .zip.', 'danger')
                return redirect('/importar_url')

            for item in dados.get('produtos', []):
                registro = ProdutoImportado(
                    nome=item['nome'],
                    categoria=item['categoria'],
                    quantidade=item['quantidade'],
                    preco=item.get('preco', 0)  # valor padrão 0 se não existir
                )
                db.session.add(registro)
            db.session.commit()
            flash('Importação por URL realizada com sucesso!', 'success',)
            return redirect('/produtos_importados')
        except Exception as e:
            flash(f'Erro ao importar: {e}', 'danger')
    return render_template('importar_url.html')


@app.route('/importar_arquivo', methods=['GET', 'POST'])
def importar_arquivo():
    if request.method == 'POST':
        arquivo = request.files['arquivo']
        if not arquivo:
            flash('Nenhum arquivo enviado.', 'danger')
            return redirect('/importar_arquivo')

        try:
            if arquivo.filename.endswith('.json'):
                dados = json.load(arquivo)
            elif arquivo.filename.endswith('.zip'):
                zip_buffer = io.BytesIO(arquivo.read())
                with zipfile.ZipFile(zip_buffer) as zipf:
                    dados = json.loads(zipf.read('dados_exportados.json').decode('utf-8'))
            else:
                flash('Formato inválido. Use .json ou .zip.', 'danger')
                return redirect('/importar_arquivo')

            for item in dados.get('produtos', []):
                registro = ProdutoImportado(
                    nome=item['nome'],
                    categoria=item['categoria'],
                    quantidade=item['quantidade'],
                    preco=item.get('preco', 0)  # valor padrão 0 se não existir
                )
                db.session.add(registro)
            db.session.commit()
            flash('Importação realizada com sucesso!', 'success')
            return redirect('/produtos_importados')
        except Exception as e:
            flash(f'Erro ao importar: {e}', 'danger')
            return redirect('/importar_arquivo')

    return render_template('importar_arquivo.html')


@app.route('/importar_para_estoque', methods=['POST'])
def importar_para_estoque():
    ids = request.form.getlist('produto_ids')

    if not ids:
        flash('Nenhum produto selecionado.', 'warning')
        return redirect('/produtos_importados')

    for pid in ids:
        imp = ProdutoImportado.query.get(pid)
        if not imp:
            continue

        # Verifica ou cria a categoria
        categoria = Categoria.query.filter_by(nome=imp.categoria).first()
        if not categoria and imp.categoria:
            categoria = Categoria(nome=imp.categoria)
            db.session.add(categoria)
            db.session.commit()

        produto_existente = Produto.query.filter_by(nome=imp.nome, categoria_id=categoria.id).first()

        if produto_existente:
            produto_existente.quantidade += imp.quantidade
            log = LogImportacao(
                tipo='atualizado',
                nome_produto=imp.nome,
                categoria=imp.categoria,
                quantidade=imp.quantidade,
                preco=imp.preco,
                detalhe='Quantidade somada ao produto existente.'
            )
            produto_final = produto_existente
        else:
            novo = Produto(
                nome=imp.nome,
                descricao="Importado de dados externos",
                quantidade=imp.quantidade,
                categoria_id=categoria.id if categoria else None,
                preco=imp.preco
            )
            db.session.add(novo)
            db.session.flush()  # garante novo.id
            log = LogImportacao(
                tipo='novo',
                nome_produto=imp.nome,
                categoria=imp.categoria,
                quantidade=imp.quantidade,
                preco=imp.preco,
                detalhe='Novo produto criado no estoque.'
            )
            produto_final = novo

        # Registra movimentação
        mov = Movimentacao(
            tipo='Entrada',
            produto_id=produto_final.id,
            quantidade=imp.quantidade,
            preco=imp.preco,
            data=datetime.utcnow()
        )
        db.session.add(mov)

        # Salva log e remove da tabela importada
        db.session.add(log)
        db.session.delete(imp)

    db.session.commit()
    flash('Produtos enviados ao estoque com sucesso!', 'success')
    return redirect('/produtos')

# endregion DADOS


# region HISTORICOS
@app.route('/historico_importacoes')
def historico_importacoes():
    logs = LogImportacao.query.order_by(LogImportacao.data.desc()).all()
    return render_template('historico_importacoes.html', logs=logs)


@app.route('/exportar_logs_importacao')
def exportar_logs_importacao():
    logs = LogImportacao.query.order_by(LogImportacao.data).all()
    linhas = [
        f"{l.data.strftime('%d/%m/%Y %H:%M:%S')} | {l.tipo.upper():<10} | {l.nome_produto} | {l.categoria} | {l.quantidade} | {l.detalhe}"
        for l in logs
    ]
    conteudo = "\n".join(linhas)

    buffer = io.BytesIO()
    buffer.write(conteudo.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='text/plain',
        as_attachment=True,
        download_name='log_importacao.txt'
    )
# endregion HISTORICOS

# region PRODUTOS


@app.route('/produtos')
def listar_produtos():
    produtos = Produto.query.all()
    return render_template('produtos.html', produtos=produtos)


@app.route('/produto/novo', methods=['GET', 'POST'])
def novo_produto():
    categorias = Categoria.query.all()
    if request.method == 'POST':
        preco_float = float(request.form['preco'].replace(',', '.'))
        preco_centavos = int(preco_float * 100)

        novo = Produto(
            nome=request.form['nome'],
            descricao=request.form['descricao'],
            quantidade=int(request.form['quantidade']),
            preco=preco_centavos,
            categoria_id=int(request.form['categoria'])
        )

        db.session.add(novo)
        db.session.commit()
        return redirect('/produtos')
    return render_template('produto_form.html', categorias=categorias)


@app.route('/produtos_importados')
def produtos_importados():
    produtos = ProdutoImportado.query.all()
    return render_template('produtos_importados.html', produtos=produtos)


# ROTA PARA EDITAR PRODUTO
@app.route('/produto/editar/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    categorias = Categoria.query.all()
    if request.method == 'POST':
        preco_float = float(request.form['preco'].replace(',', '.'))
        preco_centavos = int(preco_float * 100)
        produto.nome = request.form['nome']
        produto.descricao = request.form['descricao']
        produto.quantidade = request.form['quantidade']
        produto.categoria_id = request.form['categoria']
        produto.preco = preco_centavos
        db.session.commit()
        return redirect('/produtos')
    return render_template('produto_form.html', produto=produto, categorias=categorias)


# ROTA PARA EXCLUIR PRODUTO
@app.route('/produto/excluir/<int:id>', methods=['GET', 'POST'])
def excluir_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect('/produtos')


@app.route('/excluir_importados', methods=['POST'])
def excluir_importados():
    ids = request.form.getlist('produto_ids')
    if not ids:
        flash('Nenhum produto selecionado para exclusão.', 'warning')
        return redirect('/produtos_importados')

    for pid in ids:
        item = ProdutoImportado.query.get(pid)
        if item:
            db.session.delete(item)

    db.session.commit()
    flash('Produtos importados excluídos com sucesso!', 'success')
    return redirect('/produtos_importados')


@app.route('/exportar_importados')
def exportar_importados():
    produtos = ProdutoImportado.query.all()
    dados = {
        'produtos': [
            {
                'id': p.id,
                'nome': p.nome,
                'categoria': p.categoria,
                'quantidade': p.quantidade,
                'preco': p.preco
            } for p in produtos
        ]
    }

    json_bytes = json.dumps(dados, indent=4).encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('produtos_importados.json', json_bytes)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='produtos_importados.zip'
    )
# endregion PRODUTOS

# region MOVIMENTACOES


@app.route('/movimentacoes')
def listar_movimentacoes():
    movimentacoes = Movimentacao.query.order_by(Movimentacao.data.desc()).all()
    return render_template('movimentacoes.html', movimentacoes=movimentacoes)


@app.route('/movimentacao/nova', methods=['GET', 'POST'])
def nova_movimentacao():
    produtos = Produto.query.all()
    if request.method == 'POST':
        tipo = request.form['tipo']
        produto_id = int(request.form['produto'])
        qtd = int(request.form['quantidade'])

        produto = Produto.query.get(produto_id)
        if tipo == 'Entrada':
            produto.quantidade += qtd
        elif tipo == 'Saída':
            if produto.quantidade >= qtd:
                produto.quantidade -= qtd
            else:
                return 'Estoque insuficiente'

        mov = Movimentacao(tipo=tipo, produto_id=produto_id, quantidade=qtd, preco=produto.preco)
        db.session.add(mov)
        db.session.commit()
        return redirect('/movimentacoes')

    return render_template('movimentacao_form.html', produtos=produtos)
# endregion MOVIMENTACOES

# region USUARIOS


@app.route('/')
def index():
    return redirect('/login')


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

def usuario_admin():
    return session.get('usuario') and Usuario.query.filter_by(email=session['usuario'], role='admin').first()



@app.route('/autenticar', methods=['POST'])
def autenticar():
    email = request.form['email']
    senha = request.form['senha']
    usuario = Usuario.query.filter_by(email=email, senha=senha).first()
    if usuario:
        session['usuario'] = usuario.email
        session['nome_usuario'] = usuario.nome
        return redirect('/produtos')
    flash('Login inválido!')
    return redirect('/login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/usuarios')
def listar_usuarios():
    if not usuario_admin():
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect('/produtos')
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)



@app.route('/usuario/novo', methods=['GET', 'POST'])
def novo_usuario():
    if not usuario_admin():
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect('/produtos')
    if request.method == 'POST':
        novo = Usuario(
            nome=request.form['nome'],
            email=request.form['email'],
            senha=request.form['senha']
        )
        db.session.add(novo)
        db.session.commit()
        return redirect('/usuarios')
    return render_template('usuario_form.html')


@app.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if not usuario_admin():
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect('/produtos')

    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        usuario.nome = request.form['nome']
        usuario.email = request.form['email']
        nova_senha = request.form['senha']

        if nova_senha:
            usuario.senha = nova_senha  # ou use hash se estiver aplicando segurança

        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect('/usuarios')

    return render_template('usuario_form.html', usuario=usuario)


# ROTA PARA EXCLUIR USUÁRIO
@app.route('/usuario/excluir/<int:id>', methods=['GET', 'POST'])
def excluir_usuario(id):
    if not usuario_admin():
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect('/produtos')
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    return redirect('/usuarios')

# endregion USUARIOS

# region SOBRE


@app.route('/sobre')
def sobre():
    return render_template('sobre.html')
# endregion SOBRE

# region CATEGORIAS


@app.route('/categorias')
def listar_categorias():
    categorias = Categoria.query.all()
    return render_template('categorias.html', categorias=categorias)


@app.route('/categoria/nova', methods=['GET', 'POST'])
def nova_categoria():
    if request.method == 'POST':
        nova = Categoria(nome=request.form['nome'])
        db.session.add(nova)
        db.session.commit()
        return redirect('/categorias')
    return render_template('categoria_form.html')


# ROTA PARA EDITAR CATEGORIA
@app.route('/categoria/editar/<int:id>', methods=['GET', 'POST'])
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    if request.method == 'POST':
        categoria.nome = request.form['nome']
        db.session.commit()
        return redirect('/categorias')
    return render_template('categoria_form.html', categoria=categoria)


# ROTA PARA EXCLUIR CATEGORIA
@app.route('/categoria/excluir/<int:id>', methods=['GET', 'POST'])
def excluir_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    db.session.delete(categoria)
    db.session.commit()
    return redirect('/categorias')

# endregion CATEGORIAS

# endregion ROTAS



# Executar
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Criar usuário admin padrão se não existir
        if not Usuario.query.filter_by(email='admin@admin.com').first():
            admin = Usuario(
    nome='Administrador',
    email='admin@admin.com',
    senha='admin',
    role='admin',
)

            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
