import React, { useState, useRef } from 'react';
import './App.css';

function App() {
  // Estado para o G-code
  const [gCode, setGCode] = useState('');
  
  // --- NOVOS ESTADOS PARA OS PARÂMETROS ---
  const[selectedFile, setSelectedFile] = useState(null)
  const [units, setUnits] = useState('G21'); // G21 = mm, G20 = polegadas
  const [spindleSpeed, setSpindleSpeed] = useState(1200); // RPM
  const [feedRate, setFeedRate] = useState(500); // Avanço (mm/min)
  const [safetyZ, setSafetyZ] = useState(5.0); // Altura de segurança Z
  const [cutDepth, setCutDepth] = useState(-1.0); // Profundidade de corte Z
  
  // Referência para o input de arquivo escondido
  const fileInputRef = useRef(null);

  // Função chamada quando um arquivo é selecionado
  const handleCreateButton = async () => { // <--- Tornou-se async
    const file = selectedFile;
    if (!file) {
      setGCode("(ERRO: Por favor, escolha um arquivo de imagem primeiro.)");
      return;
    }

    console.log("Enviando para o backend:", file.name);
    console.log("Parâmetros:", { units, spindleSpeed, feedRate, safetyZ, cutDepth });

    // 1. Criar um FormData para enviar arquivo + campos
    const formData = new FormData();
    formData.append('file', file); // A chave 'file' deve ser a mesma do FastAPI
    
    // Adiciona os parâmetros. As chaves devem ser as mesmas do FastAPI
    formData.append('units', units);
    formData.append('spindleSpeed', spindleSpeed);
    formData.append('feedRate', feedRate);
    formData.append('safetyZ', safetyZ);
    formData.append('cutDepth', cutDepth);

    // Limpa o G-code antigo e mostra um 'loading'
    setGCode("(Processando imagem com OpenCV e gerando G-code...)");

    try {
      // 2. Fazer a chamada de API para o backend
      const response = await fetch('http://localhost:8000/api/generate-gcode', {
        method: 'POST',
        body: formData,
        // Não defina 'Content-Type', o browser faz isso
        // automaticamente para FormData (incluindo o 'boundary')
      });

      // 3. Lidar com a resposta
      if (!response.ok) {
        // Se a resposta não foi OK, leia a mensagem de erro como TEXTO
        const errorText = await response.text();
        
        // Tenta fazer o parse do erro (FastAPI envia JSON para erros)
        try {
           const errorJson = JSON.parse(errorText);
           setGCode(`(ERRO DO BACKEND: ${errorJson.detail || errorText})`);
        } catch (e) {
           // Se não for JSON, mostre o texto do erro
           setGCode(`(ERRO DO BACKEND: ${errorText})`);
        }

      } else {
        // Sucesso! A resposta é JSON (uma string JSON)
        // Usar response.json() faz o parse automático da string JSON
        // para uma string JavaScript, que o textarea entende.
        const gcodeString = await response.json(); 
        setGCode(gcodeString);
      }

    } catch (error) {
      console.error("Erro ao conectar com o backend:", error);
      setGCode(`(ERRO DE CONEXÃO: Não foi possível conectar ao backend em http://localhost:8000. Você iniciou o servidor Python?)`);
    }
  };

  const handleFileSelected = (event) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      setSelectedFile(file);
      console.log("Arquivo armazenado:", file.name);
    }
  };

  const handleUploadButtonClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="container">
      <header className="header">
        <h1>G-code Automator</h1>
      </header>
      
      <main className="content">
        
        <div className="left-column">
          
          <button className="upload-button" onClick={handleUploadButtonClick}>
            Escolher Imagem (PNG/JPG)
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
          
          {/* --- NOVA ÁREA DE PARÂMETROS --- */}
          <div className="parameters-form">
            <h3>Parâmetros Iniciais</h3>
            
            <div className="form-group">
              <label>Unidades</label>
              <select value={units} onChange={e => setUnits(e.target.value)}>
                <option value="G21">Milímetros (G21)</option>
                <option value="G20">Polegadas (G20)</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Veloc. Spindle (RPM)</label>
              <input type="number" value={spindleSpeed} onChange={e => setSpindleSpeed(e.target.value)} />
            </div>
            
            <div className="form-group">
              <label>Avanço de Corte (mm/min)</label>
              <input type="number" value={feedRate} onChange={e => setFeedRate(e.target.value)} />
            </div>
            
            <div className="form-group">
              <label>Altura Segurança (Z)</label>
              <input type="number" step="0.1" value={safetyZ} onChange={e => setSafetyZ(e.target.value)} />
            </div>
            
            <div className="form-group">
              <label>Profundidade Corte (Z)</label>
              <input type="number" step="0.1" value={cutDepth} onChange={e => setCutDepth(e.target.value)} />
            </div>
          </div>

          <button className="create-button" onClick={handleCreateButton}> 
              Gerar código
          </button>

        </div>

        {/* Coluna da Direita: Caixa de G-code */}
        <textarea
          className="gcode-textarea"
          value={gCode}
          readOnly
          placeholder="O código G-code gerado aparecerá aqui..."
        />
      </main>
    </div>
  );
}

export default App;