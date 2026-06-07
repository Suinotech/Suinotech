const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

const dbPath = path.join(__dirname, 'suinotech.db');
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Erro ao conectar ao banco de dados:', err.message);
  } else {
    console.log('Conectado ao banco de dados SQLite');
    initDatabase();
  }
});

function initDatabase() {
  db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS suinos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      identificacao TEXT NOT NULL UNIQUE,
      data_nascimento TEXT,
      sexo TEXT,
      peso_nascimento REAL,
      peso_atual REAL,
      data_pesagem TEXT,
      status TEXT DEFAULT 'ativo',
      observacoes TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS racao (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nome TEXT NOT NULL,
      tipo TEXT,
      quantidade_total REAL,
      unidade TEXT,
      data_validade TEXT,
      fornecedor TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS consumo_racao (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      suino_id INTEGER,
      racao_id INTEGER,
      quantidade REAL,
      data_consumo TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (suino_id) REFERENCES suinos(id),
      FOREIGN KEY (racao_id) REFERENCES racao(id)
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS saude (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      suino_id INTEGER,
      tipo TEXT,
      descricao TEXT,
      data_evento TEXT DEFAULT CURRENT_TIMESTAMP,
      veterinario TEXT,
      FOREIGN KEY (suino_id) REFERENCES suinos(id)
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS sync_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      action TEXT NOT NULL,
      table_name TEXT NOT NULL,
      data TEXT NOT NULL,
      status TEXT DEFAULT 'pending',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
  });
}

app.get('/api/suinos', (req, res) => {
  db.all('SELECT * FROM suinos ORDER BY created_at DESC', [], (err, rows) => {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ data: rows });
  });
});

app.post('/api/suinos', (req, res) => {
  const { identificacao, data_nascimento, sexo, peso_nascimento, peso_atual, observacoes } = req.body;
  const data_pesagem = new Date().toISOString().split('T')[0];
  
  const sql = `INSERT INTO suinos (identificacao, data_nascimento, sexo, peso_nascimento, peso_atual, data_pesagem, observacoes) 
               VALUES (?, ?, ?, ?, ?, ?, ?)`;
  
  db.run(sql, [identificacao, data_nascimento, sexo, peso_nascimento, peso_atual, data_pesagem, observacoes], function(err) {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ id: this.lastID, ...req.body });
  });
});

app.put('/api/suinos/:id', (req, res) => {
  const { identificacao, data_nascimento, sexo, peso_nascimento, peso_atual, observacoes, status } = req.body;
  const data_pesagem = new Date().toISOString().split('T')[0];
  
  const sql = `UPDATE suinos SET identificacao=?, data_nascimento=?, sexo=?, peso_nascimento=?, 
               peso_atual=?, data_pesagem=?, observacoes=?, status=?, updated_at=CURRENT_TIMESTAMP 
               WHERE id=?`;
  
  db.run(sql, [identificacao, data_nascimento, sexo, peso_nascimento, peso_atual, data_pesagem, observacoes, status, req.params.id], function(err) {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ id: req.params.id, ...req.body });
  });
});

app.delete('/api/suinos/:id', (req, res) => {
  db.run('DELETE FROM suinos WHERE id=?', [req.params.id], function(err) {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ message: 'Suíno removido com sucesso' });
  });
});

app.get('/api/racao', (req, res) => {
  db.all('SELECT * FROM racao ORDER BY created_at DESC', [], (err, rows) => {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ data: rows });
  });
});

app.post('/api/racao', (req, res) => {
  const { nome, tipo, quantidade_total, unidade, data_validade, fornecedor } = req.body;
  const sql = `INSERT INTO racao (nome, tipo, quantidade_total, unidade, data_validade, fornecedor) 
               VALUES (?, ?, ?, ?, ?, ?)`;
  
  db.run(sql, [nome, tipo, quantidade_total, unidade, data_validade, fornecedor], function(err) {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ id: this.lastID, ...req.body });
  });
});

app.get('/api/consumo', (req, res) => {
  const sql = `SELECT c.*, s.identificacao, r.nome as racao_nome 
               FROM consumo_racao c 
               JOIN suinos s ON c.suino_id = s.id 
               JOIN racao r ON c.racao_id = r.id 
               ORDER BY c.data_consumo DESC`;
  
  db.all(sql, [], (err, rows) => {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ data: rows });
  });
});

app.post('/api/consumo', (req, res) => {
  const { suino_id, racao_id, quantidade } = req.body;
  const sql = `INSERT INTO consumo_racao (suino_id, racao_id, quantidade) VALUES (?, ?, ?)`;
  
  db.run(sql, [suino_id, racao_id, quantidade], function(err) {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ id: this.lastID, ...req.body });
  });
});

app.get('/api/saude', (req, res) => {
  const sql = `SELECT s.*, su.identificacao 
               FROM saude s 
               JOIN suinos su ON s.suino_id = su.id 
               ORDER BY s.data_evento DESC`;
  
  db.all(sql, [], (err, rows) => {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ data: rows });
  });
});

app.post('/api/saude', (req, res) => {
  const { suino_id, tipo, descricao, veterinario } = req.body;
  const sql = `INSERT INTO saude (suino_id, tipo, descricao, veterinario) VALUES (?, ?, ?, ?)`;
  
  db.run(sql, [suino_id, tipo, descricao, veterinario], function(err) {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ id: this.lastID, ...req.body });
  });
});

app.get('/api/relatorios/resumo', (req, res) => {
  const sql = `
    SELECT 
      (SELECT COUNT(*) FROM suinos WHERE status='ativo') as total_suinos,
      (SELECT COUNT(*) FROM suinos WHERE sexo='Macho' AND status='ativo') as machos,
      (SELECT COUNT(*) FROM suinos WHERE sexo='Fêmea' AND status='ativo') as femeas,
      (SELECT SUM(peso_atual) FROM suinos WHERE status='ativo') as peso_total,
      (SELECT SUM(quantidade_total) FROM racao) as total_racao
  `;
  
  db.get(sql, [], (err, row) => {
    if (err) res.status(500).json({ error: err.message });
    else res.json({ data: row });
  });
});

app.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);
});
