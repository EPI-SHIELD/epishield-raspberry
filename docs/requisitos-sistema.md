# Requisitos para colocar o sistema em funcionamento

## O que já está definido

- Uma Raspberry Pi 4 emprestada, webcam USB, uma pessoa por vez e operador no dashboard.
- Inspeção manual: 10 capturas ao longo de pelo menos 3 segundos; cada EPI exige 8 confirmações
  com confiança >= 80%. Prazo máximo 60 segundos. Sem acionamento físico de portas.
- Raspberry: captura/inferência/prévia. Computador ou servidor: API e PostgreSQL.
- Prévia até 2 fps, JPEG 640x480, pausada durante inspeções. Não há gravação de vídeo.

## Hardware e desempenho — confirmar antes do piloto

| Item | Requisito/verificação |
|---|---|
| Placa | Raspberry Pi 4; RAM e arquitetura ainda não informadas |
| Sistema | Linux compatível com o modelo EIM e Python >=3.10; não reinstalar automaticamente |
| Webcam | USB compatível com V4L2, acesso permitido ao usuário e captura 640x480 |
| Alimentação | Fonte adequada à placa e webcam, sem sinais de subtensão durante teste |
| Temperatura | Refrigeração suficiente para evitar queda sustentada de desempenho |
| Espaço | Venv, dependências e modelo; verificar espaço antes de instalar; não guardar fotos na placa |
| Modelo | `.eim` exportado para ARMv7/AARCH64 conforme diagnóstico, versão e SHA-256 confiáveis |

Não há garantia prévia de que qualquer modelo caiba ou execute a tempo. O Edge Impulse suporta
Raspberry Pi 4, mas o custo depende da arquitetura da rede neural, entrada e quantização.
Critério funcional: completar as 10 inferências e entrega dentro de 60 s; o agente reserva tempo
para upload limitando a coleta/inferência a 45 s. Se falhar, nenhuma liberação é produzida.
O alvo de três segundos é **duração mínima de amostragem**, não promessa de latência.

Executar ensaio de 30 min e registrar latência, uso máximo de memória, CPU, temperatura,
falhas e quedas de desempenho. Não aceitar crescimento de memória sustentado. Se necessário,
otimizar/quantizar ou exportar modelo menor e repetir a calibração; nunca baixar limiar apenas
para disfarçar resultado ruim. Fonte: https://docs.edgeimpulse.com/tools/libraries/sdks/inference/linux

## Rede local, Ethernet/Wi-Fi e internet

O sistema funciona na **mesma rede**: configure `api_url` da Raspberry e `VITE_API_URL` do
dashboard para o mesmo endereço HTTPS alcançável da API, por exemplo `https://epi.instituicao.edu:8001`.
O endereço é ilustrativo e deve ser substituído pelo nome/IP real cujo certificado seja válido.
`localhost` na Raspberry aponta para a própria Raspberry, não para o computador que executa a API.

- Ethernet é preferida no piloto; Wi-Fi usa exatamente o mesmo protocolo.
- Mesmo cabo/rede não garante acesso: VLANs, isolamento Wi-Fi e firewall podem impedir comunicação.
- O responsável pela rede deve autorizar comunicação de saída da Raspberry para a porta HTTPS da
  API e entrada nessa porta no servidor. Não abrir portas na placa nem contornar regras institucionais.
- Certificado deve incluir nome/IP utilizado e ser confiável; CA institucional vai no `ca_bundle`
  do agente. O navegador/Electron também precisa confiar nessa CA conforme política institucional.
- API pode ficar em servidor autorizado na internet se a LAN bloquear comunicação entre clientes.
- Banco e pgAdmin permanecem restritos ao loopback do servidor. Nunca publicar 5432/8080 na rede.

## API e dashboard

- API: Python >=3.10, dependências de `requirements.txt`, PostgreSQL 16 e migrations aplicadas.
- Dashboard: Node.js 22 para desenvolvimento/CI, `npm ci`, `npm run build`; configurar URL da API
  antes do build. A URL não é segredo; **tokens nunca entram em variáveis VITE_***.
- Usar `APP_PROFILE=real`, hashes de tokens distintos de admin/operador, CORS explícito e HTTPS.
- Rodar API com **um worker** neste piloto: prévias/demanda e rate limiting são em memória.
- API precisa de permissão na própria pasta `storage/frames/inspections`, com quota inicial
  500 MB. Quota cheia interrompe novas inspeções; não há exclusão automática.
- Setor ativo, EPIs obrigatórios cadastrados e agente provisionado para aquele setor.
- Credencial de dispositivo expira em no máximo 30 dias, sem acesso administrativo; revogar ao fim.

## Segurança da placa emprestada

Rodar diagnóstico e instalador do repositório apenas como usuário comum. Destino deve ser novo.
Sem sudo automático, alteração do sistema, limpeza, desinstalador ou sobrescrita de arquivos.
Segredos em arquivo privado, fora do Git; modelo sem credenciais de conta. O administrador da placa
pode ler memória/arquivos locais: credencial restrita e revogável limita o impacto.
O SDK usa um diretório temporário de IPC próprio; nosso adaptador encerra apenas seu subprocesso
e preserva esse diretório em vez de executar remoção recursiva. Não há fotos/filas em disco.

## Checklist de liberação do piloto

### Se houver sobrecarga

1. Definir `preview_enabled=false`, ou reduzir `preview_fps`, `preview_width` e `preview_height`
   em `config.json`. A configuração aceita até 2 fps e 640x480; o limiar de EPI não muda.
2. Aumentar `sample_interval_seconds` de 0,34 para até 4 segundos, mantendo dez capturas e prazo
   máximo. Isso diminui a frequência de processamento, mas não acelera inferência individual.
3. Quantizar/reduzir o modelo no Edge Impulse e validar novamente precisão e falsos positivos.
4. Verificar refrigeração/fonte com o responsável, sem alterar frequências do sistema automaticamente.
5. Se ainda inviável, planejar inferência no servidor. **Essa alternativa não está implementada:**
   exigirá novo contrato de frames, processamento servidor e análise de banda/privacidade.

Timeout resulta em falha técnica; nunca baixar a exigência 8/10 para mascarar sobrecarga.

- [ ] Diagnóstico de sistema, RAM, arquitetura, webcam e espaço concluído.
- [ ] Modelo real e mapeamento de classes validados, incluindo pré-processamento do Studio.
- [ ] Conexão HTTPS validada na rede que será usada.
- [ ] Credenciais, setor e EPIs configurados; mock desativado.
- [ ] Testes dos três repositórios aprovados; teste PostgreSQL executado em banco isolado.
- [ ] Ensaio hardware de 30 min e calibração independente concluídos.
- [ ] Testes de perda de rede, câmera ausente, revogação e encerramento confirmados.
- [ ] Responsável ciente de que confiança/concordância temporal não são precisão comprovada.

Veja também [plano](plano-integracao.md), [calibração](calibracao.md) e
[testes e CI](testes.md). Os itens de hardware permanecem pendentes até acesso à placa/modelo.
