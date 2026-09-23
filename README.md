# EPI Shield — Raspberry Pi 4

Agente manual para webcam USB, inferência local Edge Impulse e envio HTTPS à API.
[Plano aprovado](docs/plano-integracao.md). Uma pessoa por vez, sem controlar portas.

## Antes de instalar

Execute `python3 scripts/diagnose.py`. Este comando apenas lê informações do sistema.
Confirme Linux ARM, Python >= 3.10, espaço disponível e permissão da webcam.
Não há formatação, sudo, limpeza, serviço, alteração de rede/SSH/boot ou dependência global automática.
Se faltar Python/venv, biblioteca nativa ou permissão da câmera, peça ao responsável pela placa.
Não execute recomendações antigas de reinstalação ou atualização geral do sistema.

Instale em uma pasta que **ainda não existe**, fora deste checkout:

```sh
python3 scripts/install.py "$HOME/epishield-piloto"
```

O instalador cria somente essa pasta, copia uma lista explícita de arquivos e usa venv e wheels
sem cache pip. A exceção é o SDK Python Edge Impulse 1.2.2, publicado como código-fonte Python.
Se não houver wheel compatível para dependências nativas, ele para, preservando a pasta parcial e todos os
arquivos anteriores. Não inclui rotina de remoção. Não execute como root.

## Modelo e configuração

Em computador confiável, exporte o modelo do Edge Impulse para Linux EIM da arquitetura
identificada (ARMv7/AARCH64). Verifique origem, versão e SHA-256 antes de transferir.
O `.eim` é um executável: o hash comprova integridade em relação ao valor confiável, não autoria.
Não transfira token de conta Edge Impulse, banco ou administração para a placa.

Crie `config.json` manualmente a partir de `config.example.json`, sem sobrescrever arquivo existente.
Configure URL HTTPS, token da placa, modelo e mapeamento de classes. O token deve estar em arquivo
privado (0600 em Linux), fora do Git. A API provisiona um token com validade máxima de 30 dias.
`ca_bundle` aponta para CA institucional fornecida pelo responsável; nunca desabilite TLS.

O agente usa o pré-processamento registrado no Studio. Reexporte modelos sem `image_resize_mode`.
Saídas suportadas: `bounding_boxes`, ou `classification` multilabel validada explicitamente;
classificação exclusiva não permite confirmar vários equipamentos simultaneamente. Classes não
mapeadas são ignoradas; todos os EPIs obrigatórios precisam estar no mapeamento.

```sh
cd "$HOME/epishield-piloto"
.venv/bin/python -m epishield.agent --config config.json
```

Uma inferência inicial verifica o formato antes de anunciar disponibilidade. Ctrl+C encerra e
libera webcam/runner. Nenhuma foto, vídeo, fila ou log é gravado pelo agente em disco.

## Inspeção e rede

O operador abre a câmera no dashboard, mantém **a mesma pessoa** enquadrada durante a sequência
e clica em Inspecionar. Cada EPI precisa atingir 8/10 capturas com confiança >=80%, em pelo menos
3 segundos. API decide; não há média entre equipamentos. Confiança não significa precisão medida.
Foto ilustrativa é o frame processado pelo modelo com menos EPIs confirmados; prévia é separada.

Ethernet e Wi-Fi usam o mesmo cliente HTTPS. A placa não abre portas. Se a rede institucional
isolar clientes, solicite um endpoint autorizado acessível a ambos ou servidor HTTPS externo.
Não configure túneis ou bypass de firewall. Não há acesso direto do dashboard à placa.
Prévia só é enviada enquanto solicitada, até 2 fps, pausando para priorizar inspeções.

Uma solicitação pode expirar em 60 s. Reenvios usam a mesma evidência; perda após reinício pode
causar expiração. Falha técnica não vira ausência de EPI. Relógio de captura é ajustado por offset
da API sem alterar o relógio do sistema. No fim do empréstimo, revogue a credencial na API.

## Validação pendente de hardware

Execute testes com `python3 -m unittest discover -s tests`. Consulte
[protocolo de calibração](docs/calibracao.md). Testes sintéticos não validam acurácia real.
