(TCC_Exemplo_Retangulo)
G21 ; Define unidades
G90 ; Coordenadas absolutas
M03 S1200 ; Liga spindle
G00 Z10.000 ; Move para Z de segurança
G00 X0.000 Y76.751
G01 Z-9.000 F75.0
G01 X0.000 Y0.000 F150.0
G01 X99.720 Y0.000 F150.0
G01 X99.720 Y76.751 F150.0
G01 X0.000 Y76.751 F150.0
G00 Z10.000 ; Retrai ferramenta
M05 ; Desliga spindle
M30 ; Fim do programa