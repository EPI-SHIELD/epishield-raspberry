# EPI Shield Raspberry — instruções para agentes

## Contexto e documentação

Agente Python para Raspberry Pi 4/Linux, webcam USB e inferência local Edge Impulse.
Projetos irmãos: `../epi-detection-api` (regras/persistência) e `../epi-dashboard` (operação).
Leia `docs/plano-integracao.md` e `docs/requisitos-sistema.md` antes de mudar a integração;
consulte `docs/testes.md` e `docs/calibracao.md` para validação.

## Preservação da placa emprestada

- A Raspberry pertence a terceiros. Comece por diagnóstico somente leitura.
- Não formatar cartão, reinstalar sistema, apagar arquivos do proprietário, executar limpeza
  recursiva, atualizar pacotes globais ou alterar boot, SSH, firewall e rede automaticamente.
- Instalação somente em pasta nova e exclusiva, como usuário comum, com venv. Recuse destino
  existente; não sobrescreva nem apague uma instalação parcial para tentar novamente.
- Não adicionar sudo, serviço automático, tarefas de boot ou desinstalador destrutivo.
  Dependências/permissões de sistema ausentes devem ser encaminhadas ao responsável pela placa.
- Nenhuma gravação de fotos, vídeo ou filas no disco da placa. Preserve buffers limitados em memória.
- Encerre apenas subprocessos criados pelo agente e libere webcam/IPC ao sair; não use comandos
  globais de encerramento de processos. Preserve o adaptador seguro de encerramento do SDK.
- Não acesse a placa nem implante alterações sem autorização que inclua o dispositivo.

## Arquitetura e contrato

- `epishield/config.py`: valida configuração, HTTPS, credencial e hash do modelo.
- `epishield/camera.py`: único leitor da webcam; guarda somente o frame mais recente.
- `epishield/detector.py`: modelo local, pré-processamento do Studio e normalização de classes/caixas.
- `epishield/agent.py`: busca inspeções, coleta, progresso, heartbeat e reenvio de resultados.
- `scripts/diagnose.py` é somente leitura; `scripts/install.py` escreve apenas na nova instalação
  e usa dependências isoladas. Preserve a lista explícita de arquivos copiados.
- SDK está fixado porque o adaptador depende de detalhes de IPC/encerramento. Ao atualizar,
  inspecione o SDK e teste encerramento/timeout antes de aceitar nova versão.
- Valide arquitetura, SHA-256, classes e saída do `.eim`; não presuma YOLO. Não use classificação
  exclusiva para confirmar vários EPIs. Modelo incompatível impede inspeção.
- Uma pessoa por vez, inspeção manual: dez frames novos após o comando, ao longo de pelo menos
  três segundos; oito confirmações com confiança >=80% por EPI. A API calcula o resultado.
- Erros de captura/inferência não são votos negativos. Não invente frames, duplique capturas,
  reduza o limiar ou marque pessoa liberada por timeout. Confiança não é acurácia medida.
- Guarde só dez listas de detecções e uma foto representativa; reutilize o mesmo payload nos
  reenvios. Não recapture depois de uma entrega de resultado com confirmação incerta.
- Prévia de até 2 fps, sob demanda e pausada durante inspeção; heartbeat 10 s, offline 30 s,
  expiração 60 s. Ajustes de carga devem preservar a regra; consulte requisitos antes de otimizá-la.

## Segurança e rede

- Conexões apenas de saída para HTTPS validado. Não abrir portas/servidor na Raspberry.
- Ethernet e Wi-Fi usam o mesmo endereço configurável. Não contorne isolamento da instituição.
- Credencial privada, restrita ao dispositivo, com expiração/revogação. Nunca levar tokens de
  admin, banco ou conta Edge Impulse à placa; não colocar segredos em URLs/logs/Git.
- Modelo, configuração real e credenciais ficam fora do versionamento. Não desative verificação TLS.

## Trabalho, testes e entrega

- Responda em português. Inspecione status/diff, preserve trabalho existente e use branch `codex/`
  da tarefa; não altere `main` diretamente. Não use reset/clean para descartar arquivos.
- Quando solicitado, commite o trabalho revisado. Push, merge e deploy precisam de autorização aplicável.
- Mudança de contrato requer revisão da API e dashboard, além dos documentos correspondentes.
- Testes sem hardware: instale `requirements-dev.txt` no venv e rode
  `python -m unittest discover -s tests -v`; valide `python -m compileall -q epishield scripts`.
- CI em `.github/workflows/ci.yml` usa Python 3.10/3.12 e doubles de câmera/modelo; não acessa a placa.
- Mudanças documentais exigem revisão de caminhos/comandos e `git diff --check`, sem repetir toda a suíte.
- Relate hardware/modelo indisponíveis como pendência. Não declare compatibilidade ARM, precisão,
  temperatura ou latência reais a partir de mocks. Ensaio real exige webcam/modelo e teste de 30 min.
