import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import localforage from 'localforage';

const API_BASE = 'http://localhost:3001/api';

function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <Navigation />
        <MainContent />
      </div>
    </Router>
  );
}

function Header() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return (
    <header className="header">
      <div className="container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>🐷 SuinoTech</h1>
          <span style={{ 
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: isOnline ? '#c8e6c9' : '#ffcdd2',
            color: isOnline ? '#2e7d32' : '#d32f2f',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            fontWeight: '600'
          }}>
            <span style={{ 
              width: '8px', 
              height: '8px', 
              background: isOnline ? '#4caf50' : '#d32f2f',
              borderRadius: '50%',
              animation: isOnline ? 'pulse 2s infinite' : 'none'
            }}></span>
            {isOnline ? 'Online' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  );
}

function Navigation() {
  const location = useLocation();

  return (
    <nav className="nav">
      <div className="container">
        <ul>
          <li><Link to="/" className={location.pathname === '/' ? 'active' : ''}>🏠 Dashboard</Link></li>
          <li><Link to="/suinos" className={location.pathname === '/suinos' ? 'active' : ''}>🐷 Suínos</Link></li>
          <li><Link to="/racao" className={location.pathname === '/racao' ? 'active' : ''}>🌾 Ração</Link></li>
          <li><Link to="/saude" className={location.pathname === '/saude' ? 'active' : ''}>💊 Saúde</Link></li>
          <li><Link to="/relatorios" className={location.pathname === '/relatorios' ? 'active' : ''}>📊 Relatórios</Link></li>
        </ul>
      </div>
    </nav>
  );
}

function MainContent() {
  return (
    <main className="main">
      <div className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/suinos" element={<Suinos />} />
          <Route path="/racao" element={<Racao />} />
          <Route path="/saude" element={<Saude />} />
          <Route path="/relatorios" element={<Relatorios />} />
        </Routes>
      </div>
    </main>
  );
}

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/relatorios/resumo`);
        const data = await res.json();
        setStats(data.data);
        await localforage.setItem('stats', data.data);
      } else {
        const cached = await localforage.getItem('stats');
        if (cached) setStats(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('stats');
      if (cached) setStats(cached);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Carregando...</div>;

  return (
    <div>
      <div className="grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.total_suinos || 0}</div>
          <div className="stat-label">Total de Suínos</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.machos || 0}</div>
          <div className="stat-label">Machos</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.femeas || 0}</div>
          <div className="stat-label">Fêmeas</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.peso_total ? stats.peso_total.toFixed(1) : 0} kg</div>
          <div className="stat-label">Peso Total</div>
        </div>
      </div>

      <div className="card">
        <h2>📋 Ações Rápidas</h2>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <Link to="/suinos" className="btn btn-primary">+ Adicionar Suíno</Link>
          <Link to="/racao" className="btn btn-primary">+ Cadastrar Ração</Link>
          <Link to="/saude" className="btn btn-primary">+ Registro de Saúde</Link>
        </div>
      </div>
    </div>
  );
}

function Suinos() {
  const [suinos, setSuinos] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    identificacao: '',
    data_nascimento: '',
    sexo: '',
    peso_nascimento: '',
    peso_atual: '',
    observacoes: '',
    status: 'ativo'
  });

  useEffect(() => {
    fetchSuinos();
  }, []);

  const fetchSuinos = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/suinos`);
        const data = await res.json();
        setSuinos(data.data);
        await localforage.setItem('suinos', data.data);
      } else {
        const cached = await localforage.getItem('suinos');
        if (cached) setSuinos(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('suinos');
      if (cached) setSuinos(cached);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (navigator.onLine) {
        if (editing) {
          await fetch(`${API_BASE}/suinos/${editing.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(form)
          });
        } else {
          await fetch(`${API_BASE}/suinos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(form)
          });
        }
      } else {
        const queue = await localforage.getItem('syncQueue') || [];
        queue.push({
          action: editing ? 'update' : 'create',
          table: 'suinos',
          data: editing ? { ...form, id: editing.id } : form
        });
        await localforage.setItem('syncQueue', queue);
      }
      setModalOpen(false);
      resetForm();
      fetchSuinos();
    } catch (error) {
      alert('Erro ao salvar: ' + error.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja remover este suíno?')) return;
    try {
      if (navigator.onLine) {
        await fetch(`${API_BASE}/suinos/${id}`, { method: 'DELETE' });
      } else {
        const queue = await localforage.getItem('syncQueue') || [];
        queue.push({ action: 'delete', table: 'suinos', data: { id } });
        await localforage.setItem('syncQueue', queue);
      }
      fetchSuinos();
    } catch (error) {
      alert('Erro ao remover: ' + error.message);
    }
  };

  const resetForm = () => {
    setForm({
      identificacao: '',
      data_nascimento: '',
      sexo: '',
      peso_nascimento: '',
      peso_atual: '',
      observacoes: '',
      status: 'ativo'
    });
    setEditing(null);
  };

  const editSuino = (suino) => {
    setEditing(suino);
    setForm(suino);
    setModalOpen(true);
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>🐷 Lista de Suínos</h2>
          <button className="btn btn-primary" onClick={() => { resetForm(); setModalOpen(true); }}>
            + Adicionar
          </button>
        </div>

        {suinos.length === 0 ? (
          <div className="empty-state">
            <p>Nenhum suíno cadastrado ainda.</p>
            <p>Clique em "Adicionar" para começar.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Identificação</th>
                <th>Sexo</th>
                <th>Peso Atual</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {suinos.map(suino => (
                <tr key={suino.id}>
                  <td><strong>{suino.identificacao}</strong></td>
                  <td>{suino.sexo}</td>
                  <td>{suino.peso_atual} kg</td>
                  <td>
                    <span className={`status-badge status-${suino.status}`}>
                      {suino.status.charAt(0).toUpperCase() + suino.status.slice(1)}
                    </span>
                  </td>
                  <td className="action-buttons">
                    <button className="btn btn-secondary btn-sm" onClick={() => editSuino(suino)}>Editar</button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(suino.id)}>Remover</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Editar Suíno' : 'Novo Suíno'}>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Identificação *</label>
            <input type="text" className="form-control" value={form.identificacao} onChange={e => setForm({...form, identificacao: e.target.value})} required />
          </div>
          <div className="form-group">
            <label>Data de Nascimento</label>
            <input type="date" className="form-control" value={form.data_nascimento} onChange={e => setForm({...form, data_nascimento: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Sexo</label>
            <select className="form-control" value={form.sexo} onChange={e => setForm({...form, sexo: e.target.value})}>
              <option value="">Selecione</option>
              <option value="Macho">Macho</option>
              <option value="Fêmea">Fêmea</option>
            </select>
          </div>
          <div className="form-group">
            <label>Peso de Nascimento (kg)</label>
            <input type="number" step="0.1" className="form-control" value={form.peso_nascimento} onChange={e => setForm({...form, peso_nascimento: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Peso Atual (kg)</label>
            <input type="number" step="0.1" className="form-control" value={form.peso_atual} onChange={e => setForm({...form, peso_atual: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Status</label>
            <select className="form-control" value={form.status} onChange={e => setForm({...form, status: e.target.value})}>
              <option value="ativo">Ativo</option>
              <option value="vendido">Vendido</option>
              <option value="morto">Morto</option>
            </select>
          </div>
          <div className="form-group">
            <label>Observações</label>
            <textarea className="form-control" rows="3" value={form.observacoes} onChange={e => setForm({...form, observacoes: e.target.value})} />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Salvar</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function Racao() {
  const [racoes, setRacoes] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    nome: '',
    tipo: '',
    quantidade_total: '',
    unidade: 'kg',
    data_validade: '',
    fornecedor: ''
  });

  useEffect(() => {
    fetchRacoes();
  }, []);

  const fetchRacoes = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/racao`);
        const data = await res.json();
        setRacoes(data.data);
        await localforage.setItem('racoes', data.data);
      } else {
        const cached = await localforage.getItem('racoes');
        if (cached) setRacoes(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('racoes');
      if (cached) setRacoes(cached);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (navigator.onLine) {
        await fetch(`${API_BASE}/racao`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form)
        });
      } else {
        const queue = await localforage.getItem('syncQueue') || [];
        queue.push({ action: 'create', table: 'racao', data: form });
        await localforage.setItem('syncQueue', queue);
      }
      setModalOpen(false);
      setForm({ nome: '', tipo: '', quantidade_total: '', unidade: 'kg', data_validade: '', fornecedor: '' });
      fetchRacoes();
    } catch (error) {
      alert('Erro ao salvar: ' + error.message);
    }
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>🌾 Estoque de Ração</h2>
          <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
            + Adicionar Ração
          </button>
        </div>

        {racoes.length === 0 ? (
          <div className="empty-state">
            <p>Nenhuma ração cadastrada ainda.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Tipo</th>
                <th>Quantidade</th>
                <th>Validade</th>
                <th>Fornecedor</th>
              </tr>
            </thead>
            <tbody>
              {racoes.map(racao => (
                <tr key={racao.id}>
                  <td><strong>{racao.nome}</strong></td>
                  <td>{racao.tipo}</td>
                  <td>{racao.quantidade_total} {racao.unidade}</td>
                  <td>{racao.data_validade}</td>
                  <td>{racao.fornecedor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nova Ração">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Nome *</label>
            <input type="text" className="form-control" value={form.nome} onChange={e => setForm({...form, nome: e.target.value})} required />
          </div>
          <div className="form-group">
            <label>Tipo</label>
            <input type="text" className="form-control" value={form.tipo} onChange={e => setForm({...form, tipo: e.target.value})} placeholder="Ex: Inicial, Crescimento, Terminação" />
          </div>
          <div className="form-group">
            <label>Quantidade Total</label>
            <input type="number" step="0.1" className="form-control" value={form.quantidade_total} onChange={e => setForm({...form, quantidade_total: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Unidade</label>
            <select className="form-control" value={form.unidade} onChange={e => setForm({...form, unidade: e.target.value})}>
              <option value="kg">kg</option>
              <option value="ton">ton</option>
              <option value="saco">saco</option>
            </select>
          </div>
          <div className="form-group">
            <label>Data de Validade</label>
            <input type="date" className="form-control" value={form.data_validade} onChange={e => setForm({...form, data_validade: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Fornecedor</label>
            <input type="text" className="form-control" value={form.fornecedor} onChange={e => setForm({...form, fornecedor: e.target.value})} />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Salvar</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function Saude() {
  const [registros, setRegistros] = useState([]);
  const [suinos, setSuinos] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    suino_id: '',
    tipo: '',
    descricao: '',
    veterinario: ''
  });

  useEffect(() => {
    fetchRegistros();
    fetchSuinos();
  }, []);

  const fetchRegistros = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/saude`);
        const data = await res.json();
        setRegistros(data.data);
        await localforage.setItem('saude', data.data);
      } else {
        const cached = await localforage.getItem('saude');
        if (cached) setRegistros(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('saude');
      if (cached) setRegistros(cached);
    }
  };

  const fetchSuinos = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/suinos`);
        const data = await res.json();
        setSuinos(data.data);
      } else {
        const cached = await localforage.getItem('suinos');
        if (cached) setSuinos(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('suinos');
      if (cached) setSuinos(cached);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (navigator.onLine) {
        await fetch(`${API_BASE}/saude`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form)
        });
      } else {
        const queue = await localforage.getItem('syncQueue') || [];
        queue.push({ action: 'create', table: 'saude', data: form });
        await localforage.setItem('syncQueue', queue);
      }
      setModalOpen(false);
      setForm({ suino_id: '', tipo: '', descricao: '', veterinario: '' });
      fetchRegistros();
    } catch (error) {
      alert('Erro ao salvar: ' + error.message);
    }
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>💊 Registros de Saúde</h2>
          <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
            + Novo Registro
          </button>
        </div>

        {registros.length === 0 ? (
          <div className="empty-state">
            <p>Nenhum registro de saúde ainda.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Suíno</th>
                <th>Tipo</th>
                <th>Descrição</th>
                <th>Data</th>
                <th>Veterinário</th>
              </tr>
            </thead>
            <tbody>
              {registros.map(reg => (
                <tr key={reg.id}>
                  <td><strong>{reg.identificacao}</strong></td>
                  <td>{reg.tipo}</td>
                  <td>{reg.descricao}</td>
                  <td>{reg.data_evento?.split('T')[0]}</td>
                  <td>{reg.veterinario}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Novo Registro de Saúde">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Suíno *</label>
            <select className="form-control" value={form.suino_id} onChange={e => setForm({...form, suino_id: e.target.value})} required>
              <option value="">Selecione</option>
              {suinos.filter(s => s.status === 'ativo').map(s => (
                <option key={s.id} value={s.id}>{s.identificacao}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Tipo *</label>
            <select className="form-control" value={form.tipo} onChange={e => setForm({...form, tipo: e.target.value})} required>
              <option value="">Selecione</option>
              <option value="Vacinação">Vacinação</option>
              <option value="Tratamento">Tratamento</option>
              <option value="Consulta">Consulta</option>
              <option value="Desparasitação">Desparasitação</option>
            </select>
          </div>
          <div className="form-group">
            <label>Descrição *</label>
            <textarea className="form-control" rows="3" value={form.descricao} onChange={e => setForm({...form, descricao: e.target.value})} required />
          </div>
          <div className="form-group">
            <label>Veterinário</label>
            <input type="text" className="form-control" value={form.veterinario} onChange={e => setForm({...form, veterinario: e.target.value})} />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Salvar</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function Relatorios() {
  const [stats, setStats] = useState(null);
  const [suinos, setSuinos] = useState([]);

  useEffect(() => {
    fetchStats();
    fetchSuinos();
  }, []);

  const fetchStats = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/relatorios/resumo`);
        const data = await res.json();
        setStats(data.data);
      } else {
        const cached = await localforage.getItem('stats');
        if (cached) setStats(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('stats');
      if (cached) setStats(cached);
    }
  };

  const fetchSuinos = async () => {
    try {
      if (navigator.onLine) {
        const res = await fetch(`${API_BASE}/suinos`);
        const data = await res.json();
        setSuinos(data.data);
      } else {
        const cached = await localforage.getItem('suinos');
        if (cached) setSuinos(cached);
      }
    } catch (error) {
      const cached = await localforage.getItem('suinos');
      if (cached) setSuinos(cached);
    }
  };

  const exportCSV = () => {
    let csv = 'Identificação,Sexo,Peso Atual,Status\n';
    suinos.forEach(s => {
      csv += `${s.identificacao},${s.sexo},${s.peso_atual},${s.status}\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `suinotech-relatorio-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>📊 Relatórios e Estatísticas</h2>
          <button className="btn btn-primary" onClick={exportCSV}>📥 Exportar CSV</button>
        </div>

        <div className="grid" style={{ marginBottom: '30px' }}>
          <div className="stat-card">
            <div className="stat-value">{stats?.total_suinos || 0}</div>
            <div className="stat-label">Total de Suínos</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats?.machos || 0}</div>
            <div className="stat-label">Machos</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats?.femeas || 0}</div>
            <div className="stat-label">Fêmeas</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats?.peso_total ? stats.peso_total.toFixed(1) : 0} kg</div>
            <div className="stat-label">Peso Total</div>
          </div>
        </div>

        {suinos.length > 0 && (
          <>
            <h3 style={{ marginBottom: '15px', color: '#555' }}>Peso Médio por Lote</h3>
            <div className="card" style={{ background: '#f9f9f9' }}>
              <p><strong>Peso médio geral:</strong> {suinos.length > 0 ? (suinos.reduce((sum, s) => sum + (s.peso_atual || 0), 0) / suinos.length).toFixed(2) : 0} kg</p>
              <p><strong>Suíno mais pesado:</strong> {suinos.length > 0 ? Math.max(...suinos.map(s => s.peso_atual || 0)) : 0} kg</p>
              <p><strong>Suíno mais leve:</strong> {suinos.length > 0 ? Math.min(...suinos.filter(s => s.peso_atual).map(s => s.peso_atual)) : 0} kg</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div className={`modal ${isOpen ? 'active' : ''}`} onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  );
}

export default App;
