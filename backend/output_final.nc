%
O1001 (teste_tcc.nc)
(GERADO AUTOMATICAMENTE - VERIFICAR D1 NO CONTROLADOR)
G21 ; Milimetros
G17 G40 G49 G80 G90 ; Config de Seguranca
T1 M6 ; Troca Ferramenta 1
G54 ; Offset de Trabalho
S1500 M3 ; Liga Spindle
M8 ; Liga Refrigerante
G00 X-20.000 Y-20.000 ; Ponto de espera seguro
G43 H1 Z50.0 ; Compensa Altura
G00 Z5.0 ; Desce rapido para perto da peca
; --- Passada Z = -2.00 ---
G00 X-20.000 Y-20.000
G01 Z-2.000 F240.0
G01 G41 D1 X0.000 Y77.679 F800.0
G01 X0.000 Y0.000
G01 X149.665 Y0.000
G01 X149.665 Y77.679
G01 X0.000 Y77.679
G01 X-20.000 Y-20.000
G40 ; Cancela compensacao
G00 Z5.0 ; Retracao entre passes
; --- Passada Z = -2.50 ---
G00 X-20.000 Y-20.000
G01 Z-2.500 F240.0
G01 G41 D1 X0.000 Y77.679 F800.0
G01 X0.000 Y0.000
G01 X149.665 Y0.000
G01 X149.665 Y77.679
G01 X0.000 Y77.679
G01 X-20.000 Y-20.000
G40 ; Cancela compensacao
G00 Z5.0 ; Retracao entre passes
M9 ; Desliga Refrigerante
M5 ; Desliga Spindle
G00 Z50.0 ; Sobe Z total
G91 G28 Z0. ; Home Z
G28 X0. Y0. ; Home Mesa
M30 ; Fim
%