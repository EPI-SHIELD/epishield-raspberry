# Integração segura com confirmação temporal de EPI

Plano aprovado: webcam USB → Raspberry Pi 4 / Edge Impulse → API → dashboard.
Piloto supervisionado, uma pessoa por vez, iniciado pelo operador; sem acionamento físico.

## Regra versionada v1
- Dez capturas novas após a solicitação, sequenciais, ao longo de pelo menos três segundos.
- Cada EPI conta no máximo uma vez por captura, com confiança >= 0,80.
- Cada EPI obrigatório precisa de pelo menos oito confirmações. Não há média entre EPIs.
- Todos confirmados: allowed. Caso contrário: blocked / EPI não confirmado, sem afirmar ausência.
- Erros de captura/inferência não são votos negativos. Dez amostras devem terminar em 60 segundos.
- Congelar regra, modelo e EPIs obrigatórios por inspeção; guardar evidências e contagens.

## Preservação da placa
- Branch codex/raspberry-integration nos três projetos antes de editar; preservar trabalho existente.
- Diagnóstico somente leitura; pasta nova exclusiva e ambiente Python isolado.
- Sem sudo automático, formatação, remoção de arquivos, atualização global, boot, SSH ou firewall.
- Execução manual e encerramento por Ctrl+C; webcam e subprocessos liberados.
- Filas e fotos apenas em memória limitada na placa. Nenhum segredo administrativo/Edge Impulse.
- Modelo .eim por arquitetura, versão/hash verificados e classes validadas antes da avaliação.

## Contratos e segurança
- Conexões somente de saída, HTTPS com certificado validado, Ethernet/Wi-Fi/servidor autorizado.
- Credenciais com hash, expiração, revogação e escopo por agente/setor; operador/admin separados.
- Dashboard autenticado, segredos apenas em memória, fotos protegidas, CORS explícito.
- POST /agents/{id}/inspections; GET /inspections/{id}; GET /edge/inspections/next.
- POST /edge/inspections/{id}/result; POST /edge/heartbeat; PUT /edge/preview;
  GET /agents/{id}/preview. Progresso/falha serão extensões autenticadas do contrato.
- API calcula resultado, valida lote/foto e garante um evento por inspeção; reenvio idêntico é idempotente.
- Migrations aditivas; histórico legado identificado; mocks apenas no perfil development.
- Foto ilustrativa: captura com menos EPIs confirmados (primeira em empate).

## Operação
- Botão Inspecionar, progresso 0/10, confirmação por equipamento e repetição após ajuste de posição.
- Prévia JPEG 640x480 até 2 fps somente sob demanda; último frame em memória expira em 10 s.
- API armazena uma foto por inspeção, quota de 500 MB; ao atingir quota, rejeitar sem apagar arquivos.
- Heartbeat 10 s, offline 30 s, uma inspeção ativa por agente, expiração 60 s.
- Reenvio com espera progressiva; perda em reinício resulta em expiração, nunca evento inventado.

## Validação
- Limites 0,80 / 8 de 10, duplicatas, conjunto obrigatório, sequência/tempo, lote incompleto.
- Autorização, isolamento, revogação, uploads, idempotência, falhas de rede e preservação de arquivos.
- Modelo real/webcam e ensaio de 30 min: CPU, memória, temperatura, latência.
- Calibração com sessões rotuladas separadas da validação; medir falsos positivos/negativos e
  liberações indevidas. Concordância temporal/confiança NÃO é precisão comprovada.

## Pendências externas
Sistema, arquitetura, modelo e acesso à placa ainda precisam ser fornecidos. Não instalar nada
na Raspberry sem diagnóstico e autorização do responsável para dependências ausentes.
