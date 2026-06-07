# SuinoTech - Sistema para Granja de Suínos

Sistema completo para gestão de granja de suínos com suporte a funcionamento offline (PWA).

## Funcionalidades

- 🐷 Controle de suínos (cadastro, edição, remoção)
- 🌾 Gestão de estoque de ração
- 💊 Registros de saúde e vacinação
- 📊 Relatórios e estatísticas
- 📱 Funciona offline (PWA)
- 🔄 Sincronização automática quando online

## Tecnologias

- **Backend**: Node.js + Express + SQLite
- **Frontend**: React + React Router
- **Offline**: PWA + LocalForage

## Instalação

1. Instale as dependências:
```bash
npm run install:all
```

2. Inicie o sistema:
```bash
npm run dev
```

Isso iniciará:
- Backend em http://localhost:3001
- Frontend em http://localhost:3000

## Como Usar

### Dashboard
- Visualize estatísticas rápidas da granja
- Acesse ações rápidas

### Suínos
- Cadastre novos suínos com identificação única
- Registre peso, sexo, data de nascimento
- Acompanhe o status (ativo, vendido, morto)

### Ração
- Gerencie o estoque de ração
- Controle validade e fornecedores

### Saúde
- Registre vacinações, tratamentos e consultas
- Acompanhe o histórico veterinário

### Relatórios
- Visualize estatísticas completas
- Exporte dados para CSV

## Offline First

O sistema funciona mesmo sem internet:
- Dados são armazenados localmente
- Quando a conexão volta, as alterações são sincronizadas
- Instale como app no celular (PWA)

## Estrutura do Projeto

```
MATRIZES/
├── backend/
│   ├── server.js          # Servidor Express
│   ├── package.json
│   └── suinotech.db       # Banco SQLite (gerado automaticamente)
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   ├── manifest.json  # Config PWA
│   │   └── service-worker.js
│   ├── src/
│   │   ├── App.js         # Aplicativo principal
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
└── package.json
```
