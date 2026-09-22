# Protocolo de calibração e aceitação do piloto

1. Identifique modelo/hash, classes, arquitetura, webcam, versão do software e regra temporal-v1.
2. Faça sessões supervisionadas com e sem cada EPI, variando luz, distância, posição e oclusão.
   Mantenha uma pessoa na janela. Não trate frames vizinhos como observações independentes.
3. Registre verdade por EPI e resultado da inspeção, incluindo falhas técnicas separadamente.
   Campos sugeridos: sessao, divisao(calibracao/validacao), inspection_id, label, presente_real,
   confirmado, hits, total, modelo, regra, latencia_ms. Não registre identidade de pessoas.
4. Separe sessões inteiras para calibração e validação. Não escolha limiares usando a validação.
5. Calcule VP/FP/VN/FN por EPI; precisão=VP/(VP+FP), sensibilidade=VP/(VP+FN), taxa de falsa
   confirmação=FP/(FP+VN). Denominador zero deve aparecer como não disponível.
6. Meça liberações indevidas por inspeção: allowed quando algum EPI obrigatório estava ausente.
   Compare com o resultado que uma única captura da mesma inspeção produziria.
7. Relate tamanho da amostra e intervalos de incerteza; não prometa 80% de acerto a partir do
   limiar de confiança de 80%. Capture correlação temporal como limitação explícita.
8. Rode 30 minutos com inferência, prévia e falhas de rede controladas. Observe CPU, memória,
   temperatura e latência com ferramentas de leitura já disponíveis. Não instale monitor global.
9. Verifique que só arquivos próprios da instalação foram criados e que não há gravação de fotos
   na placa; pressione Ctrl+C e confirme webcam liberada. Não remova arquivos para verificar.

Aceite funcional: exatamente um evento por inspeção concluída, nenhuma liberação por falha técnica,
sem vazamento entre agentes, memória sem crescimento sustentado e sem alterações fora da instalação.
Qualidade do modelo só será aceita após os responsáveis analisarem métricas reais. Até lá, uso
supervisionado e demonstrativo, sem controle físico de acesso.
