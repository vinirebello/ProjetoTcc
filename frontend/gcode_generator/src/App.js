import React, { useState, useRef } from 'react';
import './App.css';

function App() {
  // Estado para o G-code
  const [gCode, setGCode] = useState('');
  
  // --- NOVOS ESTADOS PARA OS PARÂMETROS ---
  const [units, setUnits] = useState('G21'); // G21 = mm, G20 = polegadas
  const [spindleSpeed, setSpindleSpeed] = useState(1200); // RPM
  const [feedRate, setFeedRate] = useState(500); // Avanço (mm/min)
  const [safetyZ, setSafetyZ] = useState(5.0); // Altura de segurança Z
  const [cutDepth, setCutDepth] = useState(-1.0); // Profundidade de corte Z
  
  // Referência para o input de arquivo escondido
  const fileInputRef = useRef(null);

  // Função chamada quando um arquivo é selecionado
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    console.log("Arquivo selecionado:", file.name);
    console.log("Parâmetros:", { units, spindleSpeed, feedRate, safetyZ, cutDepth });

    // --- SIMULAÇÃO USANDO OS PARÂMETROS DO ESTADO ---
    // No seu TCC, você enviaria esses parâmetros junto com a imagem
    // para o seu backend Python.
    const simulatedGCode = `(Código G-code gerado para: ${file.name})
${units} ; Define unidades (${units === 'G21' ? 'milímetros' : 'polegadas'})
G90 ; Define modo de coordenada absoluta
M03 S${spindleSpeed} ; Liga o spindle a ${spindleSpeed} RPM
G00 Z${safetyZ} ; Move rápido para a altura de segurança
G00 X10 Y10 ; Move para o ponto inicial (X:10, Y:10)
G01 Z${cutDepth} F${feedRate / 2} ; Mergulha no material (avanço de mergulho mais lento)
G01 X50 Y10 F${feedRate} ; Corta uma linha reta com avanço ${feedRate}
G01 X50 Y50
G01 X10 Y50
G01 X10 Y10
G00 Z${safetyZ} ; Retrai a ferramenta
M05 ; Desliga o spindle
M30 ; Fim do programa`;
    
    setGCode(simulatedGCode);
  };

  // Função para acionar o clique no input de arquivo
  const handleButtonClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="container">
      <header className="header">
        <h1>G-code Automator</h1>
      </header>
      
      <main className="content">
        
        {/* Coluna da Esquerda: Botão + Formulário */}
        <div className="left-column">
          
          {/* Botão de Upload */}
          <button className="upload-button" onClick={handleButtonClick}>
            Escolher Imagem (PNG/JPG)
          </button>

          {/* Input de arquivo real escondido */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
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
          {/* --- FIM DA NOVA ÁREA --- */}

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