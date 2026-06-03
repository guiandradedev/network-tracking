import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './App.css';

// --- Interfaces Limpas ---
interface Host {
  host: string;
  status: string;
  MAC?: string;
  fabricante?: string;
}

interface GrowthStats {
  current_avg: number;
  previous_avg: number;
  growth_absolute: number;
  growth_percentage: number;
}

interface TimeData {
  time: string;
  active_devices: number;
}

interface PeakActivity {
  timestamp: string;
  total_active: number;
}

interface DeviceHistory {
  mac_address: string;
  frequency_percentage: number;
  total_uptime_events: number;
  timeline: { timestamp: string; status: string }[];
}

function App() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dbError, setDbError] = useState<string | null>(null);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'up' | 'down'>('all');

  const [growthStats, setGrowthStats] = useState<GrowthStats | null>(null);
  const [timeStats, setTimeStats] = useState<TimeData[]>([]);
  const [peakStats, setPeakStats] = useState<PeakActivity[]>([]);

  const [selectedDevice, setSelectedDevice] = useState<DeviceHistory | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchDatabaseStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/health/database');
      if (!response.ok) {
        const data = await response.json();
        setDbError(data.message || 'Falha ao conectar ao banco de dados');
      } else {
        setDbError(null);
      }
    } catch (err) {
      setDbError('Não foi possível verificar a conexão com o banco de dados');
    }
  };

  const fetchHosts = async () => {
    try {
      const response = await fetch('http://localhost:8000/');
      if (!response.ok) throw new Error('Falha ao buscar hosts');
      const data: Host[] = await response.json();
      setHosts(data);
      setError(null);
    } catch (err) {
      setError('Falha de conexão com o backend (http://localhost:8000).');
    }
  };

  const fetchDashboardStats = async () => {
    try {
      const [growthRes, timeRes, peakRes] = await Promise.all([
        fetch('http://localhost:8000/api/stats/growth'),
        fetch('http://localhost:8000/api/stats/active-by-time'),
        fetch('http://localhost:8000/api/stats/peak-activity')
      ]);
      setGrowthStats(await growthRes.json());
      setTimeStats(await timeRes.json());
      setPeakStats(await peakRes.json());
    } catch (err) {
      console.error("Erro ao carregar estatísticas", err);
    }
  };

  const fetchDeviceHistory = async (mac: string) => {
    setLoadingHistory(true);
    try {
      const response = await fetch(`http://localhost:8000/api/device/${mac}/history`);
      if (response.ok) setSelectedDevice(await response.json());
    } catch (err) {
      console.error("Erro ao carregar histórico");
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    await Promise.all([fetchHosts(), fetchDashboardStats(), fetchDatabaseStatus()]);
    setLoading(false);
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(() => {
      fetchHosts();
      fetchDashboardStats();
      fetchDatabaseStatus();
    }, 15000); 
    return () => clearInterval(interval);
  }, []);

  const filteredHosts = hosts.filter(host => {
    const matchesSearch = 
      host.host.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (host.MAC && host.MAC.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (host.fabricante && host.fabricante.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = filterStatus === 'all' || 
      (filterStatus === 'up' && host.status === 'up') ||
      (filterStatus === 'down' && host.status !== 'up');
    return matchesSearch && matchesStatus;
  }).sort((a, b) => a.host.localeCompare(b.host));

  const upCount = hosts.filter(h => h.status === 'up').length;

  return (
    <div className="app-wrapper">
      <div className="max-width-container">
        
        {/* --- HEADER --- */}
        <header className="app-header">
          <div>
            <h1 className="header-title">
              NetScanner
            </h1>
            <p className="header-subtitle">Monitoramento de Ativos de Rede</p>
          </div>
          <button onClick={loadAllData} className="btn-primary">
            Atualizar Dados
          </button>
        </header>

        {/* --- ALERTAS --- */}
        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        {dbError && (
          <div className="alert alert-warning">
            <span>⚠️</span>
            <div>
              <strong>Aviso:</strong> {dbError}
            </div>
          </div>
        )}

        {/* --- WIDGETS DE RESUMO --- */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Dispositivos Online</div>
            <div className="stat-value text-success">
              {upCount} <span>/ {hosts.length}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Variação (Última Hora)</div>
            <div className="stat-value-group">
              <div className="stat-value text-white">
                {(growthStats?.growth_absolute ?? 0) > 0 ? '+' : ''}{growthStats?.growth_absolute ?? 0}
              </div>
              <div style={{ fontWeight: 500, fontSize: '0.875rem' }} className={(growthStats?.growth_percentage ?? 0) >= 0 ? 'text-success' : 'text-danger'}>
                ({growthStats?.growth_percentage ?? 0}%)
              </div>
            </div>
          </div>

          <div className="stat-card span-2">
            <div className="stat-label">Último Grande Pico de Atividade</div>
            {peakStats.length > 0 ? (
              <div className="stat-value-group">
                <div className="stat-value text-primary">
                  {peakStats[0].total_active} <span>hosts</span>
                </div>
                <div style={{ borderLeft: '1px solid var(--border-light)', paddingLeft: '1rem', marginLeft: '1rem' }}>
                  <div style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>
                    {new Date(peakStats[0].timestamp).toLocaleDateString('pt-BR')}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-darker)' }}>
                    {new Date(peakStats[0].timestamp).toLocaleTimeString('pt-BR')}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-darker)', fontSize: '0.875rem' }}>Aguardando dados...</div>
            )}
          </div>
        </div>

        {/* --- GRÁFICO TEMPORAL --- */}
        <div className="chart-card">
           <div className="stat-label" style={{ marginBottom: '1rem' }}>Média de Hosts Ativos (24h)</div>
           <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeStats} margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                  <defs>
                    <linearGradient id="colorActive" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} dy={10} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                    itemStyle={{ color: '#60a5fa' }}
                  />
                  <Area type="monotone" dataKey="active_devices" name="Média Ativos" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorActive)" />
                </AreaChart>
              </ResponsiveContainer>
           </div>
        </div>

        {/* --- TABELA DE DISPOSITIVOS --- */}
        <div className="data-section">
          <div className="data-controls">
            <input
              type="text"
              placeholder="Buscar IP, MAC, Vendor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-control search-input"
            />
            <select 
              className="input-control select-filter"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
            >
              <option value="all">Todos os Status</option>
              <option value="up">Apenas Online</option>
              <option value="down">Apenas Offline</option>
            </select>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th>MAC / Fabricante</th>
                  <th>Status</th>
                  <th className="text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {loading && hosts.length === 0 ? (
                  <tr><td colSpan={4} className="text-center" style={{ color: 'var(--text-darker)' }}>Carregando dispositivos...</td></tr>
                ) : filteredHosts.length === 0 ? (
                  <tr><td colSpan={4} className="text-center" style={{ color: 'var(--text-darker)' }}>Nenhum dispositivo encontrado.</td></tr>
                ) : (
                  filteredHosts.map((host, idx) => (
                    <tr key={idx} className="row-hover">
                      <td className="font-mono" style={{ fontWeight: 500, color: '#fff' }}>{host.host}</td>
                      <td>
                        {host.MAC ? (
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span className="font-mono text-muted">{host.MAC}</span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-darker)' }}>{host.fabricante || 'Desconhecido'}</span>
                          </div>
                        ) : <span style={{ color: 'var(--text-darker)' }}>-</span>}
                      </td>
                      <td>
                        <span className={`badge ${host.status === 'up' ? 'badge-up' : 'badge-down'}`}>
                          {host.status}
                        </span>
                      </td>
                      <td className="text-right">
                        {host.MAC && (
                          <button 
                            onClick={() => fetchDeviceHistory(host.MAC!)}
                            className="btn-outline"
                          >
                            Histórico
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* --- MODAL DE HISTÓRICO --- */}
      {selectedDevice && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <div>
                <h3 className="modal-title">Histórico do Ativo</h3>
                <p className="modal-subtitle font-mono">{selectedDevice.mac_address}</p>
              </div>
              <button onClick={() => setSelectedDevice(null)} className="btn-close">✕</button>
            </div>
            
            <div className="modal-body custom-scrollbar">
              {loadingHistory ? (
                <div className="text-center" style={{ padding: '2.5rem 0', color: 'var(--text-darker)' }}>Buscando registros...</div>
              ) : (
                <>
                  <div className="modal-summary">
                    <div>
                      <div className="summary-label">Frequência (24h)</div>
                      <div className="stat-value text-primary">{selectedDevice.frequency_percentage}%</div>
                    </div>
                    <div className="summary-divider"></div>
                    <div>
                      <div className="summary-label">Scans Válidos</div>
                      <div className="stat-value text-white">{selectedDevice.total_uptime_events}</div>
                    </div>
                  </div>

                  <h4 style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-darker)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Timeline Recente</h4>
                  <div className="timeline-list">
                    {selectedDevice.timeline.length > 0 ? selectedDevice.timeline.map((event, idx) => {
                      const d = new Date(event.timestamp);
                      return (
                        <div key={idx} className="timeline-item">
                          <div className={`timeline-dot ${event.status === 'up' ? 'dot-up' : 'dot-down'}`}></div>
                          <span className="font-mono timeline-time">{d.toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'})}</span>
                          <span className="timeline-date">{d.toLocaleDateString('pt-BR')}</span>
                          <span className="timeline-status">{event.status}</span>
                        </div>
                      )
                    }) : (
                      <div className="text-center" style={{ color: 'var(--text-darker)', padding: '1rem 0' }}>Sem registros.</div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;