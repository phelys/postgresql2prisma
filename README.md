# PostgreSQL to Prisma - Gerador de Schema + Dicionário de Dados com IA

Aplicação web Flask que conecta em bancos de dados PostgreSQL e gera automaticamente arquivos de schema Prisma a partir de tabelas existentes, além de oferecer um assistente de IA para criar dicionários de dados e analisar a estrutura do banco.

## Requisitos

- Python 3.8+
- PostgreSQL (servidor de banco de dados para conectar)
- pip (gerenciador de pacotes Python)
- **Chave de API do Grok (xAI)** (para o recurso de dicionário de dados com IA)

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd postgresql2prisma
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

**Nota**: Se você estiver em um ambiente gerenciado pelo sistema, use um virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. **Configure a chave da API do Grok (xAI)** (necessário para Dicionário de Dados):
```bash
cp .env.example .env
```

Edite o arquivo `.env` e adicione sua chave da API:
```
XAI_API_KEY=sua_chave_api_aqui
```

**Como obter a chave da API:**
- Acesse [https://console.x.ai/](https://console.x.ai/)
- Crie uma conta ou faça login
- Navegue até "API Keys" e crie uma nova chave
- Cole a chave no arquivo `.env`

## Como Rodar

Execute o comando:
```bash
python main.py
```

A aplicação estará disponível em: **http://localhost:5000**

## Liberando a Porta 5000 no Firewall do Ubuntu

Se você precisar acessar a aplicação de outros dispositivos na rede, será necessário liberar a porta 5000 no firewall.

### Usando UFW (Uncomplicated Firewall)

1. Verifique o status do firewall:
```bash
sudo ufw status
```

2. Libere a porta 5000:
```bash
sudo ufw allow 5000/tcp
```

3. Verifique se a regra foi adicionada:
```bash
sudo ufw status numbered
```

4. (Opcional) Se o UFW estiver inativo, ative-o:
```bash
sudo ufw enable
```

### Removendo a regra do firewall (quando não precisar mais)

```bash
sudo ufw delete allow 5000/tcp
```

### Permitir apenas de um IP específico

Para maior segurança, você pode liberar a porta apenas para um IP específico:
```bash
sudo ufw allow from 192.168.1.100 to any port 5000
```

## Como Usar

### 1. Gerador de Schema Prisma

1. Acesse http://localhost:5000 no navegador
2. Preencha as credenciais do banco de dados PostgreSQL:
   - Host
   - Port
   - Database
   - User
   - Password
3. Clique em "Conectar"
4. Na aba **"Gerador de Schema"**:
   - Selecione as tabelas que deseja gerar o schema Prisma
   - Escolha o formato de saída:
     - **Arquivo separado para cada tabela (ZIP)**: Um arquivo para cada tabela
     - **Arquivo único com todas as tabelas**: Todos os models em um único arquivo `.prisma`
5. Clique em "Gerar e Baixar Schemas"

### 2. Dicionário de Dados com IA 💡 **NOVO**

1. Após conectar ao banco, clique na aba **"Dicionário de Dados (IA)"**
2. **Selecione os Schemas** que deseja analisar
3. Clique em **"Iniciar Análise"**
4. **Converse com a IA** sobre sua estrutura de banco de dados:

   **Exemplos de perguntas:**
   - "Explique o propósito deste banco de dados"
   - "Quais são os relacionamentos entre as tabelas?"
   - "Para que serve a tabela users?"
   - "Que tipo de sistema usa essa estrutura?"
   - "Sugira melhorias para este schema"
   - "Explique todos os campos da tabela X"
   - "Como essas tabelas se relacionam?"

5. A IA fornecerá:
   - Análise detalhada da estrutura
   - Explicação de schemas, tabelas e campos
   - Identificação de relacionamentos (foreign keys)
   - Propósitos e casos de uso
   - Sugestões de melhorias
   - Padrões de design identificados

## Funcionalidades

### Gerador de Schema Prisma
- ✅ Conexão com bancos PostgreSQL
- ✅ Listagem de schemas e tabelas
- ✅ Geração automática de models Prisma
- ✅ Detecção de chaves primárias
- ✅ Mapeamento de tipos PostgreSQL → Prisma
- ✅ Suporte a múltiplos schemas
- ✅ Detecção de valores padrão (auto-increment, timestamps)
- ✅ Persistência de configurações de conexão
- ✅ Exportação em arquivo único ou múltiplos arquivos (ZIP)

### Dicionário de Dados com IA 💡
- ✅ Chat interativo com Grok AI (xAI)
- ✅ Análise automática de estrutura de banco de dados
- ✅ Extração completa de metadados:
  - Schemas, tabelas e colunas
  - Chaves primárias e estrangeiras
  - Índices e constraints
  - Relacionamentos entre tabelas
- ✅ Explicação inteligente de propósitos e casos de uso
- ✅ Identificação de padrões de design
- ✅ Sugestões de melhorias
- ✅ Conversação contextual (histórico mantido)
- ✅ Respostas em português brasileiro

## Mapeamento de Tipos

| PostgreSQL | Prisma |
|------------|--------|
| integer, int4, serial | Int |
| bigint, int8, bigserial | BigInt |
| real, float4 | Float |
| double precision, float8 | Float |
| numeric, decimal | Decimal |
| varchar, text, char, etc. | String |
| timestamp, date, time | DateTime |
| boolean, bool | Boolean |
| json, jsonb | Json |
| uuid | String |
| bytea | Bytes |

## Estrutura do Projeto

```
postgresql2prisma/
├── main.py              # Aplicação Flask completa (backend + frontend)
├── requirements.txt     # Dependências Python
├── .env.example        # Exemplo de configuração de variáveis de ambiente
├── .env                # Variáveis de ambiente (criar manualmente)
├── db_config.json      # Configurações de conexão (auto-gerado)
└── README.md           # Este arquivo
```

## Tecnologias Utilizadas

### Backend
- **Flask**: Framework web Python
- **psycopg2**: Driver PostgreSQL
- **OpenAI SDK**: Integração com Grok AI (xAI) via formato OpenAI-compatible
- **python-dotenv**: Gerenciamento de variáveis de ambiente

### Frontend
- **Tailwind CSS**: Framework CSS (via CDN)
- **Vanilla JavaScript**: Sem frameworks adicionais
- **Fetch API**: Comunicação com backend

### IA
- **Grok 3**: Modelo de linguagem da xAI
- **Max Tokens**: 4096 por resposta
- **Temperature**: 0.7
- **Contexto**: Estrutura completa do banco de dados
- **API**: Formato OpenAI-compatible (https://api.x.ai/v1)

## Troubleshooting

### Erro de conexão com PostgreSQL
- Verifique se as credenciais estão corretas
- Confirme que o PostgreSQL está rodando
- Verifique se o firewall do servidor PostgreSQL permite conexões

### "Serviço de IA não disponível" ou erro 503
- Verifique se o arquivo `.env` existe na raiz do projeto
- Confirme que contém a variável `XAI_API_KEY=sua_chave_aqui`
- Verifique se a chave da API é válida (teste em https://console.x.ai/)
- Reinicie a aplicação após configurar o `.env`
- Verifique os logs no terminal para mensagens de erro

### "XAI_API_KEY não encontrada"
O recurso de dicionário de dados ficará desabilitado se a chave não for configurada:
```bash
# Verifique se o arquivo .env existe
ls -la .env

# Crie o arquivo se não existir
cp .env.example .env

# Edite e adicione sua chave
nano .env
```

### Pacotes Python não instalados
Se você receber erro sobre ambiente gerenciado externamente:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python main.py
```

### Porta 5000 já em uso
Altere a porta no final do arquivo `main.py` ou mate o processo que está usando a porta:
```bash
sudo lsof -ti:5000 | xargs kill -9
```

### Chat não responde / Timeout
- Verifique sua conexão com a internet
- Confirme que sua conta xAI tem créditos disponíveis
- Bancos de dados muito grandes podem gerar contextos grandes - tente selecionar menos schemas

## Licença

[Adicione a licença do projeto aqui]
