Claro, Luan! Abaixo estão:

---

## 📘 `README.md` – Projeto de Sistema de Estoque

````markdown
# 🗂️ Sistema de Gerenciamento de Estoque

Este projeto é um sistema web simples para gerenciamento de estoque, desenvolvido com **Python (Flask)** e **SQLite**, com foco em usabilidade, organização e controle de entradas e saídas de produtos.

---

## 👨‍💻 Tecnologias Utilizadas

- **Python 3**
- **Flask**
- **SQLite**
- **HTML/CSS (Bootstrap básico)**
- **Jinja2**
- **JavaScript (mínimo)**
- **Requests e ZipFile** (para importação de dados via URL ou arquivo)

---

## 🚀 Funcionalidades

- ✅ Login com sessão de usuário
- ✅ Restrição de acesso à área de usuários apenas para administradores
- ✅ Cadastro e edição de produtos, categorias e movimentações
- ✅ Importação de produtos via `.json` ou `.zip` (com preço, categoria e quantidade)
- ✅ Exportação de dados em `.zip`
- ✅ Registro automático de movimentações de entrada
- ✅ Histórico de importações com exportação em `.txt`
- ✅ Interface amigável com cálculo de total em estoque (R$)

---

## 📂 Organização

- `app.py`: aplicação principal
- `templates/`: arquivos HTML
- `static/`: (opcional) estilos e scripts
- `estoque.db`: banco de dados SQLite

---

## 🛠️ Como executar

1. Instale o ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
````

2. Instale as dependências:

   ```bash
   pip install flask requests
   ```

3. Execute o sistema:

   ```bash
   python app.py
   ```

4. Acesse em: `http://localhost:5000`

---

## 👤 Acesso padrão

* **E-mail**: `admin@admin.com`
* **Senha**: `admin`

