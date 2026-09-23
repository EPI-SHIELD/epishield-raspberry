# Testes do sistema e CI

## Execução local

No repositório da API:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

O teste real de PostgreSQL exige `TEST_DATABASE_URL` apontando para banco exclusivo cujo nome
começa com `epi_test_`. Ele cria schema aleatório dentro de transação e faz rollback de suas
próprias mudanças; nunca usa `DB_URL` nem o banco da aplicação. Sem a variável, esse teste é
marcado como skipped, não como aprovado. Não execute contra banco real.

No dashboard:

```sh
npm ci
npm test
npm run build
```

No repositório Raspberry (sem webcam/modelo para os testes automatizados):

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Use ambientes virtuais locais. No Windows, se pytest não puder escrever no TEMP, crie uma pasta
de testes dentro do checkout e passe `--basetemp` com subpasta nova por execução.

## Cobertura funcional

| Camada | Cenários |
|---|---|
| Regra API | 0,80 conta; 8/10 confirma; 7/10 bloqueia; duplicatas; equipamentos independentes |
| Evidências | Tempo, sequência, capturas anteriores, lote incompleto, confiança/caixa inválidas |
| Segurança | TLS, tokens, escopos, revogação/expiração, isolamento e mock bloqueado |
| Mídia | JPEG inválido, limites/quota, preservação de arquivos, demanda/expiração de prévia |
| PostgreSQL | Migrations, solicitação, snapshot dos EPIs, persistência, reenvio e fotos autenticadas |
| Raspberry | Mapeamento, coleta de 10 capturas, foto representativa, reenvios, TLS e instalação segura |
| Dashboard | Credencial em memória, chamadas autenticadas, login, progresso e resultado por EPI |

CI em cada repositório executa em push/PR, com `contents: read`, sem segredos de produção e sem
deploy. API usa serviço PostgreSQL 16 descartável; agente usa doubles de hardware; dashboard
executa testes e build. Os workflows só rodarão no GitHub após envio das branches.

## O que CI não comprova

Compatibilidade ARM do artefato real, driver da webcam, acesso da rede institucional, temperatura,
consumo de RAM na placa e precisão do modelo. Esses testes estão no protocolo de calibração e
exigem hardware real. Testes de tela usam API simulada; teste PostgreSQL usa as rotas reais da API.
