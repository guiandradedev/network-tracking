import { useState, useEffect } from 'react'
import './App.css'

interface Port {
  port: string;
  state: string;
  name: string;
  product?: string;
  version?: string;
  extrainfo?: string;
}

interface Protocol {
  0: string; // protocol name (tcp/udp)
  1: Port[];
}

interface Host {
  host: string;
  status: string;
  MAC?: string;
  fabricante?: string;
  protocols: Protocol[];
  lastUpdated?: string;
}

function App() {
  const [hosts, setHosts] = useState<Host[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'up' | 'down'>('all')

  const fetchHosts = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/')
      
      if (!response.ok) {
        throw new Error('Failed to fetch hosts')
      }
      
      const data: Host[] = await response.json()
      setHosts(data)
      setError(null)
    } catch (err) {
      setError('Erro ao conectar com o servidor. Verifique se o backend está rodando na porta 8000.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHosts()
    
    // Refresh every 10 seconds
    const interval = setInterval(fetchHosts, 10000)
    
    return () => clearInterval(interval)
  }, [])

  const filteredHosts = hosts
    .filter(host => {
      const matchesSearch = 
        host.host.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (host.MAC && host.MAC.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (host.fabricante && host.fabricante.toLowerCase().includes(searchTerm.toLowerCase()))
      
      const matchesStatus = 
        filterStatus === 'all' || 
        (filterStatus === 'up' && host.status === 'up') ||
        (filterStatus === 'down' && host.status !== 'up')
      
      return matchesSearch && matchesStatus
    })
    .sort((a, b) => a.host.localeCompare(b.host))

  const upCount = hosts.filter(h => h.status === 'up').length
  const totalCount = hosts.length

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-emerald-400 flex items-center gap-3">
              🌐 Network Scanner
            </h1>
            <p className="text-gray-400 mt-1">Monitoramento em tempo real da rede local</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="bg-gray-900 px-4 py-2 rounded-xl text-sm">
              <span className="text-emerald-400 font-mono">{upCount}</span>
              <span className="text-gray-500"> / </span>
              <span className="font-mono">{totalCount}</span>
              <span className="text-gray-400 ml-2">hosts ativos</span>
            </div>
            
            <button 
              onClick={fetchHosts}
              className="bg-emerald-600 hover:bg-emerald-500 px-5 py-2 rounded-xl flex items-center gap-2 transition-colors"
            >
              🔄 Atualizar
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <input
            type="text"
            placeholder="Buscar por IP, MAC ou fabricante..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 focus:outline-none focus:border-emerald-500 text-white"
          />
          
          <div className="flex gap-2">
            <button 
              onClick={() => setFilterStatus('all')}
              className={`px-5 py-3 rounded-xl transition-all ${filterStatus === 'all' ? 'bg-white text-black' : 'bg-gray-900 hover:bg-gray-800'}`}
            >
              Todos
            </button>
            <button 
              onClick={() => setFilterStatus('up')}
              className={`px-5 py-3 rounded-xl transition-all ${filterStatus === 'up' ? 'bg-emerald-500 text-black' : 'bg-gray-900 hover:bg-gray-800'}`}
            >
              Ativos
            </button>
            <button 
              onClick={() => setFilterStatus('down')}
              className={`px-5 py-3 rounded-xl transition-all ${filterStatus === 'down' ? 'bg-rose-500 text-black' : 'bg-gray-900 hover:bg-gray-800'}`}
            >
              Inativos
            </button>
          </div>
        </div>

        {loading && hosts.length === 0 && (
          <div className="flex justify-center py-20">
            <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-950 border border-red-800 text-red-400 p-6 rounded-2xl mb-8">
            {error}
            <button 
              onClick={fetchHosts}
              className="ml-4 underline hover:text-red-300"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {/* Hosts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredHosts.map((host, index) => (
            <div 
              key={index} 
              className="bg-gray-900 border border-gray-800 rounded-3xl overflow-hidden hover:border-emerald-500/30 transition-all group"
            >
              <div className="p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono text-2xl text-white">{host.host}</div>
                    {host.MAC && (
                      <div className="font-mono text-sm text-gray-500 mt-1">{host.MAC}</div>
                    )}
                  </div>
                  
                  <div className={`px-4 py-1.5 rounded-full text-xs font-medium uppercase tracking-wider ${
                    host.status === 'up' 
                      ? 'bg-emerald-500/20 text-emerald-400' 
                      : 'bg-gray-700 text-gray-400'
                  }`}>
                    {host.status}
                  </div>
                </div>

                {host.fabricante && (
                  <div className="mt-4 text-sm text-gray-400">
                    🏭 {host.fabricante}
                  </div>
                )}
              </div>

              {/* Ports */}
              <div className="border-t border-gray-800 bg-gray-950 p-6">
                <div className="uppercase text-xs tracking-widest text-gray-500 mb-4">Portas abertas</div>
                
                {host.protocols && host.protocols.length > 0 ? (
                  <div className="space-y-6">
                    {host.protocols.map((proto, pIndex) => (
                      <div key={pIndex}>
                        <div className="text-emerald-400 text-sm mb-2 font-medium">
                          {proto[0].toUpperCase()}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                          {proto[1].map((port, portIndex) => (
                            <div 
                              key={portIndex}
                              className="bg-gray-900 rounded-xl p-3 text-sm"
                            >
                              <div className="flex justify-between">
                                <span className="font-mono text-emerald-400">:{port.port}</span>
                                <span className="text-gray-500">{port.state}</span>
                              </div>
                              {port.name && (
                                <div className="text-gray-400 text-xs mt-1 truncate">
                                  {port.name}
                                </div>
                              )}
                              {port.product && (
                                <div className="text-amber-400 text-xs mt-0.5 truncate">
                                  {port.product}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm py-8 text-center">
                    Nenhuma porta detectada
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {filteredHosts.length === 0 && !loading && (
          <div className="text-center py-20 text-gray-500">
            Nenhum host encontrado com os filtros aplicados.
          </div>
        )}

        <div className="text-center text-xs text-gray-600 mt-12">
          Backend: Flask + nmap • Atualização automática a cada 10s • MongoDB
        </div>
      </div>
    </div>
  )
}

export default App