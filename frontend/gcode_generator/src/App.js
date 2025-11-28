import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {

  const [gCode, setGCode] = useState('');
  const [selectedFile, setSelectedFile] = useState(null)
  
  // Estados do Formulário
  const [spindleSpeed, setSpindleSpeed] = useState(1200); 
  const [feedRate, setFeedRate] = useState(500); 
  const [safetyZ, setSafetyZ] = useState(5.0); 
  const [thickness, setThickness] = useState(10.0); // Ajustei padrão para positivo para facilitar
  const [stepDown, setStepDown] = useState(2.0); 
  
  // Novo Estado para o Histórico
  const [historyList, setHistoryList] = useState([]);
  
  const fileInputRef = useRef(null);

  // --- 1. Buscar Histórico ao Iniciar ---
  const fetchHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/history');
      if (response.ok) {
        const data = await response.json();
        setHistoryList(data);
      }
    } catch (error) {
      console.error("Erro ao buscar histórico:", error);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleLoadHistory = (item) => {

    setSpindleSpeed(item.params.spindleSpeed);
    setFeedRate(item.params.feedRate);
    setSafetyZ(item.params.safetyZ);
    setThickness(item.params.thickness);
    setStepDown(item.params.stepDown);
    
    setGCode(item.gcode);
    
    setSelectedFile(null); 
  };

  const handleDeleteHistory = async (e, id) => {
    e.stopPropagation(); 
    if(!window.confirm("Deseja deletar este registro?")) return;

    try {
        await fetch(`http://localhost:8000/api/history/${id}`, { method: 'DELETE' });
        fetchHistory(); 
    } catch (error) {
        console.error("Erro ao deletar", error);
    }
  };

  const handleCreateButton = async () => { 
    const file = selectedFile;
    if (!file) {
      setGCode("(ERRO: Por favor, escolha um arquivo de imagem primeiro.)");
      return;
    }

    const formData = new FormData();
    formData.append('file', file); 
    formData.append('spindleSpeed', spindleSpeed);
    formData.append('feedRate', feedRate);
    formData.append('safetyZ', safetyZ);
    formData.append('thickness', thickness);
    formData.append('stepDown', stepDown)

    setGCode("(Processando imagem e salvando no banco...)");

    try {
      const response = await fetch('http://localhost:8000/api/generate-gcode', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        setGCode(`(ERRO: ${errorText})`);
      } else {
        const data = await response.json(); 
        setGCode(data.gcode);
        
        fetchHistory();
      }

    } catch (error) {
      console.error("Erro:", error);
      setGCode(`(ERRO DE CONEXÃO)`);
    }
  };

  const handleFileSelected = (event) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      setSelectedFile(file);
    }
  };

  const handleUploadButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleExportGCode = () => {
    if (!gCode) return; 
    const blob = new Blob([gCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    let fileName = 'projeto.gcode';
    if (selectedFile && selectedFile.name) {
      const nameWithoutExt = selectedFile.name.split('.').slice(0, -1).join('.');
      fileName = `${nameWithoutExt}.gcode`;
    }
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>G-code Generator</h1>
      </header>
      
      <div className="main-layout">
        
        <aside className="sidebar">
            <h3>Histórico</h3>
            <div className="history-list">
                {historyList.length === 0 && <p style={{fontSize:'0.8rem', color:'#666'}}>Nenhum registro.</p>}
                
                {historyList.map((item) => (
                    <div key={item.id} className="history-item" onClick={() => handleLoadHistory(item)}>
                        <div className="history-info">
                            <strong>{item.filename}</strong>
                            <span>{item.timestamp}</span>
                        </div>
                        <button className="delete-btn" onClick={(e) => handleDeleteHistory(e, item.id)}>
                            X
                        </button>
                    </div>
                ))}
            </div>
        </aside>

        <main className="content">
          
          <div className="left-column">
            
            <button className="upload-button" onClick={handleUploadButtonClick}>
              Escolher Nova Imagem
            </button>
            
            {selectedFile && (
              <span className="file-name-display">
                Arquivo: {selectedFile.name}
              </span>
            )}

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelected}
              accept=".png, .jpeg, .jpg"
              style={{ display: 'none' }} 
            />
            
            <div className="parameters-form">
              <h3>Configuração</h3>
              
              <div className="form-group">
                <label>Veloc. Spindle (RPM)</label>
                <input type="number" value={spindleSpeed} onChange={e => setSpindleSpeed(e.target.value)} />
              </div>
              
              <div className="form-group">
                <label>Avanço (mm/min)</label>
                <input type="number" value={feedRate} onChange={e => setFeedRate(e.target.value)} />
              </div>
              
              <div className="form-group">
                <label>Z Segurança (mm)</label>
                <input type="number" step="0.1" value={safetyZ} onChange={e => setSafetyZ(e.target.value)} />
              </div>
              
              <div className="form-group">
                <label>Espessura Peça (mm)</label>
                <input type="number" step="0.1" value={thickness} onChange={e => setThickness(e.target.value)} />
              </div>

              <div className="form-group">
                <label>Passo Z (Step Down)</label>
                <input 
                  type="number" 
                  step="0.1" 
                  value={stepDown} 
                  onChange={e => setStepDown(e.target.value)}
                />
              </div>
            </div>

            <button className="create-button" onClick={handleCreateButton}> 
                Gerar G-Code
            </button>

          </div>

          <div className="right-column">
            <textarea
              className="gcode-textarea"
              value={gCode}
              placeholder="O código G-code aparecerá aqui..."
              readOnly
            />
            
            {gCode && (
              <button className="export-button" onClick={handleExportGCode}>
                Baixar .gcode
              </button>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;