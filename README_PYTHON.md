# SuinoTech - Sistema de Gestão para Granja de Suínos (Python)

Sistema completo para gestão de granja de suínos, com suporte a PWA (instalação como app no celular).

## Funcionalidades Principais

✅ **Matrizes**: Cadastro completo de leitoas e porcas  
✅ **Partos**: Registro detalhado de partos (nascidos vivos, mortos, mumificados)  
✅ **Lotes**: Organização por fases (Maternidade, Creche, Recria, Terminação)  
✅ **Suínos**: Cadastro com sexo (Macho, Fêmea, Irrelevante), lote e matriz  
✅ **Pesagens**: Histórico de pesagens por animal  
✅ **Ração**: Controle de estoque, preço e validade  
✅ **Saúde**: Registro de vacinações, tratamentos e consultas  
✅ **Relatórios**: Estatísticas e exportação para CSV  
✅ **PWA**: Instale como app no celular!

## Como Instalar e Rodar

### 1. Instale o Python
Baixe e instale o Python (versão 3.8 ou superior): https://www.python.org/downloads/  
**IMPORTANTE**: Marque a opção "Add Python to PATH" durante a instalação!

### 2. Instale o Flask
Abra o Prompt de Comando (CMD) ou PowerShell e digite:
```bash
pip install flask
```

### 3. Rode o Sistema
Navegue até a pasta do projeto e execute:
```bash
cd C:\Users\Joe Santos\Desktop\MATRIZES
py main.py
```
Ou se `py` não funcionar:
```bash
python main.py
```

### 4. Acesse no Navegador
Abra o navegador e digite: http://localhost:5000

## Como Instalar como App (PWA)

1. Acesse o sistema no Chrome ou Edge
2. Clique no ícone de "Instalar aplicativo" na barra de endereço
3. Pronto! O app aparecerá na sua tela inicial

## Estrutura do Projeto

```
MATRIZES/
├── main.py                  # Arquivo principal (sistema todo aqui!)
├── suinotech.db            # Banco de dados SQLite (gerado automaticamente)
├── requirements.txt        # Dependências Python
├── templates/              # Páginas HTML
│   ├── base.html
│   ├── dashboard.html
│   ├── matrizes.html
│   ├── form_matriz.html
│   ├── partos.html
│   ├── form_parto.html
│   ├── lotes.html
│   ├── form_lote.html
│   ├── suinos.html
│   ├── form_suino.html
│   ├── pesagens.html
│   ├── racao.html
│   ├── form_racao.html
│   ├── saude.html
│   ├── form_saude.html
│   └── relatorios.html
└── static/                 # Arquivos do PWA
    ├── manifest.json
    └── service-worker.js
```

## Banco de Dados

O banco de dados SQLite (`suinotech.db`) é criado automaticamente na primeira execução, com todas as tabelas necessárias.

## Dúvidas?

Se precisar de ajuda, é só perguntar!
