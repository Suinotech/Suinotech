from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import sqlite3
import os
from datetime import datetime
import zlib
import struct
from functools import lru_cache
import ssl
from urllib.parse import urlparse, parse_qs, unquote

try:
    import pg8000.dbapi as pg_dbapi
except Exception:
    pg_dbapi = None

app = Flask(__name__)
DATABASE_PATH = os.getenv("DATABASE_PATH", "suinotech.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

_db_initialized = False

def ensure_db_initialized():
    global _db_initialized
    if _db_initialized:
        return
    init_db()
    _db_initialized = True

@app.context_processor
def inject_globals():
    return {"datetime": datetime}

def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack("!I", len(data)) + chunk_type + data + struct.pack("!I", crc)


@lru_cache(maxsize=4)
def _generate_solid_png(size: int) -> bytes:
    r, g, b, a = 46, 125, 50, 255
    rgba = bytes([r, g, b, a])
    raw = bytearray()
    for _y in range(size):
        raw.append(0)
        raw.extend(rgba * size)
    compressed = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack("!IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


@app.route("/icon-192.png")
def icon_192():
    return Response(_generate_solid_png(192), mimetype="image/png")


@app.route("/icon-512.png")
def icon_512():
    return Response(_generate_solid_png(512), mimetype="image/png")


class CursorProxy:
    def __init__(self, backend, cursor, conn_proxy):
        self._backend = backend
        self._cursor = cursor
        self._conn_proxy = conn_proxy
        self._col_names = None

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        sql2 = self._conn_proxy._adapt_sql(sql)
        self._cursor.execute(sql2, params)
        self._col_names = None
        return self

    def _ensure_col_names(self):
        if self._col_names is not None:
            return
        desc = getattr(self._cursor, "description", None)
        if not desc:
            self._col_names = []
            return
        self._col_names = [d[0] for d in desc]

    def _to_mapping(self, row):
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        if self._backend != "postgres":
            return row
        self._ensure_col_names()
        if self._col_names and not hasattr(row, "keys"):
            return {self._col_names[i]: row[i] for i in range(min(len(self._col_names), len(row)))}
        return row

    def fetchone(self):
        return self._to_mapping(self._cursor.fetchone())

    def fetchall(self):
        rows = self._cursor.fetchall()
        if self._backend != "postgres":
            return rows
        return [self._to_mapping(r) for r in rows]

    @property
    def lastrowid(self):
        if self._backend == "sqlite":
            return getattr(self._cursor, "lastrowid", None)
        return None


class DBConn:
    def __init__(self, backend, conn):
        self.backend = backend
        self._conn = conn

    def _adapt_sql(self, sql: str) -> str:
        if self.backend == "postgres":
            return sql.replace("?", "%s")
        return sql

    def cursor(self):
        cur = self._conn.cursor()
        return CursorProxy(self.backend, cur, self)

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db():
    if DATABASE_URL:
        if pg_dbapi is None:
            raise RuntimeError("pg8000 não está instalado")
        parsed = urlparse(DATABASE_URL)
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        host = parsed.hostname or ""
        port = parsed.port or 5432
        database = (parsed.path or "").lstrip("/")

        qs = parse_qs(parsed.query or "")
        sslmode = (qs.get("sslmode", ["require"])[0] or "require").lower()
        ssl_context = None
        if sslmode != "disable":
            ssl_context = ssl.create_default_context()

        conn = pg_dbapi.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            ssl_context=ssl_context,
        )
        return DBConn("postgres", conn)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return DBConn("sqlite", conn)

def init_db():
    conn = get_db()
    c = conn.cursor()

    def existing_columns(table_name: str) -> set:
        if conn.backend == "sqlite":
            rows = c.execute(f"PRAGMA table_info({table_name})").fetchall()
            return {row[1] for row in rows}
        rows = c.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=?",
            (table_name,),
        ).fetchall()
        return {r["column_name"] for r in rows}

    def ensure_columns(table_name: str, columns: list):
        cols = existing_columns(table_name)
        for col_name, col_def in columns:
            if col_name not in cols:
                if conn.backend == "sqlite":
                    c.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
                else:
                    c.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_def}")
    
    # Tabela de Matrizes (Porcas/Leitoas)
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS matrizes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      identificacao TEXT NOT NULL UNIQUE,
                      baia_numero TEXT,
                      tipo TEXT NOT NULL,
                      raca TEXT,
                      data_nascimento TEXT,
                      data_entrada TEXT,
                      status TEXT DEFAULT 'ativa',
                      observacoes TEXT,
                      created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS matrizes
                     (id SERIAL PRIMARY KEY,
                      identificacao TEXT NOT NULL UNIQUE,
                      baia_numero TEXT,
                      tipo TEXT NOT NULL,
                      raca TEXT,
                      data_nascimento TEXT,
                      data_entrada TEXT,
                      status TEXT DEFAULT 'ativa',
                      observacoes TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    ensure_columns("matrizes", [
        ("identificacao", "identificacao TEXT"),
        ("baia_numero", "baia_numero TEXT"),
        ("tipo", "tipo TEXT"),
        ("raca", "raca TEXT"),
        ("data_nascimento", "data_nascimento TEXT"),
        ("data_entrada", "data_entrada TEXT"),
        ("status", "status TEXT DEFAULT 'ativa'"),
        ("observacoes", "observacoes TEXT"),
        ("created_at", "created_at TEXT DEFAULT CURRENT_TIMESTAMP"),
    ])
    
    # Tabela de Partos
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS partos
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      matriz_id INTEGER NOT NULL,
                      data_parto TEXT NOT NULL,
                      numero_parto INTEGER,
                      nascidos_vivos INTEGER DEFAULT 0,
                      nascidos_mortos INTEGER DEFAULT 0,
                      mumificados INTEGER DEFAULT 0,
                      peso_medio_nascimento REAL,
                      observacoes TEXT,
                      FOREIGN KEY (matriz_id) REFERENCES matrizes(id))''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS partos
                     (id SERIAL PRIMARY KEY,
                      matriz_id INTEGER NOT NULL,
                      data_parto TEXT NOT NULL,
                      numero_parto INTEGER,
                      nascidos_vivos INTEGER DEFAULT 0,
                      nascidos_mortos INTEGER DEFAULT 0,
                      mumificados INTEGER DEFAULT 0,
                      peso_medio_nascimento DOUBLE PRECISION,
                      observacoes TEXT)''')
    ensure_columns("partos", [
        ("matriz_id", "matriz_id INTEGER"),
        ("data_parto", "data_parto TEXT"),
        ("numero_parto", "numero_parto INTEGER"),
        ("nascidos_vivos", "nascidos_vivos INTEGER DEFAULT 0"),
        ("nascidos_mortos", "nascidos_mortos INTEGER DEFAULT 0"),
        ("mumificados", "mumificados INTEGER DEFAULT 0"),
        ("peso_medio_nascimento", "peso_medio_nascimento REAL"),
        ("observacoes", "observacoes TEXT"),
    ])
    
    # Tabela de Lotes
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS lotes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      nome TEXT NOT NULL UNIQUE,
                      fase TEXT NOT NULL,
                      data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                      numero_animais INTEGER DEFAULT 0,
                      observacoes TEXT)''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS lotes
                     (id SERIAL PRIMARY KEY,
                      nome TEXT NOT NULL UNIQUE,
                      fase TEXT NOT NULL,
                      data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      numero_animais INTEGER DEFAULT 0,
                      observacoes TEXT)''')
    ensure_columns("lotes", [
        ("nome", "nome TEXT"),
        ("fase", "fase TEXT"),
        ("data_criacao", "data_criacao TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("numero_animais", "numero_animais INTEGER DEFAULT 0"),
        ("observacoes", "observacoes TEXT"),
    ])
    
    # Tabela de Suínos (agora com link para lote e matriz)
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS suinos
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      identificacao TEXT NOT NULL UNIQUE,
                      lote_id INTEGER,
                      matriz_id INTEGER,
                      parto_id INTEGER,
                      data_nascimento TEXT,
                      sexo TEXT,
                      peso_nascimento REAL,
                      status TEXT DEFAULT 'ativo',
                      observacoes TEXT,
                      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (lote_id) REFERENCES lotes(id),
                      FOREIGN KEY (matriz_id) REFERENCES matrizes(id),
                      FOREIGN KEY (parto_id) REFERENCES partos(id))''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS suinos
                     (id SERIAL PRIMARY KEY,
                      identificacao TEXT NOT NULL UNIQUE,
                      lote_id INTEGER,
                      matriz_id INTEGER,
                      parto_id INTEGER,
                      data_nascimento TEXT,
                      sexo TEXT,
                      peso_nascimento DOUBLE PRECISION,
                      status TEXT DEFAULT 'ativo',
                      observacoes TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    ensure_columns("suinos", [
        ("identificacao", "identificacao TEXT"),
        ("lote_id", "lote_id INTEGER"),
        ("matriz_id", "matriz_id INTEGER"),
        ("parto_id", "parto_id INTEGER"),
        ("data_nascimento", "data_nascimento TEXT"),
        ("sexo", "sexo TEXT"),
        ("peso_nascimento", "peso_nascimento REAL"),
        ("status", "status TEXT DEFAULT 'ativo'"),
        ("observacoes", "observacoes TEXT"),
        ("created_at", "created_at TEXT DEFAULT CURRENT_TIMESTAMP"),
    ])
    
    # Tabela de Pesagens
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS pesagens
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      suino_id INTEGER NOT NULL,
                      peso REAL NOT NULL,
                      data_pesagem TEXT DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (suino_id) REFERENCES suinos(id))''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS pesagens
                     (id SERIAL PRIMARY KEY,
                      suino_id INTEGER NOT NULL,
                      peso DOUBLE PRECISION NOT NULL,
                      data_pesagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    ensure_columns("pesagens", [
        ("suino_id", "suino_id INTEGER"),
        ("peso", "peso REAL"),
        ("data_pesagem", "data_pesagem TEXT DEFAULT CURRENT_TIMESTAMP"),
    ])
    
    # Tabela de Ração (melhorada)
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS racao
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      nome TEXT NOT NULL,
                      fase_aplicacao TEXT,
                      tipo TEXT,
                      quantidade_total REAL,
                      unidade TEXT DEFAULT 'kg',
                      data_validade TEXT,
                      fornecedor TEXT,
                      preco_kg REAL,
                      created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS racao
                     (id SERIAL PRIMARY KEY,
                      nome TEXT NOT NULL,
                      fase_aplicacao TEXT,
                      tipo TEXT,
                      quantidade_total DOUBLE PRECISION,
                      unidade TEXT DEFAULT 'kg',
                      data_validade TEXT,
                      fornecedor TEXT,
                      preco_kg DOUBLE PRECISION,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    ensure_columns("racao", [
        ("nome", "nome TEXT"),
        ("fase_aplicacao", "fase_aplicacao TEXT"),
        ("tipo", "tipo TEXT"),
        ("quantidade_total", "quantidade_total REAL"),
        ("unidade", "unidade TEXT DEFAULT 'kg'"),
        ("data_validade", "data_validade TEXT"),
        ("fornecedor", "fornecedor TEXT"),
        ("preco_kg", "preco_kg REAL"),
        ("created_at", "created_at TEXT DEFAULT CURRENT_TIMESTAMP"),
    ])
    
    # Tabela de Saúde (melhorada)
    if conn.backend == "sqlite":
        c.execute('''CREATE TABLE IF NOT EXISTS saude
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      suino_id INTEGER,
                      matriz_id INTEGER,
                      tipo TEXT NOT NULL,
                      produto TEXT,
                      dosagem TEXT,
                      descricao TEXT,
                      data_evento TEXT DEFAULT CURRENT_TIMESTAMP,
                      veterinario TEXT,
                      FOREIGN KEY (suino_id) REFERENCES suinos(id),
                      FOREIGN KEY (matriz_id) REFERENCES matrizes(id))''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS saude
                     (id SERIAL PRIMARY KEY,
                      suino_id INTEGER,
                      matriz_id INTEGER,
                      tipo TEXT NOT NULL,
                      produto TEXT,
                      dosagem TEXT,
                      descricao TEXT,
                      data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      veterinario TEXT)''')
    ensure_columns("saude", [
        ("suino_id", "suino_id INTEGER"),
        ("matriz_id", "matriz_id INTEGER"),
        ("tipo", "tipo TEXT"),
        ("produto", "produto TEXT"),
        ("dosagem", "dosagem TEXT"),
        ("descricao", "descricao TEXT"),
        ("data_evento", "data_evento TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("veterinario", "veterinario TEXT"),
    ])
    
    conn.commit()
    conn.close()

def parse_id_list(text: str):
    if not text:
        return []
    items = []
    for raw in text.replace("\r", "\n").split("\n"):
        v = raw.strip()
        if v:
            items.append(v)
    seen = set()
    out = []
    for v in items:
        if v not in seen:
            out.append(v)
            seen.add(v)
    return out

def identificacao_existe(conn, identificacao: str) -> bool:
    row = conn.execute("SELECT 1 FROM suinos WHERE identificacao=? LIMIT 1", (identificacao,)).fetchone()
    return row is not None

def gerar_identificacoes(conn, prefixo: str, inicio: int, quantidade: int):
    result = []
    n = max(1, int(inicio or 1))
    while len(result) < quantidade:
        candidato = f"{prefixo}{str(n).zfill(3)}"
        if not identificacao_existe(conn, candidato):
            result.append(candidato)
        n += 1
    return result

# --- DASHBOARD ---
@app.route('/')
def dashboard():
    ensure_db_initialized()
    conn = get_db()
    c = conn.cursor()
    
    total_suinos = c.execute("SELECT COUNT(*) AS n FROM suinos WHERE status='ativo'").fetchone()["n"]
    total_matrizes = c.execute("SELECT COUNT(*) AS n FROM matrizes WHERE status='ativa'").fetchone()["n"]
    total_lotes = c.execute("SELECT COUNT(*) AS n FROM lotes").fetchone()["n"]
    
    partos_recentes = conn.execute('''SELECT p.*, m.identificacao as matriz 
                                      FROM partos p JOIN matrizes m ON p.matriz_id = m.id 
                                      ORDER BY p.data_parto DESC LIMIT 5''').fetchall()
    
    stats = {
        'total_suinos': total_suinos,
        'total_matrizes': total_matrizes,
        'total_lotes': total_lotes
    }
    
    conn.close()
    return render_template('dashboard.html', stats=stats, partos_recentes=partos_recentes)

# --- MATRIZES ---
@app.route('/matrizes')
def matrizes():
    ensure_db_initialized()
    conn = get_db()
    matrizes_list = conn.execute("SELECT * FROM matrizes ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('matrizes.html', matrizes=matrizes_list)

@app.route('/matrizes/<int:id>')
def matriz_detalhe(id):
    ensure_db_initialized()
    conn = get_db()
    matriz = conn.execute("SELECT * FROM matrizes WHERE id=?", (id,)).fetchone()
    if matriz is None:
        conn.close()
        return "Matriz não encontrada", 404

    partos_list = conn.execute('''SELECT p.*,
                                         COUNT(s.id) AS leitoes_registrados
                                  FROM partos p
                                  LEFT JOIN suinos s ON s.parto_id = p.id
                                  WHERE p.matriz_id=?
                                  GROUP BY p.id
                                  ORDER BY p.data_parto DESC, p.id DESC''', (id,)).fetchall()

    leitoes = conn.execute('''SELECT s.*, l.nome as lote
                              FROM suinos s
                              LEFT JOIN lotes l ON s.lote_id = l.id
                              WHERE s.matriz_id=? AND s.parto_id IS NOT NULL
                              ORDER BY s.data_nascimento DESC, s.id DESC
                              LIMIT 200''', (id,)).fetchall()

    resumo = conn.execute('''SELECT
                                 COUNT(*) AS total_partos,
                                 COALESCE(SUM(p.nascidos_vivos), 0) AS total_nascidos_vivos,
                                 COALESCE(SUM(p.nascidos_mortos), 0) AS total_nascidos_mortos,
                                 COALESCE(SUM(p.mumificados), 0) AS total_mumificados
                             FROM partos p
                             WHERE p.matriz_id=?''', (id,)).fetchone()

    conn.close()
    return render_template('matriz_detalhe.html', matriz=matriz, partos=partos_list, leitoes=leitoes, resumo=resumo)

@app.route('/matrizes/nova', methods=['GET', 'POST'])
def nova_matriz():
    ensure_db_initialized()
    if request.method == 'POST':
        conn = get_db()
        data = request.form
        conn.execute('''INSERT INTO matrizes (identificacao, baia_numero, tipo, raca, data_nascimento, data_entrada, observacoes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (data['identificacao'], (data.get('baia_numero') or "").strip(), data['tipo'], data['raca'],
                     data['data_nascimento'], data['data_entrada'], data['observacoes']))
        conn.commit()
        conn.close()
        return redirect(url_for('matrizes'))
    return render_template('form_matriz.html', matriz=None)

@app.route('/matrizes/<int:id>/editar', methods=['GET', 'POST'])
def editar_matriz(id):
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        conn.execute('''UPDATE matrizes SET identificacao=?, baia_numero=?, tipo=?, raca=?, data_nascimento=?,
                        data_entrada=?, status=?, observacoes=? WHERE id=?''',
                    (data['identificacao'], (data.get('baia_numero') or "").strip(), data['tipo'], data['raca'], data['data_nascimento'],
                     data['data_entrada'], data['status'], data['observacoes'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('matrizes'))
    matriz = conn.execute("SELECT * FROM matrizes WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('form_matriz.html', matriz=matriz)

@app.route('/matrizes/<int:id>/deletar')
def deletar_matriz(id):
    ensure_db_initialized()
    conn = get_db()
    conn.execute("DELETE FROM matrizes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('matrizes'))

# --- PARTOS ---
@app.route('/partos')
def partos():
    ensure_db_initialized()
    conn = get_db()
    partos_list = conn.execute('''SELECT p.*, m.identificacao as matriz 
                                  FROM partos p JOIN matrizes m ON p.matriz_id = m.id 
                                  ORDER BY p.data_parto DESC''').fetchall()
    conn.close()
    return render_template('partos.html', partos=partos_list)

@app.route('/partos/<int:id>')
def parto_detalhe(id):
    ensure_db_initialized()
    conn = get_db()
    parto = conn.execute('''SELECT p.*, m.identificacao as matriz_identificacao, m.id as matriz_id
                            FROM partos p
                            JOIN matrizes m ON p.matriz_id = m.id
                            WHERE p.id=?''', (id,)).fetchone()
    if parto is None:
        conn.close()
        return "Parto não encontrado", 404

    leitoes = conn.execute('''SELECT s.*, l.nome as lote
                              FROM suinos s
                              LEFT JOIN lotes l ON s.lote_id = l.id
                              WHERE s.parto_id=?
                              ORDER BY s.identificacao ASC''', (id,)).fetchall()
    conn.close()
    return render_template('parto_detalhe.html', parto=parto, leitoes=leitoes)

@app.route('/partos/novo', methods=['GET', 'POST'])
def novo_parto():
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        matriz_id = int(data['matriz_id'])
        data_parto = data['data_parto']
        numero_parto = data.get('numero_parto') or None
        nascidos_vivos = int(data.get('nascidos_vivos') or 0)
        nascidos_mortos = int(data.get('nascidos_mortos') or 0)
        mumificados = int(data.get('mumificados') or 0)
        peso_medio_nascimento = data.get('peso_medio_nascimento') or None
        observacoes = data.get('observacoes') or ""

        cursor = conn.execute('''INSERT INTO partos (matriz_id, data_parto, numero_parto, nascidos_vivos,
                        nascidos_mortos, mumificados, peso_medio_nascimento, observacoes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''' + (" RETURNING id" if conn.backend == "postgres" else ""),
                    (matriz_id, data_parto, numero_parto,
                     nascidos_vivos, nascidos_mortos, mumificados,
                     peso_medio_nascimento, observacoes))
        if conn.backend == "postgres":
            parto_id = cursor.fetchone()["id"]
        else:
            parto_id = cursor.lastrowid

        criar_leitoes = (data.get("criar_leitoes") == "on")
        lote_id_raw = (data.get("lote_id") or "").strip()
        lote_id = int(lote_id_raw) if lote_id_raw else None

        if criar_leitoes and nascidos_vivos > 0:
            matriz_row = conn.execute("SELECT identificacao FROM matrizes WHERE id=?", (matriz_id,)).fetchone()
            matriz_identificacao = matriz_row["identificacao"] if matriz_row else str(matriz_id)

            ids_lista = parse_id_list(data.get("lista_identificacoes") or "")
            if ids_lista:
                for ident in ids_lista:
                    if identificacao_existe(conn, ident):
                        conn.close()
                        return f"Identificação já existe: {ident}", 400
                ident_list = ids_lista
            else:
                prefixo = (data.get("prefixo") or "").strip()
                if not prefixo:
                    prefixo = f"{matriz_identificacao}-{data_parto.replace('-', '')}-"
                inicio = int(data.get("inicio_sequencia") or 1)
                ident_list = gerar_identificacoes(conn, prefixo, inicio, nascidos_vivos)

            for ident in ident_list[:nascidos_vivos]:
                conn.execute('''INSERT INTO suinos (identificacao, lote_id, matriz_id, parto_id, data_nascimento, sexo, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (ident, lote_id, matriz_id, parto_id, data_parto, "Irrelevante", "ativo"))
        conn.commit()
        conn.close()
        return redirect(url_for('parto_detalhe', id=parto_id))

    selected_matriz_id = request.args.get("matriz_id", "").strip()
    selected_matriz_id = int(selected_matriz_id) if selected_matriz_id.isdigit() else None
    matrizes = conn.execute("SELECT * FROM matrizes WHERE status='ativa' ORDER BY identificacao ASC").fetchall()
    lotes = conn.execute("SELECT * FROM lotes ORDER BY fase ASC, nome ASC").fetchall()
    conn.close()
    return render_template('form_parto.html', matrizes=matrizes, lotes=lotes, selected_matriz_id=selected_matriz_id)

@app.route('/partos/<int:parto_id>/leitoes/novo', methods=['GET', 'POST'])
def novo_leitao(parto_id):
    ensure_db_initialized()
    conn = get_db()
    parto = conn.execute("SELECT * FROM partos WHERE id=?", (parto_id,)).fetchone()
    if parto is None:
        conn.close()
        return "Parto não encontrado", 404
    matriz = conn.execute("SELECT * FROM matrizes WHERE id=?", (parto["matriz_id"],)).fetchone()
    lotes = conn.execute("SELECT * FROM lotes ORDER BY fase ASC, nome ASC").fetchall()

    if request.method == 'POST':
        data = request.form
        identificacao = (data.get("identificacao") or "").strip()
        if not identificacao:
            conn.close()
            return "Identificação obrigatória", 400
        if identificacao_existe(conn, identificacao):
            conn.close()
            return f"Identificação já existe: {identificacao}", 400

        lote_id_raw = (data.get("lote_id") or "").strip()
        lote_id = int(lote_id_raw) if lote_id_raw else None
        sexo = data.get("sexo") or "Irrelevante"
        peso_nascimento = data.get("peso_nascimento") or None
        observacoes = data.get("observacoes") or ""

        conn.execute('''INSERT INTO suinos (identificacao, lote_id, matriz_id, parto_id, data_nascimento, sexo, peso_nascimento, status, observacoes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (identificacao, lote_id, parto["matriz_id"], parto_id, parto["data_parto"], sexo, peso_nascimento, "ativo", observacoes))
        conn.commit()
        conn.close()
        return redirect(url_for('parto_detalhe', id=parto_id))

    conn.close()
    return render_template('form_leitao.html', parto=parto, matriz=matriz, lotes=lotes)

# --- LOTES ---
@app.route('/lotes')
def lotes():
    ensure_db_initialized()
    conn = get_db()
    lotes_list = conn.execute("SELECT * FROM lotes ORDER BY data_criacao DESC, id DESC").fetchall()
    conn.close()
    return render_template('lotes.html', lotes=lotes_list)

@app.route('/lotes/novo', methods=['GET', 'POST'])
def novo_lote():
    ensure_db_initialized()
    if request.method == 'POST':
        conn = get_db()
        data = request.form
        conn.execute('''INSERT INTO lotes (nome, fase, numero_animais, observacoes)
                        VALUES (?, ?, ?, ?)''',
                    (data['nome'], data['fase'], data['numero_animais'], data['observacoes']))
        conn.commit()
        conn.close()
        return redirect(url_for('lotes'))
    return render_template('form_lote.html', lote=None)

@app.route('/lotes/<int:id>/editar', methods=['GET', 'POST'])
def editar_lote(id):
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        conn.execute('''UPDATE lotes SET nome=?, fase=?, numero_animais=?, observacoes=? WHERE id=?''',
                    (data['nome'], data['fase'], data['numero_animais'], data['observacoes'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('lotes'))
    lote = conn.execute("SELECT * FROM lotes WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('form_lote.html', lote=lote)

# --- SUÍNOS (melhorado) ---
@app.route('/suinos')
def suinos():
    ensure_db_initialized()
    conn = get_db()
    suinos_list = conn.execute('''SELECT s.*, l.nome as lote, m.identificacao as matriz 
                                  FROM suinos s 
                                  LEFT JOIN lotes l ON s.lote_id = l.id 
                                  LEFT JOIN matrizes m ON s.matriz_id = m.id 
                                  ORDER BY s.created_at DESC''').fetchall()
    lotes = conn.execute("SELECT * FROM lotes").fetchall()
    matrizes = conn.execute("SELECT * FROM matrizes WHERE status='ativa'").fetchall()
    conn.close()
    return render_template('suinos.html', suinos=suinos_list, lotes=lotes, matrizes=matrizes)

@app.route('/suinos/novo', methods=['GET', 'POST'])
def novo_suino():
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        cursor = conn.execute('''INSERT INTO suinos (identificacao, lote_id, matriz_id, data_nascimento, sexo, peso_nascimento, observacoes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''' + (" RETURNING id" if conn.backend == "postgres" else ""),
                    (data['identificacao'], data['lote_id'] or None, data['matriz_id'] or None,
                     data['data_nascimento'], data['sexo'], data['peso_nascimento'], data['observacoes']))
        if data['peso_nascimento']:
            if conn.backend == "postgres":
                suino_id = cursor.fetchone()["id"]
            else:
                suino_id = cursor.lastrowid
            conn.execute("INSERT INTO pesagens (suino_id, peso) VALUES (?, ?)", (suino_id, data['peso_nascimento']))
        conn.commit()
        conn.close()
        return redirect(url_for('suinos'))
    lotes = conn.execute("SELECT * FROM lotes").fetchall()
    matrizes = conn.execute("SELECT * FROM matrizes WHERE status='ativa'").fetchall()
    conn.close()
    return render_template('form_suino.html', suino=None, lotes=lotes, matrizes=matrizes)

@app.route('/suinos/<int:id>/editar', methods=['GET', 'POST'])
def editar_suino(id):
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        conn.execute('''UPDATE suinos SET identificacao=?, lote_id=?, matriz_id=?, data_nascimento=?,
                        sexo=?, status=?, observacoes=? WHERE id=?''',
                    (data['identificacao'], data['lote_id'] or None, data['matriz_id'] or None,
                     data['data_nascimento'], data['sexo'], data['status'], data['observacoes'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('suinos'))
    suino = conn.execute("SELECT * FROM suinos WHERE id=?", (id,)).fetchone()
    lotes = conn.execute("SELECT * FROM lotes").fetchall()
    matrizes = conn.execute("SELECT * FROM matrizes WHERE status='ativa'").fetchall()
    conn.close()
    return render_template('form_suino.html', suino=suino, lotes=lotes, matrizes=matrizes)

@app.route('/suinos/<int:id>/deletar')
def deletar_suino(id):
    ensure_db_initialized()
    conn = get_db()
    conn.execute("DELETE FROM suinos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('suinos'))

# --- PESAGENS ---
@app.route('/suinos/<int:id>/pesagens', methods=['GET', 'POST'])
def pesagens_suino(id):
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        conn.execute("INSERT INTO pesagens (suino_id, peso, data_pesagem) VALUES (?, ?, ?)",
                    (id, data['peso'], data['data_pesagem']))
        conn.commit()
    suino = conn.execute("SELECT * FROM suinos WHERE id=?", (id,)).fetchone()
    pesagens = conn.execute("SELECT * FROM pesagens WHERE suino_id=? ORDER BY data_pesagem DESC", (id,)).fetchall()
    conn.close()
    return render_template('pesagens.html', suino=suino, pesagens=pesagens)

# --- RACAO ---
@app.route('/racao')
def racao():
    ensure_db_initialized()
    conn = get_db()
    racoes = conn.execute("SELECT * FROM racao ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('racao.html', racoes=racoes)

@app.route('/racao/nova', methods=['GET', 'POST'])
def nova_racao():
    ensure_db_initialized()
    if request.method == 'POST':
        conn = get_db()
        data = request.form
        conn.execute('''INSERT INTO racao (nome, fase_aplicacao, tipo, quantidade_total, unidade, data_validade, fornecedor, preco_kg)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (data['nome'], data['fase_aplicacao'], data['tipo'], data['quantidade_total'],
                     data['unidade'], data['data_validade'], data['fornecedor'], data['preco_kg']))
        conn.commit()
        conn.close()
        return redirect(url_for('racao'))
    return render_template('form_racao.html', racao=None)

# --- SAUDE ---
@app.route('/saude')
def saude():
    ensure_db_initialized()
    conn = get_db()
    registros = conn.execute('''SELECT s.*, su.identificacao as suino, m.identificacao as matriz
                                FROM saude s 
                                LEFT JOIN suinos su ON s.suino_id = su.id 
                                LEFT JOIN matrizes m ON s.matriz_id = m.id 
                                ORDER BY s.data_evento DESC''').fetchall()
    suinos = conn.execute("SELECT * FROM suinos WHERE status='ativo'").fetchall()
    matrizes = conn.execute("SELECT * FROM matrizes WHERE status='ativa'").fetchall()
    conn.close()
    return render_template('saude.html', registros=registros, suinos=suinos, matrizes=matrizes)

@app.route('/saude/novo', methods=['GET', 'POST'])
def novo_saude():
    ensure_db_initialized()
    conn = get_db()
    if request.method == 'POST':
        data = request.form
        conn.execute('''INSERT INTO saude (suino_id, matriz_id, tipo, produto, dosagem, descricao, veterinario)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (data['suino_id'] or None, data['matriz_id'] or None, data['tipo'],
                     data['produto'], data['dosagem'], data['descricao'], data['veterinario']))
        conn.commit()
        conn.close()
        return redirect(url_for('saude'))
    suinos = conn.execute("SELECT * FROM suinos WHERE status='ativo'").fetchall()
    matrizes = conn.execute("SELECT * FROM matrizes WHERE status='ativa'").fetchall()
    conn.close()
    return render_template('form_saude.html', suinos=suinos, matrizes=matrizes)

# --- RELATORIOS ---
@app.route('/relatorios')
def relatorios():
    ensure_db_initialized()
    conn = get_db()
    c = conn.cursor()
    
    total_suinos = c.execute("SELECT COUNT(*) AS n FROM suinos WHERE status='ativo'").fetchone()["n"]
    total_matrizes = c.execute("SELECT COUNT(*) AS n FROM matrizes WHERE status='ativa'").fetchone()["n"]
    total_lotes = c.execute("SELECT COUNT(*) AS n FROM lotes").fetchone()["n"]
    
    total_nascidos_vivos = c.execute("SELECT COALESCE(SUM(nascidos_vivos), 0) AS n FROM partos").fetchone()["n"]
    total_nascidos_mortos = c.execute("SELECT COALESCE(SUM(nascidos_mortos), 0) AS n FROM partos").fetchone()["n"]
    
    stats = {
        'total_suinos': total_suinos,
        'total_matrizes': total_matrizes,
        'total_lotes': total_lotes,
        'total_nascidos_vivos': total_nascidos_vivos,
        'total_nascidos_mortos': total_nascidos_mortos
    }
    
    # Taxa de mortalidade
    if total_nascidos_vivos > 0:
        stats['taxa_mortalidade'] = round((total_nascidos_mortos / total_nascidos_vivos) * 100, 2)
    else:
        stats['taxa_mortalidade'] = 0
    
    suinos = conn.execute('''SELECT s.*, l.nome as lote
                             FROM suinos s
                             LEFT JOIN lotes l ON s.lote_id = l.id''').fetchall()
    lotes = conn.execute("SELECT * FROM lotes").fetchall()
    
    conn.close()
    return render_template('relatorios.html', stats=stats, suinos=suinos, lotes=lotes)

if __name__ == '__main__':
    ensure_db_initialized()
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)
